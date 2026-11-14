"""Dependências compartilhadas da camada de API.

Concentra a autenticação do operador (RN11), com token obrigatório.
"""

from __future__ import annotations

from secrets import compare_digest
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import token_operador

security = HTTPBearer(auto_error=False)
"""Esquema de segurança Bearer.

``auto_error=False`` permite devolver HTTP 401 (e não o 403 padrão) quando o
cabeçalho ``Authorization`` está ausente, mantendo o corpo de erro padronizado.
"""


def get_current_operator(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> str:
    """Valida o token do operador (RN11).

    O token recebido no cabeçalho ``Authorization: Bearer <token>`` é comparado
    com a variável de ambiente ``OPERATOR_TOKEN``.

    Args:
        credentials: Credenciais extraídas do cabeçalho HTTP pelo ``HTTPBearer``.

    Returns:
        O token validado.

    Raises:
        HTTPException: 401 para credencial inválida; 503 para configuração ausente.
    """
    try:
        token_esperado = token_operador()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503, detail="Autenticação do operador não configurada."
        ) from exc
    if credentials is None or not compare_digest(
        credentials.credentials.encode("utf-8"), token_esperado.encode("utf-8")
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token ausente ou inválido.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


__all__ = ["get_current_operator", "security"]
