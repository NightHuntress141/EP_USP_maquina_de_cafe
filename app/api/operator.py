"""Endpoints do fluxo do operador (autenticados, exceto o login).

Este módulo implementa apenas a camada de controller: valida a entrada via
Pydantic, delega a execução das regras de negócio aos serviços e devolve a
resposta HTTP. As exceções de negócio são traduzidas para códigos HTTP pelos
handlers globais registrados em :mod:`app.main`.

Todas as rotas, exceto ``POST /operador/login``, exigem o token do operador no
cabeçalho ``Authorization: Bearer <token>`` (RN11).
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path, Query

from app.api.deps import get_current_operator
from app.api.responses import _erro
from app.core.exceptions import OperacaoInvalidaError
from app.core.valores import ID_MAXIMO
from app.schemas.estoque import (
    EstoqueResponse,
    ReabastecimentoRequest,
    ReabastecimentoResponse,
)
from app.schemas.operador import (
    LimpezaResponse,
    LoginRequest,
    LoginResponse,
    ManutencaoRequest,
    ManutencaoResponse,
)
from app.schemas.produto import PrecoRequest, ProdutoResponse
from app.schemas.relatorio import RelatorioResponse
from app.services import (
    estoque_service,
    operador_service,
    produto_service,
    relatorio_service,
)

router = APIRouter(prefix="/operador", tags=["Operador"])


_ERRO_NAO_AUTORIZADO = _erro(
    401, "Token ausente ou inválido.", "NAO_AUTORIZADO", "Token ausente ou inválido."
)
"""Documentação padronizada da resposta 401 das rotas protegidas."""


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Autentica o operador",
    responses={
        **_erro(
            401,
            "Credenciais inválidas.",
            "NAO_AUTORIZADO",
            "Usuário ou senha inválidos.",
        ),
    },
)
def login(payload: LoginRequest) -> dict[str, Any]:
    """Autentica o operador e devolve o token de acesso.

    Regras de negócio acionadas:
        - RN11: as credenciais são validadas contra ``OPERATOR_USER`` e
          ``OPERATOR_PASSWORD`` e, em caso de sucesso, ``OPERATOR_TOKEN`` é
          devolvido.

    Args:
        payload: Usuário e senha do operador.

    Returns:
        Token no formato :class:`app.schemas.operador.LoginResponse`.
    """
    token = operador_service.autenticar(payload.usuario, payload.senha)
    return {"token": token, "tipo": "bearer"}


@router.get(
    "/estoque",
    response_model=EstoqueResponse,
    summary="Consulta o estoque da máquina",
    dependencies=[Depends(get_current_operator)],
    responses={**_ERRO_NAO_AUTORIZADO},
)
def consultar_estoque() -> dict[str, Any]:
    """Retorna a situação de todos os reservatórios e insumos.

    Regras de negócio acionadas:
        - RN09: o operador acompanha níveis atuais, capacidade e alerta de nível
          baixo de cada reservatório.

    Returns:
        Estoque no formato :class:`app.schemas.estoque.EstoqueResponse`.
    """
    return estoque_service.consultar_estoque()


@router.post(
    "/estoque/reabastecer",
    response_model=ReabastecimentoResponse,
    summary="Reabastece um reservatório",
    dependencies=[Depends(get_current_operator)],
    responses={
        **_erro(
            400,
            "Quantidade inválida.",
            "DADOS_INVALIDOS",
            "A quantidade deve ser maior que zero.",
        ),
        **_ERRO_NAO_AUTORIZADO,
        **_erro(
            409,
            "Máquina não está em manutenção.",
            "ESTADO_INVALIDO",
            "A máquina não está em manutenção.",
        ),
        **_erro(
            422,
            "Capacidade excedida.",
            "CAPACIDADE_EXCEDIDA",
            "A quantidade excede a capacidade do reservatório.",
        ),
    },
)
def reabastecer(payload: ReabastecimentoRequest) -> dict[str, Any]:
    """Adiciona insumo a um reservatório, respeitando sua capacidade máxima.

    Regras de negócio acionadas:
        - RN09: o reabastecimento só é permitido com a máquina em manutenção e
          não pode ultrapassar a capacidade máxima do reservatório.

    Args:
        payload: Reservatório e quantidade a adicionar.

    Returns:
        Reservatório atualizado no formato
        :class:`app.schemas.estoque.ReabastecimentoResponse`.
    """
    return estoque_service.reabastecer(payload.item.value, payload.quantidade)


@router.put(
    "/produtos/{produto_id}/preco",
    response_model=ProdutoResponse,
    summary="Altera o preço de uma bebida",
    dependencies=[Depends(get_current_operator)],
    responses={
        **_erro(
            400,
            "Preço inválido.",
            "DADOS_INVALIDOS",
            "O preço deve ser maior que zero.",
        ),
        **_ERRO_NAO_AUTORIZADO,
        **_erro(
            404,
            "Bebida inexistente.",
            "BEBIDA_NAO_ENCONTRADA",
            "Bebida não encontrada no cardápio.",
        ),
    },
)
def alterar_preco(
    produto_id: Annotated[int, Path(ge=1, le=ID_MAXIMO)], payload: PrecoRequest
) -> dict[str, Any]:
    """Atualiza o preço de uma bebida do cardápio.

    Regras de negócio acionadas:
        - RN10: apenas o operador autenticado altera o preço de uma bebida
          existente; o novo preço deve ser maior que zero.

    Args:
        produto_id: Identificador da bebida.
        payload: Novo preço em reais.

    Returns:
        Bebida atualizada no formato
        :class:`app.schemas.produto.ProdutoResponse`.
    """
    return produto_service.alterar_preco(produto_id, payload.preco)


@router.post(
    "/manutencao",
    response_model=ManutencaoResponse,
    summary="Entra ou sai da manutenção",
    dependencies=[Depends(get_current_operator)],
    responses={
        **_erro(
            400,
            "Ação de manutenção inválida.",
            "DADOS_INVALIDOS",
            "A ação deve ser ENTRAR ou SAIR.",
        ),
        **_ERRO_NAO_AUTORIZADO,
        **_erro(
            409,
            "Transição de manutenção inválida.",
            "ESTADO_INVALIDO",
            "A máquina não pode entrar em manutenção agora.",
        ),
    },
)
def alterar_manutencao(payload: ManutencaoRequest) -> dict[str, Any]:
    """Coloca a máquina em manutenção ou a devolve à operação.

    Regras de negócio acionadas:
        - RN08: somente o operador autenticado altera o modo de manutenção,
          respeitando as transições válidas do estado da máquina.

    Args:
        payload: Ação ``ENTRAR`` ou ``SAIR``.

    Returns:
        Estado da máquina no formato
        :class:`app.schemas.operador.ManutencaoResponse`.
    """
    return operador_service.alterar_manutencao(payload.acao.value)


@router.post(
    "/limpeza",
    response_model=LimpezaResponse,
    summary="Registra a limpeza da máquina",
    dependencies=[Depends(get_current_operator)],
    responses={
        **_ERRO_NAO_AUTORIZADO,
        **_erro(
            409,
            "Limpeza não permitida no estado atual.",
            "ESTADO_INVALIDO",
            "A máquina não está em manutenção.",
        ),
    },
)
def registrar_limpeza() -> dict[str, Any]:
    """Registra a limpeza e zera o contador de preparos desde a última limpeza.

    Regras de negócio acionadas:
        - RN07: exige ``MANUTENCAO``, registra a limpeza e zera o contador
          de preparos. A máquina permanece em manutenção até a saída explícita
          desse modo (RN08).

    Returns:
        Contador e estado no formato
        :class:`app.schemas.operador.LimpezaResponse`.
    """
    return operador_service.registrar_limpeza()


@router.get(
    "/relatorio",
    response_model=RelatorioResponse,
    summary="Gera o relatório de vendas do período",
    dependencies=[Depends(get_current_operator)],
    responses={
        **_erro(
            400,
            "Período inválido.",
            "DADOS_INVALIDOS",
            "O início do período deve ser anterior ao fim.",
        ),
        **_ERRO_NAO_AUTORIZADO,
    },
)
def gerar_relatorio(
    inicio: Annotated[
        datetime,
        Query(description="Início do período (ISO 8601).", examples=["2026-03-01T00:00:00"]),
    ],
    fim: Annotated[
        datetime, Query(description="Fim do período (ISO 8601).", examples=["2026-03-31T23:59:59"])
    ],
) -> dict[str, Any]:
    """Gera o relatório consolidado de vendas do período.

    Regras de negócio acionadas:
        - RN12: consolida os pedidos concluídos entre ``inicio`` e ``fim``, com
          total de pedidos, faturamento total e detalhamento por bebida.

    Args:
        inicio: Início do período consultado.
        fim: Fim do período consultado.

    Returns:
        Relatório no formato :class:`app.schemas.relatorio.RelatorioResponse`.

    Raises:
        OperacaoInvalidaError: Se ``inicio`` for posterior a ``fim``.
    """
    try:
        periodo_invalido = inicio > fim
    except TypeError:
        periodo_invalido = True
    if periodo_invalido:
        raise OperacaoInvalidaError("O início do período deve ser anterior ou igual ao fim.")
    return relatorio_service.gerar_relatorio(inicio, fim)


__all__ = [
    "alterar_manutencao",
    "alterar_preco",
    "consultar_estoque",
    "gerar_relatorio",
    "login",
    "reabastecer",
    "registrar_limpeza",
    "router",
]
