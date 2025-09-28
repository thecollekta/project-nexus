# apps/orders/management/commands/orders_sample_data.py - Complete fixed version

"""
Management command to populate the database with realistic order data.

This command creates sample orders, order items, and carts that reference
the products created by the products_sample_data command.

Usage:
    python manage.py orders_sample_data
    python manage.py orders_sample_data --clear-existing
    python manage.py orders_sample_data --count 50
"""

import random
from datetime import timedelta
from decimal import Decimal

import structlog
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from djmoney.money import Money

from apps.accounts.models import User
from apps.core.utils import clean_price_value, create_money_from_price
from apps.orders.enums import OrderStatus, PaymentStatus
from apps.orders.models import Cart, CartItem, Order, OrderItem
from apps.products.models import Product

logger = structlog.get_logger(__name__)

# Constants for order generation
DEFAULT_ORDER_COUNT = 30
MIN_ITEMS_PER_ORDER = 1
MAX_ITEMS_PER_ORDER = 5
MIN_QUANTITY_PER_ITEM = 1
MAX_QUANTITY_PER_ITEM = 5
SHIPPING_COST = Decimal("50.00")  # Flat rate shipping in GHS
TAX_RATE = Decimal("0.12")  # 12% tax rate

# Ghanaian cities for shipping addresses
GHANAIAN_CITIES = [
    "Accra",
    "Kumasi",
    "Tamale",
    "Sekondi-Takoradi",
    "Ashaiman",
    "Sunyani",
    "Cape Coast",
    "Obuasi",
    "Teshie",
    "Tema",
    "Madina",
    "Koforidua",
    "Wa",
    "Ho",
    "Techiman",
    "Bolgatanga",
    "Bawku",
    "Aflao",
    "Tarkwa",
    "Elmina",
    "Nkawkaw",
    "Dome",
    "Gbawe",
    "Kintampo",
    "Suhum",
    "Akim Oda",
    "Yendi",
    "Hohoe",
    "Mampong",
]

# Ghanaian names for sample users
GHANAIAN_FIRST_NAMES = [
    "Kwame",
    "Ama",
    "Kofi",
    "Abena",
    "Kwabena",
    "Akua",
    "Kwadwo",
    "Adwoa",
    "Kwaku",
    "Yaa",
    "Yaw",
    "Afia",
    "Kweku",
    "Kwasi",
    "Akosua",
    "Kwesi",
    "Esi",
    "Kojo",
    "Adjoa",
    "Efia",
]

GHANAIAN_LAST_NAMES = [
    "Mensah",
    "Osei",
    "Boateng",
    "Asare",
    "Agyemang",
    "Appiah",
    "Amoah",
    "Asante",
    "Baffour",
    "Bonsu",
    "Danso",
    "Frimpong",
    "Gyamfi",
    "Kwarteng",
    "Ofori",
    "Opoku",
    "Owusu",
    "Sarpong",
    "Yeboah",
    "Acheampong",
    "Adomah",
    "Agyapong",
    "Amponsah",
    "Asiedu",
    "Boatemaa",
    "Darko",
    "Fosu",
]

# Sample order status weights (for realistic distribution)
ORDER_STATUS_WEIGHTS = {
    OrderStatus.PENDING: 15,
    OrderStatus.PROCESSING: 25,
    OrderStatus.SHIPPED: 30,
    OrderStatus.DELIVERED: 25,
    OrderStatus.CANCELLED: 5,
}

# Sample payment status weights
PAYMENT_STATUS_WEIGHTS = {
    PaymentStatus.PENDING: 10,
    PaymentStatus.PAID: 80,
    PaymentStatus.FAILED: 5,
    PaymentStatus.REFUNDED: 5,
}


