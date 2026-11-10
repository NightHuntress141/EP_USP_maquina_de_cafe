"""DTOs de crédito e troco (RN01 e RN06)."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

VALORES_CREDITO_ACEITOS: tuple[float, ...] = (0.50, 1.00, 2.00, 5.00, 10.00, 20.00)
"""Valores de crédito aceitos pela máquina (RN01)."""


class CreditoRequest(BaseModel):
    """Corpo da requisição de inserção de crédito.

    Attributes:
        valor: Valor a ser inserido. Deve ser um dos valores aceitos (RN01).
    """

    valor: float = Field(
        ...,
        gt=0,
        description="Valor a inserir. Aceitos: 0.50, 1.00, 2.00, 5.00, 10.00 e 20.00 (RN01).",
        examples=[10.00],
    )

    @field_validator("valor")
    @classmethod
    def _validar_valor_aceito(cls, valor: float) -> float:
        """Garante que o valor pertence ao conjunto aceito pela RN01.

        Args:
            valor: Valor informado na requisição.

        Returns:
            O próprio valor, quando válido.

        Raises:
            ValueError: Se o valor não for um dos aceitos pela máquina.
        """
        if round(valor, 2) not in VALORES_CREDITO_ACEITOS:
            aceitos = ", ".join(f"R$ {v:.2f}" for v in VALORES_CREDITO_ACEITOS)
            raise ValueError(f"Valor de crédito não aceito. Aceitos: {aceitos}.")
        return valor


class CreditoResponse(BaseModel):
    """Resposta com o crédito acumulado atual.

    Attributes:
        credito: Crédito total disponível na máquina após a operação.
    """

    credito: float = Field(..., description="Crédito acumulado atual.", examples=[10.00])


class TrocoResponse(BaseModel):
    """Resposta da devolução de todo o crédito restante (RN06).

    Attributes:
        valor_devolvido: Valor devolvido ao cliente.
        credito: Crédito restante após a devolução (sempre zero).
    """

    valor_devolvido: float = Field(..., description="Valor devolvido ao cliente.", examples=[3.50])
    credito: float = Field(..., description="Crédito restante após o troco.", examples=[0.00])


__all__ = ["VALORES_CREDITO_ACEITOS", "CreditoRequest", "CreditoResponse", "TrocoResponse"]
