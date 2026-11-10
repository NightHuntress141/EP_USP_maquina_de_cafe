"""Dependências compartilhadas da camada de API.

Concentra a autenticação do operador (RN11). Nesta entrega o módulo já fica
pronto para os endpoints de ``/operador`` da próxima rodada.
"""

from __future__ import annotations

import os

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security = HTTPBearer(auto_error=False)
"""Esquema de segurança Bearer.

``auto_error=False`` permite devolver HTTP 401 (e não o 403 padrão) quando o
cabeçalho ``Authorization`` está ausente, mantendo o corpo de erro padronizado.
"""

TOKEN_PADRAO_DEV = "senha_padrao_para_dev"
"""Token usado quando a variável de ambiente ``OPERATOR_TOKEN`` não está definida."""


def get_current_operator(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    """Valida o token do operador (RN11).

    O token recebido no cabeçalho ``Authorization: Bearer <token>`` é comparado
    com a variável de ambiente ``OPERATOR_TOKEN``.

    Args:
        credentials: Credenciais extraídas do cabeçalho HTTP pelo ``HTTPBearer``.

    Returns:
        O token validado.

    Raises:
        HTTPException: 401 caso o token esteja ausente ou seja inválido.
    """
    token_esperado = os.getenv("OPERATOR_TOKEN", TOKEN_PADRAO_DEV)
    if credentials is None or credentials.credentials != token_esperado:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token ausente ou inválido.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


__all__ = ["security", "get_current_operator", "TOKEN_PADRAO_DEV"]
