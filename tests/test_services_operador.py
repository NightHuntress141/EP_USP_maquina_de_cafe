"""Testes das operações do operador com o schema e o seed reais."""

import sqlite3
from pathlib import Path

import pytest

from app.core.exceptions import (
    BebidaNaoEncontradaError,
    EstadoInvalidoError,
    OperacaoInvalidaError,
    PersistenciaError,
)
from app.services import operador_service, produto_service


@pytest.fixture
def banco(tmp_path, monkeypatch):
    """Inicializa um banco isolado usando os scripts versionados."""
    caminho = tmp_path / "maquina.db"
    monkeypatch.setenv("DATABASE_PATH", str(caminho))
    raiz = Path(__file__).resolve().parents[1]
    with sqlite3.connect(caminho) as conexao:
        conexao.executescript((raiz / "database/schema.sql").read_text())
        conexao.executescript((raiz / "database/seed.sql").read_text())
    return caminho


def test_preco_persistido_e_disponibilidade(banco):
    produto = produto_service.alterar_preco(1, 8.50)
    assert produto["preco"] == 8.50
    assert produto["tempo_preparo"] == 5
    assert produto["disponivel"] is True
    with sqlite3.connect(banco) as conexao:
        assert (
            conexao.execute("SELECT preco_centavos FROM produto WHERE id = 1").fetchone()[0] == 850
        )
        conexao.execute("UPDATE ingrediente SET quantidade_atual = 0 WHERE codigo = 'COPOS'")
    assert produto_service.alterar_preco(1, 9)["disponivel"] is False
    with pytest.raises(BebidaNaoEncontradaError):
        produto_service.alterar_preco(99, 8)


@pytest.mark.parametrize("preco", [0, -1, float("inf"), float("nan")])
def test_preco_invalido_nao_altera_banco(banco, preco):
    with pytest.raises(OperacaoInvalidaError):
        produto_service.alterar_preco(1, preco)
    with sqlite3.connect(banco) as conexao:
        assert (
            conexao.execute("SELECT preco_centavos FROM produto WHERE id = 1").fetchone()[0] == 400
        )


@pytest.mark.parametrize(
    "contador, esperado",
    [(29, "PRONTA"), (30, "AGUARDANDO_LIMPEZA"), (31, "AGUARDANDO_LIMPEZA")],
)
def test_saida_respeita_limpeza_pendente(banco, contador, esperado):
    with sqlite3.connect(banco) as conexao:
        conexao.execute(
            "UPDATE maquina SET estado='MANUTENCAO', preparos_desde_limpeza=?, credito=10",
            (contador,),
        )
    assert operador_service.alterar_manutencao("SAIR") == {"estado": esperado}
    with sqlite3.connect(banco) as conexao:
        assert conexao.execute(
            "SELECT credito, preparos_desde_limpeza FROM maquina"
        ).fetchone() == (10, contador)


@pytest.mark.parametrize(
    "estado,acao",
    [
        ("PREPARANDO", "ENTRAR"),
        ("MANUTENCAO", "ENTRAR"),
        ("PRONTA", "SAIR"),
        ("AGUARDANDO_LIMPEZA", "SAIR"),
    ],
)
def test_transicoes_invalidas_preservam_banco(banco, estado, acao):
    with sqlite3.connect(banco) as conexao:
        conexao.execute("UPDATE maquina SET estado=?", (estado,))
    with pytest.raises(EstadoInvalidoError):
        operador_service.alterar_manutencao(acao)
    with sqlite3.connect(banco) as conexao:
        assert conexao.execute("SELECT estado FROM maquina").fetchone()[0] == estado


@pytest.mark.parametrize("estado", ["PRONTA", "PREPARANDO", "AGUARDANDO_LIMPEZA"])
def test_limpeza_exige_manutencao(banco, estado):
    with sqlite3.connect(banco) as conexao:
        conexao.execute("UPDATE maquina SET estado=?, preparos_desde_limpeza=30", (estado,))
    with pytest.raises(EstadoInvalidoError):
        operador_service.registrar_limpeza()
    with sqlite3.connect(banco) as conexao:
        assert conexao.execute("SELECT COUNT(*) FROM limpeza").fetchone()[0] == 0
        assert conexao.execute("SELECT preparos_desde_limpeza FROM maquina").fetchone()[0] == 30


def test_fluxo_http_com_banco_real(banco, client, monkeypatch):
    monkeypatch.setenv("OPERATOR_TOKEN", "test-token")
    h = {"Authorization": "Bearer test-token"}
    with sqlite3.connect(banco) as conexao:
        conexao.execute(
            "UPDATE maquina SET estado='AGUARDANDO_LIMPEZA', preparos_desde_limpeza=30, credito=10"
        )
    assert client.post("/operador/limpeza", headers=h).status_code == 409
    assert client.post("/operador/manutencao", json={"acao": "ENTRAR"}, headers=h).json() == {
        "estado": "MANUTENCAO"
    }
    assert client.post("/operador/limpeza", headers=h).json() == {
        "estado": "MANUTENCAO",
        "preparos_desde_limpeza": 0,
    }
    assert client.post("/operador/manutencao", json={"acao": "SAIR"}, headers=h).json() == {
        "estado": "PRONTA"
    }
    assert client.put("/operador/produtos/1/preco", json={"preco": 8}, headers=h).status_code == 200
    with sqlite3.connect(banco) as conexao:
        assert conexao.execute(
            "SELECT credito, preparos_desde_limpeza FROM maquina"
        ).fetchone() == (10, 0)
        assert conexao.execute("SELECT COUNT(*) FROM limpeza").fetchone()[0] == 1
        assert conexao.execute("SELECT preco_centavos FROM produto WHERE id=1").fetchone()[0] == 800


def test_falha_ao_zerar_contador_reverte_registro_de_limpeza(banco):
    """Uma falha no segundo comando da limpeza também desfaz a auditoria."""
    with sqlite3.connect(banco) as conexao:
        conexao.execute("UPDATE maquina SET estado='MANUTENCAO', preparos_desde_limpeza=30")
        conexao.execute(
            "CREATE TRIGGER impedir_update BEFORE UPDATE ON maquina BEGIN SELECT RAISE(ABORT, 'falha simulada'); END"
        )
    with pytest.raises(PersistenciaError):
        operador_service.registrar_limpeza()
    with sqlite3.connect(banco) as conexao:
        assert conexao.execute("SELECT COUNT(*) FROM limpeza").fetchone()[0] == 0
        assert conexao.execute("SELECT estado, preparos_desde_limpeza FROM maquina").fetchone() == (
            "MANUTENCAO",
            30,
        )
