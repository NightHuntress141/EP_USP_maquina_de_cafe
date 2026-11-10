"""Testes dos endpoints do fluxo do cliente.

Os serviços são mockados com ``unittest.mock.patch`` para isolar a camada de
controller das regras de negócio e do banco de dados.
"""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

PRODUTOS = [
    {"id": 1, "nome": "Café expresso", "preco": 4.00, "tempo_preparo": 8, "disponivel": True},
    {"id": 4, "nome": "Cappuccino", "preco": 6.50, "tempo_preparo": 12, "disponivel": True},
]

PEDIDO = {
    "id": 1,
    "produto": "Cappuccino",
    "acucar": 2,
    "status": "EM_PREPARO",
    "preco": 6.50,
    "credito_restante": 3.50,
    "previsao_termino": "2026-03-10T14:30:12",
}


# --------------------------------------------------------------------------- #
# GET /produtos
# --------------------------------------------------------------------------- #
@patch("app.services.produto_service.listar_produtos")
def test_listar_produtos(mock_listar: object, client: TestClient) -> None:
    """GET /produtos devolve 200 e a lista do cardápio."""
    mock_listar.return_value = PRODUTOS

    response = client.get("/produtos")

    assert response.status_code == 200
    assert response.json()[0]["nome"] == "Café expresso"
    mock_listar.assert_called_once()


# --------------------------------------------------------------------------- #
# GET /status
# --------------------------------------------------------------------------- #
@patch("app.services.status_service.obter_status")
def test_obter_status(mock_status: object, client: TestClient) -> None:
    """GET /status devolve o estado da máquina e o crédito."""
    mock_status.return_value = {"estado": "PRONTA", "credito": 10.00}

    response = client.get("/status")

    assert response.status_code == 200
    assert response.json() == {"estado": "PRONTA", "credito": 10.00}


# --------------------------------------------------------------------------- #
# POST /credito
# --------------------------------------------------------------------------- #
@patch("app.services.credito_service.adicionar_credito")
def test_inserir_credito_valido(mock_adicionar: object, client: TestClient) -> None:
    """POST /credito com valor aceito devolve 200 e o crédito acumulado."""
    mock_adicionar.return_value = 10.00

    response = client.post("/credito", json={"valor": 10.00})

    assert response.status_code == 200
    assert response.json() == {"credito": 10.00}
    mock_adicionar.assert_called_once_with(10.00)


def test_inserir_credito_valor_nao_aceito(client: TestClient) -> None:
    """POST /credito com valor fora do conjunto da RN01 devolve 400."""
    response = client.post("/credito", json={"valor": 3.00})

    assert response.status_code == 400
    assert response.json()["erro"] == "DADOS_INVALIDOS"


def test_inserir_credito_negativo(client: TestClient) -> None:
    """POST /credito com valor negativo devolve 400."""
    response = client.post("/credito", json={"valor": -1.00})

    assert response.status_code == 400


# --------------------------------------------------------------------------- #
# POST /troco
# --------------------------------------------------------------------------- #
@patch("app.services.credito_service.devolver_troco")
def test_devolver_troco(mock_troco: object, client: TestClient) -> None:
    """POST /troco devolve o valor e zera o crédito."""
    mock_troco.return_value = {"valor_devolvido": 3.50, "credito": 0.00}

    response = client.post("/troco")

    assert response.status_code == 200
    assert response.json() == {"valor_devolvido": 3.50, "credito": 0.00}


# --------------------------------------------------------------------------- #
# POST /pedidos
# --------------------------------------------------------------------------- #
@patch("app.services.pedido_service.criar_pedido")
def test_criar_pedido_sucesso(mock_criar: object, client: TestClient) -> None:
    """POST /pedidos válido devolve 201 e o pedido criado."""
    mock_criar.return_value = PEDIDO

    response = client.post("/pedidos", json={"produto_id": 4, "acucar": 2})

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == 1
    assert body["status"] == "EM_PREPARO"
    assert body["credito_restante"] == 3.50
    mock_criar.assert_called_once_with(4, 2)


def test_criar_pedido_acucar_acima_do_limite(client: TestClient) -> None:
    """POST /pedidos com açúcar > 3 devolve 400 (RN02)."""
    response = client.post("/pedidos", json={"produto_id": 4, "acucar": 4})

    assert response.status_code == 400
    assert response.json()["erro"] == "DADOS_INVALIDOS"


def test_criar_pedido_acucar_negativo(client: TestClient) -> None:
    """POST /pedidos com açúcar negativo devolve 400."""
    response = client.post("/pedidos", json={"produto_id": 4, "acucar": -1})

    assert response.status_code == 400


def test_criar_pedido_sem_produto_id(client: TestClient) -> None:
    """POST /pedidos sem produto_id devolve 400."""
    response = client.post("/pedidos", json={"acucar": 0})

    assert response.status_code == 400


@patch("app.services.pedido_service.criar_pedido")
def test_criar_pedido_bebida_inexistente(mock_criar: object, client: TestClient) -> None:
    """POST /pedidos de bebida inexistente devolve 404."""
    from app.core.exceptions import BebidaNaoEncontradaError

    mock_criar.side_effect = BebidaNaoEncontradaError("Bebida não encontrada.")

    response = client.post("/pedidos", json={"produto_id": 99, "acucar": 0})

    assert response.status_code == 404
    assert response.json()["erro"] == "BEBIDA_NAO_ENCONTRADA"


