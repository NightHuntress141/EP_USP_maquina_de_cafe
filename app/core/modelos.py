"""Tipos de domínio independentes de HTTP e de SQLite."""

from dataclasses import dataclass
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
