"""Documentação compartilhada das respostas de erro HTTP."""

from typing import Any

from app.schemas.erro import ErroResponse


def _erro(
    codigo: int, descricao: str, exemplo_erro: str, exemplo_mensagem: str
) -> dict[int, dict[str, Any]]:
    """Monta a documentação de uma resposta de erro para o Swagger.

    Args:
        codigo: Código HTTP da resposta.
        descricao: Descrição exibida na documentação.
        exemplo_erro: Valor de exemplo para o campo ``erro``.
        exemplo_mensagem: Valor de exemplo para o campo ``mensagem``.

    Returns:
        Dicionário no formato aceito pelo parâmetro ``responses`` do FastAPI.
    """
    return {
        codigo: {
            "model": ErroResponse,
            "description": descricao,
            "content": {
                "application/json": {
                    "example": {"erro": exemplo_erro, "mensagem": exemplo_mensagem}
                }
            },
        }
    }
