"""DTOs do fluxo do operador (RN07, RN08 e RN11)."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from app.schemas.status import EstadoMaquina


class LoginRequest(BaseModel):
    """Credenciais de acesso do operador (RN11).

    Attributes:
        usuario: Nome de usuário do operador.
        senha: Senha do operador.
    """

    usuario: str = Field(..., min_length=1, description="Usuário do operador.", examples=["operador"])
    senha: str = Field(..., min_length=1, description="Senha do operador.", examples=["senha_padrao_para_dev"])


class LoginResponse(BaseModel):
    """Token de acesso concedido ao operador (RN11).

    Attributes:
        token: Token a ser enviado no cabeçalho ``Authorization``.
        tipo: Esquema de autenticação, sempre ``bearer``.
    """

    token: str = Field(..., description="Token de acesso do operador.", examples=["senha_padrao_para_dev"])
    tipo: str = Field("bearer", description="Tipo do token.", examples=["bearer"])


class AcaoManutencao(str, Enum):
    """Ações de manutenção disponíveis ao operador (RN08)."""

    ENTRAR = "ENTRAR"
    SAIR = "SAIR"


class ManutencaoRequest(BaseModel):
    """Corpo da requisição de entrada/saída de manutenção (RN08).

    Attributes:
        acao: Ação a executar (``ENTRAR`` ou ``SAIR``).
    """

    acao: AcaoManutencao = Field(..., description="Ação de manutenção.", examples=["ENTRAR"])


class ManutencaoResponse(BaseModel):
    """Estado da máquina após a alteração de manutenção.

    Attributes:
        estado: Estado operacional atual da máquina.
    """

    estado: EstadoMaquina = Field(..., description="Estado atual da máquina.", examples=["MANUTENCAO"])


class LimpezaResponse(BaseModel):
    """Resultado do registro de limpeza (RN07).

    Attributes:
        preparos_desde_limpeza: Contador de preparos desde a última limpeza.
        estado: Estado da máquina após a limpeza.
    """

    preparos_desde_limpeza: int = Field(..., description="Preparos desde a última limpeza.", examples=[0])
    estado: EstadoMaquina = Field(..., description="Estado atual da máquina.", examples=["PRONTA"])


__all__ = [
    "LoginRequest",
    "LoginResponse",
    "AcaoManutencao",
    "ManutencaoRequest",
    "ManutencaoResponse",
    "LimpezaResponse",
]
