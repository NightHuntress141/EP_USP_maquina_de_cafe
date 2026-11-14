"""Testes dos endpoints do fluxo do operador.

Os serviços são mockados com ``unittest.mock.patch`` para isolar a camada de
controller das regras de negócio. A autenticação usa ``OPERATOR_TOKEN``
definido via ``monkeypatch``.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

ITEM_ESTOQUE = {
    "item": "leite",
    "atual": 2.5,
    "capacidade": 10.0,
    "nivel_baixo": True,
}

ESTOQUE = {"reservatorios": [ITEM_ESTOQUE]}

ITEM_REABASTECIDO = {
    "item": {
        "item": "agua",
        "atual": 6.5,
        "capacidade": 10.0,
        "nivel_baixo": False,
    }
}

PRODUTO = {
    "id": 4,
    "nome": "Cappuccino",
    "preco": 7.00,
    "tempo_preparo": 12,
    "disponivel": True,
}

RELATORIO = {
    "inicio": "2026-03-01T00:00:00",
    "fim": "2026-03-31T23:59:59",
    "total_pedidos": 12,
    "faturamento_total": 78.00,
    "por_bebida": [
        {"produto_id": 4, "nome": "Cappuccino", "quantidade": 12, "faturamento": 78.00},
    ],
}


@pytest.fixture
def auth_headers(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Define o token de teste e devolve o cabeçalho de autorização."""
    monkeypatch.setenv("OPERATOR_TOKEN", "test-token")
    return {"Authorization": "Bearer test-token"}


# --------------------------------------------------------------------------- #
# POST /operador/login
# --------------------------------------------------------------------------- #
@patch("app.services.operador_service.autenticar")
def test_login_sucesso(mock_autenticar: object, client: TestClient) -> None:
    """POST /operador/login válido devolve 200 e o token."""
    mock_autenticar.return_value = "test-token"

    response = client.post(
        "/operador/login",
        json={"usuario": "operador", "senha": "senha_padrao_para_dev"},
    )

    assert response.status_code == 200
    assert response.json() == {"token": "test-token", "tipo": "bearer"}
    mock_autenticar.assert_called_once_with("operador", "senha_padrao_para_dev")


@patch("app.services.operador_service.autenticar")
def test_login_credenciais_invalidas(mock_autenticar: object, client: TestClient) -> None:
    """POST /operador/login com credenciais inválidas devolve 401 (RN11)."""
    from app.core.exceptions import CredenciaisInvalidasError

    mock_autenticar.side_effect = CredenciaisInvalidasError("Usuário ou senha inválidos.")

    response = client.post("/operador/login", json={"usuario": "operador", "senha": "errada"})

    assert response.status_code == 401
    assert response.json()["erro"] == "NAO_AUTORIZADO"


def test_login_sem_campos(client: TestClient) -> None:
    """POST /operador/login sem usuário/senha devolve 400."""
    response = client.post("/operador/login", json={})

    assert response.status_code == 400
    assert response.json()["erro"] == "DADOS_INVALIDOS"


# --------------------------------------------------------------------------- #
# GET /operador/estoque
# --------------------------------------------------------------------------- #
def test_estoque_sem_token(client: TestClient) -> None:
    """GET /operador/estoque sem token devolve 401 (RN11)."""
    response = client.get("/operador/estoque")

    assert response.status_code == 401
    assert response.json()["erro"] == "NAO_AUTORIZADO"


