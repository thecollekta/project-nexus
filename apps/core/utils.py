# apps/core/utils.py

import re
from decimal import Decimal, InvalidOperation
from typing import Union

import structlog
from djmoney.money import Money

logger = structlog.get_logger(__name__)


def clean_price_value(price: Union[str, Money, Decimal, float, int, None]) -> Decimal:
    """
    Clean price value and convert to Decimal with comprehensive error handling.

    Args:
        price: Price value in various formats

    Returns:
        Decimal: Cleaned price value

    Raises:
        ValueError: If price cannot be converted to Decimal
    """
    if price is None:
        return Decimal("0.00")

    try:
        # Handle Money objects
        if isinstance(price, Money):
            return price.amount

        # Handle Decimal objects
        if isinstance(price, Decimal):
            return price

        # Handle numeric types
        if isinstance(price, (float, int)):
            return Decimal(str(price))

        # Handle string values
        if isinstance(price, str):
            # Remove whitespace
            price_str = price.strip()

            # Handle empty strings
            if not price_str:
                return Decimal("0.00")

            # Remove currency symbols and other formatting
            # This regex removes: GHS, ¢, $, €, £, ¥, commas, and other common currency symbols
            clean_str = re.sub(r"[^\d.-]", "", price_str)

            # Handle edge cases
            if not clean_str or clean_str in [".", "-", "-."]:
                return Decimal("0.00")

            # Handle multiple decimal points by keeping only the last one
            if clean_str.count(".") > 1:
                # Split on decimal points and reconstruct
                parts = clean_str.split(".")
                if len(parts) > 2:
                    # Join all but the last part, then add the last part as decimal
                    integer_part = "".join(parts[:-1])
                    decimal_part = parts[-1]
                    clean_str = f"{integer_part}.{decimal_part}"

            # Handle multiple negative signs
            if clean_str.count("-") > 1:
                # Count negative signs and keep only one at the beginning
                negative_count = clean_str.count("-")
                clean_str = clean_str.replace("-", "")
                if negative_count % 2 == 1:  # Odd number of negatives = negative result
                    clean_str = "-" + clean_str

            # Ensure there's a digit before or after decimal point
            if clean_str.startswith("."):
                clean_str = "0" + clean_str
            elif clean_str.endswith("."):
                clean_str = clean_str + "00"
            elif clean_str == "-":
                clean_str = "0.00"

            try:
                return Decimal(clean_str)
            except InvalidOperation:
                logger.warning(
                    f"Could not convert cleaned string '{clean_str}' to Decimal, using 0.00"
                )
                return Decimal("0.00")

        # Handle objects with amount attribute (like other money libraries)
        if hasattr(price, "amount"):
            return clean_price_value(price.amount)

        # Last resort: try to convert to string and process
        try:
            return clean_price_value(str(price))
        except Exception:
            logger.warning(
                f"Could not convert {type(price).__name__} object to Decimal, using 0.00"
            )
            return Decimal("0.00")

    except Exception as e:
        logger.error(
            f"Failed to clean price value {price} ({type(price).__name__}): {str(e)}"
        )
        raise ValueError(f"Could not convert {price} to Decimal: {str(e)}") from e


def create_money_from_price(
    price: Union[str, Money, Decimal, float, int, None], currency: str = "GHS"
) -> Money:
    """
    Create a Money object from various price formats.

    Args:
        price: Price value in various formats
        currency: Currency code (default: GHS)

    Returns:
        Money: Money object with cleaned price

    Raises:
        ValueError: If price cannot be converted
    """
    try:
        # If already a Money object, ensure correct currency
        if isinstance(price, Money):
            if price.currency == currency:
                return price
            else:
                return Money(price.amount, currency)

        # Clean the price and create Money object
        cleaned_price = clean_price_value(price)
        return Money(cleaned_price, currency)

    except Exception as e:
        logger.error(f"Failed to create Money object from {price}: {str(e)}")
        raise ValueError(f"Could not create Money object from {price}: {str(e)}") from e


def validate_price_format(price: Union[str, Money, Decimal, float, int]) -> bool:
    """
    Validate if a price can be properly converted.

    Args:
        price: Price value to validate

    Returns:
        bool: True if price can be converted, False otherwise
    """
    try:
        clean_price_value(price)
        return True
    except (ValueError, InvalidOperation):
        return False


# Test function for debugging (remove in production)
def test_price_cleaning():
    """Test various price formats for debugging purposes."""
    test_cases = [
        "GHS275.54",
        "GHS3,249.51",
        "GHS3,487.95",
        "GHS1,374.99",
        "$1,234.56",
        "€999.99",
        "1234.56",
        "1,234.56",
        "1234",
        "0.99",
        ".99",
        "99.",
        "",
        None,
        Money(Decimal("123.45"), "GHS"),
        Decimal("678.90"),
        123.45,
        0,
    ]

    results = []
    for test_case in test_cases:
        try:
            cleaned = clean_price_value(test_case)
            money_obj = create_money_from_price(test_case)
            valid = validate_price_format(test_case)
            results.append(
                f"{test_case!r} -> {cleaned} -> {money_obj} (valid: {valid})"
            )
        except Exception as e:
            results.append(f"{test_case!r} -> ERROR: {e}")

    return "\n".join(results)


class SensitiveDataFilter:
    """Filter that redacts sensitive information from log records."""

    PATTERNS = [
        (r'email[\'"]\s*:\s*[\'"]([^\'"]*)[\'"]', "email"),
        (r'user_id[\'"]\s*:\s*[\'"]([^\'"]*)[\'"]', "user_id"),
        (r'ip_address[\'"]\s*:\s*[\'"]([^\'"]*)[\'"]', "ip_address"),
        (r'password[\'"]\s*:\s*[\'"]([^\'"]*)[\'"]', "password"),
    ]

    def filter(self, record):
        if isinstance(record.msg, str):
            for pattern, field_name in self.PATTERNS:
                record.msg = re.sub(pattern, f'{field_name}: "[*****]"', record.msg)

            # Handle extra dict if it exists
            if hasattr(record, "extra"):
                for key in record.extra.keys():
                    if key in ["email", "user_id", "ip_address", "password"]:
                        record.extra[key] = "[*****]"

        return True
