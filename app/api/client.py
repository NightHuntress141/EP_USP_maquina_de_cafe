"""Endpoints do fluxo do cliente (sem autenticação).

Este módulo implementa apenas a camada de controller: valida a entrada via
Pydantic, delega a execução das regras de negócio aos serviços e devolve a
resposta HTTP. As exceções de negócio são traduzidas para códigos HTTP pelos
handlers globais registrados em :mod:`app.main`.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, status

from app.schemas.credito import CreditoRequest, CreditoResponse, TrocoResponse
from app.schemas.erro import ErroResponse
from app.schemas.pedido import PedidoRequest, PedidoResponse
from app.schemas.produto import ProdutoResponse
from app.schemas.status import StatusResponse
from app.services import credito_service, pedido_service, produto_service, status_service

router = APIRouter(tags=["Cliente"])


def _erro(codigo: int, descricao: str, exemplo_erro: str, exemplo_mensagem: str) -> dict[int, dict[str, Any]]:
    """Monta a documentação de uma resposta de erro para o Swagger.

    Args:
        codigo: Código HTTP da resposta.
        descricao: Descrição exibida na documentação.
        exemplo_erro: Valor de exemplo para o campo ``erro``.
        exemplo_mensagem: Valor de exemplo para o campo ``mensagem``.

    Returns:
        Dicionário no formato aceito pelo parâmetro ``responses`` do FastAPI.
    """
    return {
        codigo: {
            "model": ErroResponse,
            "description": descricao,
            "content": {"application/json": {"example": {"erro": exemplo_erro, "mensagem": exemplo_mensagem}}},
        }
    }


@router.get(
    "/produtos",
    response_model=list[ProdutoResponse],
    summary="Lista o cardápio",
    responses={**_erro(400, "Requisição inválida.", "DADOS_INVALIDOS", "Requisição inválida.")},
)
def listar_produtos() -> list[dict[str, Any]]:
    """Retorna o cardápio com preço, tempo de preparo e disponibilidade.

    Delega a montagem do cardápio ao serviço de produtos.

    Regras de negócio acionadas:
        - RN10: o cardápio informa se cada bebida está disponível (estoque
          suficiente para prepará-la agora).

    Returns:
        Lista de bebidas no formato :class:`app.schemas.produto.ProdutoResponse`.
    """
    return produto_service.listar_produtos()


@router.get(
    "/status",
    response_model=StatusResponse,
    summary="Consulta o estado da máquina",
)
def obter_status() -> dict[str, Any]:
    """Retorna o estado operacional atual da máquina e o crédito acumulado.

    Returns:
        Estado da máquina no formato :class:`app.schemas.status.StatusResponse`.
    """
    return status_service.obter_status()


@router.post(
    "/credito",
    response_model=CreditoResponse,
    summary="Insere crédito na máquina",
    responses={**_erro(400, "Valor de crédito não aceito.", "DADOS_INVALIDOS", "Valor de crédito não aceito.")},
)
def inserir_credito(payload: CreditoRequest) -> dict[str, Any]:
    """Insere um valor de crédito na máquina.

    O valor é validado por :class:`app.schemas.credito.CreditoRequest` antes de
    chegar ao serviço.

    Regras de negócio acionadas:
        - RN01: valores aceitos (0,50 / 1,00 / 2,00 / 5,00 / 10,00 / 20,00) e
          limite de crédito acumulado de R$ 50,00.

    Args:
        payload: Valor a inserir.

    Returns:
        Crédito acumulado no formato :class:`app.schemas.credito.CreditoResponse`.
    """
    novo_credito = credito_service.adicionar_credito(payload.valor)
    return {"credito": novo_credito}


@router.post(
    "/troco",
    response_model=TrocoResponse,
    summary="Devolve todo o crédito restante",
)
def devolver_troco() -> dict[str, Any]:
    """Devolve todo o crédito restante ao cliente e zera o saldo.

    Regras de negócio acionadas:
        - RN06: a devolução zera o crédito acumulado.

    Returns:
        Valor devolvido no formato :class:`app.schemas.credito.TrocoResponse`.
    """
    return credito_service.devolver_troco()


@router.post(
    "/pedidos",
    response_model=PedidoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cria um novo pedido",
    responses={
        **_erro(400, "Dados do pedido inválidos.", "DADOS_INVALIDOS", "Açúcar deve estar entre 0 e 3."),
        **_erro(402, "Crédito insuficiente.", "CREDITO_INSUFICIENTE", "Crédito não cobre o preço da bebida."),
        **_erro(404, "Bebida inexistente.", "BEBIDA_NAO_ENCONTRADA", "Bebida não encontrada no cardápio."),
        **_erro(409, "Estoque insuficiente ou máquina ocupada.", "MAQUINA_OCUPADA", "A máquina está preparando outra bebida."),
        **_erro(503, "Máquina indisponível.", "MAQUINA_INDISPONIVEL", "A máquina está em manutenção."),
    },
)
def criar_pedido(pedido: PedidoRequest) -> dict[str, Any]:
    """Cria um novo pedido de bebida.

    Regras de negócio acionadas (executadas pelo serviço de pedidos):
        - RN02: máquina PRONTA, crédito suficiente e estoque de ingredientes,
          açúcar e copo.
        - RN03: cobrança do preço e desconto dos ingredientes.
        - RN04: pedido nasce EM_PREPARO e a máquina passa a PREPARANDO.

    Args:
        pedido: Bebida desejada e porções de açúcar.

    Returns:
        Pedido criado no formato :class:`app.schemas.pedido.PedidoResponse`.
    """
    return pedido_service.criar_pedido(pedido.produto_id, pedido.acucar)


@router.get(
    "/pedidos/{pedido_id}",
    response_model=PedidoResponse,
    summary="Consulta um pedido",
    responses={**_erro(404, "Pedido inexistente.", "PEDIDO_NAO_ENCONTRADO", "Pedido não encontrado.")},
)
def consultar_pedido(pedido_id: int) -> dict[str, Any]:
    """Consulta um pedido e seu status atual.

    Regras de negócio acionadas:
        - RN04: o status é calculado na consulta (EM_PREPARO até o término
          previsto, depois CONCLUIDO), sem uso de timer.

    Args:
        pedido_id: Identificador do pedido.

    Returns:
        Pedido no formato :class:`app.schemas.pedido.PedidoResponse`.
    """
    return pedido_service.consultar_pedido(pedido_id)


@router.post(
    "/pedidos/{pedido_id}/cancelar",
    response_model=PedidoResponse,
    summary="Cancela um pedido em preparo",
    responses={
        **_erro(404, "Pedido inexistente.", "PEDIDO_NAO_ENCONTRADO", "Pedido não encontrado."),
        **_erro(409, "Pedido não pode ser cancelado.", "DADOS_INVALIDOS", "Apenas pedidos em preparo podem ser cancelados."),
    },
)
def cancelar_pedido(pedido_id: int) -> dict[str, Any]:
    """Cancela um pedido que esteja EM_PREPARO.

    Regras de negócio acionadas:
        - RN05: apenas pedidos EM_PREPARO; o valor é devolvido ao crédito, os
          ingredientes já consumidos não retornam ao estoque e a máquina volta
          a PRONTA.

    Args:
        pedido_id: Identificador do pedido.

    Returns:
        Pedido cancelado no formato :class:`app.schemas.pedido.PedidoResponse`.
    """
    return pedido_service.cancelar_pedido(pedido_id)


__all__ = [
    "router",
    "listar_produtos",
    "obter_status",
    "inserir_credito",
    "devolver_troco",
    "criar_pedido",
    "consultar_pedido",
    "cancelar_pedido",
]
