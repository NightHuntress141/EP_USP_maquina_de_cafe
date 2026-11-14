"""Exceções de negócio customizadas.

Cada exceção carrega o código HTTP sugerido (``status_code``) e um identificador
legível (``erro``) usado no corpo padronizado de erro da API::

    {"erro": "MAQUINA_OCUPADA", "mensagem": "A máquina está preparando outra bebida."}

O mapeamento para a resposta HTTP é feito de forma centralizada pelos handlers
globais registrados em :mod:`app.main`, mantendo os controllers finos.
"""

from __future__ import annotations


class BusinessError(Exception):
    """Erro base de negócio.

    Todas as exceções de domínio devem herdar desta classe, informando o
    ``status_code`` HTTP e o ``erro`` (slug) correspondentes.

    Attributes:
        status_code: Código HTTP devolvido ao cliente.
        erro: Identificador curto do erro (slug em maiúsculas).
        mensagem: Texto explicativo, legível por humanos.
    """

    status_code: int = 400
    erro: str = "ERRO_DE_NEGOCIO"

    def __init__(self, mensagem: str = "Erro de negócio.") -> None:
        """Inicializa a exceção.

        Args:
            mensagem: Descrição textual do erro exibida ao cliente.
        """
        self.mensagem = mensagem
        super().__init__(mensagem)


class OperacaoInvalidaError(BusinessError):
    """Operação ou dado de entrada inválido (HTTP 400)."""

    status_code = 400
    erro = "DADOS_INVALIDOS"


class CreditoInsuficienteError(BusinessError):
    """Crédito acumulado não cobre o preço do pedido (HTTP 402, RN02)."""

    status_code = 402
    erro = "CREDITO_INSUFICIENTE"


class BebidaNaoEncontradaError(BusinessError):
    """Bebida inexistente no cardápio (HTTP 404, RN10)."""

    status_code = 404
    erro = "BEBIDA_NAO_ENCONTRADA"


class PedidoNaoEncontradoError(BusinessError):
    """Pedido inexistente (HTTP 404)."""

    status_code = 404
    erro = "PEDIDO_NAO_ENCONTRADO"


class EstoqueInsuficienteError(BusinessError):
    """Estoque de ingrediente, açúcar ou copo insuficiente (HTTP 409, RN02)."""

    status_code = 409
    erro = "ESTOQUE_INSUFICIENTE"


class MaquinaOcupadaError(BusinessError):
    """Máquina preparando outra bebida; novos pedidos são recusados (HTTP 409, RN02/RN04)."""

    status_code = 409
    erro = "MAQUINA_OCUPADA"


class CapacidadeExcedidaError(BusinessError):
    """Reabastecimento acima da capacidade máxima do reservatório (HTTP 422, RN09)."""

    status_code = 422
    erro = "CAPACIDADE_EXCEDIDA"


class MaquinaIndisponivelError(BusinessError):
    """Máquina em manutenção ou aguardando limpeza (HTTP 503, RN07/RN08)."""

    status_code = 503
    erro = "MAQUINA_INDISPONIVEL"


class CredenciaisInvalidasError(BusinessError):
    """Usuário ou senha de operador inválidos (HTTP 401, RN11)."""

    status_code = 401
    erro = "NAO_AUTORIZADO"


class PedidoNaoCancelavelError(BusinessError):
    """Pedido não está mais em preparo e não pode ser cancelado (HTTP 409, RN05)."""

    status_code = 409
    erro = "PEDIDO_NAO_CANCELAVEL"


class EstadoInvalidoError(BusinessError):
    """Operação incompatível com o estado atual da máquina (HTTP 409)."""

    status_code = 409
    erro = "ESTADO_INVALIDO"


class PersistenciaError(BusinessError):
    """Falha interna de persistência, sem expor detalhes do banco (HTTP 500)."""

    status_code = 500
    erro = "ERRO_INTERNO"


class BancoIndisponivelError(BusinessError):
    """Banco inacessível, não inicializado ou temporariamente ocupado (HTTP 503)."""

    status_code = 503
    erro = "BANCO_INDISPONIVEL"


class ConfiguracaoIndisponivelError(BusinessError):
    """Configuração obrigatória ausente, sem expor os valores esperados (HTTP 503)."""

    status_code = 503
    erro = "SERVICO_INDISPONIVEL"


__all__ = [
    "BancoIndisponivelError",
    "BebidaNaoEncontradaError",
    "BusinessError",
    "CapacidadeExcedidaError",
    "ConfiguracaoIndisponivelError",
    "CredenciaisInvalidasError",
    "CreditoInsuficienteError",
    "EstadoInvalidoError",
    "EstoqueInsuficienteError",
    "MaquinaIndisponivelError",
    "MaquinaOcupadaError",
    "OperacaoInvalidaError",
    "PedidoNaoCancelavelError",
    "PedidoNaoEncontradoError",
    "PersistenciaError",
]
