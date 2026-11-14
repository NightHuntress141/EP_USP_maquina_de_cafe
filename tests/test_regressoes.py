"""Regressões de segurança, precisão, inicialização e concorrência."""

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import origens_cors, timeout_banco
from app.core.exceptions import (
    BancoIndisponivelError,
    EstadoInvalidoError,
    OperacaoInvalidaError,
)
from app.main import app
from app.repositories.database import inicializar, migrar
from app.repositories.operador_repository import transacao, validar_banco
from app.schemas.credito import CreditoRequest
from app.schemas.estoque import ReabastecimentoRequest
from app.services import operador_service, produto_service


@pytest.fixture
def banco(tmp_path, monkeypatch):
    """Cria um banco novo com as rotinas administrativas reais."""
    caminho = tmp_path / "teste.db"
    monkeypatch.setenv("DATABASE_PATH", str(caminho))
    inicializar(caminho)
    return caminho


@pytest.mark.parametrize("valor", ["0.499", "0.501", "1.001", "Infinity", "NaN", "-1"])
def test_credito_exige_denominacao_exata(valor):
    with pytest.raises(ValidationError):
        CreditoRequest(valor=valor)


@pytest.mark.parametrize("valor", ["0.50", "1", "2", "5", "10", "20"])
def test_credito_preserva_decimal(valor):
    assert CreditoRequest(valor=valor).valor == Decimal(valor)


@pytest.mark.parametrize("valor", ["0.001", "1e20", "99999999.999", "0", "-1", "NaN"])
def test_preco_invalido_preserva_banco(banco, client, valor):
    h = {"Authorization": "Bearer test-token"}
    assert (
        client.put("/operador/produtos/1/preco", headers=h, json={"preco": valor}).status_code
        == 400
    )
    with pytest.raises(OperacaoInvalidaError):
        produto_service.alterar_preco(1, Decimal(valor))
    with sqlite3.connect(banco) as conexao:
        assert conexao.execute("SELECT preco_centavos FROM produto WHERE id=1").fetchone()[0] == 400


@pytest.mark.parametrize(
    "valor,centavos", [("0.01", 1), ("8.99", 899), ("99999999.99", 9999999999)]
)
def test_preco_exato_nos_limites(banco, client, valor, centavos):
    r = client.put(
        "/operador/produtos/1/preco",
        headers={"Authorization": "Bearer test-token"},
        json={"preco": valor},
    )
    assert r.status_code == 200
    with sqlite3.connect(banco) as conexao:
        assert conexao.execute(
            "SELECT preco_centavos, typeof(preco_centavos) FROM produto WHERE id=1"
        ).fetchone() == (centavos, "integer")


@pytest.mark.parametrize("identificador", [0, -1, 10**30])
def test_id_invalido_http_e_servico(banco, client, identificador):
    assert (
        client.put(
            f"/operador/produtos/{identificador}/preco",
            headers={"Authorization": "Bearer test-token"},
            json={"preco": 5},
        ).status_code
        == 400
    )
    with pytest.raises(OperacaoInvalidaError):
        produto_service.alterar_preco(identificador, 5)


@pytest.mark.parametrize("valor", ["", " ", None])
def test_token_ausente_nao_usa_padrao(banco, client, monkeypatch, valor):
    if valor is None:
        monkeypatch.delenv("OPERATOR_TOKEN")
    else:
        monkeypatch.setenv("OPERATOR_TOKEN", valor)
    r = client.post(
        "/operador/manutencao",
        headers={"Authorization": "Bearer senha_padrao_para_dev"},
        json={"acao": "ENTRAR"},
    )
    assert r.status_code == 503
    with pytest.raises(RuntimeError, match="OPERATOR_TOKEN"), TestClient(app):
        pass
    with sqlite3.connect(banco) as conexao:
        assert conexao.execute("SELECT estado FROM maquina").fetchone()[0] == "PRONTA"


def test_startup_valido(banco):
    with TestClient(app) as client:
        assert client.get("/openapi.json").status_code == 200


def test_banco_ausente_nao_cria_arquivo(tmp_path, monkeypatch, client):
    caminho = tmp_path / "ausente.db"
    monkeypatch.setenv("DATABASE_PATH", str(caminho))
    with pytest.raises(BancoIndisponivelError):
        validar_banco()
    r = client.post(
        "/operador/manutencao",
        headers={"Authorization": "Bearer test-token"},
        json={"acao": "ENTRAR"},
    )
    assert r.status_code == 503
    assert r.json()["erro"] == "BANCO_INDISPONIVEL"
    assert str(caminho) not in r.text
    assert not caminho.exists()


