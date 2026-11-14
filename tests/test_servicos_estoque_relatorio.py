"""Testes de aceitação dos serviços de estoque, relatório e login."""

from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Barrier

import pytest

from app.core.exceptions import (
    CapacidadeExcedidaError,
    ConfiguracaoIndisponivelError,
    CredenciaisInvalidasError,
    EstadoInvalidoError,
    OperacaoInvalidaError,
    PersistenciaError,
)
from app.repositories.database import inicializar
from app.services import estoque_service, operador_service, relatorio_service

ITENS_ESPERADOS = ["agua", "cafe", "leite", "chocolate", "acucar", "copos"]


@pytest.fixture
def banco(tmp_path, monkeypatch):
    """Inicializa um banco isolado pelas rotinas administrativas reais."""
    caminho = tmp_path / "operador.db"
    monkeypatch.setenv("DATABASE_PATH", str(caminho))
    inicializar(caminho)
    return caminho


def _configurar_manutencao(banco, estado="MANUTENCAO"):
    with sqlite3.connect(banco) as conexao:
        conexao.execute("UPDATE maquina SET estado = ? WHERE id = 1", (estado,))


def _configurar_agua(banco, quantidade):
    with sqlite3.connect(banco) as conexao:
        conexao.execute(
            "UPDATE ingrediente SET quantidade_atual = ? WHERE codigo = 'AGUA'", (quantidade,)
        )


def _contar(banco, tabela):
    with sqlite3.connect(banco) as conexao:
        return conexao.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]


def _inserir_pedido(banco, pedido_id, produto_id, preco, status, criado_em):
    with sqlite3.connect(banco) as conexao:
        conexao.execute(
            "INSERT INTO pedido VALUES (?, ?, 0, ?, ?, ?, ?)",
            (pedido_id, produto_id, preco, status, criado_em, criado_em),
        )


# --------------------------------------------------------------------------- #
# RN09 – consulta de estoque
# --------------------------------------------------------------------------- #
def test_consulta_estoque_mapeia_seis_itens_em_ordem_sem_escrever(banco):
    with sqlite3.connect(banco) as conexao:
        antes = conexao.execute(
            "SELECT id, quantidade_atual, capacidade_maxima, nivel_alerta FROM ingrediente ORDER BY id"
        ).fetchall()
        maquina_antes = conexao.execute(
            "SELECT estado, credito, preparos_desde_limpeza FROM maquina"
        ).fetchone()

    estoque = estoque_service.consultar_estoque()

    assert [item["item"] for item in estoque["reservatorios"]] == ITENS_ESPERADOS
    assert estoque["reservatorios"] == [
        {"item": "agua", "atual": 2000, "capacidade": 2000, "nivel_baixo": False},
        {"item": "cafe", "atual": 500, "capacidade": 500, "nivel_baixo": False},
        {"item": "leite", "atual": 1000, "capacidade": 1000, "nivel_baixo": False},
        {"item": "chocolate", "atual": 400, "capacidade": 400, "nivel_baixo": False},
        {"item": "acucar", "atual": 300, "capacidade": 300, "nivel_baixo": False},
        {"item": "copos", "atual": 50, "capacidade": 50, "nivel_baixo": False},
    ]
    with sqlite3.connect(banco) as conexao:
        assert (
            conexao.execute(
                "SELECT id, quantidade_atual, capacidade_maxima, nivel_alerta FROM ingrediente ORDER BY id"
            ).fetchall()
            == antes
        )
        assert (
            conexao.execute(
                "SELECT estado, credito, preparos_desde_limpeza FROM maquina"
            ).fetchone()
            == maquina_antes
        )
        assert conexao.execute("SELECT COUNT(*) FROM reabastecimento").fetchone()[0] == 0


def test_alerta_de_nivel_inclui_igualdade_ao_limite(banco):
    with sqlite3.connect(banco) as conexao:
        conexao.execute(
            "UPDATE ingrediente SET quantidade_atual = nivel_alerta WHERE codigo = 'AGUA'"
        )
        conexao.execute(
            "UPDATE ingrediente SET quantidade_atual = nivel_alerta + 1 WHERE codigo = 'LEITE'"
        )

    itens = {item["item"]: item for item in estoque_service.consultar_estoque()["reservatorios"]}

    assert itens["agua"]["nivel_baixo"] is True
    assert itens["leite"]["nivel_baixo"] is False


