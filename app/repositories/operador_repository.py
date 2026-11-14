"""Persistência SQLite do operador e unidade de trabalho transacional."""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from app.core.config import caminho_banco, timeout_banco
from app.core.exceptions import BancoIndisponivelError, PersistenciaError
from app.core.modelos import EstadoMaquina, Maquina, ProdutoAtualizado

logger = logging.getLogger(__name__)


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
        for tabela in ("limpeza", "ingrediente", "receita_item"):
            # Nomes constantes definidos pela aplicação, nunca fornecidos pelo cliente.
            if (
                self._conexao.execute(
                    "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
                    (tabela,),
                ).fetchone()
                is None
            ):
                raise BancoIndisponivelError("Banco não inicializado corretamente.")


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
        logger.exception("Banco indisponível durante operação do operador.")
        raise BancoIndisponivelError("Banco temporariamente indisponível.") from exc
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


def validar_banco() -> None:
    """Valida o banco sem alterar dados, durante a inicialização da API."""
    with transacao() as repositorio:
        repositorio.validar_schema()
