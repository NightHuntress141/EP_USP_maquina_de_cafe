"""Contrato do serviço de pedidos.

A implementação real das regras de negócio (RN02 a RN05) é de responsabilidade
dos demais integrantes. Este módulo define apenas a interface consumida pela API.
"""

from __future__ import annotations

from typing import Any


def criar_pedido(produto_id: int, acucar: int) -> dict[str, Any]:
    """Cria um novo pedido de bebida.

    Regras envolvidas:
        RN02 – aceita apenas com a máquina PRONTA, crédito suficiente e estoque
        suficiente de ingredientes, açúcar e copo.
        RN03 – debita o preço do crédito e desconta os ingredientes do estoque.
        RN04 – o pedido nasce EM_PREPARO e a máquina passa a PREPARANDO.

    Args:
        produto_id: Identificador da bebida desejada.
        acucar: Porções de açúcar (0 a 3), já validadas pela API.

    Returns:
        Dicionário no formato aceito por
        :class:`app.schemas.pedido.PedidoResponse`.

    Raises:
        BebidaNaoEncontradaError: Se a bebida não existir no cardápio.
        CreditoInsuficienteError: Se o crédito não cobrir o preço.
        EstoqueInsuficienteError: Se faltar ingrediente, açúcar ou copo.
        MaquinaOcupadaError: Se houver outra bebida em preparo.
        MaquinaIndisponivelError: Se a máquina estiver em manutenção/limpeza.
        NotImplementedError: Enquanto a regra de negócio não for implementada.
    """
    raise NotImplementedError("pedido_service.criar_pedido ainda não foi implementado.")


def consultar_pedido(pedido_id: int) -> dict[str, Any]:
    """Consulta um pedido e calcula seu status atual.

    Regras envolvidas:
        RN04 – o status é calculado no momento da consulta (sem timer):
        EM_PREPARO até o horário previsto de término, depois CONCLUIDO.

    Args:
        pedido_id: Identificador do pedido.

    Returns:
        Dicionário no formato aceito por
        :class:`app.schemas.pedido.PedidoResponse`.

    Raises:
        PedidoNaoEncontradoError: Se o pedido não existir.
        NotImplementedError: Enquanto a regra de negócio não for implementada.
    """
    raise NotImplementedError("pedido_service.consultar_pedido ainda não foi implementado.")


def cancelar_pedido(pedido_id: int) -> dict[str, Any]:
    """Cancela um pedido que esteja EM_PREPARO.

    Regras envolvidas:
        RN05 – permitido apenas com o pedido EM_PREPARO; o valor é devolvido ao
        crédito, os ingredientes já consumidos não retornam ao estoque e a
        máquina volta a PRONTA.

    Args:
        pedido_id: Identificador do pedido.

    Returns:
        Dicionário no formato aceito por
        :class:`app.schemas.pedido.PedidoResponse`, com status CANCELADO.

    Raises:
        PedidoNaoEncontradoError: Se o pedido não existir.
        OperacaoInvalidaError: Se o pedido não estiver EM_PREPARO.
        NotImplementedError: Enquanto a regra de negócio não for implementada.
    """
    raise NotImplementedError("pedido_service.cancelar_pedido ainda não foi implementado.")


__all__ = ["criar_pedido", "consultar_pedido", "cancelar_pedido"]
