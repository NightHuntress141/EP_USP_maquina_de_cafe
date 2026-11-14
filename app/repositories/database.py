"""Inicialização e migração explícitas do SQLite, executadas fora da API.

Uso: ``python -m app.repositories.database init`` ou ``migrate``.
Antes de migrar, faça backup e pare a API e outros processos que escrevem no banco.
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from app.core.config import caminho_banco
from app.core.valores import para_centavos

RAIZ = Path(__file__).resolve().parents[2]


def inicializar(caminho: Path) -> None:
    """Cria um banco novo sem sobrescrever arquivos existentes.

    Args:
        caminho: Caminho do novo banco.

    Raises:
        FileExistsError: Se já existir um arquivo nesse caminho.
    """
    # A criação exclusiva evita alterar um banco já existente, inclusive vazio.
    with caminho.open("xb"):
        pass
    conexao: sqlite3.Connection | None = None
    try:
        conexao = sqlite3.connect(caminho)
        schema = (RAIZ / "database/schema.sql").read_text()
        seed = (RAIZ / "database/seed.sql").read_text()
        conexao.execute("PRAGMA foreign_keys = ON")
        conexao.executescript("BEGIN IMMEDIATE;\n" + schema + "\n" + seed + "\nCOMMIT;")
    except Exception:
        # O arquivo foi criado por esta chamada e não existia antes: não deixar
        # um banco parcial que impeça uma nova tentativa de init.
        if conexao is not None:
            conexao.close()
            conexao = None
        caminho.unlink(missing_ok=True)
        raise
    finally:
        if conexao is not None:
            if conexao.in_transaction:
                conexao.rollback()
            conexao.close()


def migrar(caminho: Path) -> None:
    """Converte o preço legado para centavos e reforça a integridade de COPOS.

    A migração é atômica e idempotente. Valores legados inválidos abortam a
    operação sem arredondamento ou perda de dados. O caminho deve existir.

    Args:
        caminho: Banco legado já inicializado.

    Raises:
        ValueError: Se houver preços inválidos ou violação de integridade.
        sqlite3.DatabaseError: Se o schema não for compatível ou o banco falhar.
    """
    conexao = sqlite3.connect(caminho.resolve().as_uri() + "?mode=rw", uri=True)
    try:
        # Necessário para substituir a tabela referenciada, sem renomear as FKs.
        # A integridade é verificada antes do commit e reativada ao fechar.
        conexao.execute("PRAGMA foreign_keys = OFF")
        conexao.execute("BEGIN IMMEDIATE")
        colunas = {linha[1] for linha in conexao.execute("PRAGMA table_info(produto)")}
        if "preco" in colunas and "preco_centavos" not in colunas:
            if colunas != {"id", "nome", "preco", "tempo_preparo_s"}:
                raise ValueError("Schema personalizado: migração automática não suportada.")
            personalizados = conexao.execute(
                "SELECT 1 FROM sqlite_master WHERE tbl_name='produto' "
                "AND type IN ('index','trigger') AND sql IS NOT NULL"
            ).fetchone()
            if personalizados:
                raise ValueError(
                    "Produto possui índices/triggers personalizados; migre manualmente."
                )
            produtos = conexao.execute(
                "SELECT id, nome, preco, tempo_preparo_s FROM produto"
            ).fetchall()
            convertidos = [
                (id_, nome, para_centavos(preco), tempo) for id_, nome, preco, tempo in produtos
            ]
            conexao.execute(
                "CREATE TABLE produto_novo (id INT PRIMARY KEY, nome VARCHAR(50) NOT NULL UNIQUE, "
                "preco_centavos INTEGER NOT NULL CHECK (typeof(preco_centavos) = 'integer' "
                "AND preco_centavos BETWEEN 1 AND 9999999999), "
                "tempo_preparo_s INT NOT NULL CHECK (tempo_preparo_s > 0))"
            )
            conexao.executemany("INSERT INTO produto_novo VALUES (?, ?, ?, ?)", convertidos)
            conexao.execute("DROP TABLE produto")
            conexao.execute("ALTER TABLE produto_novo RENAME TO produto")
        elif "preco_centavos" not in colunas:
            raise ValueError("Schema de produto não reconhecido.")
        invalidos = conexao.execute(
            "SELECT 1 FROM ingrediente WHERE codigo = 'COPOS' AND typeof(quantidade_atual) != 'integer'"
        ).fetchone()
        if invalidos:
            raise ValueError(
                "COPOS contém quantidade fracionária; corrija os dados antes de migrar."
            )
        for evento in ("INSERT", "UPDATE"):
            nome = "copos_inteiros_" + evento.lower()
            conexao.execute(
                f"CREATE TRIGGER IF NOT EXISTS {nome} BEFORE {evento} ON ingrediente "
                "WHEN NEW.codigo = 'COPOS' AND typeof(NEW.quantidade_atual) != 'integer' "
                "BEGIN SELECT RAISE(ABORT, 'COPOS exige quantidade inteira'); END"
            )
        if conexao.execute("PRAGMA foreign_key_check").fetchone():
            raise ValueError("Banco contém referências inválidas; migração abortada.")
        conexao.commit()
    finally:
        if conexao.in_transaction:
            conexao.rollback()
        conexao.execute("PRAGMA foreign_keys = ON")
        conexao.close()


def main() -> None:
    """Executa a operação administrativa escolhida na linha de comando."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operacao", choices=("init", "migrate"))
    args = parser.parse_args()
    caminho = caminho_banco()
    if args.operacao == "init":
        inicializar(caminho)
    else:
        migrar(caminho)
    print(f"Banco pronto: {caminho}")


if __name__ == "__main__":
    main()
