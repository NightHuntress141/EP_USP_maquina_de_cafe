"""Serviço de produtos: alteração de preço e contrato de consulta do cardápio."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.core.exceptions import BebidaNaoEncontradaError, OperacaoInvalidaError
from app.core.modelos import ProdutoAtualizado
from app.core.valores import para_centavos, validar_id
from app.repositories.operador_repository import transacao


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


def alterar_preco(produto_id: int, preco: Decimal | float) -> ProdutoAtualizado:
    """Atualiza o preço de uma bebida existente do cardápio (RN10).

    Args:
        produto_id: Identificador positivo representável pelo banco.
        preco: Valor em reais com no máximo duas casas decimais.

    Returns:
        Bebida com preço atualizado e disponibilidade calculada pela receita.

    Raises:
        OperacaoInvalidaError: Se o ID ou o preço não respeitarem os limites.
        BebidaNaoEncontradaError: Se a bebida não estiver cadastrada.
    """
    try:
        validar_id(produto_id)
        centavos = para_centavos(preco)
    except ValueError as exc:
        raise OperacaoInvalidaError(str(exc)) from exc
    with transacao() as repositorio:
        produto = repositorio.obter_produto(produto_id)
        if produto is None:
            raise BebidaNaoEncontradaError("Bebida não encontrada no cardápio.")
        repositorio.atualizar_preco(produto_id, centavos)
        produto["preco"] = centavos / 100
        return produto


__all__ = ["alterar_preco", "listar_produtos"]
