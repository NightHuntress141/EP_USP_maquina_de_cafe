"""DTO de estado da máquina (seção 2 do enunciado: Estados da máquina)."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class EstadoMaquina(str, Enum):
    """Estados possíveis da máquina de café."""

    PRONTA = "PRONTA"
    PREPARANDO = "PREPARANDO"
    AGUARDANDO_LIMPEZA = "AGUARDANDO_LIMPEZA"
    MANUTENCAO = "MANUTENCAO"


class StatusResponse(BaseModel):
    """Estado atual da máquina e crédito disponível.

    Attributes:
        estado: Estado operacional da máquina.
        credito: Crédito acumulado atual do cliente.
    """

    estado: EstadoMaquina = Field(..., description="Estado operacional atual.", examples=["PRONTA"])
    credito: float = Field(..., description="Crédito acumulado atual.", examples=[10.00])


__all__ = ["EstadoMaquina", "StatusResponse"]
