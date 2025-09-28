# apps/products/mixins.py

"""
Mixins for products app models.
"""

from decimal import Decimal
from typing import Any, Dict, Optional

import structlog
from django.core.exceptions import ValidationError
from djmoney.money import Money
from forex_python.converter import CurrencyRates, RatesNotAvailableError

logger = structlog.get_logger(__name__)


class PriceMixin:
    """
    Mixin class for models that need price-related functionality.
    To be used with models that have price, compare_at_price, and cost_price fields.
    """

    @property
    def price_with_currency(self) -> str:
        """Return formatted price with currency symbol."""
        if not hasattr(self, "price") or not self.price:
            return "N/A"
        return f"{self.price.currency} {self.price.amount:.2f}"

    @property
    def discount_amount(self) -> Optional[Money]:
        """Return the discount amount if compare_at_price is set and higher than price."""
        if (
            hasattr(self, "compare_at_price")
            and self.compare_at_price
            and self.compare_at_price.amount > self.price.amount
        ):
            return self.compare_at_price - self.price
        return None

    @property
    def discount_percentage(self) -> Optional[Decimal]:
        """Calculate discount percentage if compare_at_price is set and higher than price."""
        discount = self.discount_amount
        if discount:
            return (discount.amount / self.compare_at_price.amount) * 100
        return None

    @property
    def profit_margin(self) -> Optional[Decimal]:
        """Calculate profit margin if cost_price is set."""
        if (
            hasattr(self, "cost_price")
            and self.cost_price
            and self.cost_price.currency == self.price.currency
            and self.price.amount > 0
        ):
            profit = self.price.amount - self.cost_price.amount
            return (profit / self.price.amount) * 100
        return None

    def convert_currency(self, target_currency: str) -> Optional[Dict[str, Any]]:
        """
        Convert price to another currency using forex-python.

        Args:
            target_currency (str): The target currency code to convert to (e.g., 'USD', 'EUR')

        Returns:
            Optional[Dict[str, Any]]: Dictionary with converted amount and metadata, or None if conversion fails

        Example:
            {
                "amount": 17.23,
                "currency": "USD",
                "conversion_rate": 0.17,
                "original_amount": 100.0,
                "original_currency": "GHS"
            }
        """
        # Get logger with context
        log = logger.bind(
            method="convert_currency",
            target_currency=target_currency,
            model_type=self.__class__.__name__,
            model_id=getattr(self, "id", None),
        )

        # Check if price exists
        if not hasattr(self, "price") or not self.price:
            log.warning("No price available for currency conversion")
            return None

        # Bind price info to logger
        log = log.bind(
            original_currency=self.price.currency,
            original_amount=float(self.price.amount),
        )

        # If same currency, return without conversion
        if self.price.currency == target_currency:
            log.debug("Target currency same as original, no conversion needed")
            return {"amount": float(self.price.amount), "currency": target_currency}

        try:
            log.debug("Initiating currency conversion")
            c = CurrencyRates()

            # Log before making the API call
            log.debug(
                "Fetching exchange rate",
                from_currency=self.price.currency,
                to_currency=target_currency,
            )

            rate = c.get_rate(self.price.currency, target_currency)
            converted_amount = float(self.price.amount) * rate

            result = {
                "amount": converted_amount,
                "currency": target_currency,
                "conversion_rate": rate,
                "original_amount": float(self.price.amount),
                "original_currency": self.price.currency,
            }

            # Log successful conversion
            log.info(
                "Currency conversion successful",
                conversion_rate=rate,
                converted_amount=converted_amount,
            )

            return result

        except RatesNotAvailableError as e:
            log.error(
                "Currency conversion rate not available", error=str(e), exc_info=True
            )
            return None

        except Exception as e:
            log.error(
                "Unexpected error during currency conversion",
                error=str(e),
                exc_info=True,
            )
            return None

    def calculate_discount_percentage(self):
        """Calculate discount percentage if compare_at_price exists."""
        if (
            hasattr(self, "compare_at_price")
            and self.compare_at_price
            and hasattr(self, "price")
            and self.price
        ):
            if self.compare_at_price.amount > self.price.amount:
                discount = self.compare_at_price.amount - self.price.amount
                return (discount / self.compare_at_price.amount) * 100
        return Decimal("0.00")

    def calculate_profit_margin(self):
        """Calculate profit margin if cost_price exists."""
        if (
            hasattr(self, "cost_price")
            and self.cost_price
            and hasattr(self, "price")
            and self.price
        ):
            if self.price.amount > self.cost_price.amount:
                profit = self.price.amount - self.cost_price.amount
                return (profit / self.price.amount) * 100
        return Decimal("0.00")

    def validate_price_relationships(self):
        """Validate price relationships."""
        errors = []

        if hasattr(self, "compare_at_price") and self.compare_at_price:
            if self.compare_at_price.amount <= self.price.amount:
                errors.append("Compare at price must be higher than regular price.")

        if hasattr(self, "cost_price") and self.cost_price:
            if self.cost_price.amount >= self.price.amount:
                errors.append("Cost price should be lower than selling price.")

        if errors:
            raise ValidationError(errors)
