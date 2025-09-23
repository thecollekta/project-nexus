# Products API Reference

This document provides detailed information about the Products API endpoints, including request/response formats and examples.

## Base URL

All API endpoints are prefixed with:

```http
/api/v1/
```

## Authentication

Most endpoints require authentication. Include the JWT token in the `Authorization` header:

```http
Authorization: Bearer your_access_token_here
```

## Categories

### List Categories

```http
GET /api/v1/categories/
```

#### Query Parameters

| Parameter | Type    | Description                    |
|-----------|---------|--------------------------------|
| parent    | integer | Filter by parent category ID   |
| featured | boolean | Filter featured categories     |
| search   | string  | Search by name or description  |
| ordering | string  | Sort results (e.g., `name`, `-created_at`) |

#### Example Response

```json
{
  "count": 4,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "4656a7db-69cc-4030-b056-0f4ce36b78cb",
      "name": "Electronics",
      "slug": "electronics",
      "description": "Electronic devices and accessories",
      "parent": null,
      "product_count": 15,
      "is_featured": true
    },
    {
      "id": "71c728cf-9a88-476b-8e31-61796326b0fa",
      "name": "Fashion & Apparel",
      "slug": "fashion-apparel",
      "description": "Clothing and accessories",
      "parent": null,
      "product_count": 42,
      "is_featured": true
    }
  ]
}
```

### Get Category Details

```http
GET /api/v1/categories/{id}/
```

#### Path Parameters

| Parameter | Type   | Description         |
|-----------|--------|---------------------|
| id        | string | Category ID or slug |

#### Example Response

```json
{
  "id": "4656a7db-69cc-4030-b056-0f4ce36b78cb",
  "name": "Electronics",
  "slug": "electronics",
  "description": "Electronic devices and accessories",
  "parent": null,
  "children": [
    {
      "id": "50222937-ea80-4445-949f-7db66627307e",
      "name": "Audio",
      "slug": "audio",
      "product_count": 5
    },
    {
      "id": "6781b411-bd08-4699-90c4-ab80d79c4219",
      "name": "Laptops",
      "slug": "laptops",
      "product_count": 10
    }
  ],
  "ancestors": [],
  "product_count": 15,
  "is_featured": true,
  "created_at": "2023-01-15T10:30:00Z",
  "updated_at": "2023-01-15T10:30:00Z"
}
```

## Products

### List Products

```http
GET /api/v1/products/
```

#### Query Parameters

| Parameter         | Type    | Description                                      |
|-------------------|---------|--------------------------------------------------|
| category         | string  | Filter by category ID or slug                    |
| price_min        | decimal | Minimum price                                    |
| price_max        | decimal | Maximum price                                    |
| in_stock         | boolean | Filter products in stock                         |
| featured         | boolean | Filter featured products                         |
| search           | string  | Search in name, description, and specifications  |
| ordering         | string  | Sort results (e.g., `price`, `-created_at`)      |
| page             | integer | Page number for pagination                       |
| page_size        | integer | Number of results per page (default: 20)         |