def test_banco_vazio_recusa_startup(tmp_path, monkeypatch):
    caminho = tmp_path / "vazio.db"
    sqlite3.connect(caminho).close()
    monkeypatch.setenv("DATABASE_PATH", str(caminho))
    with pytest.raises(BancoIndisponivelError), TestClient(app):
        pass


def test_lock_temporario_retorna_503_sem_vazar_dados(banco, monkeypatch, client):
    monkeypatch.setenv("DATABASE_TIMEOUT_SECONDS", "0")
    con = sqlite3.connect(banco)
    try:
        con.execute("BEGIN IMMEDIATE")
        r = client.post(
            "/operador/manutencao",
            headers={"Authorization": "Bearer test-token"},
            json={"acao": "ENTRAR"},
        )
        assert r.status_code == 503
        assert "locked" not in r.text
        assert str(banco) not in r.text
    finally:
        con.rollback()
        con.close()
    assert operador_service.alterar_manutencao("ENTRAR")["estado"] == "MANUTENCAO"


def test_copos_inteiros_no_dto_e_banco(banco):
    with pytest.raises(ValidationError):
        ReabastecimentoRequest(item="copos", quantidade=0.5)
    assert ReabastecimentoRequest(item="copos", quantidade=2).quantidade == 2
    assert ReabastecimentoRequest(item="agua", quantidade=0.5).quantidade == 0.5
    with sqlite3.connect(banco) as con, pytest.raises(sqlite3.IntegrityError):
        con.execute("UPDATE ingrediente SET quantidade_atual=0.5 WHERE codigo='COPOS'")


def test_duas_entradas_concorrentes_apenas_uma_transicao(banco):
    barreira = Barrier(2)

    def entrar():
        barreira.wait(timeout=5)
        try:
            return operador_service.alterar_manutencao("ENTRAR")["estado"]
        except EstadoInvalidoError:
            return "recusada"

    with ThreadPoolExecutor(max_workers=2) as executor:
        resultados = list(executor.map(lambda _: entrar(), range(2)))
    assert sorted(resultados) == ["MANUTENCAO", "recusada"]


def test_limpezas_concorrentes_preservam_auditoria(banco):
    operador_service.alterar_manutencao("ENTRAR")
    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(lambda _: operador_service.registrar_limpeza(), range(4)))
    with sqlite3.connect(banco) as con:
        assert con.execute("SELECT COUNT(*),COUNT(DISTINCT id) FROM limpeza").fetchone() == (4, 4)
        assert con.execute("SELECT preparos_desde_limpeza FROM maquina").fetchone()[0] == 0


@pytest.fixture
def legado(tmp_path):
    """Reproduz o schema anterior e dados referenciando o produto."""
    from app.repositories.database import RAIZ

    caminho = tmp_path / "legado.db"
    schema = (
        (RAIZ / "database/schema.sql")
        .read_text()
        .replace(
            "preco_centavos  INTEGER NOT NULL\n        CHECK (typeof(preco_centavos) = 'integer' AND preco_centavos BETWEEN 1 AND 9999999999),",
            "preco NUMERIC(10,2) NOT NULL CHECK (preco > 0),",
        )
    )
    with sqlite3.connect(caminho) as con:
        con.executescript(schema)
        con.execute("INSERT INTO produto VALUES (1,'Café',8.99,5)")
        con.execute("INSERT INTO ingrediente VALUES (1,'COPOS','un',50,50,10)")
        con.execute("INSERT INTO receita_item VALUES (1,1,1)")
        con.execute("INSERT INTO maquina VALUES (1,'PRONTA',10,29)")
        con.execute("INSERT INTO pedido VALUES (1,1,0,8.99,'CONCLUIDO','2026-01-01','2026-01-01')")
    return caminho


def test_migracao_preserva_relacoes_e_e_idempotente(legado):
    migrar(legado)
    migrar(legado)
    with sqlite3.connect(legado) as con:
        assert con.execute("SELECT id,nome,preco_centavos FROM produto").fetchone() == (
            1,
            "Café",
            899,
        )
        assert con.execute("SELECT COUNT(*) FROM receita_item").fetchone()[0] == 1
        assert con.execute("SELECT preco_cobrado FROM pedido").fetchone()[0] == 8.99
        assert con.execute("SELECT credito,preparos_desde_limpeza FROM maquina").fetchone() == (
            10,
            29,
        )
        assert con.execute("PRAGMA foreign_key_check").fetchall() == []


