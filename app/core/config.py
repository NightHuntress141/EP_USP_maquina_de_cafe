"""Configuração explícita de autenticação, banco e CORS."""

import os
from pathlib import Path
from urllib.parse import urlsplit


def token_operador() -> str:
    """Obtém o segredo obrigatório, sem fallback de desenvolvimento.

    Returns:
        Token configurado em OPERATOR_TOKEN.

    Raises:
        RuntimeError: Se o token estiver ausente ou contiver espaços de borda.
    """
    token = os.getenv("OPERATOR_TOKEN", "")
    if not token or token != token.strip():
        raise RuntimeError("Defina OPERATOR_TOKEN com um segredo não vazio e sem espaços de borda.")
    return token


def caminho_banco() -> Path:
    """Retorna o caminho absoluto do banco SQLite configurado."""
    return Path(
        os.getenv("DATABASE_PATH", str(Path(__file__).resolve().parents[2] / "maquina.db"))
    ).resolve()


def timeout_banco() -> float:
    """Retorna o tempo máximo de espera por lock, limitado a 30 segundos.

    Raises:
        RuntimeError: Se DATABASE_TIMEOUT_SECONDS não estiver entre 0 e 30.
    """
    try:
        valor = float(os.getenv("DATABASE_TIMEOUT_SECONDS", "5"))
        if not 0 <= valor <= 30:
            raise ValueError
    except ValueError as exc:
        raise RuntimeError("DATABASE_TIMEOUT_SECONDS deve estar entre 0 e 30.") from exc
    return valor


def origens_cors() -> list[str]:
    """Obtém origens explícitas separadas por vírgula, sem credenciais por cookie.

    Raises:
        RuntimeError: Se a configuração usar wildcard ou não for HTTP(S).
    """
    origens = [
        origem.strip() for origem in os.getenv("CORS_ORIGINS", "").split(",") if origem.strip()
    ]
    for origem in origens:
        try:
            url = urlsplit(origem)
            _ = url.port
        except ValueError as exc:
            raise RuntimeError("Origem CORS inválida.") from exc
        if (
            url.scheme not in ("http", "https")
            or not url.netloc
            or "*" in origem
            or url.path
            or url.query
            or url.fragment
            or url.username
            or url.password
        ):
            raise RuntimeError("CORS_ORIGINS deve conter origens HTTP(S) explícitas, sem caminhos.")
    return origens
