"""Persistência SQLite do operador e unidade de trabalho transacional."""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal

from app.core.config import caminho_banco, timeout_banco
from app.core.exceptions import BancoIndisponivelError, PersistenciaError
from app.core.modelos import (
    EstadoMaquina,
    Ingrediente,
    Maquina,
    PedidoConcluido,
    ProdutoAtualizado,
)

logger = logging.getLogger(__name__)

CODIGOS_BANCO_INDISPONIVEL = {
    sqlite3.SQLITE_BUSY,
    sqlite3.SQLITE_LOCKED,
    sqlite3.SQLITE_CANTOPEN,
    sqlite3.SQLITE_IOERR,
    sqlite3.SQLITE_NOTADB,
    sqlite3.SQLITE_PROTOCOL,
}
"""Códigos de ``OperationalError`` tratados como indisponibilidade temporária."""


class OperadorRepository:
    """Operações de persistência que compartilham uma única transação."""

    def __init__(self, conexao: sqlite3.Connection) -> None:
        """Recebe a conexão administrada pela unidade de trabalho.

        Args:
            conexao: Conexão da transação atual.
        """
        self._conexao = conexao

    def obter_maquina(self) -> Maquina:
        """Consulta o estado e contador da máquina única.

        Returns:
            Estado de domínio independente de SQLite.

        Raises:
            BancoIndisponivelError: Se o seed não tiver sido carregado.
        """
        linha = self._conexao.execute(
            "SELECT estado, preparos_desde_limpeza FROM maquina WHERE id = 1"
        ).fetchone()
        if linha is None:
            raise BancoIndisponivelError("Banco não inicializado corretamente.")
        return Maquina(EstadoMaquina(linha["estado"]), linha["preparos_desde_limpeza"])

    def atualizar_estado(self, estado: EstadoMaquina) -> None:
        """Persiste uma transição já validada pelo serviço.

        Args:
            estado: Novo estado operacional.
        """
        self._conexao.execute("UPDATE maquina SET estado = ? WHERE id = 1", (estado.value,))

    def registrar_limpeza(self) -> None:
        """Registra a auditoria e zera o contador na mesma transação.

        A geração do ID é protegida pelo BEGIN IMMEDIATE da unidade de trabalho.
        """
        self._conexao.execute(
            "INSERT INTO limpeza (id, realizada_em) "
            "SELECT COALESCE(MAX(id), 0) + 1, CURRENT_TIMESTAMP FROM limpeza"
        )
        self._conexao.execute("UPDATE maquina SET preparos_desde_limpeza = 0 WHERE id = 1")

    def obter_produto(self, produto_id: int) -> ProdutoAtualizado | None:
        """Consulta uma bebida e sua disponibilidade pela receita.

        Args:
            produto_id: Identificador validado pelo serviço.

        Returns:
            Dados públicos da bebida, ou None quando inexistente.
        """
        produto = self._conexao.execute(
            "SELECT id, nome, preco_centavos, tempo_preparo_s FROM produto WHERE id = ?",
            (produto_id,),
        ).fetchone()
        if produto is None:
            return None
        receita = self._conexao.execute(
            "SELECT r.quantidade, i.quantidade_atual FROM receita_item r "
            "JOIN ingrediente i ON i.id = r.ingrediente_id WHERE r.produto_id = ?",
            (produto_id,),
        ).fetchall()
        return {
            "id": produto["id"],
            "nome": produto["nome"],
            "preco": produto["preco_centavos"] / 100,
            "tempo_preparo": produto["tempo_preparo_s"],
            "disponivel": bool(receita)
            and all(item["quantidade_atual"] >= item["quantidade"] for item in receita),
        }

    def listar_ingredientes(self) -> list[Ingrediente]:
        """Lista os reservatórios e insumos em ordem determinística por ID.

        Returns:
            Ingredientes mapeados para o domínio, na unidade do seed.
        """
        linhas = self._conexao.execute(
            "SELECT id, codigo, unidade, quantidade_atual, capacidade_maxima, nivel_alerta "
            "FROM ingrediente ORDER BY id"
        ).fetchall()
        return [self._ingrediente(linha) for linha in linhas]

    def obter_ingrediente(self, codigo: str) -> Ingrediente | None:
        """Consulta um ingrediente pelo código interno do banco.

        Args:
            codigo: Código em maiúsculas, já validado pelo serviço.

        Returns:
            Ingrediente encontrado, ou None quando não cadastrado.
        """
        linha = self._conexao.execute(
            "SELECT id, codigo, unidade, quantidade_atual, capacidade_maxima, nivel_alerta "
            "FROM ingrediente WHERE codigo = ?",
            (codigo,),
        ).fetchone()
        return None if linha is None else self._ingrediente(linha)

    @staticmethod
    def _ingrediente(linha: sqlite3.Row) -> Ingrediente:
        """Mapeia uma linha de ingrediente para o domínio."""
        return Ingrediente(
            id=linha["id"],
            codigo=linha["codigo"],
            unidade=linha["unidade"],
            quantidade_atual=linha["quantidade_atual"],
            capacidade_maxima=linha["capacidade_maxima"],
            nivel_alerta=linha["nivel_alerta"],
        )

    def atualizar_estoque(self, ingrediente_id: int, quantidade: int) -> None:
        """Persiste a quantidade validada de um reservatório.

        Args:
            ingrediente_id: Identificador do ingrediente.
            quantidade: Nova quantidade, já convertida para inteiro.
        """
        self._conexao.execute(
            "UPDATE ingrediente SET quantidade_atual = ? WHERE id = ?",
            (quantidade, ingrediente_id),
        )

    def registrar_reabastecimento(self, ingrediente_id: int, quantidade: int) -> None:
        """Insere a auditoria do reabastecimento na transação corrente.

        O ID é gerado de forma explícita porque ``INT PRIMARY KEY`` não é
        autoincremento no SQLite; a leitura e a inserção são protegidas pelo
        ``BEGIN IMMEDIATE`` da unidade de trabalho.

        Args:
            ingrediente_id: Identificador do ingrediente reabastecido.
            quantidade: Quantidade inteira adicionada.
        """
        self._conexao.execute(
            "INSERT INTO reabastecimento (id, ingrediente_id, quantidade, criado_em) "
            "SELECT COALESCE(MAX(id), 0) + 1, ?, ?, CURRENT_TIMESTAMP FROM reabastecimento",
            (ingrediente_id, quantidade),
        )

    def listar_pedidos_concluidos(self) -> list[PedidoConcluido]:
        """Lista pedidos concluídos para a consolidação do relatório.

        O filtro de período é aplicado pelo serviço, com normalização de fuso,
        para não depender do formato textual gravado em ``criado_em``.

        Returns:
            Pedidos concluídos em ordem de identificador.

        Raises:
            PersistenciaError: Se uma data ou valor histórico for inválido.
        """
        linhas = self._conexao.execute(
            "SELECT p.id, p.produto_id, pr.nome, p.preco_cobrado, p.criado_em "
            "FROM pedido p JOIN produto pr ON pr.id = p.produto_id "
            "WHERE p.status = 'CONCLUIDO' ORDER BY p.id"
        ).fetchall()
        return [
            PedidoConcluido(
                pedido_id=linha["id"],
                produto_id=linha["produto_id"],
                nome=linha["nome"],
                preco_cobrado=Decimal(str(linha["preco_cobrado"])),
                criado_em=_converter_data(linha["criado_em"]),
            )
            for linha in linhas
        ]

    def atualizar_preco(self, produto_id: int, centavos: int) -> None:
        """Armazena o preço como inteiro, sem perda de precisão decimal.

        Args:
            produto_id: Identificador da bebida existente.
            centavos: Preço validado em centavos.
        """
        self._conexao.execute(
            "UPDATE produto SET preco_centavos = ? WHERE id = ?", (centavos, produto_id)
        )

    def validar_schema(self) -> None:
        """Verifica as tabelas usadas pelos serviços e a migração monetária.

        Raises:
            BancoIndisponivelError: Se o banco precisar ser inicializado ou migrado.
        """
        colunas = {linha["name"] for linha in self._conexao.execute("PRAGMA table_info(produto)")}
        if "preco_centavos" not in colunas:
            raise BancoIndisponivelError("Inicialize ou migre o banco antes de iniciar a API.")
        self.obter_maquina()
        for tabela in ("limpeza", "ingrediente", "receita_item", "pedido", "reabastecimento"):
            # Nomes constantes definidos pela aplicação, nunca fornecidos pelo cliente.
            if (
                self._conexao.execute(
                    "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
                    (tabela,),
                ).fetchone()
                is None
            ):
                raise BancoIndisponivelError("Banco não inicializado corretamente.")


