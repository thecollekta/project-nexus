# apps/products/schema.py

import graphene
from django.db.models import Q
from graphene_django import DjangoObjectType
from graphql import GraphQLError

from apps.products.models import Category, Product, ProductImage, ProductSpecification


class CategoryType(DjangoObjectType):
    class Meta:
        model = Category
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "parent",
            "image",
            "icon",
            "sort_order",
            "is_featured",
            "meta_title",
            "meta_description",
            "meta_keywords",
            "created_at",
            "updated_at",
        )

    product_count = graphene.Int()
    level = graphene.Int()
    children = graphene.List(lambda: CategoryType)
    ancestors = graphene.List(lambda: CategoryType)

    def resolve_product_count(self, info):
        return self.products.count()

    def resolve_level(self, info):
        return self.get_level()

    def resolve_children(self, info):
        return self.children.filter(is_active=True).order_by("sort_order", "name")

    def resolve_ancestors(self, info):
        return self.get_ancestors()


class ProductImageType(DjangoObjectType):
    class Meta:
        model = ProductImage
        fields = ("id", "image", "alt_text", "sort_order", "is_primary", "created_at")


class ProductSpecificationType(DjangoObjectType):
    class Meta:
        model = ProductSpecification
        fields = ("id", "name", "value", "sort_order")


class ProductType(DjangoObjectType):
    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "slug",
            "sku",
            "description",
            "short_description",
            "category",
            "price",
            "compare_at_price",
            "cost_price",
            "stock_quantity",
            "low_stock_threshold",
            "track_inventory",
            "allow_backorders",
            "weight",
            "dimensions_length",
            "dimensions_width",
            "dimensions_height",
            "featured_image",
            "is_featured",
            "is_digital",
            "requires_shipping",
            "meta_title",
            "meta_description",
            "meta_keywords",
            "available_from",
            "available_until",
            "created_at",
            "updated_at",
        )

    images = graphene.List(ProductImageType)
    specifications = graphene.List(ProductSpecificationType)
    discount_percentage = graphene.Float()
    is_in_stock = graphene.Boolean()
    is_low_stock = graphene.Boolean()

    def resolve_images(self, info):
        return self.images.all().order_by("sort_order")

    def resolve_specifications(self, info):
        return self.specifications.all().order_by("sort_order")

    def resolve_discount_percentage(self, info):
        if self.compare_at_price and self.compare_at_price > self.price:
            return round(
                ((self.compare_at_price - self.price) / self.compare_at_price) * 100,
                2,
            )
        return 0

    def resolve_is_in_stock(self, info):
        return self.is_in_stock()

    def resolve_is_low_stock(self, info):
        return self.is_low_stock()


class CategoryInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    slug = graphene.String()
    description = graphene.String()
    parent_id = graphene.ID()
    image = graphene.String()
    icon = graphene.String()
    sort_order = graphene.Int()
    is_featured = graphene.Boolean()
    meta_title = graphene.String()
    meta_description = graphene.String()
    meta_keywords = graphene.String()


class ProductInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    slug = graphene.String()
    sku = graphene.String(required=True)
    description = graphene.String(required=True)
    short_description = graphene.String()
    category_id = graphene.ID(required=True)
    price = graphene.Decimal(required=True)
    compare_at_price = graphene.Decimal()
    cost_price = graphene.Decimal()
    stock_quantity = graphene.Int(required=True)
    low_stock_threshold = graphene.Int()
    track_inventory = graphene.Boolean()
    allow_backorders = graphene.Boolean()
    weight = graphene.Decimal()
    dimensions_length = graphene.Decimal()
    dimensions_width = graphene.Decimal()
    dimensions_height = graphene.Decimal()
    featured_image = graphene.String()
    is_featured = graphene.Boolean()
    is_digital = graphene.Boolean()
    requires_shipping = graphene.Boolean()
    meta_title = graphene.String()
    meta_description = graphene.String()
    meta_keywords = graphene.String()
    available_from = graphene.DateTime()
    available_until = graphene.DateTime()


