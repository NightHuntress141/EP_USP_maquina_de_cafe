"""Contrato do serviço de relatórios.

A implementação real das regras de negócio (RN12) é de responsabilidade dos
demais integrantes. Este módulo define apenas a interface consumida pela API.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


def gerar_relatorio(inicio: datetime, fim: datetime) -> dict[str, Any]:
    """Gera o relatório consolidado de vendas do período.

    Regras envolvidas:
        RN12 – consolida os pedidos concluídos no intervalo informado, com total
        de pedidos, faturamento total e detalhamento por bebida.

    Args:
        inicio: Início do período (inclusive), já validado pela API.
        fim: Fim do período (inclusive), já validado pela API.

    Returns:
        Dicionário no formato aceito por
        :class:`app.schemas.relatorio.RelatorioResponse`.

    Raises:
        NotImplementedError: Enquanto a regra de negócio não for implementada.
    """
    raise NotImplementedError("relatorio_service.gerar_relatorio ainda não foi implementado.")


__all__ = ["gerar_relatorio"]
