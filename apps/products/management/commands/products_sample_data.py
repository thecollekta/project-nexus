# apps/products/management/commands/products_sample_data.py

"""
Management command to populate the database with realistic sample data.

This command creates a complete product catalog with categories, products,
images, and specifications for testing and demonstration purposes.

Usage:
    python manage.py products_sample_data
    python manage.py products_sample_data --clear-existing
    python manage.py products_sample_data --categories-only
    python manage.py products_sample_data --products-only --count 50
"""

import random
from decimal import Decimal
from typing import Any

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from apps.products.models import (Category, Product, ProductImage,
                                  ProductReview, ProductSpecification)

# Constants for product generation
DEFAULT_PRODUCT_COUNT = 100
PRICE_QUANTIZE = Decimal("0.99")
DISCOUNT_CHANCE = 0.3  # 30% chance of a discount
DISCOUNT_RANGE = (0.1, 0.4)  # 10-40% discount range
MAX_STOCK_QUANTITY = 200
LOW_STOCK_THRESHOLD_RANGE = (5, 20)
DEFAULT_FEATURED_CHANCE = 0.1
WEIGHT_QUANTIZE = Decimal("0.01")
DEFAULT_DESCRIPTION_LIMIT = 100
SKU_NUMBER_LENGTH = 3
MIN_IMAGES_PER_PRODUCT = 1
MAX_IMAGES_PER_PRODUCT = 4
IMAGE_SIZES = [400, 500, 600]  # Width in pixels

# Constants for availability dates
FUTURE_AVAILABILITY_CHANCE = 0.1  # 10% chance of future availability
LIMITED_AVAILABILITY_CHANCE = 0.05  # 5% chance of limited time availability
MIN_FUTURE_DAYS = 1
MAX_FUTURE_DAYS = 30
MIN_PAST_DAYS = 1
MAX_PAST_DAYS = 30
MIN_AVAILABILITY_DAYS = 30
MAX_AVAILABILITY_DAYS = 90

User = get_user_model()