class Command(BaseCommand):
    """Populate database with sample order data."""

    help = _("Populate the database with sample orders, order items, and carts")

    def __init__(self):
        super().__init__()
        self.products = []
        self.users = []

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear-existing",
            action="store_true",
            help=_("Clear existing order data before populating"),
        )
        parser.add_argument(
            "--count",
            type=int,
            default=DEFAULT_ORDER_COUNT,
            help=_(f"Number of orders to create (default: {DEFAULT_ORDER_COUNT})"),
        )
        parser.add_argument(
            "--users",
            type=int,
            default=10,
            help=_("Number of users to create orders for (default: 10)"),
        )
        parser.add_argument(
            "--debug-prices",
            action="store_true",
            help=_("Show debug information about price cleaning"),
        )

    def handle(self, *args, **options):
        """Handle the population command."""
        clear_existing = options["clear_existing"]
        order_count = options["count"]
        user_count = options["users"]
        debug_prices = options["debug_prices"]

        if debug_prices:
            self._debug_price_cleaning()
            return

        # Disable signals during sample data creation
        from django.db.models.signals import post_save, pre_delete

        from apps.orders import signals as order_signals

        # Disconnect order-related signals
        post_save.disconnect(order_signals.handle_order_status_change, sender=Order)
        pre_delete.disconnect(
            order_signals.handle_order_item_deletion, sender=OrderItem
        )

        try:
            # Get or create sample users (outside transaction for better error handling)
            self.users = self._get_or_create_sample_users(user_count)

            # Get sample products
            self.products = list(Product.objects.all())

            if not self.products:
                self.stdout.write(
                    self.style.ERROR(
                        "No products found. Please run 'python manage.py products_sample_data' first."
                    )
                )
                return

            if clear_existing:
                self._clear_existing_data()

            # Create orders in transaction
            with transaction.atomic():
                self._create_sample_orders(order_count)

            # Create carts outside transaction to avoid atomic block issues
            self._create_sample_carts()

            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully created {order_count} sample orders and carts"
                )
            )

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error during population: {e}"))
            logger.error(f"Population error: {str(e)}", exc_info=True)
            raise
        finally:
            # Re-enable signals
            post_save.connect(order_signals.handle_order_status_change, sender=Order)
            pre_delete.connect(
                order_signals.handle_order_item_deletion, sender=OrderItem
            )

    def _debug_price_cleaning(self):
        """Debug price cleaning functionality."""
        self.stdout.write("Testing price cleaning functionality...")

        # Get a few products to test with
        products = Product.objects.all()[:5]

        for product in products:
            try:
                original_price = product.price
                cleaned_price = clean_price_value(original_price)
                money_obj = create_money_from_price(original_price)

                self.stdout.write(
                    f"Product: {product.name}\n"
                    f"  Original: {original_price} ({type(original_price).__name__})\n"
                    f"  Cleaned:  {cleaned_price} ({type(cleaned_price).__name__})\n"
                    f"  Money:    {money_obj} ({type(money_obj).__name__})\n"
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error with product {product.name}: {e}")
                )

    def _get_or_create_sample_users(self, count: int) -> list[User]:
        """Get or create sample users for orders."""
        users = []

        # Get existing users if they exist
        existing_users = list(User.objects.all()[:count])
        users.extend(existing_users)

        # Create additional users if needed
        for i in range(len(existing_users), count):
            first_name = random.choice(GHANAIAN_FIRST_NAMES)
            last_name = random.choice(GHANAIAN_LAST_NAMES)
            username = f"{first_name.lower()}.{last_name.lower()}{i}"
            email = f"{username}@example.com"

            user = User.objects.create_user(
                username=username,
                email=email,
                password="password123",
                first_name=first_name,
                last_name=last_name,
            )
            users.append(user)

        return users

    def _clear_existing_data(self) -> None:
        """Clear existing order data."""
        self.stdout.write("Clearing existing order data...")
        OrderItem.objects.all().delete()
        Order.objects.all().delete()
        CartItem.objects.all().delete()
        Cart.objects.all().delete()

    def _create_sample_orders(self, count: int) -> None:
        """Create sample orders with order items."""
        self.stdout.write(f"Creating {count} sample orders...")

        for i in range(count):
            user = random.choice(self.users)
            order_date = timezone.now() - timedelta(days=random.randint(0, 90))

            # Random order status based on weights
            status = random.choices(
                list(ORDER_STATUS_WEIGHTS.keys()),
                weights=list(ORDER_STATUS_WEIGHTS.values()),
                k=1,
            )[0]

            # Payment status based on order status
            if status == OrderStatus.CANCELLED:
                payment_status = random.choice(
                    [PaymentStatus.REFUNDED, PaymentStatus.FAILED]
                )
            else:
                payment_status = random.choices(
                    list(PAYMENT_STATUS_WEIGHTS.keys()),
                    weights=list(PAYMENT_STATUS_WEIGHTS.values()),
                    k=1,
                )[0]

            # Calculate initial amounts
            shipping_cost = Money(SHIPPING_COST, "GHS")
            discount_amount = Money(Decimal("0.00"), "GHS")

            # Create order with minimal initial data
            order = Order.objects.create(
                user=user,
                email=user.email,
                phone_number=f"+233{random.randint(20, 59)}{random.randint(1000000, 9999999)}",
                shipping_first_name=user.first_name,
                shipping_last_name=user.last_name,
                shipping_address_line_1=f"{random.randint(1, 999)} {random.choice(['Main', 'High', 'Market', 'Circle'])} St.",
                shipping_city=random.choice(GHANAIAN_CITIES),
                shipping_state="Greater Accra",
                shipping_postal_code=f"GA{random.randint(100, 999)}",
                shipping_country="Ghana",
                billing_same_as_shipping=True,
                status=status,
                payment_status=payment_status,
                shipping_cost=shipping_cost,
                discount_amount=discount_amount,
                # These will be calculated after items are added
                subtotal=Money(Decimal("0.00"), "GHS"),
                tax_amount=Money(Decimal("0.00"), "GHS"),
                total_amount=Money(Decimal("0.01"), "GHS"),  # Minimum required value
                notes=f"Sample order {i + 1}",
                created_at=order_date,
                updated_at=order_date,
            )

            # Add order items and calculate subtotal
            num_items = random.randint(MIN_ITEMS_PER_ORDER, MAX_ITEMS_PER_ORDER)
            product_list = list(self.products)
            selected_products = random.sample(
                product_list, min(num_items, len(product_list))
            )

            subtotal = Decimal("0.00")
            for product in selected_products:
                quantity = random.randint(MIN_QUANTITY_PER_ITEM, MAX_QUANTITY_PER_ITEM)

                try:
                    # Clean the price and create Money object
                    price_amount = clean_price_value(product.price)
                    price_money = create_money_from_price(product.price, "GHS")
                    item_total = price_amount * quantity

                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        product_name=product.name,
                        product_sku=product.sku,
                        quantity=quantity,
                        price=price_money,
                        total_price=Money(item_total, "GHS"),
                    )
                    subtotal += item_total

                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f"Error with product {product.name}: {e}")
                    )
                    logger.warning(f"Product order item error: {str(e)}")
                    continue

            # Calculate final totals
            tax_amount = subtotal * TAX_RATE
            total_amount = subtotal + tax_amount + SHIPPING_COST - Decimal("0.00")

            # Update order with calculated amounts
            order.subtotal = Money(subtotal, "GHS")
            order.tax_amount = Money(tax_amount, "GHS")
            order.total_amount = Money(total_amount, "GHS")
            order.save(
                update_fields=["subtotal", "tax_amount", "total_amount", "updated_at"]
            )

            # Update order status dates based on status
            self._update_order_dates(order)

    def _update_order_dates(self, order: Order) -> None:
        """Update order dates based on status."""
        if order.status in [OrderStatus.SHIPPED, OrderStatus.DELIVERED]:
            order.shipped_at = order.created_at + timedelta(days=random.randint(1, 3))
            order.tracking_number = f"GH{random.randint(1000000000, 9999999999)}"
            order.carrier = random.choice(["DHL", "FedEx", "UPS", "Ghana Post"])
            order.estimated_delivery_date = order.shipped_at + timedelta(
                days=random.randint(2, 7)
            )

        if order.status == OrderStatus.DELIVERED:
            order.delivered_at = order.shipped_at + timedelta(days=random.randint(1, 5))

        order.save()

    def _create_sample_carts(self) -> None:
        """Create sample shopping carts with items."""
        self.stdout.write("Creating sample shopping carts...")

        try:
            # Clear existing carts and cart items outside of transaction
            CartItem.objects.all().delete()
            Cart.objects.all().delete()

            product_list = list(self.products)
            User = get_user_model()
            users = list(User.objects.filter(is_active=True))

            successful_carts = 0
            total_cart_items = 0

            for user in users:
                try:
                    # Create cart for each user
                    cart = Cart.objects.create(user=user)
                    num_items = random.randint(1, min(3, len(product_list)))
                    cart_products = random.sample(product_list, k=num_items)

                    cart_items_created = 0
                    for product in cart_products:
                        try:
                            quantity = random.randint(1, 3)

                            # Skip if insufficient inventory
                            if (
                                product.track_inventory
                                and product.stock_quantity < quantity
                            ):
                                self.stdout.write(
                                    self.style.WARNING(
                                        f"Skipping {product.name} - insufficient stock"
                                    )
                                )
                                continue

                            # Clean the price BEFORE creating the CartItem
                            price_amount = clean_price_value(product.price)

                            # Validate the cleaned price
                            if price_amount <= 0:
                                self.stdout.write(
                                    self.style.WARNING(
                                        f"Skipping {product.name} - invalid price: {price_amount}"
                                    )
                                )
                                continue

                            # Create the cart item with properly formatted Money object
                            CartItem.objects.create(
                                cart=cart,
                                product=product,
                                quantity=quantity,
                                price=Money(price_amount, "GHS"),
                            )

                            cart_items_created += 1
                            total_cart_items += 1

                            logger.info(
                                f"Created cart item for {user.username}: "
                                f"{product.name} x{quantity} @ GHS{price_amount}"
                            )

                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(
                                    f"Error creating cart item for {product.name}: {e}"
                                )
                            )
                            logger.error(
                                f"Cart item creation error: {str(e)}", exc_info=True
                            )
                            continue

                    # Only update totals if we have items
                    if cart_items_created > 0:
                        cart.update_totals()
                        successful_carts += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Created cart for {user.username} with {cart_items_created} items"
                            )
                        )
                    else:
                        # Delete empty cart
                        cart.delete()
                        self.stdout.write(
                            self.style.WARNING(
                                f"No items added to cart for {user.username} - cart deleted"
                            )
                        )

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f"Error creating cart for {user.username}: {e}"
                        )
                    )
                    logger.error(f"Cart creation error: {str(e)}", exc_info=True)
                    continue

            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully created {successful_carts} shopping carts "
                    f"with {total_cart_items} total items"
                )
            )

        except Exception as e:
            logger.error(f"Error creating sample carts: {str(e)}", exc_info=True)
            raise
