"""DTO do corpo padronizado de erro."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ErroResponse(BaseModel):
    """Corpo de erro padronizado devolvido pela API.

    Attributes:
        erro: Identificador curto do erro (slug em maiúsculas).
        mensagem: Descrição legível do erro.
    """

    erro: str = Field(..., description="Identificador do erro.", examples=["MAQUINA_OCUPADA"])
    mensagem: str = Field(
        ..., description="Descrição legível do erro.", examples=["A máquina está preparando outra bebida."]
    )


__all__ = ["ErroResponse"]
