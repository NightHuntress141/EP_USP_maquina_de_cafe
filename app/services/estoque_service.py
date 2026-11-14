"""Contrato do serviço de estoque.

A implementação real das regras de negócio (RN09) é de responsabilidade dos
demais integrantes. Este módulo define apenas a interface consumida pela API.
"""

from __future__ import annotations

from typing import Any


def consultar_estoque() -> dict[str, Any]:
    """Retorna a situação de todos os reservatórios e insumos.

    Returns:
        Dicionário no formato aceito por
        :class:`app.schemas.estoque.EstoqueResponse`, com a chave
        ``reservatorios``.

    Raises:
        NotImplementedError: Enquanto a regra de negócio não for implementada.
    """
    raise NotImplementedError("estoque_service.consultar_estoque ainda não foi implementado.")


def reabastecer(item: str, quantidade: float) -> dict[str, Any]:
    """Adiciona insumo a um reservatório, respeitando sua capacidade máxima.

    Regras envolvidas:
        RN09 – o reabastecimento só é permitido com a máquina em manutenção e
        não pode ultrapassar a capacidade máxima do reservatório.

    Args:
        item: Reservatório a reabastecer, já validado pela API.
        quantidade: Quantidade a adicionar, maior que zero, já validada pela API.

    Returns:
        Dicionário no formato aceito por
        :class:`app.schemas.estoque.ReabastecimentoResponse`, com a chave
        ``item`` contendo o reservatório atualizado.

    Raises:
        EstadoInvalidoError: Se a máquina não estiver em manutenção.
        CapacidadeExcedidaError: Se a quantidade ultrapassar a capacidade.
        NotImplementedError: Enquanto a regra de negócio não for implementada.
    """
    raise NotImplementedError("estoque_service.reabastecer ainda não foi implementado.")


__all__ = ["consultar_estoque", "reabastecer"]
