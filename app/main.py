"""Ponto de entrada da API REST da máquina de café.

Responsável por criar a aplicação FastAPI, configurar CORS, registrar as rotas
e centralizar o tratamento padronizado de erros. O corpo de erro segue o
formato ``{"erro": SLUG, "mensagem": "..."}``.
"""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.client import router as client_router
from app.core.exceptions import BusinessError

app = FastAPI(
    title="API da Máquina de Café",
    version="0.1.0",
    description=(
        "Back-end de uma máquina de café automática. A máquina física é apenas "
        "um cliente; toda a inteligência (cardápio, estoque, pagamento, preparo "
        "e manutenção) reside nesta API."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(client_router)


STATUS_PARA_ERRO: dict[int, str] = {
    400: "DADOS_INVALIDOS",
    401: "NAO_AUTORIZADO",
    403: "ACESSO_NEGADO",
    404: "NAO_ENCONTRADO",
    405: "METODO_NAO_PERMITIDO",
    402: "CREDITO_INSUFICIENTE",
    409: "CONFLITO",
    422: "ENTIDADE_NAO_PROCESSAVEL",
    503: "SERVICO_INDISPONIVEL",
}
"""Slug de erro para os códigos HTTP genéricos."""


def _mensagem_validacao(exc: RequestValidationError) -> str:
    """Formata os erros de validação do Pydantic em uma mensagem legível.

    Args:
        exc: Exceção de validação do FastAPI/Pydantic.

    Returns:
        Mensagem única concatenando o campo inválido e o motivo.
    """
    partes: list[str] = []
    for erro in exc.errors():
        local = ".".join(str(item) for item in erro.get("loc", ()) if item != "body")
        campo = local or "corpo"
        partes.append(f"{campo}: {erro.get('msg', 'valor inválido')}")
    return "; ".join(partes) if partes else "Dados de entrada inválidos."


@app.exception_handler(BusinessError)
async def business_error_handler(request: Request, exc: BusinessError) -> JSONResponse:
    """Traduz exceções de negócio no corpo de erro padronizado.

    Cada exceção carrega seu ``status_code`` e ``erro``.

    Args:
        request: Requisição HTTP (não utilizada).
        exc: Exceção de negócio lançada pelo serviço.

    Returns:
        Resposta JSON com o código HTTP e o corpo ``{"erro", "mensagem"}``.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"erro": exc.erro, "mensagem": str(exc)},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Converte erros de validação de entrada em HTTP 400 padronizado.

    Diferente do padrão 422 do FastAPI, dados inválidos são reportados como
    HTTP 400, conforme a tabela de erros do enunciado.

    Args:
        request: Requisição HTTP (não utilizada).
        exc: Exceção de validação do Pydantic.

    Returns:
        Resposta JSON 400 com o corpo ``{"erro", "mensagem"}``.
    """
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"erro": "DADOS_INVALIDOS", "mensagem": _mensagem_validacao(exc)},
    )


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Padroniza as respostas de erro levantadas como ``HTTPException``.

    Inclui o 401 do ``HTTPBearer`` e o 404 de rotas inexistentes.

    Args:
        request: Requisição HTTP (não utilizada).
        exc: Exceção HTTP do Starlette/FastAPI.

    Returns:
        Resposta JSON com o corpo ``{"erro", "mensagem"}``.
    """
    erro = STATUS_PARA_ERRO.get(exc.status_code, "ERRO")
    mensagem = exc.detail if isinstance(exc.detail, str) else "Erro."
    return JSONResponse(
        status_code=exc.status_code,
        content={"erro": erro, "mensagem": mensagem},
        headers=getattr(exc, "headers", None),
    )


__all__ = [
    "app",
    "business_error_handler",
    "validation_error_handler",
    "http_error_handler",
    "STATUS_PARA_ERRO",
]
