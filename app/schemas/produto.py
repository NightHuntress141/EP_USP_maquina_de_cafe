"""DTO do cardápio (RN10)."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.core.valores import para_centavos


class PrecoRequest(BaseModel):
    """Corpo da requisição de alteração de preço (RN10).

    Attributes:
        preco: Novo preço da bebida, em reais.
    """

    preco: Decimal = Field(
        ...,
        gt=0,
        le=Decimal("99999999.99"),
        allow_inf_nan=False,
        description="Preço em reais, com no máximo duas casas decimais.",
        examples=[7.00],
    )

    @field_validator("preco")
    @classmethod
    def validar_preco(cls, preco: Decimal) -> Decimal:
        """Recusa frações de centavo sem arredondar a entrada.

        Args:
            preco: Preço informado em reais.

        Returns:
            Valor validado.
        """
        para_centavos(preco)
        return preco


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
        ...,
        description="Indica se há estoque suficiente para preparar a bebida agora.",
        examples=[True],
    )


__all__ = ["PrecoRequest", "ProdutoResponse"]
