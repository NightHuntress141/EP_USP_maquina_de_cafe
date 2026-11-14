"""Serviços de autenticação, manutenção e limpeza do operador."""

from __future__ import annotations

from secrets import compare_digest

from app.core.config import credenciais_operador, token_operador
from app.core.exceptions import (
    ConfiguracaoIndisponivelError,
    CredenciaisInvalidasError,
    EstadoInvalidoError,
    OperacaoInvalidaError,
)
from app.core.modelos import EstadoMaquina, ResultadoLimpeza, ResultadoManutencao
from app.repositories.operador_repository import transacao


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
        ConfiguracaoIndisponivelError: Se as variáveis de autenticação estiverem ausentes.
    """
    if not isinstance(usuario, str) or not isinstance(senha, str) or not usuario or not senha:
        raise CredenciaisInvalidasError("Usuário ou senha inválidos.")
    try:
        usuario_configurado, senha_configurada = credenciais_operador()
        token = token_operador()
    except RuntimeError as exc:
        raise ConfiguracaoIndisponivelError("Autenticação do operador não configurada.") from exc
    usuario_ok = compare_digest(usuario.encode("utf-8"), usuario_configurado.encode("utf-8"))
    senha_ok = compare_digest(senha.encode("utf-8"), senha_configurada.encode("utf-8"))
    if not (usuario_ok and senha_ok):
        raise CredenciaisInvalidasError("Usuário ou senha inválidos.")
    return token


def alterar_manutencao(acao: str) -> ResultadoManutencao:
    """Executa a entrada ou saída explícita da manutenção (RN08).

    Args:
        acao: ENTRAR ou SAIR.

    Returns:
        Estado atualizado da máquina, preservando crédito e contador.

    Raises:
        OperacaoInvalidaError: Se a ação for desconhecida.
        EstadoInvalidoError: Se a transição não for permitida.
    """
    if acao not in ("ENTRAR", "SAIR"):
        raise OperacaoInvalidaError("A ação deve ser ENTRAR ou SAIR.")
    with transacao() as repositorio:
        maquina = repositorio.obter_maquina()
        if acao == "ENTRAR":
            if maquina.estado not in (
                EstadoMaquina.PRONTA,
                EstadoMaquina.AGUARDANDO_LIMPEZA,
            ):
                raise EstadoInvalidoError("A máquina não pode entrar em manutenção agora.")
            estado = EstadoMaquina.MANUTENCAO
        else:
            if maquina.estado != EstadoMaquina.MANUTENCAO:
                raise EstadoInvalidoError("A máquina não está em manutenção.")
            estado = (
                EstadoMaquina.AGUARDANDO_LIMPEZA
                if maquina.preparos_desde_limpeza >= 30
                else EstadoMaquina.PRONTA
            )
        repositorio.atualizar_estado(estado)
        return {"estado": estado}


def registrar_limpeza() -> ResultadoLimpeza:
    """Registra a limpeza e zera o contador de preparos em manutenção (RN07).

    A máquina permanece em MANUTENCAO até a saída explícita desse modo.
    O registro de limpeza e a atualização do contador são atômicos.

    Returns:
        Estado da máquina e contador zerado.

    Raises:
        EstadoInvalidoError: Se a máquina não estiver em manutenção.
    """
    with transacao() as repositorio:
        maquina = repositorio.obter_maquina()
        if maquina.estado != EstadoMaquina.MANUTENCAO:
            raise EstadoInvalidoError("A limpeza exige a máquina em manutenção.")
        repositorio.registrar_limpeza()
        return {"estado": maquina.estado, "preparos_desde_limpeza": 0}


__all__ = ["alterar_manutencao", "autenticar", "registrar_limpeza"]