@patch("app.services.estoque_service.consultar_estoque")
def test_estoque_com_token(
    mock_consultar: object, client: TestClient, auth_headers: dict[str, str]
) -> None:
    """GET /operador/estoque com token devolve 200 e o estoque."""
    mock_consultar.return_value = ESTOQUE

    response = client.get("/operador/estoque", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["reservatorios"][0]["item"] == "leite"
    mock_consultar.assert_called_once()


# --------------------------------------------------------------------------- #
# POST /operador/estoque/reabastecer
# --------------------------------------------------------------------------- #
@patch("app.services.estoque_service.reabastecer")
def test_reabastecer_sucesso(
    mock_reabastecer: object, client: TestClient, auth_headers: dict[str, str]
) -> None:
    """POST /operador/estoque/reabastecer válido devolve 200 (RN09)."""
    mock_reabastecer.return_value = ITEM_REABASTECIDO

    response = client.post(
        "/operador/estoque/reabastecer",
        json={"item": "agua", "quantidade": 1.5},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["item"]["atual"] == 6.5
    mock_reabastecer.assert_called_once_with("agua", 1.5)


def test_reabastecer_quantidade_invalida(client: TestClient, auth_headers: dict[str, str]) -> None:
    """POST /operador/estoque/reabastecer com quantidade <= 0 devolve 400."""
    response = client.post(
        "/operador/estoque/reabastecer",
        json={"item": "agua", "quantidade": 0},
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert response.json()["erro"] == "DADOS_INVALIDOS"


@patch("app.services.estoque_service.reabastecer")
def test_reabastecer_capacidade_excedida(
    mock_reabastecer: object, client: TestClient, auth_headers: dict[str, str]
) -> None:
    """POST /operador/estoque/reabastecer acima da capacidade devolve 422 (RN09)."""
    from app.core.exceptions import CapacidadeExcedidaError

    mock_reabastecer.side_effect = CapacidadeExcedidaError("Capacidade do reservatório excedida.")

    response = client.post(
        "/operador/estoque/reabastecer",
        json={"item": "agua", "quantidade": 20.0},
        headers=auth_headers,
    )

    assert response.status_code == 422
    assert response.json()["erro"] == "CAPACIDADE_EXCEDIDA"


@patch("app.services.estoque_service.reabastecer")
def test_reabastecer_fora_de_manutencao(
    mock_reabastecer: object, client: TestClient, auth_headers: dict[str, str]
) -> None:
    """POST /operador/estoque/reabastecer fora de manutenção devolve 409 (RN09)."""
    from app.core.exceptions import EstadoInvalidoError

    mock_reabastecer.side_effect = EstadoInvalidoError("A máquina precisa estar em manutenção.")

    response = client.post(
        "/operador/estoque/reabastecer",
        json={"item": "agua", "quantidade": 1.5},
        headers=auth_headers,
    )

    assert response.status_code == 409
    assert response.json()["erro"] == "ESTADO_INVALIDO"


# --------------------------------------------------------------------------- #
# PUT /operador/produtos/{produto_id}/preco
# --------------------------------------------------------------------------- #
@patch("app.services.produto_service.alterar_preco")
def test_alterar_preco_sucesso(
    mock_alterar: object, client: TestClient, auth_headers: dict[str, str]
) -> None:
    """PUT /operador/produtos/{id}/preco válido devolve 200 (RN10)."""
    mock_alterar.return_value = PRODUTO

    response = client.put(
        "/operador/produtos/4/preco",
        json={"preco": 7.00},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["preco"] == 7.00
    mock_alterar.assert_called_once_with(4, 7.00)


def test_alterar_preco_invalido(client: TestClient, auth_headers: dict[str, str]) -> None:
    """PUT /operador/produtos/{id}/preco com preço <= 0 devolve 400."""
    response = client.put(
        "/operador/produtos/4/preco",
        json={"preco": 0},
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert response.json()["erro"] == "DADOS_INVALIDOS"


@patch("app.services.produto_service.alterar_preco")
def test_alterar_preco_bebida_inexistente(
    mock_alterar: object, client: TestClient, auth_headers: dict[str, str]
) -> None:
    """PUT /operador/produtos/{id}/preco de bebida inexistente devolve 404 (RN10)."""
    from app.core.exceptions import BebidaNaoEncontradaError

    mock_alterar.side_effect = BebidaNaoEncontradaError("Bebida não encontrada.")

    response = client.put(
        "/operador/produtos/99/preco",
        json={"preco": 7.00},
        headers=auth_headers,
    )

    assert response.status_code == 404
    assert response.json()["erro"] == "BEBIDA_NAO_ENCONTRADA"


# --------------------------------------------------------------------------- #
# POST /operador/manutencao
# --------------------------------------------------------------------------- #
@patch("app.services.operador_service.alterar_manutencao")
def test_entrar_manutencao(
    mock_alterar: object, client: TestClient, auth_headers: dict[str, str]
) -> None:
    """POST /operador/manutencao com ENTRAR devolve 200 e MANUTENCAO (RN08)."""
    mock_alterar.return_value = {"estado": "MANUTENCAO"}

    response = client.post("/operador/manutencao", json={"acao": "ENTRAR"}, headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == {"estado": "MANUTENCAO"}
    mock_alterar.assert_called_once_with("ENTRAR")


@patch("app.services.operador_service.alterar_manutencao")
def test_sair_manutencao(
    mock_alterar: object, client: TestClient, auth_headers: dict[str, str]
) -> None:
    """POST /operador/manutencao com SAIR devolve 200 e PRONTA (RN08)."""
    mock_alterar.return_value = {"estado": "PRONTA"}

    response = client.post("/operador/manutencao", json={"acao": "SAIR"}, headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == {"estado": "PRONTA"}
    mock_alterar.assert_called_once_with("SAIR")


@patch("app.services.operador_service.alterar_manutencao")
def test_manutencao_transicao_invalida(
    mock_alterar: object, client: TestClient, auth_headers: dict[str, str]
) -> None:
    """POST /operador/manutencao com transição inválida devolve 409 (RN08)."""
    from app.core.exceptions import EstadoInvalidoError

    mock_alterar.side_effect = EstadoInvalidoError("A máquina não pode entrar em manutenção agora.")

    response = client.post("/operador/manutencao", json={"acao": "ENTRAR"}, headers=auth_headers)

    assert response.status_code == 409
    assert response.json()["erro"] == "ESTADO_INVALIDO"


# --------------------------------------------------------------------------- #
# POST /operador/limpeza
# --------------------------------------------------------------------------- #
@patch("app.services.operador_service.registrar_limpeza")
def test_registrar_limpeza(
    mock_limpeza: object, client: TestClient, auth_headers: dict[str, str]
) -> None:
    """POST /operador/limpeza devolve 200 com contador zerado (RN07)."""
    mock_limpeza.return_value = {"preparos_desde_limpeza": 0, "estado": "MANUTENCAO"}

    response = client.post("/operador/limpeza", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == {"preparos_desde_limpeza": 0, "estado": "MANUTENCAO"}
    mock_limpeza.assert_called_once()


@patch("app.services.operador_service.registrar_limpeza")
def test_limpeza_fora_de_estado_valido(
    mock_limpeza: object, client: TestClient, auth_headers: dict[str, str]
) -> None:
    """POST /operador/limpeza fora do estado permitido devolve 409 (RN07)."""
    from app.core.exceptions import EstadoInvalidoError

    mock_limpeza.side_effect = EstadoInvalidoError("A máquina não está em manutenção.")

    response = client.post("/operador/limpeza", headers=auth_headers)

    assert response.status_code == 409
    assert response.json()["erro"] == "ESTADO_INVALIDO"


# --------------------------------------------------------------------------- #
# GET /operador/relatorio
# --------------------------------------------------------------------------- #
@patch("app.services.relatorio_service.gerar_relatorio")
def test_gerar_relatorio(
    mock_relatorio: object, client: TestClient, auth_headers: dict[str, str]
) -> None:
    """GET /operador/relatorio válido devolve 200 e o consolidado (RN12)."""
    mock_relatorio.return_value = RELATORIO

    response = client.get(
        "/operador/relatorio",
        params={"inicio": "2026-03-01T00:00:00", "fim": "2026-03-31T23:59:59"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["total_pedidos"] == 12
    assert response.json()["faturamento_total"] == 78.00
    mock_relatorio.assert_called_once_with(
        datetime(2026, 3, 1, 0, 0, 0),
        datetime(2026, 3, 31, 23, 59, 59),
    )


def test_gerar_relatorio_periodo_invalido(client: TestClient, auth_headers: dict[str, str]) -> None:
    """GET /operador/relatorio com início > fim devolve 400 (RN12)."""
    response = client.get(
        "/operador/relatorio",
        params={"inicio": "2026-03-31T00:00:00", "fim": "2026-03-01T00:00:00"},
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert response.json()["erro"] == "DADOS_INVALIDOS"


@pytest.mark.parametrize("valor", ["Infinity", "-Infinity", "NaN", "1e999", 0, -1, "invalido"])
@pytest.mark.parametrize(
    "metodo,rota,corpo,servico",
    [
        (
            "put",
            "/operador/produtos/1/preco",
            "preco",
            "app.services.produto_service.alterar_preco",
        ),
        (
            "post",
            "/operador/estoque/reabastecer",
            "quantidade",
            "app.services.estoque_service.reabastecer",
        ),
    ],
)
def test_numero_invalido_nao_chega_ao_servico(
    client, auth_headers, valor, metodo, rota, corpo, servico
):
    """Recusa números não finitos, não positivos e texto antes da delegação."""
    payload = {corpo: valor}
    if corpo == "quantidade":
        payload["item"] = "agua"
    with patch(servico) as mock_servico:
        resposta = client.request(metodo, rota, json=payload, headers=auth_headers)
    assert resposta.status_code == 400
    assert resposta.json()["erro"] == "DADOS_INVALIDOS"
    mock_servico.assert_not_called()


@pytest.mark.parametrize("autorizacao", [None, "Bearer invalido", "Basic test-token"])
@pytest.mark.parametrize(
    "metodo,rota,payload,servico",
    [
        (
            "get",
            "/operador/estoque",
            None,
            "app.services.estoque_service.consultar_estoque",
        ),
        (
            "post",
            "/operador/estoque/reabastecer",
            {"item": "agua", "quantidade": 1},
            "app.services.estoque_service.reabastecer",
        ),
        (
            "put",
            "/operador/produtos/1/preco",
            {"preco": 5},
            "app.services.produto_service.alterar_preco",
        ),
        (
            "post",
            "/operador/manutencao",
            {"acao": "ENTRAR"},
            "app.services.operador_service.alterar_manutencao",
        ),
        (
            "post",
            "/operador/limpeza",
            None,
            "app.services.operador_service.registrar_limpeza",
        ),
        (
            "get",
            "/operador/relatorio?inicio=2026-01-01T00:00:00&fim=2026-12-31T00:00:00",
            None,
            "app.services.relatorio_service.gerar_relatorio",
        ),
    ],
)
def test_rotas_protegidas_recusam_credenciais(
    client, auth_headers, autorizacao, metodo, rota, payload, servico
):
    """Todas as rotas protegidas recusam credenciais inválidas sem chamar serviços."""
    headers = {} if autorizacao is None else {"Authorization": autorizacao}
    with patch(servico) as mock_servico:
        resposta = client.request(metodo, rota, json=payload, headers=headers)
    assert resposta.status_code == 401
    assert resposta.json()["erro"] == "NAO_AUTORIZADO"
    assert resposta.headers["www-authenticate"] == "Bearer"
    mock_servico.assert_not_called()
