"""DTOs do relatório de vendas (RN12)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class VendaPorBebida(BaseModel):
    """Consolidado de vendas de uma bebida no período.

    Attributes:
        produto_id: Identificador da bebida.
        nome: Nome comercial da bebida.
        quantidade: Quantidade de pedidos concluídos no período.
        faturamento: Faturamento gerado pela bebida no período.
    """

    produto_id: int = Field(..., description="Identificador da bebida.", examples=[4])
    nome: str = Field(..., description="Nome da bebida.", examples=["Cappuccino"])
    quantidade: int = Field(..., description="Pedidos concluídos no período.", examples=[12])
    faturamento: float = Field(
        ..., description="Faturamento da bebida no período.", examples=[78.0]
    )


class RelatorioResponse(BaseModel):
    """Relatório de vendas do período solicitado (RN12).

    Attributes:
        inicio: Início do período consultado.
        fim: Fim do período consultado.
        total_pedidos: Total de pedidos concluídos no período.
        faturamento_total: Faturamento total do período.
        por_bebida: Consolidado por bebida.
    """

    inicio: datetime = Field(
        ..., description="Início do período.", examples=["2026-03-01T00:00:00"]
    )
    fim: datetime = Field(..., description="Fim do período.", examples=["2026-03-31T23:59:59"])
    total_pedidos: int = Field(..., description="Total de pedidos concluídos.", examples=[42])
    faturamento_total: float = Field(
        ..., description="Faturamento total do período.", examples=[273.0]
    )
    por_bebida: list[VendaPorBebida] = Field(..., description="Consolidado por bebida.")


__all__ = ["RelatorioResponse", "VendaPorBebida"]
