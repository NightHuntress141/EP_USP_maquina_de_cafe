"""DTOs de pedido (RN02 a RN05)."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class StatusPedido(str, Enum):
    """Ciclo de vida de um pedido (RN04/RN05)."""

    EM_PREPARO = "EM_PREPARO"
    CONCLUIDO = "CONCLUIDO"
    CANCELADO = "CANCELADO"


class PedidoRequest(BaseModel):
    """Corpo da requisição de criação de pedido.

    Attributes:
        produto_id: Identificador da bebida desejada.
        acucar: Número de porções de açúcar (0 a 3, sem custo adicional, RN02).
    """

    produto_id: int = Field(..., ge=1, description="Identificador da bebida.", examples=[4])
    acucar: int = Field(
        0,
        ge=0,
        le=3,
        description="Porções de açúcar de 5 g (0 a 3, sem custo adicional).",
        examples=[2],
    )


class PedidoResponse(BaseModel):
    """Representação de um pedido criado ou consultado.

    Attributes:
        id: Identificador do pedido.
        produto: Nome da bebida do pedido.
        acucar: Porções de açúcar escolhidas.
        status: Situação atual do pedido.
        preco: Preço cobrado pela bebida.
        credito_restante: Crédito disponível após a cobrança.
        previsao_termino: Horário previsto de conclusão do preparo, quando aplicável.
    """

    id: int = Field(..., description="Identificador do pedido.", examples=[1])
    produto: str = Field(..., description="Nome da bebida.", examples=["Cappuccino"])
    acucar: int = Field(..., description="Porções de açúcar.", examples=[2])
    status: StatusPedido = Field(..., description="Situação atual do pedido.", examples=["EM_PREPARO"])
    preco: float = Field(..., description="Preço cobrado pela bebida.", examples=[6.50])
    credito_restante: float = Field(..., description="Crédito após a cobrança.", examples=[3.50])
    previsao_termino: datetime | None = Field(
        None, description="Horário previsto de término do preparo.", examples=["2026-03-10T14:30:12"]
    )


__all__ = ["StatusPedido", "PedidoRequest", "PedidoResponse"]