def _converter_data(valor: object) -> datetime:
    """Converte o timestamp persistido em datetime, preservando o fuso existente.

    Args:
        valor: Texto ISO/UTC ou datetime devolvido pelo driver.

    Returns:
        Data/hora correspondente.

    Raises:
        PersistenciaError: Se o valor não for uma data reconhecível.
    """
    if isinstance(valor, datetime):
        return valor
    try:
        return datetime.fromisoformat(str(valor))
    except ValueError as exc:
        raise PersistenciaError("Data inválida encontrada no banco.") from exc


@contextmanager
def transacao() -> Iterator[OperadorRepository]:
    """Abre uma unidade de trabalho com commit, rollback e fechamento garantidos.

    Returns:
        Contexto com o repositório ligado à transação de escrita atual.

    Raises:
        BancoIndisponivelError: Se o banco estiver ausente, bloqueado ou inacessível.
        PersistenciaError: Se uma gravação falhar por integridade ou erro interno.
    """
    conexao: sqlite3.Connection | None = None
    try:
        # mode=rw impede criar silenciosamente um banco vazio em um caminho incorreto.
        conexao = sqlite3.connect(
            caminho_banco().as_uri() + "?mode=rw", uri=True, timeout=timeout_banco()
        )
        conexao.row_factory = sqlite3.Row
        conexao.execute("PRAGMA foreign_keys = ON")
        conexao.execute("BEGIN IMMEDIATE")
        yield OperadorRepository(conexao)
        conexao.commit()
    except sqlite3.OperationalError as exc:
        if getattr(exc, "sqlite_errorcode", None) in CODIGOS_BANCO_INDISPONIVEL:
            logger.exception("Banco indisponível durante operação do operador.")
            raise BancoIndisponivelError("Banco temporariamente indisponível.") from exc
        logger.exception("Falha interna de persistência do operador.")
        raise PersistenciaError("Não foi possível concluir a operação.") from exc
    except sqlite3.DatabaseError as exc:
        logger.exception("Falha interna de persistência do operador.")
        raise PersistenciaError("Não foi possível concluir a operação.") from exc
    finally:
        if conexao is not None:
            try:
                if conexao.in_transaction:
                    conexao.rollback()
            finally:
                conexao.close()