def test_estoque_http_com_banco_real(banco, client):
    resposta = client.get("/operador/estoque", headers={"Authorization": "Bearer test-token"})

    assert resposta.status_code == 200
    assert [item["item"] for item in resposta.json()["reservatorios"]] == ITENS_ESPERADOS


# --------------------------------------------------------------------------- #
# RN09 – reabastecimento
# --------------------------------------------------------------------------- #
def test_reabastecimento_sucesso_persiste_e_audita(banco):
    _configurar_manutencao(banco)
    _configurar_agua(banco, 1800)

    resultado = estoque_service.reabastecer("agua", 100)

    assert resultado == {
        "item": {"item": "agua", "atual": 1900, "capacidade": 2000, "nivel_baixo": False}
    }
    with sqlite3.connect(banco) as conexao:
        assert (
            conexao.execute(
                "SELECT quantidade_atual FROM ingrediente WHERE codigo = 'AGUA'"
            ).fetchone()[0]
            == 1900
        )
        ingrediente_id, quantidade, criado_em = conexao.execute(
            "SELECT ingrediente_id, quantidade, criado_em FROM reabastecimento"
        ).fetchone()
        assert (ingrediente_id, quantidade) == (1, 100)
        assert criado_em is not None
        assert conexao.execute(
            "SELECT estado, credito, preparos_desde_limpeza FROM maquina"
        ).fetchone() == ("MANUTENCAO", 0, 0)
        assert conexao.execute("SELECT COUNT(*) FROM limpeza").fetchone()[0] == 0
        assert conexao.execute("PRAGMA foreign_key_check").fetchall() == []


def test_reabastecimento_reabre_confirmando_dados(banco):
    _configurar_manutencao(banco)
    _configurar_agua(banco, 1800)
    estoque_service.reabastecer("agua", 100)

    with sqlite3.connect(banco) as conexao:
        assert (
            conexao.execute(
                "SELECT quantidade_atual FROM ingrediente WHERE codigo = 'AGUA'"
            ).fetchone()[0]
            == 1900
        )
        assert (
            conexao.execute(
                "SELECT quantidade FROM reabastecimento WHERE ingrediente_id = 1"
            ).fetchone()[0]
            == 100
        )
        assert conexao.execute("PRAGMA foreign_key_check").fetchall() == []


def test_reabastecimento_atinge_capacidade_exata(banco):
    _configurar_manutencao(banco)
    _configurar_agua(banco, 1900)

    resultado = estoque_service.reabastecer("agua", 100)

    assert resultado["item"]["atual"] == 2000
    assert resultado["item"]["nivel_baixo"] is False


def test_reabastecimento_acima_da_capacidade_nao_altera_dados(banco):
    _configurar_manutencao(banco)
    _configurar_agua(banco, 1900)

    with pytest.raises(CapacidadeExcedidaError):
        estoque_service.reabastecer("agua", 101)

    with sqlite3.connect(banco) as conexao:
        assert (
            conexao.execute(
                "SELECT quantidade_atual FROM ingrediente WHERE codigo = 'AGUA'"
            ).fetchone()[0]
            == 1900
        )
        assert conexao.execute("SELECT COUNT(*) FROM reabastecimento").fetchone()[0] == 0


@pytest.mark.parametrize(
    "quantidade",
    [0, -1, 0.5, 1.25, float("nan"), float("inf"), float("-inf"), True, "10", None],
)
def test_reabastecimento_recusa_quantidade_invalida(banco, quantidade):
    _configurar_manutencao(banco)
    _configurar_agua(banco, 1800)

    with pytest.raises(OperacaoInvalidaError):
        estoque_service.reabastecer("agua", quantidade)

    with sqlite3.connect(banco) as conexao:
        assert (
            conexao.execute(
                "SELECT quantidade_atual FROM ingrediente WHERE codigo = 'AGUA'"
            ).fetchone()[0]
            == 1800
        )
        assert conexao.execute("SELECT COUNT(*) FROM reabastecimento").fetchone()[0] == 0


