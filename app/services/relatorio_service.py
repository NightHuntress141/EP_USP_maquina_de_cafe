"""Serviço de relatórios: consolidação de vendas concluídas (RN12)."""

from __future__ import annotations

from datetime import datetime

from app.core.exceptions import OperacaoInvalidaError, PersistenciaError
from app.core.modelos import (
    PedidoConcluido,
    ResultadoRelatorio,
    VendaPorBebida,
    normalizar_utc,
)
from app.core.valores import para_centavos
from app.repositories.operador_repository import transacao_leitura


def gerar_relatorio(inicio: datetime, fim: datetime) -> ResultadoRelatorio:
    """Gera o relatório consolidado de vendas do período.

    Regras envolvidas:
        RN12 – considera somente pedidos ``CONCLUIDO``, com ``inicio`` e ``fim``
        inclusivos, agrupa pela identidade da bebida e usa ``preco_cobrado``
        (preço histórico) em vez do preço atual do produto.

    Decisões de contrato:
        - O instante da venda é ``pedido.criado_em`` porque o schema não possui
          ``finalizado_em``. Uma conclusão real exigirá coluna/migração e
          integração com o serviço de pedidos.
        - Datas sem fuso são interpretadas como UTC e todas as comparações são
          feitas em UTC. Os campos ``inicio`` e ``fim`` devolvidos preservam os
          valores recebidos.
        - Os valores são acumulados em centavos inteiros, a partir de Decimal,
          em vez de ``SUM`` de floats.

    Args:
        inicio: Início do período (inclusive).
        fim: Fim do período (inclusive).

    Returns:
        Relatório no formato aceito por :class:`app.schemas.relatorio.RelatorioResponse`.

    Raises:
        OperacaoInvalidaError: Se as datas forem inválidas ou se ``inicio > fim``.
        PersistenciaError: Se houver valor histórico inválido no banco.
    """
    if not isinstance(inicio, datetime) or not isinstance(fim, datetime):
        raise OperacaoInvalidaError("O período deve ser informado com datas válidas.")
    inicio_utc = normalizar_utc(inicio)
    fim_utc = normalizar_utc(fim)
    if inicio_utc > fim_utc:
        raise OperacaoInvalidaError("O início do período deve ser anterior ou igual ao fim.")

    with transacao_leitura() as repositorio:
        pedidos = repositorio.listar_pedidos_concluidos()

    total_centavos = 0
    total_pedidos = 0
    grupos: dict[int, dict[str, int | str]] = {}
    for pedido in pedidos:
        if not _no_periodo(pedido, inicio_utc, fim_utc):
            continue
        centavos = _centavos_historicos(pedido)
        total_centavos += centavos
        total_pedidos += 1
        grupo = grupos.setdefault(
            pedido.produto_id, {"nome": pedido.nome, "quantidade": 0, "centavos": 0}
        )
        grupo["quantidade"] = int(grupo["quantidade"]) + 1
        grupo["centavos"] = int(grupo["centavos"]) + centavos

    por_bebida: list[VendaPorBebida] = [
        {
            "produto_id": produto_id,
            "nome": str(grupo["nome"]),
            "quantidade": int(grupo["quantidade"]),
            "faturamento": int(grupo["centavos"]) / 100,
        }
        for produto_id, grupo in sorted(grupos.items())
    ]
    return {
        "inicio": inicio,
        "fim": fim,
        "total_pedidos": total_pedidos,
        "faturamento_total": total_centavos / 100,
        "por_bebida": por_bebida,
    }


def _no_periodo(pedido: PedidoConcluido, inicio_utc: datetime, fim_utc: datetime) -> bool:
    """Verifica se o pedido concluído pertence ao intervalo inclusivo em UTC.

    Args:
        pedido: Pedido lido do repositório.
        inicio_utc: Início normalizado para UTC.
        fim_utc: Fim normalizado para UTC.

    Returns:
        ``True`` quando ``inicio <= criado_em <= fim``.
    """
    criado_em = normalizar_utc(pedido.criado_em)
    return inicio_utc <= criado_em <= fim_utc


def _centavos_historicos(pedido: PedidoConcluido) -> int:
    """Converte o preço histórico em centavos exatos.

    Args:
        pedido: Pedido com ``preco_cobrado`` lido do banco.

    Returns:
        Preço histórico em centavos.

    Raises:
        PersistenciaError: Se o valor persistido não representar centavos exatos.
    """
    try:
        return para_centavos(pedido.preco_cobrado)
    except ValueError as exc:
        raise PersistenciaError("Valor histórico inválido encontrado no banco.") from exc


__all__ = ["gerar_relatorio"]
