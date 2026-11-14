"""Tipos de domínio independentes de HTTP e de SQLite."""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import TypedDict


class EstadoMaquina(str, Enum):
    """Estados operacionais permitidos para a máquina."""

    PRONTA = "PRONTA"
    PREPARANDO = "PREPARANDO"
    AGUARDANDO_LIMPEZA = "AGUARDANDO_LIMPEZA"
    MANUTENCAO = "MANUTENCAO"


@dataclass(frozen=True)
class Maquina:
    """Estado e contador persistidos da máquina única."""

    estado: EstadoMaquina
    preparos_desde_limpeza: int


class ProdutoAtualizado(TypedDict):
    """Dados públicos da bebida após uma alteração de preço."""

    id: int
    nome: str
    preco: float
    tempo_preparo: int
    disponivel: bool


class ResultadoManutencao(TypedDict):
    """Estado operacional resultante de uma transição."""

    estado: EstadoMaquina


class ResultadoLimpeza(TypedDict):
    """Estado e contador após o registro da limpeza."""

    estado: EstadoMaquina
    preparos_desde_limpeza: int


@dataclass(frozen=True)
class Ingrediente:
    """Reservatório ou insumo com os limites persistidos.

    Attributes:
        id: Identificador do ingrediente.
        codigo: Código interno em maiúsculas (AGUA, CAFE etc.).
        unidade: Unidade do seed (ml, g ou un), sem conversão implícita.
        quantidade_atual: Quantidade disponível na unidade do insumo.
        capacidade_maxima: Capacidade máxima na mesma unidade.
        nivel_alerta: Limite a partir do qual o nível é considerado baixo.
    """

    id: int
    codigo: str
    unidade: str
    quantidade_atual: int
    capacidade_maxima: int
    nivel_alerta: int


@dataclass(frozen=True)
class PedidoConcluido:
    """Pedido concluído usado na consolidação do relatório (RN12).

    Attributes:
        pedido_id: Identificador do pedido.
        produto_id: Identificador da bebida vendida.
        nome: Nome da bebida no momento da consulta.
        preco_cobrado: Preço histórico em reais, sem depender do preço atual.
        criado_em: Instante de criação usado como referência temporal da venda.
    """

    pedido_id: int
    produto_id: int
    nome: str
    preco_cobrado: Decimal
    criado_em: datetime


class ItemEstoque(TypedDict):
    """Situação pública de um reservatório no contrato da API."""

    item: str
    atual: float
    capacidade: float
    nivel_baixo: bool


class ResultadoEstoque(TypedDict):
    """Estoque completo devolvido ao operador."""

    reservatorios: list[ItemEstoque]


class ResultadoReabastecimento(TypedDict):
    """Reservatório atualizado após o reabastecimento."""

    item: ItemEstoque


class VendaPorBebida(TypedDict):
    """Consolidado de uma bebida no relatório."""

    produto_id: int
    nome: str
    quantidade: int
    faturamento: float


class ResultadoRelatorio(TypedDict):
    """Relatório consolidado de vendas do período."""

    inicio: datetime
    fim: datetime
    total_pedidos: int
    faturamento_total: float
    por_bebida: list[VendaPorBebida]


def normalizar_utc(valor: datetime) -> datetime:
    """Interpreta datas sem fuso como UTC e converte as demais para UTC.

    Args:
        valor: Data/hora recebida ou persistida.

    Returns:
        Data/hora com fuso UTC, própria para comparação consistente.
    """
    if valor.tzinfo is None:
        return valor.replace(tzinfo=timezone.utc)
    return valor.astimezone(timezone.utc)