#### Example Response

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "23febcc0-9641-4b63-a4e8-b2f42171dac2",
      "name": "Pixel 11 Pro",
      "slug": "pixel-11-pro",
      "price": "735.55",
      "compare_at_price": "899.99",
      "discount_percentage": 18.27,
      "featured_image": "/media/products/images/pixel-11-pro.jpg",
      "category": {
        "id": "c752ec9a-6f7e-4638-b22d-b14f884408ea",
        "name": "Smartphones",
        "slug": "smartphones"
      },
      "is_in_stock": true,
      "is_low_stock": false,
      "created_at": "2023-06-15T14:30:00Z"
    }
  ]
}
```

### Get Product Details

```http
GET /api/v1/products/{id}/
```

#### Path Parameters

| Parameter | Type   | Description       |
|-----------|--------|-------------------|
| id        | string | Product ID or slug |

#### Example Response

```json
{
  "id": "23febcc0-9641-4b63-a4e8-b2f42171dac2",
  "name": "Pixel 11 Pro",
  "slug": "pixel-11-pro",
  "sku": "PIX11PRO-BLK-128",
  "description": "The latest Pixel smartphone with advanced camera features and AI capabilities.",
  "short_description": "Flagship smartphone with best-in-class camera",
  "price": "735.55",
  "compare_at_price": "899.99",
  "cost_price": "650.00",
  "stock_quantity": 25,
  "low_stock_threshold": 5,
  "is_featured": true,
  "is_digital": false,
  "requires_shipping": true,
  "weight": "0.20",
  "dimensions_length": "15.0",
  "dimensions_width": "7.5",
  "dimensions_height": "0.8",
  "meta_title": "Google Pixel 11 Pro - Best Android Phone 2023",
  "meta_description": "Experience the power of Google with the Pixel 11 Pro. Advanced camera, AI features, and pure Android experience.",
  "meta_keywords": "google pixel, pixel 11 pro, android phone, best camera phone",
  "category": {
    "id": "c752ec9a-6f7e-4638-b22d-b14f884408ea",
    "name": "Smartphones",
    "slug": "smartphones"
  },
  "images": [
    {
      "image": "/media/products/images/pixel-11-pro-1.jpg",
      "alt_text": "Google Pixel 11 Pro front view",
      "is_primary": true
    },
    {
      "image": "/media/products/images/pixel-11-pro-2.jpg",
      "alt_text": "Google Pixel 11 Pro back view",
      "is_primary": false
    }
  ],
  "specifications": [
    {
      "name": "Display",
      "value": "6.7-inch QHD+ LTPO AMOLED, 120Hz",
      "sort_order": 1
    },
    {
      "name": "Processor",
      "value": "Google Tensor G3",
      "sort_order": 2
    },
    {
      "name": "Storage",
      "value": "128GB",
      "sort_order": 3
    }
  ],
  "is_in_stock": true,
  "is_low_stock": false,
  "discount_percentage": 18.27,
  "profit_margin": 13.16,
  "created_at": "2023-06-15T14:30:00Z",
  "updated_at": "2023-06-20T09:15:00Z"
}
```

### Update Product Inventory

```http
PATCH /api/v1/products/{id}/inventory/
```

#### Request Body

```json
{
  "stock_quantity": 30,
  "low_stock_threshold": 5,
  "track_inventory": true,
  "allow_backorders": false
}
```

#### Response

```json
{
  "id": "23febcc0-9641-4b63-a4e8-b2f42171dac2",
  "stock_quantity": 30,
  "low_stock_threshold": 5,
  "is_in_stock": true,
  "is_low_stock": false,
  "track_inventory": true,
  "allow_backorders": false,
  "updated_at": "2023-06-25T11:20:00Z"
}
```

## Public API Endpoints

The following endpoints are available without authentication:

- `GET /api/v1/public/categories/` - List all categories
- `GET /api/v1/public/categories/{id}/` - Get category details
- `GET /api/v1/public/products/` - List products
- `GET /api/v1/public/products/{id}/` - Get product details
- `GET /api/v1/public/products/featured/` - Get featured products
- `GET /api/v1/public/products/search/` - Search products

## Error Responses

### 400 Bad Request

```json
{
  "error": {
    "code": "validation_error",
    "message": "Invalid input data",
    "details": {
      "price": [
        "Ensure this value is greater than or equal to 0.01."
      ]
    }
  }
}
```

### 401 Unauthorized

```json
{
  "error": {
    "code": "authentication_failed",
    "message": "Authentication credentials were not provided."
  }
}
```

### 404 Not Found

```json
{
  "error": {
    "code": "not_found",
    "message": "Not found."
  }
}
```

### 500 Internal Server Error

```json
{
  "error": {
    "code": "server_error",
    "message": "An unexpected error occurred. Please try again later."
  }
}
```