@pytest.mark.parametrize("item", ["", "AGUA", "desconhecido", None])
def test_reabastecimento_recusa_item_invalido(banco, item):
    _configurar_manutencao(banco)

    with pytest.raises(OperacaoInvalidaError):
        estoque_service.reabastecer(item, 10)


@pytest.mark.parametrize("estado", ["PRONTA", "PREPARANDO", "AGUARDANDO_LIMPEZA"])
def test_reabastecimento_exige_manutencao(banco, estado):
    _configurar_manutencao(banco, estado)
    _configurar_agua(banco, 1800)

    with pytest.raises(EstadoInvalidoError):
        estoque_service.reabastecer("agua", 10)

    with sqlite3.connect(banco) as conexao:
        assert (
            conexao.execute(
                "SELECT quantidade_atual FROM ingrediente WHERE codigo = 'AGUA'"
            ).fetchone()[0]
            == 1800
        )
        assert conexao.execute("SELECT COUNT(*) FROM reabastecimento").fetchone()[0] == 0


def test_falha_na_auditoria_reverte_estoque(banco):
    _configurar_manutencao(banco)
    _configurar_agua(banco, 1800)
    with sqlite3.connect(banco) as conexao:
        conexao.execute(
            "CREATE TRIGGER falhar_reabastecimento BEFORE INSERT ON reabastecimento "
            "BEGIN SELECT RAISE(ABORT, 'falha simulada'); END"
        )

    with pytest.raises(PersistenciaError):
        estoque_service.reabastecer("agua", 100)

    with sqlite3.connect(banco) as conexao:
        assert (
            conexao.execute(
                "SELECT quantidade_atual FROM ingrediente WHERE codigo = 'AGUA'"
            ).fetchone()[0]
            == 1800
        )
        assert conexao.execute("SELECT COUNT(*) FROM reabastecimento").fetchone()[0] == 0


def test_duas_reposicoes_concorrentes_nao_excedem_capacidade(banco):
    _configurar_manutencao(banco)
    _configurar_agua(banco, 1900)
    barreira = Barrier(2)

    def repor():
        barreira.wait(timeout=5)
        try:
            estoque_service.reabastecer("agua", 100)
            return "ok"
        except CapacidadeExcedidaError:
            return "excedida"

    with ThreadPoolExecutor(max_workers=2) as executor:
        resultados = list(executor.map(lambda _: repor(), range(2)))

    assert sorted(resultados) == ["excedida", "ok"]
    with sqlite3.connect(banco) as conexao:
        assert (
            conexao.execute(
                "SELECT quantidade_atual FROM ingrediente WHERE codigo = 'AGUA'"
            ).fetchone()[0]
            == 2000
        )
        assert conexao.execute("SELECT COUNT(*) FROM reabastecimento").fetchone()[0] == 1


def test_reposicoes_concorrentes_geram_ids_de_auditoria_unicos(banco):
    _configurar_manutencao(banco)
    with sqlite3.connect(banco) as conexao:
        conexao.execute("UPDATE ingrediente SET quantidade_atual = 1")
    itens = ["agua", "cafe", "leite", "chocolate"]
    barreira = Barrier(len(itens))

    def repor(item):
        barreira.wait(timeout=5)
        estoque_service.reabastecer(item, 1)

    with ThreadPoolExecutor(max_workers=len(itens)) as executor:
        list(executor.map(repor, itens))

    with sqlite3.connect(banco) as conexao:
        assert conexao.execute(
            "SELECT COUNT(*), COUNT(DISTINCT id) FROM reabastecimento"
        ).fetchone() == (4, 4)


def test_reabastecimento_http_com_banco_real(banco, client):
    _configurar_manutencao(banco)
    _configurar_agua(banco, 1800)

    resposta = client.post(
        "/operador/estoque/reabastecer",
        headers={"Authorization": "Bearer test-token"},
        json={"item": "agua", "quantidade": 100},
    )

    assert resposta.status_code == 200
    assert resposta.json() == {
        "item": {"item": "agua", "atual": 1900, "capacidade": 2000, "nivel_baixo": False}
    }
    assert _contar(banco, "reabastecimento") == 1


