"""Validação compartilhada de identificadores e valores monetários."""

from decimal import Decimal, InvalidOperation

ID_MAXIMO = 2**63 - 1
PRECO_MAXIMO_CENTAVOS = 9_999_999_999


def validar_id(identificador: int) -> None:
    """Exige um identificador positivo representável pelo SQLite.

    Args:
        identificador: Identificador recebido pelo serviço.

    Raises:
        ValueError: Se o valor não for um inteiro positivo suportado.
    """
    if (
        isinstance(identificador, bool)
        or not isinstance(identificador, int)
        or not 1 <= identificador <= ID_MAXIMO
    ):
        raise ValueError("Identificador fora da faixa permitida.")


def para_centavos(valor: Decimal | float | str) -> int:
    """Converte reais em centavos sem arredondar valores inválidos.

    Args:
        valor: Valor positivo com no máximo duas casas decimais.

    Returns:
        Número inteiro de centavos, limitado à precisão de NUMERIC(10,2).

    Raises:
        ValueError: Se o valor não for finito, positivo ou representável.
    """
    try:
        decimal = Decimal(str(valor))
        if not decimal.is_finite() or not 0 < decimal <= Decimal(PRECO_MAXIMO_CENTAVOS) / 100:
            raise ValueError("Preço deve estar entre R$ 0,01 e R$ 99.999.999,99.")
        quantizado = decimal.quantize(Decimal("0.01"))
        if decimal != quantizado:
            raise ValueError("Preço deve ter no máximo duas casas decimais.")
        return int(quantizado * 100)
    except (InvalidOperation, TypeError) as exc:
        raise ValueError("Preço inválido.") from exc