@contextmanager
def transacao_leitura() -> Iterator[OperadorRepository]:
    """Abre uma unidade de leitura sem adquirir o lock de escrita.

    Todas as consultas feitas dentro do contexto compartilham o mesmo snapshot,
    o que mantém totais e agrupamentos coerentes sem serializar escritores.

    Returns:
        Contexto com o repositório ligado à transação de leitura atual.

    Raises:
        BancoIndisponivelError: Se o banco estiver ausente, bloqueado ou inacessível.
        PersistenciaError: Se uma consulta falhar por erro interno.
    """
    conexao: sqlite3.Connection | None = None
    try:
        conexao = sqlite3.connect(
            caminho_banco().as_uri() + "?mode=ro", uri=True, timeout=timeout_banco()
        )
        conexao.row_factory = sqlite3.Row
        conexao.execute("BEGIN")
        yield OperadorRepository(conexao)
    except sqlite3.OperationalError as exc:
        if getattr(exc, "sqlite_errorcode", None) in CODIGOS_BANCO_INDISPONIVEL:
            logger.exception("Banco indisponível durante leitura do operador.")
            raise BancoIndisponivelError("Banco temporariamente indisponível.") from exc
        logger.exception("Falha interna de leitura do operador.")
        raise PersistenciaError("Não foi possível concluir a consulta.") from exc
    except sqlite3.DatabaseError as exc:
        logger.exception("Falha interna de leitura do operador.")
        raise PersistenciaError("Não foi possível concluir a consulta.") from exc
    finally:
        if conexao is not None:
            try:
                if conexao.in_transaction:
                    conexao.rollback()
            finally:
                conexao.close()


def validar_banco() -> None:
    """Valida o banco sem alterar dados, durante a inicialização da API."""
    with transacao_leitura() as repositorio:
        repositorio.validar_schema()