@pytest.mark.parametrize("quantidade", [0.5, 1.25, True, "10", 0, -1])
def test_reabastecimento_http_recusa_quantidade_invalida(banco, client, quantidade):
    _configurar_manutencao(banco)
    _configurar_agua(banco, 1800)

    resposta = client.post(
        "/operador/estoque/reabastecer",
        headers={"Authorization": "Bearer test-token"},
        json={"item": "agua", "quantidade": quantidade},
    )

    assert resposta.status_code == 400
    assert _contar(banco, "reabastecimento") == 0


# --------------------------------------------------------------------------- #
# RN12 – relatório
# --------------------------------------------------------------------------- #
def test_relatorio_sem_vendas_retorna_zero_e_lista_vazia(banco):
    inicio = datetime(2026, 3, 1)
    fim = datetime(2026, 3, 31, 23, 59, 59)

    relatorio = relatorio_service.gerar_relatorio(inicio, fim)

    assert relatorio == {
        "inicio": inicio,
        "fim": fim,
        "total_pedidos": 0,
        "faturamento_total": 0,
        "por_bebida": [],
    }


def test_relatorio_consolida_concluidos_e_exclui_demais_status(banco):
    _inserir_pedido(banco, 1, 1, 4.00, "CONCLUIDO", "2026-03-01T00:00:00")
    _inserir_pedido(banco, 2, 1, 4.50, "CONCLUIDO", "2026-03-15T10:00:00")
    _inserir_pedido(banco, 3, 4, 6.50, "CONCLUIDO", "2026-03-31T23:59:59")
    _inserir_pedido(banco, 4, 4, 6.50, "EM_PREPARO", "2026-03-10T10:00:00")
    _inserir_pedido(banco, 5, 4, 6.50, "CANCELADO", "2026-03-10T10:00:00")
    _inserir_pedido(banco, 6, 2, 4.50, "CONCLUIDO", "2026-02-28T23:59:59")
    _inserir_pedido(banco, 7, 2, 4.50, "CONCLUIDO", "2026-04-01T00:00:00")

    relatorio = relatorio_service.gerar_relatorio(
        datetime(2026, 3, 1), datetime(2026, 3, 31, 23, 59, 59)
    )

    assert relatorio["total_pedidos"] == 3
    assert relatorio["faturamento_total"] == 15.00
    assert relatorio["por_bebida"] == [
        {"produto_id": 1, "nome": "Café expresso", "quantidade": 2, "faturamento": 8.50},
        {"produto_id": 4, "nome": "Cappuccino", "quantidade": 1, "faturamento": 6.50},
    ]


def test_relatorio_usa_preco_historico_apos_alterar_preco_atual(banco):
    _inserir_pedido(banco, 1, 1, 4.00, "CONCLUIDO", "2026-03-10T10:00:00")
    with sqlite3.connect(banco) as conexao:
        conexao.execute("UPDATE produto SET preco_centavos = 999 WHERE id = 1")

    relatorio = relatorio_service.gerar_relatorio(
        datetime(2026, 3, 1), datetime(2026, 3, 31, 23, 59, 59)
    )

    assert relatorio["faturamento_total"] == 4.00
    assert relatorio["por_bebida"][0]["faturamento"] == 4.00


def test_relatorio_soma_centavos_sem_erro_de_float(banco):
    _inserir_pedido(banco, 1, 1, 0.10, "CONCLUIDO", "2026-03-10T10:00:00")
    _inserir_pedido(banco, 2, 1, 0.20, "CONCLUIDO", "2026-03-10T10:01:00")

    relatorio = relatorio_service.gerar_relatorio(
        datetime(2026, 3, 1), datetime(2026, 3, 31, 23, 59, 59)
    )

    assert relatorio["faturamento_total"] == 0.30
    assert relatorio["por_bebida"][0]["faturamento"] == 0.30


def test_relatorio_recusa_preco_historico_sem_centavos_exatos(banco):
    _inserir_pedido(banco, 1, 1, 0.001, "CONCLUIDO", "2026-03-10T10:00:00")

    with pytest.raises(PersistenciaError):
        relatorio_service.gerar_relatorio(datetime(2026, 3, 1), datetime(2026, 3, 31, 23, 59, 59))