def test_migracao_invalida_reverte_toda_alteracao(legado):
    with sqlite3.connect(legado) as con:
        con.execute("UPDATE produto SET preco=0.001")
    with pytest.raises(ValueError):
        migrar(legado)
    with sqlite3.connect(legado) as con:
        assert con.execute("SELECT preco FROM produto").fetchone()[0] == 0.001
        assert (
            con.execute("SELECT name FROM sqlite_master WHERE name='produto_novo'").fetchone()
            is None
        )


def test_inicializacao_nao_sobrescreve_banco(banco):
    antes = banco.read_bytes()
    with pytest.raises(FileExistsError):
        inicializar(banco)
    assert banco.read_bytes() == antes


def test_cors_e_timeout_exigem_configuracao_valida(monkeypatch):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    assert origens_cors() == []
    monkeypatch.setenv("CORS_ORIGINS", "*")
    with pytest.raises(RuntimeError):
        origens_cors()
    monkeypatch.setenv("DATABASE_TIMEOUT_SECONDS", "NaN")
    with pytest.raises(RuntimeError):
        timeout_banco()


def test_repositorio_ativa_chaves_estrangeiras(banco):
    from app.core.exceptions import PersistenciaError

    with pytest.raises(PersistenciaError), transacao() as repositorio:
        # Teste de infraestrutura: usa a conexão privada apenas para provocar a FK.
        repositorio._conexao.execute("INSERT INTO receita_item VALUES (999,999,1)")


@pytest.mark.parametrize(
    "valor", ["8.9900000000000000000000000000000000001", "0.000000000000000000000000000000000001"]
)
def test_preco_nao_arredonda_com_precisao_extrema(banco, valor):
    with pytest.raises(OperacaoInvalidaError):
        produto_service.alterar_preco(1, Decimal(valor))


def test_migracao_com_fk_invalida_reverte_tabela_substituida(legado):
    with sqlite3.connect(legado) as con:
        con.execute("INSERT INTO receita_item VALUES (999,1,1)")
    with pytest.raises(ValueError, match="referências inválidas"):
        migrar(legado)
    with sqlite3.connect(legado) as con:
        assert con.execute("SELECT preco FROM produto").fetchone()[0] == 8.99
        assert (
            con.execute("SELECT name FROM sqlite_master WHERE name='produto_novo'").fetchone()
            is None
        )


def test_migracao_preserva_banco_personalizado(legado):
    with sqlite3.connect(legado) as con:
        con.execute("CREATE INDEX indice_personalizado ON produto(nome)")
    with pytest.raises(ValueError, match="personalizados"):
        migrar(legado)
    with sqlite3.connect(legado) as con:
        assert con.execute("SELECT preco FROM produto").fetchone()[0] == 8.99
        assert con.execute(
            "SELECT name FROM sqlite_master WHERE name='indice_personalizado'"
        ).fetchone()


def test_erro_interno_do_banco_tem_json_generico(banco, client):
    with sqlite3.connect(banco) as con:
        con.execute(
            "CREATE TRIGGER falhar BEFORE UPDATE ON produto BEGIN SELECT RAISE(ABORT, 'detalhe privado'); END"
        )
    r = client.put(
        "/operador/produtos/1/preco",
        headers={"Authorization": "Bearer test-token"},
        json={"preco": 5},
    )
    assert r.status_code == 500
    assert r.json()["erro"] == "ERRO_INTERNO"
    assert "detalhe privado" not in r.text
    assert str(banco) not in r.text
    with sqlite3.connect(banco) as con:
        assert con.execute("SELECT preco_centavos FROM produto WHERE id=1").fetchone()[0] == 400


@pytest.mark.parametrize(
    "origem",
    [
        "http://localhost:porta",
        "http://[",
        "https://user:senha@example.com",
        "https://example.com/caminho",
        "https://*.example.com",
    ],
)
def test_cors_recusa_origens_invalidas(monkeypatch, origem):
    monkeypatch.setenv("CORS_ORIGINS", origem)
    with pytest.raises(RuntimeError):
        origens_cors()


def test_cors_aceita_origens_explicitas(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000, https://cafe.example.com")
    assert origens_cors() == ["http://localhost:3000", "https://cafe.example.com"]
