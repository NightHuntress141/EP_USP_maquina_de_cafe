"""DTO do cardápio (RN10)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ProdutoResponse(BaseModel):
    """Item do cardápio retornado pela API.

    Attributes:
        id: Identificador da bebida (1 a 5, na ordem do cardápio).
        nome: Nome comercial da bebida.
        preco: Preço atual em reais.
        tempo_preparo: Tempo de preparo simulado, em segundos.
        disponivel: ``True`` se há estoque suficiente para preparar a bebida agora.
    """

    id: int = Field(..., description="Identificador da bebida.", examples=[4])
    nome: str = Field(..., description="Nome da bebida.", examples=["Cappuccino"])
    preco: float = Field(..., description="Preço em reais.", examples=[6.50])
    tempo_preparo: int = Field(..., description="Tempo de preparo em segundos.", examples=[12])
    disponivel: bool = Field(
        ..., description="Indica se há estoque suficiente para preparar a bebida agora.", examples=[True]
    )


__all__ = ["ProdutoResponse"]
