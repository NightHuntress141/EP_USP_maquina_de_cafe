"""Contrato do serviço de produtos (cardápio).

A implementação real das regras de negócio (RN10) é de responsabilidade dos
demais integrantes. Este módulo define apenas a interface consumida pela API.
"""

from __future__ import annotations

from typing import Any


def listar_produtos() -> list[dict[str, Any]]:
    """Retorna o cardápio completo com preço, tempo de preparo e disponibilidade.

    Regras envolvidas:
        RN10 – o cardápio informa se cada bebida está disponível, isto é, se há
        estoque suficiente para prepará-la agora.

    Returns:
        Lista de dicionários no formato aceito por
        :class:`app.schemas.produto.ProdutoResponse`.

    Raises:
        NotImplementedError: Enquanto a regra de negócio não for implementada.
    """
    raise NotImplementedError("produto_service.listar_produtos ainda não foi implementado.")


__all__ = ["listar_produtos"]
