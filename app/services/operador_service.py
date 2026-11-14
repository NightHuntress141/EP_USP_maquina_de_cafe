"""Serviços de manutenção e limpeza e contrato de autenticação do operador."""

from __future__ import annotations

from app.core.exceptions import EstadoInvalidoError, OperacaoInvalidaError
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
        NotImplementedError: Enquanto a regra de negócio não for implementada.
    """
    raise NotImplementedError("operador_service.autenticar ainda não foi implementado.")


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