class Query(graphene.ObjectType):
    categories = graphene.List(
        CategoryType,
        featured=graphene.Boolean(),
        parent=graphene.ID(),
        search=graphene.String(),
    )
    category = graphene.Field(CategoryType, id=graphene.ID(), slug=graphene.String())

    products = graphene.List(
        ProductType,
        category=graphene.ID(),
        featured=graphene.Boolean(),
        in_stock=graphene.Boolean(),
        search=graphene.String(),
        min_price=graphene.Decimal(),
        max_price=graphene.Decimal(),
        sort_by=graphene.String(),
        sort_order=graphene.String(),
    )
    product = graphene.Field(ProductType, id=graphene.ID(), slug=graphene.String())

    def resolve_categories(
        self,
        info,
        featured=None,
        parent=None,
        search=None,
        **kwargs,
    ):
        queryset = Category.objects.all()

        if featured is not None:
            queryset = queryset.filter(is_featured=featured)

        if parent is not None:
            if parent == "null":
                queryset = queryset.filter(parent__isnull=True)
            else:
                queryset = queryset.filter(parent_id=parent)
        else:
            queryset = queryset.filter(parent__isnull=True)

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(description__icontains=search),
            )

        return queryset.order_by("sort_order", "name")

    def resolve_category(self, info, id=None, slug=None, **kwargs):
        if id:
            return Category.objects.get(pk=id)
        if slug:
            return Category.objects.get(slug=slug)
        return None

    def resolve_products(
        self,
        info,
        category=None,
        featured=None,
        in_stock=None,
        search=None,
        min_price=None,
        max_price=None,
        sort_by="created_at",
        sort_order="desc",
        **kwargs,
    ):
        queryset = Product.objects.filter(is_active=True)

        if category:
            queryset = queryset.filter(category_id=category)

        if featured is not None:
            queryset = queryset.filter(is_featured=featured)

        if in_stock is not None:
            if in_stock:
                queryset = queryset.filter(stock_quantity__gt=0)
            else:
                queryset = queryset.filter(stock_quantity=0)

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(description__icontains=search)
                | Q(sku__iexact=search),
            )

        if min_price is not None:
            queryset = queryset.filter(price__gte=min_price)

        if max_price is not None:
            queryset = queryset.filter(price__lte=max_price)

        # Handle sorting
        if sort_order.lower() not in ["asc", "desc"]:
            sort_order = "desc"

        if sort_order.lower() == "desc":
            sort_by = f"-{sort_by}"

        return queryset.order_by(sort_by)

    def resolve_product(self, info, id=None, slug=None, **kwargs):
        if id:
            return Product.objects.get(pk=id, is_active=True)
        if slug:
            return Product.objects.get(slug=slug, is_active=True)
        return None


class CreateCategory(graphene.Mutation):
    class Arguments:
        input = CategoryInput(required=True)

    ok = graphene.Boolean()
    category = graphene.Field(CategoryType)
    errors = graphene.List(graphene.String)

    @classmethod
    def mutate(cls, root, info, input):
        # Check if user is admin/staff
        if not info.context.user.is_authenticated or not info.context.user.is_staff:
            error_msg = "Permission denied: Admin access required."
            raise GraphQLError(error_msg)
        try:
            # Check for existing category with same name and parent
            existing_category = Category.objects.filter(
                name=input.name,
                parent_id=input.get("parent_id"),
            ).first()

            if existing_category:
                return CreateCategory(
                    ok=False,
                    category=None,
                    errors=[f"Category '{input.name}' already exists"],
                )

            # Provide default values
            category_data = {
                "name": input.name,
                "slug": input.get("slug") or "",
                "description": input.get("description") or "",
                "icon": input.get("icon") or "",
                "sort_order": input.get("sort_order", 0),
                "is_featured": input.get("is_featured", False),
                "meta_title": input.get("meta_title") or "",
                "meta_description": input.get("meta_description") or "",
                "meta_keywords": input.get("meta_keywords") or "",
            }

            # Handle parent separately
            if input.get("parent_id"):
                category_data["parent_id"] = input.get("parent_id")

            # Handle image if provided
            if input.get("image"):
                category_data["image"] = input.get("image")

            category = Category.objects.create(**category_data)
            return CreateCategory(ok=True, category=category, errors=None)

        except Exception as e:
            return CreateCategory(ok=False, category=None, errors=[str(e)])


