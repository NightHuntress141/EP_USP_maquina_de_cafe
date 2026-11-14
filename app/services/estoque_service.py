"""Serviço de estoque: consulta e reabastecimento dos reservatórios (RN09)."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from app.core.exceptions import (
    BancoIndisponivelError,
    CapacidadeExcedidaError,
    EstadoInvalidoError,
    OperacaoInvalidaError,
    PersistenciaError,
)
from app.core.modelos import (
    EstadoMaquina,
    Ingrediente,
    ItemEstoque,
    ResultadoEstoque,
    ResultadoReabastecimento,
)
from app.repositories.operador_repository import transacao, transacao_leitura

ITEM_POR_CODIGO = {
    "AGUA": "agua",
    "CAFE": "cafe",
    "LEITE": "leite",
    "CHOCOLATE": "chocolate",
    "ACUCAR": "acucar",
    "COPOS": "copos",
}
"""Mapeamento dos códigos internos do banco para o contrato da API."""

CODIGO_POR_ITEM = {item: codigo for codigo, item in ITEM_POR_CODIGO.items()}
"""Mapeamento inverso usado para validar chamadas diretas ao serviço."""


def _item_estoque(ingrediente: Ingrediente) -> ItemEstoque:
    """Converte o insumo persistido para o contrato de resposta.

    O alerta é considerado quando a quantidade atual é menor ou igual ao
    ``nivel_alerta`` do banco. Não há conversão de ml/g/un para outra unidade.

    Args:
        ingrediente: Insumo lido do banco.

    Returns:
        Situação pública do reservatório.
    """
    codigo = ITEM_POR_CODIGO.get(ingrediente.codigo)
    if codigo is None:
        raise PersistenciaError("Ingrediente desconhecido encontrado no banco.")
    return {
        "item": codigo,
        "atual": ingrediente.quantidade_atual,
        "capacidade": ingrediente.capacidade_maxima,
        "nivel_baixo": ingrediente.quantidade_atual <= ingrediente.nivel_alerta,
    }


def _inteiro_positivo(quantidade: object) -> int:
    """Valida uma quantidade positiva e inteira para o schema atual.

    O SQLite declara as quantidades como INT, mas não impõe integralidade pela
    afinidade de tipo. Como não há migração acordada para unidades menores,
    frações são recusadas em vez de truncadas ou arredondadas silenciosamente.

    Args:
        quantidade: Valor recebido pelo serviço, possivelmente de chamada direta.

    Returns:
        Quantidade convertida para inteiro.

    Raises:
        OperacaoInvalidaError: Se o valor não for finito, positivo e inteiro.
    """
    if isinstance(quantidade, bool) or not isinstance(quantidade, (int, float, Decimal)):
        raise OperacaoInvalidaError("A quantidade deve ser um número positivo e finito.")
    try:
        valor = Decimal(str(quantidade))
    except (InvalidOperation, ValueError) as exc:
        raise OperacaoInvalidaError("A quantidade deve ser um número positivo e finito.") from exc
    if not valor.is_finite() or valor <= 0:
        raise OperacaoInvalidaError("A quantidade deve ser um número positivo e finito.")
    if valor != valor.to_integral_value():
        raise OperacaoInvalidaError(
            "A quantidade deve ser inteira na unidade atual do reservatório."
        )
    return int(valor)


def consultar_estoque() -> ResultadoEstoque:
    """Retorna a situação de todos os reservatórios e insumos.

    Regras envolvidas:
        RN09 – o operador acompanha os seis insumos com quantidade atual,
        capacidade e indicação de nível baixo, sem alterar qualquer dado.

    Returns:
        Estoque completo no formato aceito por
        :class:`app.schemas.estoque.EstoqueResponse`.
    """
    with transacao_leitura() as repositorio:
        ingredientes = repositorio.listar_ingredientes()
    return {"reservatorios": [_item_estoque(ingrediente) for ingrediente in ingredientes]}


def reabastecer(item: str, quantidade: float) -> ResultadoReabastecimento:
    """Adiciona um insumo ao estoque em modo de manutenção.

    Regras envolvidas:
        RN09 – exige MANUTENCAO, valida a quantidade inteira positiva e respeita
        a capacidade máxima do reservatório. O estoque e a auditoria são
        gravados na mesma transação, sem alterar crédito, estado ou limpeza.

    Args:
        item: Código do insumo no contrato da API (agua, cafe, leite etc.).
        quantidade: Quantidade positiva, na unidade definida para o insumo.

    Returns:
        Situação atualizada do reservatório.

    Raises:
        OperacaoInvalidaError: Se o item ou a quantidade forem inválidos.
        EstadoInvalidoError: Se a máquina não estiver em manutenção.
        CapacidadeExcedidaError: Se a capacidade máxima for ultrapassada.
        BancoIndisponivelError: Se o banco ou o insumo não estiverem disponíveis.
    """
    codigo = CODIGO_POR_ITEM.get(getattr(item, "value", item))
    if codigo is None:
        raise OperacaoInvalidaError("Item de estoque inválido.")
    adicionado = _inteiro_positivo(quantidade)

    with transacao() as repositorio:
        maquina = repositorio.obter_maquina()
        if maquina.estado != EstadoMaquina.MANUTENCAO:
            raise EstadoInvalidoError("O reabastecimento exige a máquina em manutenção.")
        ingrediente = repositorio.obter_ingrediente(codigo)
        if ingrediente is None:
            raise BancoIndisponivelError("Insumo não encontrado no banco inicializado.")
        nova_quantidade = ingrediente.quantidade_atual + adicionado
        if nova_quantidade > ingrediente.capacidade_maxima:
            raise CapacidadeExcedidaError("A quantidade excede a capacidade do reservatório.")
        repositorio.atualizar_estoque(ingrediente.id, nova_quantidade)
        repositorio.registrar_reabastecimento(ingrediente.id, adicionado)
        atualizado = Ingrediente(
            id=ingrediente.id,
            codigo=ingrediente.codigo,
            unidade=ingrediente.unidade,
            quantidade_atual=nova_quantidade,
            capacidade_maxima=ingrediente.capacidade_maxima,
            nivel_alerta=ingrediente.nivel_alerta,
        )
    return {"item": _item_estoque(atualizado)}


__all__ = ["consultar_estoque", "reabastecer"]
