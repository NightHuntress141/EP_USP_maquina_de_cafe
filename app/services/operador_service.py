"""Contrato do serviço do operador.

A implementação real das regras de negócio (RN07, RN08 e RN11) é de
responsabilidade dos demais integrantes. Este módulo define apenas a interface
consumida pela API.
"""

from __future__ import annotations

from typing import Any


def autenticar(usuario: str, senha: str) -> str:
    """Autentica o operador e devolve o token de acesso.

    Regras envolvidas:
        RN11 – as credenciais são comparadas com ``OPERATOR_USER`` e
        ``OPERATOR_PASSWORD`` (variáveis de ambiente) e, em caso de sucesso, o
        token ``OPERATOR_TOKEN`` é devolvido.

    Args:
        usuario: Usuário informado no login.
        senha: Senha informada no login.

    Returns:
        Token de acesso do operador.

    Raises:
        CredenciaisInvalidasError: Se usuário ou senha não conferirem.
        NotImplementedError: Enquanto a regra de negócio não for implementada.
    """
    raise NotImplementedError("operador_service.autenticar ainda não foi implementado.")


def alterar_manutencao(acao: str) -> dict[str, Any]:
    """Coloca a máquina em manutenção ou a devolve à operação.

    Regras envolvidas:
        RN08 – apenas o operador autenticado pode entrar ou sair da manutenção,
        respeitando as transições de estado válidas da máquina.

    Args:
        acao: ``ENTRAR`` ou ``SAIR``, já validado pela API.

    Returns:
        Dicionário no formato aceito por
        :class:`app.schemas.operador.ManutencaoResponse`, com a chave ``estado``.

    Raises:
        EstadoInvalidoError: Se a transição não for permitida no estado atual.
        NotImplementedError: Enquanto a regra de negócio não for implementada.
    """
    raise NotImplementedError("operador_service.alterar_manutencao ainda não foi implementado.")


def registrar_limpeza() -> dict[str, Any]:
    """Registra a limpeza da máquina e zera o contador de preparos.

    Regras envolvidas:
        RN07 – a limpeza é permitida quando a máquina está
        ``AGUARDANDO_LIMPEZA`` (ou em manutenção) e reinicia o contador de
        preparos desde a última limpeza.

    Returns:
        Dicionário no formato aceito por
        :class:`app.schemas.operador.LimpezaResponse`, com as chaves
        ``preparos_desde_limpeza`` e ``estado``.

    Raises:
        EstadoInvalidoError: Se a máquina não puder ser limpa no estado atual.
        NotImplementedError: Enquanto a regra de negócio não for implementada.
    """
    raise NotImplementedError("operador_service.registrar_limpeza ainda não foi implementado.")


__all__ = ["autenticar", "alterar_manutencao", "registrar_limpeza"]