class UpdateCategory(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        input = CategoryInput(required=True)

    ok = graphene.Boolean()
    category = graphene.Field(CategoryType)
    errors = graphene.List(graphene.String)

    @classmethod
    def mutate(cls, root, info, id, input):
        try:
            category = Category.objects.get(pk=id)
            for field, value in input.items():
                if field == "parent_id" and value is not None:
                    category.parent_id = value
                elif value is not None:
                    setattr(category, field, value)
            category.save()
            return UpdateCategory(ok=True, category=category, errors=None)
        except Category.DoesNotExist:
            return UpdateCategory(
                ok=False,
                category=None,
                errors=["Category not found"],
            )
        except Exception as e:
            return UpdateCategory(ok=False, category=None, errors=[str(e)])


class DeleteCategory(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()
    message = graphene.String()

    @classmethod
    def mutate(cls, root, info, id):
        try:
            category = Category.objects.get(pk=id)
            category.delete()
            return DeleteCategory(ok=True, message="Category deleted successfully")
        except Category.DoesNotExist:
            return DeleteCategory(ok=False, message="Category not found")
        except Exception as e:
            return DeleteCategory(ok=False, message=str(e))


class CreateProduct(graphene.Mutation):
    class Arguments:
        input = ProductInput(required=True)

    ok = graphene.Boolean()
    product = graphene.Field(ProductType)
    errors = graphene.List(graphene.String)

    @classmethod
    def mutate(cls, root, info, input):
        try:
            product_data = {
                "name": input.name,
                "slug": input.get("slug", ""),
                "sku": input.sku,
                "description": input.description,
                "short_description": input.get("short_description", ""),
                "category_id": input.category_id,
                "price": input.price,
                "compare_at_price": input.get("compare_at_price"),
                "cost_price": input.get("cost_price"),
                "stock_quantity": input.stock_quantity,
                "low_stock_threshold": input.get("low_stock_threshold", 10),
                "track_inventory": input.get("track_inventory", True),
                "allow_backorders": input.get("allow_backorders", False),
                "weight": input.get("weight"),
                "dimensions_length": input.get("dimensions_length"),
                "dimensions_width": input.get("dimensions_width"),
                "dimensions_height": input.get("dimensions_height"),
                "featured_image": input.get("featured_image"),
                "is_featured": input.get("is_featured", False),
                "is_digital": input.get("is_digital", False),
                "requires_shipping": input.get("requires_shipping", True),
                "meta_title": input.get("meta_title", ""),
                "meta_description": input.get("meta_description", ""),
                "meta_keywords": input.get("meta_keywords", ""),
                "available_from": input.get("available_from"),
                "available_until": input.get("available_until"),
            }

            # Remove None values to use model defaults
            product_data = {k: v for k, v in product_data.items() if v is not None}

            product = Product.objects.create(**product_data)
            return CreateProduct(ok=True, product=product, errors=None)
        except Exception as e:
            return CreateProduct(ok=False, product=None, errors=[str(e)])


class UpdateProduct(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        input = ProductInput(required=True)

    ok = graphene.Boolean()
    product = graphene.Field(ProductType)
    errors = graphene.List(graphene.String)

    @classmethod
    def mutate(cls, root, info, id, input):
        try:
            product = Product.objects.get(pk=id, is_active=True)
            for field, value in input.items():
                if field == "category_id" and value is not None:
                    product.category_id = value
                elif value is not None:
                    setattr(product, field, value)
            product.save()
            return UpdateProduct(ok=True, product=product, errors=None)
        except Product.DoesNotExist:
            return UpdateProduct(ok=False, product=None, errors=["Product not found"])
        except Exception as e:
            return UpdateProduct(ok=False, product=None, errors=[str(e)])


class DeleteProduct(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()
    message = graphene.String()

    @classmethod
    def mutate(cls, root, info, id):
        try:
            product = Product.objects.get(pk=id)
            product.is_active = False
            product.save(update_fields=["is_active"])
            return DeleteProduct(ok=True, message="Product deactivated successfully")
        except Product.DoesNotExist:
            return DeleteProduct(ok=False, message="Product not found")
        except Exception as e:
            return DeleteProduct(ok=False, message=str(e))


class Mutation(graphene.ObjectType):
    create_category = CreateCategory.Field()
    update_category = UpdateCategory.Field()
    delete_category = DeleteCategory.Field()

    create_product = CreateProduct.Field()
    update_product = UpdateProduct.Field()
    delete_product = DeleteProduct.Field()
