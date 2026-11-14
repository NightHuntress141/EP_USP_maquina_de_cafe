"""DTOs de estoque e reabastecimento (RN09)."""

from __future__ import annotations

from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator


class ItemReservatorio(str, Enum):
    """Reservatórios e insumos controlados pela máquina."""

    AGUA = "agua"
    CAFE = "cafe"
    LEITE = "leite"
    CHOCOLATE = "chocolate"
    ACUCAR = "acucar"
    COPOS = "copos"


class ItemEstoque(BaseModel):
    """Situação atual de um reservatório ou insumo.

    Attributes:
        item: Identificador do reservatório.
        atual: Quantidade disponível no momento.
        capacidade: Capacidade máxima do reservatório.
        nivel_baixo: Indica se o nível está abaixo do limite de alerta.
    """

    item: ItemReservatorio = Field(..., description="Reservatório ou insumo.", examples=["leite"])
    atual: float = Field(..., description="Quantidade disponível.", examples=[2.5])
    capacidade: float = Field(..., description="Capacidade máxima.", examples=[10.0])
    nivel_baixo: bool = Field(
        ..., description="Indica nível abaixo do limite de alerta.", examples=[True]
    )


class EstoqueResponse(BaseModel):
    """Estoque completo da máquina.

    Attributes:
        reservatorios: Situação de cada reservatório ou insumo.
    """

    reservatorios: list[ItemEstoque] = Field(..., description="Situação de todos os reservatórios.")


class ReabastecimentoRequest(BaseModel):
    """Corpo da requisição de reabastecimento (RN09).

    Attributes:
        item: Reservatório a reabastecer.
        quantidade: Quantidade a adicionar, em unidades do insumo.
    """

    item: ItemReservatorio = Field(
        ..., description="Reservatório a reabastecer.", examples=["agua"]
    )
    quantidade: float = Field(
        ...,
        gt=0,
        allow_inf_nan=False,
        description="Quantidade a adicionar.",
        examples=[1.5],
    )

    @field_validator("quantidade", mode="before")
    @classmethod
    def recusar_valor_nao_numerico(cls, quantidade: object) -> object:
        """Impede coerções laxas de booleanos e textos para quantidade.

        Args:
            quantidade: Valor bruto recebido no JSON.

        Returns:
            O próprio valor, quando for um número.

        Raises:
            ValueError: Se o valor não for int, float ou Decimal.
        """
        if isinstance(quantidade, bool) or not isinstance(quantidade, (int, float, Decimal)):
            raise ValueError("A quantidade deve ser um número.")
        return quantidade

    @model_validator(mode="after")
    def validar_copos(self) -> ReabastecimentoRequest:
        """Exige unidades inteiras quando o insumo é COPOS.

        Returns:
            Requisição validada, preservando as unidades dos demais insumos.

        Raises:
            ValueError: Se a quantidade de copos for fracionária.
        """
        if self.item == ItemReservatorio.COPOS and not self.quantidade.is_integer():
            raise ValueError("A quantidade de copos deve ser inteira.")
        return self


class ReabastecimentoResponse(BaseModel):
    """Reservatório atualizado após o reabastecimento.

    Attributes:
        item: Situação atualizada do reservatório reabastecido.
    """

    item: ItemEstoque = Field(..., description="Reservatório após o reabastecimento.")


__all__ = [
    "EstoqueResponse",
    "ItemEstoque",
    "ItemReservatorio",
    "ReabastecimentoRequest",
    "ReabastecimentoResponse",
]