class Command(BaseCommand):
    """Populate database with realistic sample data."""

    help = _("Populate the database with sample categories, products, and related data")

    def __init__(self):
        super().__init__()
        self.user = None
        self.categories = {}
        self.sample_users = []

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear-existing",
            action="store_true",
            help=_("Clear existing data before populating"),
        )
        parser.add_argument(
            "--categories-only",
            action="store_true",
            help=_("Only create categories, skip products"),
        )
        parser.add_argument(
            "--products-only",
            action="store_true",
            help=_(
                "Only create products, skip categories (requires existing categories)",
            ),
        )
        parser.add_argument(
            "--count",
            type=int,
            default=DEFAULT_PRODUCT_COUNT,
            help=_("Number of products to create (default: 100)"),
        )
        parser.add_argument(
            "--user",
            type=str,
            default="admin",
            help=_("Username to assign as creator (default: admin)"),
        )
        parser.add_argument(
            "--with-images",
            action="store_true",
            help=_("Create sample product images (placeholder URLs)"),
        )
        parser.add_argument(
            "--with-specs",
            action="store_true",
            help=_("Create sample product specifications"),
        )
        parser.add_argument(
            "--scenario",
            type=str,
            choices=["basic", "advanced", "demo", "performance"],
            default="basic",
            help=_("Data scenario to create"),
        )

    def handle(self, *args, **options):
        """Handle the population command."""
        clear_existing = options["clear_existing"]
        categories_only = options["categories_only"]
        products_only = options["products_only"]
        product_count = options["count"]
        username = options["user"]
        with_images = options["with_images"]
        with_specs = options["with_specs"]
        scenario = options.get("scenario", "basic")

        # Get or create user
        try:
            self.user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    _(f"User '{username}' does not exist. Creating superuser..."),
                ),
            )
            self.user = User.objects.create_superuser(
                username=username,
                email=f"{username}@example.com",
                password="admin123",  # noqa: S106
            )
            self.stdout.write(
                self.style.SUCCESS(_(f"Created superuser: {username}")),
            )

        # Create additional users for reviews
        self.stdout.write(_("Creating sample users for reviews..."))
        for i in range(5):
            email = f"user{i+1}@example.com"
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "username": f"user{i+1}",
                    "first_name": "Sample",
                    "last_name": f"User{i+1}",
                },
            )
            if created:
                user.set_password("password123")
                user.save()
            self.sample_users.append(user)

        # Clear existing data if requested
        if clear_existing:
            self._clear_existing_data()

        try:
            with transaction.atomic():
                if not products_only:
                    self._create_categories()

                if not categories_only:
                    if scenario == "basic":
                        # Create basic catalog (50 products)
                        options = 50
                        options = False
                        options = True
                    elif scenario == "advanced":
                        # Create advanced catalog (200 products with images and specs)
                        options = 200
                        options = True
                        options = True
                    elif scenario == "demo":
                        # Create demo catalog (100 featured products)
                        options = 100
                        options = True
                        options = True
                        self._create_demo_featured_products()
                    elif scenario == "performance":
                        # Create large catalog for performance testing (1000 products)
                        options = 1000
                        options = False
                        options = False

                    self._create_products(product_count, with_images, with_specs)

        except Exception as e:
            self.stderr.write(
                self.style.ERROR(_(f"Error during population: {e}")),
            )
            raise

        self.stdout.write(
            self.style.SUCCESS(_("Sample data population completed successfully!")),
        )

    def _clear_existing_data(self):
        """Clear existing sample data."""
        self.stdout.write(_("Clearing existing data..."))

        # Delete in proper order to avoid foreign key constraints
        ProductSpecification.objects.all().delete()
        ProductImage.objects.all().delete()
        Product.objects.all().delete()
        Category.objects.all().delete()

        self.stdout.write(self.style.SUCCESS(_("Existing data cleared")))

    def _create_categories(self):
        """Create sample category hierarchy."""
        self.stdout.write(_("Creating sample categories..."))

        category_data = {
            # Electronics
            "Electronics": {
                "description": "Electronic devices and accessories",
                "is_featured": True,
                "children": {
                    "Smartphones": {
                        "description": "Mobile phones and smartphones",
                        "is_featured": True,
                        "children": {
                            "iPhone": {"description": "Apple iPhone devices"},
                            "Android": {"description": "Android smartphones"},
                            "Accessories": {
                                "description": "Phone cases, chargers, screen protectors",
                            },
                        },
                    },
                    "Laptops": {
                        "description": "Laptop computers and notebooks",
                        "is_featured": True,
                        "children": {
                            "Gaming Laptops": {
                                "description": "High-performance gaming laptops",
                            },
                            "Business Laptops": {
                                "description": "Professional business laptops",
                            },
                            "Ultrabooks": {"description": "Thin and light ultrabooks"},
                        },
                    },
                    "Tablets": {
                        "description": "Tablet computers",
                        "children": {
                            "iPad": {"description": "Apple iPad tablets"},
                            "Android Tablets": {"description": "Android-based tablets"},
                            "Windows Tablets": {"description": "Windows-based tablets"},
                        },
                    },
                    "Audio": {
                        "description": "Audio equipment and accessories",
                        "children": {
                            "Headphones": {
                                "description": "Over-ear and on-ear headphones",
                            },
                            "Earbuds": {"description": "In-ear and wireless earbuds"},
                            "Speakers": {"description": "Bluetooth and wired speakers"},
                        },
                    },
                    "Smart Home": {
                        "description": "Smart home devices and IoT products",
                        "children": {
                            "Smart Speakers": {
                                "description": "Voice-activated smart speakers",
                            },
                            "Smart Lights": {
                                "description": "Smart bulbs and lighting systems",
                            },
                            "Security": {
                                "description": "Smart cameras and security systems",
                            },
                        },
                    },
                },
            },
            # Fashion & Apparel
            "Fashion & Apparel": {
                "description": "Clothing, shoes, and fashion accessories",
                "is_featured": True,
                "children": {
                    "Men's Clothing": {
                        "description": "Men's fashion and apparel",
                        "children": {
                            "Shirts": {"description": "Casual and formal shirts"},
                            "Pants": {"description": "Jeans, chinos, and dress pants"},
                            "Outerwear": {"description": "Jackets, coats, and hoodies"},
                        },
                    },
                    "Women's Clothing": {
                        "description": "Women's fashion and apparel",
                        "children": {
                            "Dresses": {"description": "Casual and formal dresses"},
                            "Tops": {"description": "Blouses, t-shirts, and tanks"},
                            "Bottoms": {"description": "Jeans, skirts, and pants"},
                        },
                    },
                    "Shoes": {
                        "description": "Footwear for all occasions",
                        "is_featured": True,
                        "children": {
                            "Sneakers": {"description": "Athletic and casual sneakers"},
                            "Dress Shoes": {"description": "Formal and business shoes"},
                            "Boots": {"description": "Casual and work boots"},
                        },
                    },
                    "Accessories": {
                        "description": "Fashion accessories",
                        "children": {
                            "Bags": {"description": "Handbags, backpacks, and wallets"},
                            "Jewelry": {"description": "Rings, necklaces, and watches"},
                            "Belts": {"description": "Leather and fabric belts"},
                        },
                    },
                },
            },
            # Home & Garden
            "Home & Garden": {
                "description": "Home improvement and gardening supplies",
                "children": {
                    "Furniture": {
                        "description": "Home and office furniture",
                        "is_featured": True,
                        "children": {
                            "Living Room": {
                                "description": "Sofas, chairs, and coffee tables",
                            },
                            "Bedroom": {
                                "description": "Beds, dressers, and nightstands",
                            },
                            "Office": {"description": "Desks, chairs, and storage"},
                        },
                    },
                    "Kitchen": {
                        "description": "Kitchen appliances and accessories",
                        "children": {
                            "Small Appliances": {
                                "description": "Blenders, coffee makers, toasters",
                            },
                            "Cookware": {
                                "description": "Pots, pans, and baking dishes",
                            },
                            "Utensils": {
                                "description": "Knives, cutting boards, and tools",
                            },
                        },
                    },
                    "Garden": {
                        "description": "Gardening supplies and outdoor equipment",
                        "children": {
                            "Plants": {"description": "Indoor and outdoor plants"},
                            "Tools": {"description": "Garden tools and equipment"},
                            "Outdoor Furniture": {
                                "description": "Patio and garden furniture",
                            },
                        },
                    },
                },
            },
            # Sports & Outdoors
            "Sports & Outdoors": {
                "description": "Athletic equipment and outdoor gear",
                "children": {
                    "Fitness": {
                        "description": "Fitness and exercise equipment",
                        "children": {
                            "Cardio Equipment": {
                                "description": "Treadmills, bikes, and ellipticals",
                            },
                            "Strength Training": {
                                "description": "Weights, benches, and racks",
                            },
                            "Accessories": {
                                "description": "Yoga mats, resistance bands",
                            },
                        },
                    },
                    "Outdoor Recreation": {
                        "description": "Outdoor activities and sports",
                        "children": {
                            "Camping": {
                                "description": "Tents, sleeping bags, and gear",
                            },
                            "Hiking": {
                                "description": "Backpacks, boots, and accessories",
                            },
                            "Water Sports": {
                                "description": "Kayaks, paddleboards, and gear",
                            },
                        },
                    },
                    "Team Sports": {
                        "description": "Equipment for team sports",
                        "children": {
                            "Basketball": {
                                "description": "Basketballs, hoops, and gear",
                            },
                            "Football": {"description": "Footballs, helmets, and pads"},
                            "Soccer": {
                                "description": "Soccer balls, cleats, and goals",
                            },
                        },
                    },
                },
            },
        }

        self._create_category_tree(category_data)
        self.stdout.write(
            self.style.SUCCESS(_(f"Created {Category.objects.count()} categories")),
        )

    def _create_category_tree(self, category_data: dict, parent=None, level=0):
        """Recursively create category hierarchy."""
        for name, data in category_data.items():
            # Create category
            category, created = Category.objects.get_or_create(
                name=name,
                description=data.get("description", f"{name} category"),
                parent=parent,
                is_featured=data.get("is_featured", False),
                sort_order=level,
                created_by=self.user,
                updated_by=self.user,
            )

            # Store for later use
            self.categories[name.lower().replace(" ", "_")] = category

            if created:
                self.stdout.write(f"  {'  ' * level}Created category: {name}")

            # Create children
            children = data.get("children", {})
            if children:
                self._create_category_tree(children, category, level + 1)

    def _get_leaf_categories(self):
        """Get all leaf categories (categories without children)."""
        leaf_categories = [
            category
            for category in Category.objects.all()
            if not category.children.exists()
        ]
        return leaf_categories or list(Category.objects.all())

    def _create_single_product(
        self,
        template: dict,
        category: Category,
        index: int,
    ) -> Product:
        """Create a single product from template."""
        try:
            # Generate product name
            name_template = random.choice(template["name_templates"])
            name = self._generate_product_name(name_template, template, index)

            # Generate unique slug
            base_slug = slugify(name)
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            # Generate SKU
            sku = self._generate_sku(name, category, index)

            # Check if SKU already exists
            while Product.objects.filter(sku=sku).exists():
                sku = f"{sku}-{random.randint(100, 999)}"

            # Generate pricing
            min_price, max_price = template["price_range"]
            base_price = Decimal(str(random.uniform(min_price, max_price))).quantize(
                PRICE_QUANTIZE
            )

            # Sometimes add compare_at_price for discounts
            compare_at_price = None
            if random.random() < DISCOUNT_CHANCE:  # 30% chance of discount
                discount = random.uniform(*DISCOUNT_RANGE)  # 10-40% discount
                compare_at_price = base_price / (
                    Decimal("1.0") - Decimal(str(discount))
                )
                compare_at_price = compare_at_price.quantize(PRICE_QUANTIZE)

            # Generate descriptions
            description = random.choice(template["descriptions"])
            short_description = (
                description[:DEFAULT_DESCRIPTION_LIMIT] + "..."
                if len(description) > DEFAULT_DESCRIPTION_LIMIT
                else description
            )

            # Generate stock
            stock_quantity = random.randint(0, MAX_STOCK_QUANTITY)
            low_stock_threshold = random.randint(*LOW_STOCK_THRESHOLD_RANGE)

            # Generate weight
            if "weight_range" in template:
                weight_min, weight_max = template["weight_range"]
                weight = Decimal(str(random.uniform(weight_min, weight_max))).quantize(
                    WEIGHT_QUANTIZE
                )
            else:
                weight = None

            # Determine if featured
            is_featured = random.random() < template.get(
                "featured_chance",
                DEFAULT_FEATURED_CHANCE,
            )

            # Create and return product
            return Product.objects.create(
                name=name,
                slug=slug,
                sku=sku,
                description=f"{description} This {name.lower()} combines quality, performance, and value in one exceptional package.",
                short_description=short_description,
                category=category,
                price=base_price,
                compare_at_price=compare_at_price,
                stock_quantity=stock_quantity,
                low_stock_threshold=low_stock_threshold,
                weight=weight,
                is_featured=is_featured,
                is_digital=template.get("digital", False),
                track_inventory=True,
                allow_backorders=random.choice([True, False]),
                created_by=self.user,
                updated_by=self.user,
            )
        except Exception as e:
            self.stderr.write(f"Error creating product: {str(e)}")
            return None

    def _generate_product_name(
        self,
        template: str,
        template_data: dict,
        index: int,
    ) -> str:
        """Generate product name from template."""
        name = template

        # Replace placeholders
        replacements = {
            "{model}": random.choice(
                template_data.get("models", [str(index % 10 + 1)]),
            ),
            "{adjective}": random.choice(template_data.get("adjectives", ["Premium"])),
            "{type}": random.choice(template_data.get("types", ["Product"])),
            "{brand}": random.choice(template_data.get("brands", ["Brand"])),
            "{material}": random.choice(template_data.get("materials", ["Premium"])),
            "{style}": random.choice(template_data.get("styles", ["Style"])),
        }

        for placeholder, replacement in replacements.items():
            name = name.replace(placeholder, replacement)

        return name

    def _generate_sku(self, name: str, category: Category, index: int) -> str:
        """Generate SKU from product name and category."""
        # Get category prefix
        category_prefix = category.name[:3].upper()

        # Get product prefix from name
        words = name.split()
        product_prefix = "".join([word[:2].upper() for word in words[:2]])

        # Generate number
        number = str(index).zfill(SKU_NUMBER_LENGTH)

        return f"{category_prefix}-{product_prefix}-{number}"

    def _create_product_images(self, product: Product):
        """Create sample product images."""
        # Create 1-4 images per product
        image_count = random.randint(MIN_IMAGES_PER_PRODUCT, MAX_IMAGES_PER_PRODUCT)

        for i in range(image_count):
            # Generate placeholder image URL
            width = random.choice(IMAGE_SIZES)
            height = width  # Square images

            # Use a placeholder service
            image_url = (
                f"https://picsum.photos/{width}/{height}?random={product.id}-{i}"
            )

            ProductImage.objects.create(
                product=product,
                image=image_url,  # In real scenario, this would be a file upload
                alt_text=f"{product.name} image {i + 1}",
                sort_order=i,
                is_primary=(i == 0),  # First image is primary
                created_by=self.user,
                updated_by=self.user,
            )

    def _create_product_specifications(self, product: Product, category_key: str):
        """Create sample product specifications."""
        spec_templates = {
            "smartphones": {
                "Display Size": [
                    "5.4 inches",
                    "6.1 inches",
                    "6.7 inches",
                    "6.8 inches",
                ],
                "Storage": ["64GB", "128GB", "256GB", "512GB", "1TB"],
                "RAM": ["4GB", "6GB", "8GB", "12GB", "16GB"],
                "Camera": ["12MP", "48MP", "64MP", "108MP"],
                "Battery": ["3000mAh", "4000mAh", "5000mAh", "6000mAh"],
                "Operating System": ["iOS 16", "iOS 17", "Android 12", "Android 13"],
            },
            "laptops": {
                "Screen Size": [
                    "13.3 inches",
                    "14 inches",
                    "15.6 inches",
                    "17.3 inches",
                ],
                "Processor": [
                    "Intel i5",
                    "Intel i7",
                    "AMD Ryzen 5",
                    "AMD Ryzen 7",
                    "Apple M1",
                    "Apple M2",
                ],
                "RAM": ["8GB", "16GB", "32GB", "64GB"],
                "Storage": ["256GB SSD", "512GB SSD", "1TB SSD", "2TB SSD"],
                "Graphics": ["Integrated", "GTX 1650", "RTX 3060", "RTX 4070"],
                "Operating System": ["Windows 11", "macOS", "Linux"],
            },
            "audio": {
                "Type": ["Over-ear", "On-ear", "In-ear", "Wireless", "Wired"],
                "Driver Size": ["30mm", "40mm", "50mm", "6mm", "10mm"],
                "Frequency Response": ["20Hz-20kHz", "15Hz-25kHz", "10Hz-40kHz"],
                "Impedance": ["16 ohms", "32 ohms", "50 ohms", "80 ohms"],
                "Connectivity": [
                    "Bluetooth 5.0",
                    "Bluetooth 5.2",
                    "Wired 3.5mm",
                    "USB-C",
                    "Lightning",
                ],
                "Battery Life": ["20 hours", "30 hours", "40 hours", "50 hours"],
            },
            "clothing": {
                "Material": [
                    "100% Cotton",
                    "Cotton Blend",
                    "Polyester",
                    "Wool",
                    "Silk",
                    "Linen",
                ],
                "Size": ["XS", "S", "M", "L", "XL", "XXL"],
                "Fit": ["Slim", "Regular", "Loose", "Athletic"],
                "Care Instructions": [
                    "Machine wash cold",
                    "Hand wash only",
                    "Dry clean only",
                ],
                "Country of Origin": ["USA", "China", "India", "Bangladesh", "Vietnam"],
            },
            "shoes": {
                "Size": ["7", "8", "9", "10", "11", "12", "13"],
                "Width": ["Narrow", "Medium", "Wide"],
                "Material": ["Leather", "Synthetic", "Canvas", "Mesh", "Suede"],
                "Sole Type": ["Rubber", "EVA", "Polyurethane", "Cork"],
                "Heel Height": [
                    "Flat",
                    "Low (1-2 inches)",
                    "Medium (2-3 inches)",
                    "High (3+ inches)",
                ],
            },
            "furniture": {
                "Material": [
                    "Solid Wood",
                    "Engineered Wood",
                    "Metal",
                    "Glass",
                    "Upholstered",
                ],
                "Dimensions": ["Small", "Medium", "Large", "Extra Large"],
                "Weight Capacity": ["100 lbs", "200 lbs", "300 lbs", "500 lbs"],
                "Assembly Required": ["Yes", "No", "Minimal"],
                "Warranty": ["1 Year", "2 Years", "5 Years", "Lifetime"],
            },
            "kitchen": {
                "Power": ["500W", "750W", "1000W", "1200W", "1500W"],
                "Capacity": ["1 cup", "4 cups", "8 cups", "12 cups", "16 cups"],
                "Material": ["Stainless Steel", "Plastic", "Glass", "Ceramic"],
                "Dishwasher Safe": ["Yes", "No", "Parts only"],
                "Warranty": ["1 Year", "2 Years", "3 Years"],
            },
            "fitness": {
                "Weight Range": ["5-50 lbs", "10-90 lbs", "Adjustable", "Fixed"],
                "Material": ["Cast Iron", "Rubber Coated", "Neoprene", "Steel"],
                "Grip Type": ["Knurled", "Ergonomic", "Textured", "Smooth"],
                "Dimensions": ["Compact", "Standard", "Large"],
                "Suitable For": ["Beginner", "Intermediate", "Advanced", "All Levels"],
            },
        }

        # Get specifications for this category
        category_specs = spec_templates.get(
            category_key,
            {
                "Brand": ["Premium", "Standard", "Value", "Professional"],
                "Model": ["Basic", "Standard", "Pro", "Elite"],
                "Warranty": ["1 Year", "2 Years", "3 Years"],
                "Color": ["Black", "White", "Silver", "Blue", "Red"],
            },
        )

        # Create 2-6 random specifications
        spec_count = random.randint(2, min(6, len(category_specs)))
        selected_specs = random.sample(list(category_specs.keys()), spec_count)

        for i, spec_name in enumerate(selected_specs):
            spec_value = random.choice(category_specs[spec_name])

            ProductSpecification.objects.create(
                product=product,
                name=spec_name,
                value=spec_value,
                sort_order=i,
                created_by=self.user,
                updated_by=self.user,
            )

    def _get_category_path_string(self, category: Category) -> str:
        """Build and return the category path as a string."""
        path = []
        current = category
        while current:
            path.append(current.name.lower())
            current = current.parent
        return " ".join(reversed(path))

    def _get_category_key(self, category: Category) -> str:
        """Get category key for template lookup."""
        # Define category patterns and their corresponding keys
        category_patterns = {
            "smartphones": ["smartphone", "iphone", "android"],
            "laptops": ["laptop"],
            "tablets": ["tablet"],
            "audio": ["audio", "headphone", "speaker"],
            "clothing": ["clothing", "shirt", "dress"],
            "shoes": ["shoe", "sneaker", "boot"],
            "furniture": ["furniture"],
            "kitchen": ["kitchen"],
            "fitness": ["fitness", "sports"],
        }

        path_str = self._get_category_path_string(category)

        # Find the first matching category pattern
        for key, patterns in category_patterns.items():
            if any(pattern in path_str for pattern in patterns):
                return key

        return "default"

    def _get_random_availability_dates(self):
        """Generate random availability dates.

        Returns:
            tuple: A tuple of (available_from, available_until) datetimes
        """
        now = timezone.now()

        # Check for future availability
        if random.random() < FUTURE_AVAILABILITY_CHANCE:
            available_from = now + timezone.timedelta(
                days=random.randint(MIN_FUTURE_DAYS, MAX_FUTURE_DAYS),
            )
            available_until = None
        # Check for limited time availability
        elif random.random() < LIMITED_AVAILABILITY_CHANCE:
            available_from = now - timezone.timedelta(
                days=random.randint(MIN_PAST_DAYS, MAX_PAST_DAYS),
            )
            available_until = now + timezone.timedelta(
                days=random.randint(MIN_AVAILABILITY_DAYS, MAX_AVAILABILITY_DAYS),
            )
        else:
            available_from = None
            available_until = None

        return available_from, available_until

    def _get_product_templates(self) -> dict[str, list[dict[str, Any]]]:
        """Get product templates organized by category."""
        return {
            "smartphones": [
                {
                    "name_templates": [
                        "iPhone {model} Pro",
                        "iPhone {model}",
                        "Galaxy S{model}",
                        "Pixel {model} Pro",
                        "OnePlus {model}T",
                        "Xiaomi Mi {model}",
                    ],
                    "models": ["13", "14", "15", "22", "23", "11", "12"],
                    "descriptions": [
                        "Latest flagship smartphone with advanced camera system and powerful performance.",
                        "Premium smartphone featuring cutting-edge technology and sleek design.",
                        "High-performance mobile device with exceptional battery life and display quality.",
                    ],
                    "price_range": (299, 1299),
                    "digital": False,
                    "weight_range": (0.150, 0.250),
                    "featured_chance": 0.3,
                },
            ],
            "laptops": [
                {
                    "name_templates": [
                        "MacBook {model}",
                        "ThinkPad {model}",
                        "XPS {model}",
                        "Surface Laptop {model}",
                        "ZenBook {model}",
                        "Pavilion {model}",
                    ],
                    "models": ["Pro", "Air", "X1", "13", "15", "17", "Studio"],
                    "descriptions": [
                        "High-performance laptop designed for professionals and power users.",
                        "Ultrabook with premium build quality and exceptional portability.",
                        "Gaming laptop with dedicated graphics and advanced cooling system.",
                    ],
                    "price_range": (599, 2999),
                    "digital": False,
                    "weight_range": (1.2, 3.5),
                    "featured_chance": 0.25,
                },
            ],
            "tablets": [
                {
                    "name_templates": [
                        "iPad {model}",
                        "Galaxy Tab {model}",
                        "Surface {model}",
                        "Fire HD {model}",
                        "MatePad {model}",
                    ],
                    "models": ["Pro", "Air", "Mini", "S8", "S9", "Pro 8", "10", "11"],
                    "descriptions": [
                        "Versatile tablet perfect for work, creativity, and entertainment.",
                        "Premium tablet with stunning display and powerful performance.",
                        "Lightweight tablet ideal for reading, browsing, and media consumption.",
                    ],
                    "price_range": (149, 1499),
                    "digital": False,
                    "weight_range": (0.3, 0.8),
                    "featured_chance": 0.2,
                },
            ],
            "audio": [
                {
                    "name_templates": [
                        "AirPods {model}",
                        "WH-1000X{model}",
                        "QuietComfort {model}",
                        "Studio{model}",
                        "JBL {model}",
                        "Beats {model}",
                    ],
                    "models": ["Pro", "Max", "M5", "45", "Live", "Solo"],
                    "descriptions": [
                        "Premium wireless headphones with noise cancellation technology.",
                        "High-fidelity audio experience with superior sound quality.",
                        "Comfortable headphones perfect for long listening sessions.",
                    ],
                    "price_range": (49, 549),
                    "digital": False,
                    "weight_range": (0.05, 0.4),
                    "featured_chance": 0.3,
                },
            ],
            "clothing": [
                {
                    "name_templates": [
                        "{adjective} {type} Shirt",
                        "{adjective} {type} Dress",
                        "{brand} {type} Jacket",
                        "{material} {type} Pants",
                    ],
                    "adjectives": [
                        "Classic",
                        "Modern",
                        "Vintage",
                        "Premium",
                        "Casual",
                        "Formal",
                    ],
                    "types": ["Cotton", "Silk", "Denim", "Wool", "Linen"],
                    "brands": ["Essentials", "Collection", "Premium", "Classic"],
                    "materials": ["Cotton", "Polyester", "Blend", "Organic"],
                    "descriptions": [
                        "Comfortable and stylish clothing item perfect for everyday wear.",
                        "High-quality garment made from premium materials.",
                        "Fashionable piece that combines style with comfort.",
                    ],
                    "price_range": (19, 199),
                    "digital": False,
                    "weight_range": (0.1, 1.0),
                    "featured_chance": 0.15,
                },
            ],
            "shoes": [
                {
                    "name_templates": [
                        "Air {model}",
                        "Ultra{model}",
                        "{brand} {type}",
                        "Classic {type}",
                        "Sport {type}",
                    ],
                    "models": ["Max", "Force", "Boost", "Runner", "Walker"],
                    "brands": ["Nike", "Adidas", "Puma", "New Balance", "Converse"],
                    "types": ["Sneaker", "Runner", "Trainer", "Casual", "Sport"],
                    "descriptions": [
                        "Comfortable athletic shoe designed for performance and style.",
                        "Premium footwear with advanced cushioning and support.",
                        "Stylish shoe perfect for casual wear and light activities.",
                    ],
                    "price_range": (59, 299),
                    "digital": False,
                    "weight_range": (0.4, 1.2),
                    "featured_chance": 0.2,
                },
            ],
            "furniture": [
                {
                    "name_templates": [
                        "{material} {type} {style}",
                        "Modern {type}",
                        "{adjective} {material} {type}",
                    ],
                    "materials": ["Oak", "Pine", "Steel", "Leather", "Fabric"],
                    "types": ["Chair", "Table", "Sofa", "Desk", "Bed", "Cabinet"],
                    "styles": ["Chair", "Table", "Set", "Collection"],
                    "adjectives": ["Vintage", "Modern", "Classic", "Contemporary"],
                    "descriptions": [
                        "Stylish furniture piece that combines functionality with design.",
                        "High-quality furniture crafted from premium materials.",
                        "Comfortable and durable furniture perfect for any home.",
                    ],
                    "price_range": (99, 1999),
                    "digital": False,
                    "weight_range": (5.0, 50.0),
                    "featured_chance": 0.1,
                },
            ],
            "kitchen": [
                {
                    "name_templates": [
                        "{brand} {type}",
                        "Professional {type}",
                        "Stainless Steel {type}",
                        "{adjective} {type}",
                    ],
                    "brands": ["KitchenAid", "Cuisinart", "Breville", "Hamilton Beach"],
                    "types": [
                        "Blender",
                        "Coffee Maker",
                        "Toaster",
                        "Mixer",
                        "Food Processor",
                    ],
                    "adjectives": ["Digital", "Premium", "Compact", "Professional"],
                    "descriptions": [
                        "High-performance kitchen appliance for culinary enthusiasts.",
                        "Professional-grade equipment perfect for home cooking.",
                        "Reliable kitchen tool that makes cooking easier and more enjoyable.",
                    ],
                    "price_range": (29, 699),
                    "digital": False,
                    "weight_range": (0.5, 15.0),
                    "featured_chance": 0.15,
                },
            ],
            "fitness": [
                {
                    "name_templates": [
                        "{type} {model}",
                        "Professional {type}",
                        "Adjustable {type}",
                        "{brand} {type}",
                    ],
                    "types": [
                        "Dumbbell",
                        "Kettlebell",
                        "Yoga Mat",
                        "Resistance Band",
                        "Foam Roller",
                    ],
                    "models": ["Set", "Pro", "Elite", "Premium", "Standard"],
                    "brands": ["Bowflex", "NordicTrack", "Gaiam", "TRX"],
                    "descriptions": [
                        "Professional fitness equipment for effective home workouts.",
                        "Durable exercise gear built to last through intensive training.",
                        "Versatile fitness accessory suitable for all skill levels.",
                    ],
                    "price_range": (15, 899),
                    "digital": False,
                    "weight_range": (0.2, 25.0),
                    "featured_chance": 0.2,
                },
            ],
            "default": [
                {
                    "name_templates": [
                        "Premium {type}",
                        "Professional {type}",
                        "Classic {type}",
                        "Modern {type}",
                    ],
                    "types": ["Product", "Item", "Accessory", "Tool", "Equipment"],
                    "descriptions": [
                        "High-quality product designed for everyday use.",
                        "Premium item with excellent build quality and performance.",
                        "Versatile product perfect for various applications.",
                    ],
                    "price_range": (19, 299),
                    "digital": False,
                    "weight_range": (0.1, 5.0),
                    "featured_chance": 0.1,
                },
            ],
        }

    def _create_single_product_with_extras(
        self,
        category,
        template,
        index,
        with_images,
        with_specs,
    ):
        """Create a single product with optional images and specifications."""
        product = self._create_single_product(template, category, index)
        if not product:
            return False

        if with_images:
            self._create_product_images(product)

        if with_specs:
            category_key = self._get_category_key(category)
            self._create_product_specifications(product, category_key)

        return True

    def _create_products(self, count: int, with_images: bool, with_specs: bool):
        """Create sample products.

        Args:
            count: Number of products to create
            with_images: Whether to create product images
            with_specs: Whether to create product specifications
        """
        self.stdout.write(_(f"Creating {count} sample products..."))

        if not Category.objects.exists():
            self.stdout.write(
                self.style.ERROR(
                    "No categories found. Please create categories first.",
                ),
            )
            return

        leaf_categories = self._get_leaf_categories()
        product_templates = self._get_product_templates()
        created_count = 0

        for i in range(count):
            try:
                category = random.choice(leaf_categories)
                templates = product_templates.get(
                    self._get_category_key(category),
                    product_templates["default"],
                )
                template = random.choice(templates)

                if self._create_single_product_with_extras(
                    category,
                    template,
                    i + 1,
                    with_images,
                    with_specs,
                ):
                    created_count += 1
                    if created_count % 20 == 0:
                        self.stdout.write(f"  Created {created_count} products...")

            except Exception as e:
                self.stderr.write(f"Error creating product {i + 1}: {e}")
                continue

        self.stdout.write(
            self.style.SUCCESS(f"Created {created_count} products successfully"),
        )

    def _print_summary(self):
        """Print summary statistics."""
        category_count = Category.objects.count()
        product_count = Product.objects.count()
        featured_count = Product.objects.filter(is_featured=True).count()
        image_count = ProductImage.objects.count()
        spec_count = ProductSpecification.objects.count()

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDatabase Population Summary:\n"
                f"{'=' * 50}\n"
                f"Categories:     {category_count:>6}\n"
                f"Products:       {product_count:>6}\n"
                f"Featured:       {featured_count:>6}\n"
                f"Images:         {image_count:>6}\n"
                f"Specifications: {spec_count:>6}\n"
                f"{'=' * 50}\n"
                f"Sample data population completed successfully!",
            ),
        )

        # Show category breakdown
        self.stdout.write("\nCategory Breakdown:")
        root_categories = Category.objects.filter(parent__isnull=True)
        for root in root_categories:
            product_count = Product.objects.filter(
                category__in=[root, root.get_descendants()],
            ).count()
            self.stdout.write(f"  {root.name}: {product_count} products")

    def _create_demo_featured_products(self):
        """Create specific featured products for demo purposes."""
        demo_products = [
            {
                "name": "iPhone 15 Pro Max",
                "category": "smartphones",
                "price": 1199.99,
                "compare_at_price": 1299.99,
                "description": "The most advanced iPhone ever with titanium design and Action Button.",
                "is_featured": True,
                "stock_quantity": 50,
            },
            {
                "name": "MacBook Pro 16-inch M3",
                "category": "laptops",
                "price": 2499.99,
                "compare_at_price": 2699.99,
                "description": "Supercharged for pros with the most advanced chip yet.",
                "is_featured": True,
                "stock_quantity": 25,
            },
            {
                "name": "AirPods Pro (2nd generation)",
                "category": "audio",
                "price": 249.99,
                "description": "Richer audio experience with Adaptive Audio and Personalized Spatial Audio.",
                "is_featured": True,
                "stock_quantity": 100,
            },
            {
                "name": "Sony WH-1000XM5",
                "category": "audio",
                "price": 399.99,
                "compare_at_price": 449.99,
                "description": "Industry-leading noise canceling with exceptional sound quality.",
                "is_featured": True,
                "stock_quantity": 75,
            },
        ]

        for product_data in demo_products:
            # Find appropriate category
            category = Category.objects.filter(
                name__icontains=product_data["category"],
            ).first()

            if category:
                Product.objects.get_or_create(
                    sku=slugify(product_data["name"]).upper()[:20],
                    defaults={
                        "name": product_data["name"],
                        "description": product_data["description"],
                        "category": category,
                        "price": Decimal(str(product_data["price"])),
                        "compare_at_price": Decimal(
                            str(product_data.get("compare_at_price", 0)),
                        )
                        or None,
                        "is_featured": product_data.get("is_featured", False),
                        "stock_quantity": product_data.get("stock_quantity", 10),
                        "created_by": self.user,
                        "updated_by": self.user,
                    },
                )

    def _create_product_reviews(self, product: Product):
        """Create sample reviews for a product."""
        review_count = random.randint(0, 15)
        if review_count == 0:
            return

        review_templates = {
            "titles": [
                "Amazing!",
                "Great product",
                "Not bad",
                "Could be better",
                "Excellent value",
                "Works as expected",
            ],
            "comments": [
                "I'm really impressed with the quality. Highly recommended.",
                "This was exactly what I was looking for. Five stars!",
                "It's a good product for the price, but I've seen better.",
                "The build quality is a bit lacking, but it does the job.",
                "Shipping was fast and the item was well-packaged. Happy with my purchase.",
                "I've been using this for a few weeks now and it's holding up well.",
            ],
        }

        for _ in range(review_count):  # noqa: F402
            user = random.choice(self.sample_users)
            # Use get_or_create to avoid errors if a user accidentally gets picked twice
            ProductReview.objects.get_or_create(
                product=product,
                user=user,
                defaults={
                    "rating": random.randint(1, 5),
                    "title": random.choice(review_templates["titles"]),
                    "comment": random.choice(review_templates["comments"]),
                },
            )

    def _create_single_product_with_extras(
        self,
        category,
        template,
        index,
        with_images,
        with_specs,
    ):
        """Create a single product with optional images, specifications, and reviews."""
        product = self._create_single_product(template, category, index)
        if not product:
            return False

        if with_images:
            self._create_product_images(product)

        if with_specs:
            category_key = self._get_category_key(category)
            self._create_product_specifications(product, category_key)

        # ADD THIS LINE: Call the new review creation method
        self._create_product_reviews(product)

        return True


