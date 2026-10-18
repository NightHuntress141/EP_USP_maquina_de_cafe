"""Contrato do serviço de crédito.

A implementação real das regras de negócio (RN01 e RN06) é de responsabilidade
dos demais integrantes. Este módulo define apenas a interface consumida pela API.
"""

from __future__ import annotations

from typing import Any


def adicionar_credito(valor: float) -> float:
    """Insere um valor de crédito e devolve o crédito acumulado.

    Regras envolvidas:
        RN01 – valores aceitos e limite de crédito acumulado (no máximo R$ 50,00).

    Args:
        valor: Valor a inserir (já validado quanto ao conjunto aceito pela API).

    Returns:
        Crédito acumulado após a inserção.

    Raises:
        ValueError: Se o valor acumulado exceder o limite da RN01.
        NotImplementedError: Enquanto a regra de negócio não for implementada.
    """
    raise NotImplementedError("credito_service.adicionar_credito ainda não foi implementado.")


def devolver_troco() -> dict[str, Any]:
    """Devolve todo o crédito restante e zera o saldo.

    Regras envolvidas:
        RN06 – a devolução zera o crédito acumulado.

    Returns:
        Dicionário no formato aceito por
        :class:`app.schemas.credito.TrocoResponse`, com as chaves
        ``valor_devolvido`` e ``credito``.

    Raises:
        NotImplementedError: Enquanto a regra de negócio não for implementada.
    """
    raise NotImplementedError("credito_service.devolver_troco ainda não foi implementado.")


__all__ = ["adicionar_credito", "devolver_troco"]
