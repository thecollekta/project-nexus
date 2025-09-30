# apps/core/pagination.py

"""
Custom pagination classes for the e-commerce API.
Provides flexible pagination options for different use cases.
"""

from collections import OrderedDict

from rest_framework.pagination import LimitOffsetPagination, PageNumberPagination
from rest_framework.response import Response


class StandardResultsSetPagination(PageNumberPagination):
    """
    Standard pagination for most API endpoints.
    Returns 20 items per page by default, with customizable page size.
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
    page_query_param = "page"

    def get_paginated_response(self, data):
        """
        Custom response format with enhanced metadata.
        """
        if not self.page:
            return Response(
                OrderedDict(
                    [
                        ("count", 0),
                        ("total_pages", 0),
                        ("current_page", 1),
                        (
                            "page_size",
                            self.get_page_size(self.request) if self.request else None,
                        ),
                        ("next", None),
                        ("previous", None),
                        ("results", []),
                        (
                            "_meta",
                            {
                                "has_next": False,
                                "has_previous": False,
                                "start_index": 0,
                                "end_index": 0,
                            },
                        ),
                    ]
                )
            )

        return Response(
            OrderedDict(
                [
                    ("count", self.page.paginator.count),
                    ("total_pages", self.page.paginator.num_pages),
                    ("current_page", self.page.number),
                    (
                        "page_size",
                        self.get_page_size(self.request) if self.request else None,
                    ),
                    ("next", self.get_next_link()),
                    ("previous", self.get_previous_link()),
                    ("results", data),
                    (
                        "_meta",
                        {
                            "has_next": self.page.has_next(),
                            "has_previous": self.page.has_previous(),
                            "start_index": self.page.start_index(),
                            "end_index": self.page.end_index(),
                        },
                    ),
                ]
            )
        )


class LargeResultsSetPagination(PageNumberPagination):
    """
    Pagination for endpoints that might return large datasets.
    Returns 50 items per page by default.
    """

    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200
    page_query_param = "page"

    def get_paginated_response(self, data):
        """Custom response format for large result sets."""
        if not self.page:
            return Response(
                OrderedDict(
                    [
                        ("count", 0),
                        ("total_pages", 0),
                        ("current_page", 1),
                        (
                            "page_size",
                            self.get_page_size(self.request) if self.request else None,
                        ),
                        ("next", None),
                        ("previous", None),
                        ("results", []),
                        (
                            "_meta",
                            {
                                "dataset_type": "large",
                                "performance_tip": "Consider using filters to reduce result set size",
                                "has_next": False,
                                "has_previous": False,
                            },
                        ),
                    ]
                )
            )

        return Response(
            OrderedDict(
                [
                    ("count", self.page.paginator.count),
                    ("total_pages", self.page.paginator.num_pages),
                    ("current_page", self.page.number),
                    (
                        "page_size",
                        self.get_page_size(self.request) if self.request else None,
                    ),
                    ("next", self.get_next_link()),
                    ("previous", self.get_previous_link()),
                    ("results", data),
                    (
                        "_meta",
                        {
                            "dataset_type": "large",
                            "performance_tip": "Consider using filters to reduce result set size",
                            "has_next": self.page.has_next(),
                            "has_previous": self.page.has_previous(),
                        },
                    ),
                ]
            )
        )


class SmallResultsSetPagination(PageNumberPagination):
    """
    Pagination for endpoints with smaller datasets.
    Returns 10 items per page by default.
    """

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50
    page_query_param = "page"

    def get_paginated_response(self, data):
        """Custom response format for small result sets."""
        if not self.page:
            return Response(
                OrderedDict(
                    [
                        ("count", 0),
                        ("total_pages", 0),
                        ("current_page", 1),
                        (
                            "page_size",
                            self.get_page_size(self.request) if self.request else None,
                        ),
                        ("next", None),
                        ("previous", None),
                        ("results", []),
                    ]
                )
            )

        return Response(
            OrderedDict(
                [
                    ("count", self.page.paginator.count),
                    ("total_pages", self.page.paginator.num_pages),
                    ("current_page", self.page.number),
                    (
                        "page_size",
                        self.get_page_size(self.request) if self.request else None,
                    ),
                    ("next", self.get_next_link()),
                    ("previous", self.get_previous_link()),
                    ("results", data),
                ]
            )
        )


class CustomLimitOffsetPagination(LimitOffsetPagination):
    """
    Offset-based pagination for cases where you need more control
    over the starting point of results.
    """

    default_limit = 20
    limit_query_param = "limit"
    offset_query_param = "offset"
    max_limit = 100

    def get_paginated_response(self, data):
        """Custom response format for limit/offset pagination."""
        next_offset = None
        offset = self.offset or 0
        limit = self.limit or self.default_limit
        count = self.count or 0

        if (
            isinstance(offset, int)
            and isinstance(limit, int)
            and isinstance(count, int)
        ):
            if offset + limit < count:
                next_offset = offset + limit

        previous_offset = None
        if isinstance(offset, int) and offset > 0 and isinstance(limit, int):
            previous_offset = max(0, offset - limit)

        remaining = (
            max(0, count - (offset + limit))  # type: ignore
            if all(isinstance(x, int) for x in [offset, limit, count])
            else 0
        )

        return Response(
            OrderedDict(
                [
                    ("count", count),
                    ("limit", limit),
                    ("offset", offset),
                    ("next", self.get_next_link()),
                    ("previous", self.get_previous_link()),
                    ("results", data),
                    (
                        "_meta",
                        {
                            "pagination_type": "limit_offset",
                            "next_offset": next_offset,
                            "previous_offset": previous_offset,
                            "remaining": remaining,
                        },
                    ),
                ]
            )
        )


class NoPagination:
    """
    Pagination class that doesn't paginate at all.
    Useful for small datasets or specific endpoints that need all results.

    WARNING: Use with caution on large datasets as it can impact performance.
    """

    def paginate_queryset(self, queryset, request, view=None):
        """Return None to indicate no pagination."""
        return None

    def get_paginated_response(self, data):
        """Return data without pagination wrapper."""
        return Response(
            OrderedDict(
                [
                    ("count", len(data)),
                    ("results", data),
                    (
                        "_meta",
                        {
                            "pagination": "disabled",
                            "warning": "All results returned - consider using pagination for large datasets",
                        },
                    ),
                ]
            )
        )


# Example usage in settings.py:
"""
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'core.pagination.StandardResultsSetPagination',
    'PAGE_SIZE': 20
}
"""

# Example usage in viewsets:
"""
from core.pagination import LargeResultsSetPagination, SmallResultsSetPagination

class ProductViewSet(BaseViewSet):
    pagination_class = LargeResultsSetPagination  # For products (many items)
    # ... rest of viewset

class CategoryViewSet(BaseViewSet):
    pagination_class = SmallResultsSetPagination  # For categories (few items)
    # ... rest of viewset
"""
