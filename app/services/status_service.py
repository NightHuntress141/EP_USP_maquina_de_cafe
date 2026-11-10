"""Contrato do serviço de estado da máquina.

A implementação real das regras de negócio é de responsabilidade dos demais
integrantes. Este módulo define apenas a interface consumida pela API.
"""

from __future__ import annotations

from typing import Any


def obter_status() -> dict[str, Any]:
    """Retorna o estado operacional atual da máquina e o crédito acumulado.

    Returns:
        Dicionário no formato aceito por
        :class:`app.schemas.status.StatusResponse`, com as chaves ``estado`` e
        ``credito``.

    Raises:
        NotImplementedError: Enquanto a regra de negócio não for implementada.
    """
    raise NotImplementedError("status_service.obter_status ainda não foi implementado.")


__all__ = ["obter_status"]