# Example usage documentation
"""
USAGE EXAMPLES:

1. Basic setup (50 products with specifications):
   python manage.py products_sample_data --scenario basic

2. Advanced setup (200 products with images and specs):
   python manage.py products_sample_data --scenario advanced

3. Demo setup (100 products with featured items):
   python manage.py products_sample_data --scenario demo

4. Performance testing (1000 products, minimal data):
   python manage.py products_sample_data --scenario performance

5. Custom setup:
   python manage.py products_sample_data --count 300 --with-images --with-specs

6. Clear and repopulate:
   python manage.py products_sample_data --clear-existing --scenario advanced

7. Only create categories:
   python manage.py products_sample_data --categories-only

8. Only create products (requires existing categories):
   python manage.py products_sample_data --products-only --count 150

SAMPLE DATA INCLUDES:

Categories (4 main hierarchies):
- Electronics (Smartphones, Laptops, Tablets, Audio, Smart Home)
- Fashion & Apparel (Men's/Women's Clothing, Shoes, Accessories)  
- Home & Garden (Furniture, Kitchen, Garden)
- Sports & Outdoors (Fitness, Outdoor Recreation, Team Sports)

Products:
- Realistic names and descriptions
- Category-appropriate specifications
- Varied pricing with occasional discounts
- Random stock levels and weights
- Featured products (10-30% depending on category)
- Proper SEO-friendly slugs and SKUs

Each product includes:
- Unique SKU based on category and name
- Realistic pricing based on category
- 30% chance of discount pricing
- Random stock levels (0-200 units)
- Weight data for physical products
- Category-specific specifications
- Optional placeholder images
"""