@patch("app.services.pedido_service.criar_pedido")
def test_criar_pedido_credito_insuficiente(mock_criar: object, client: TestClient) -> None:
    """POST /pedidos sem crédito suficiente devolve 402."""
    from app.core.exceptions import CreditoInsuficienteError

    mock_criar.side_effect = CreditoInsuficienteError("Crédito de R$ 3,50 não cobre R$ 7,00.")

    response = client.post("/pedidos", json={"produto_id": 5, "acucar": 0})

    assert response.status_code == 402
    assert response.json()["erro"] == "CREDITO_INSUFICIENTE"


@patch("app.services.pedido_service.criar_pedido")
def test_criar_pedido_maquina_ocupada(mock_criar: object, client: TestClient) -> None:
    """POST /pedidos com a máquina preparando outra bebida devolve 409."""
    from app.core.exceptions import MaquinaOcupadaError

    mock_criar.side_effect = MaquinaOcupadaError("A máquina está preparando outra bebida.")

    response = client.post("/pedidos", json={"produto_id": 1, "acucar": 0})

    assert response.status_code == 409
    assert response.json()["erro"] == "MAQUINA_OCUPADA"


@patch("app.services.pedido_service.criar_pedido")
def test_criar_pedido_estoque_insuficiente(mock_criar: object, client: TestClient) -> None:
    """POST /pedidos sem estoque suficiente devolve 409."""
    from app.core.exceptions import EstoqueInsuficienteError

    mock_criar.side_effect = EstoqueInsuficienteError("Estoque de leite insuficiente.")

    response = client.post("/pedidos", json={"produto_id": 3, "acucar": 0})

    assert response.status_code == 409
    assert response.json()["erro"] == "ESTOQUE_INSUFICIENTE"


@patch("app.services.pedido_service.criar_pedido")
def test_criar_pedido_maquina_indisponivel(mock_criar: object, client: TestClient) -> None:
    """POST /pedidos com a máquina em manutenção devolve 503."""
    from app.core.exceptions import MaquinaIndisponivelError

    mock_criar.side_effect = MaquinaIndisponivelError("A máquina está em manutenção.")

    response = client.post("/pedidos", json={"produto_id": 1, "acucar": 0})

    assert response.status_code == 503
    assert response.json()["erro"] == "MAQUINA_INDISPONIVEL"


# --------------------------------------------------------------------------- #
# GET /pedidos/{id}
# --------------------------------------------------------------------------- #
@patch("app.services.pedido_service.consultar_pedido")
def test_consultar_pedido(mock_consultar: object, client: TestClient) -> None:
    """GET /pedidos/{id} devolve 200 e o pedido."""
    mock_consultar.return_value = {**PEDIDO, "status": "CONCLUIDO"}

    response = client.get("/pedidos/1")

    assert response.status_code == 200
    assert response.json()["status"] == "CONCLUIDO"
    mock_consultar.assert_called_once_with(1)


@patch("app.services.pedido_service.consultar_pedido")
def test_consultar_pedido_inexistente(mock_consultar: object, client: TestClient) -> None:
    """GET /pedidos/{id} de pedido inexistente devolve 404."""
    from app.core.exceptions import PedidoNaoEncontradoError

    mock_consultar.side_effect = PedidoNaoEncontradoError("Pedido não encontrado.")

    response = client.get("/pedidos/999")

    assert response.status_code == 404
    assert response.json()["erro"] == "PEDIDO_NAO_ENCONTRADO"


# --------------------------------------------------------------------------- #
# POST /pedidos/{id}/cancelar
# --------------------------------------------------------------------------- #
@patch("app.services.pedido_service.cancelar_pedido")
def test_cancelar_pedido(mock_cancelar: object, client: TestClient) -> None:
    """POST /pedidos/{id}/cancelar devolve 200 e o pedido cancelado."""
    mock_cancelar.return_value = {**PEDIDO, "status": "CANCELADO"}

    response = client.post("/pedidos/1/cancelar")

    assert response.status_code == 200
    assert response.json()["status"] == "CANCELADO"
    mock_cancelar.assert_called_once_with(1)


@patch("app.services.pedido_service.cancelar_pedido")
def test_cancelar_pedido_inexistente(mock_cancelar: object, client: TestClient) -> None:
    """POST /pedidos/{id}/cancelar de pedido inexistente devolve 404."""
    from app.core.exceptions import PedidoNaoEncontradoError

    mock_cancelar.side_effect = PedidoNaoEncontradoError("Pedido não encontrado.")

    response = client.post("/pedidos/999/cancelar")

    assert response.status_code == 404


@patch("app.services.pedido_service.cancelar_pedido")
def test_cancelar_pedido_nao_cancelavel(mock_cancelar: object, client: TestClient) -> None:
    """POST /pedidos/{id}/cancelar de pedido já concluído devolve 400 (RN05)."""
    from app.core.exceptions import OperacaoInvalidaError

    mock_cancelar.side_effect = OperacaoInvalidaError("Apenas pedidos em preparo podem ser cancelados.")

    response = client.post("/pedidos/1/cancelar")

    assert response.status_code == 400
    assert response.json()["erro"] == "DADOS_INVALIDOS"