def test_relatorio_normaliza_timezone(banco):
    _inserir_pedido(banco, 1, 1, 4.00, "CONCLUIDO", "2026-03-01T01:00:00+00:00")
    _inserir_pedido(banco, 2, 1, 4.00, "CONCLUIDO", "2026-03-01T00:30:00")

    relatorio = relatorio_service.gerar_relatorio(
        datetime(2026, 2, 28, 22, 0, tzinfo=timezone.utc),
        datetime(2026, 3, 1, 1, 0, tzinfo=timezone.utc),
    )

    assert relatorio["total_pedidos"] == 2


def test_relatorio_periodo_invertido_e_tipos_invalidos(banco):
    with pytest.raises(OperacaoInvalidaError):
        relatorio_service.gerar_relatorio(datetime(2026, 3, 2), datetime(2026, 3, 1))
    with pytest.raises(OperacaoInvalidaError):
        relatorio_service.gerar_relatorio("2026-03-01", datetime(2026, 3, 1))


def test_relatorio_http_com_banco_real(banco, client):
    _inserir_pedido(banco, 1, 1, 4.00, "CONCLUIDO", "2026-03-10T10:00:00")

    resposta = client.get(
        "/operador/relatorio",
        headers={"Authorization": "Bearer test-token"},
        params={"inicio": "2026-03-01T00:00:00", "fim": "2026-03-31T23:59:59"},
    )

    assert resposta.status_code == 200
    assert resposta.json()["total_pedidos"] == 1
    assert resposta.json()["faturamento_total"] == 4.00


# --------------------------------------------------------------------------- #
# RN11 – login
# --------------------------------------------------------------------------- #
def test_login_aceita_credenciais_e_token_no_bearer(banco, client):
    token = operador_service.autenticar("operador", "senha-teste")

    resposta = client.get("/operador/estoque", headers={"Authorization": f"Bearer {token}"})

    assert resposta.status_code == 200


@pytest.mark.parametrize(("usuario", "senha"), [("operador", "errada"), ("outro", "senha-teste")])
def test_login_recusa_credenciais_incorretas(banco, usuario, senha):
    with pytest.raises(CredenciaisInvalidasError, match="Usuário ou senha inválidos."):
        operador_service.autenticar(usuario, senha)


@pytest.mark.parametrize(("usuario", "senha"), [("", "senha-teste"), ("operador", ""), (None, "x")])
def test_login_recusa_campos_vazios_em_chamada_direta(banco, usuario, senha):
    with pytest.raises(CredenciaisInvalidasError):
        operador_service.autenticar(usuario, senha)


@pytest.mark.parametrize("variavel", ["OPERATOR_USER", "OPERATOR_PASSWORD", "OPERATOR_TOKEN"])
def test_login_configuracao_ausente_nao_expoe_valores(banco, client, monkeypatch, variavel):
    monkeypatch.delenv(variavel)

    with pytest.raises(ConfiguracaoIndisponivelError):
        operador_service.autenticar("operador", "senha-teste")

    resposta = client.post("/operador/login", json={"usuario": "operador", "senha": "senha-teste"})

    assert resposta.status_code == 503
    assert resposta.json()["erro"] == "SERVICO_INDISPONIVEL"
    assert "test-token" not in resposta.text
    assert "senha-teste" not in resposta.text


def test_login_http_sucesso_e_erro(banco, client):
    sucesso = client.post("/operador/login", json={"usuario": "operador", "senha": "senha-teste"})
    erro = client.post("/operador/login", json={"usuario": "operador", "senha": "errada"})

    assert sucesso.status_code == 200
    assert sucesso.json() == {"token": "test-token", "tipo": "bearer"}
    assert erro.status_code == 401
    assert erro.json()["erro"] == "NAO_AUTORIZADO"
    assert erro.json()["mensagem"] == "Usuário ou senha inválidos."


def test_inicializacao_falha_nao_deixa_arquivo_parcial(tmp_path, monkeypatch):
    from app.repositories import database

    caminho = tmp_path / "parcial.db"
    monkeypatch.setattr(database, "RAIZ", tmp_path / "inexistente")

    with pytest.raises(FileNotFoundError):
        database.inicializar(caminho)

    assert not caminho.exists()


def test_startup_exige_credenciais(banco, monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import app

    monkeypatch.delenv("OPERATOR_PASSWORD")

    with pytest.raises(RuntimeError, match="OPERATOR_PASSWORD"), TestClient(app):
        pass
