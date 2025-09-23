# GraphQL API Reference

This document provides detailed information about the GraphQL API endpoints, including mutations, queries, and their respective request/response formats.

## Base URL

All GraphQL endpoints are available at:

```http
POST /graphql/
```

## Authentication

Most GraphQL operations require authentication. Include the JWT token in the `Authorization` header:

```http
Authorization: Bearer your_access_token_here
```

## Authentication Mutations

### Register a New User

Create a new user account.

```graphql
mutation {
  registerUser(
    username: "kwame"
    email: "kwame.nkrumah@ghana.com"
    password: "Blackstar233."
    passwordConfirm: "Blackstar233."
    acceptTerms: true
  ) {
    ok
    errors
    user {
      id
      email
      username
    }
  }
}
```

#### Register a New User Success Response

```json
{
  "data": {
    "registerUser": {
      "ok": true,
      "errors": [],
      "user": {
        "id": "b675f7a6-c781-4985-a041-0f3dfb99237a",
        "email": "kwame.nkrumah@ghana.com",
        "username": "kwame"
      }
    }
  }
}
```

#### Register a New User Error Response

```json
{
  "data": {
    "registerUser": {
      "ok": false,
      "errors": [
        "username: A user with this username already exists.",
        "email: A user with this email address already exists."
      ],
      "user": null
    }
  }
}
```

### User Login

Authenticate a user and obtain JWT tokens.

```graphql
mutation {
  login(email: "kwame.nkrumah@ghana.com", password: "Blackstar233.") {
    ok
    access
    refresh
    errors
  }
}
```

#### User Login Success Response

```json
{
  "data": {
    "login": {
      "ok": true,
      "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "errors": []
    }
  }
}
```

#### User Login Error Response

```json
{
  "data": {
    "login": {
      "ok": false,
      "access": null,
      "refresh": null,
      "errors": ["detail: Invalid email or password."]
    }
  }
}
```

**Note**: Use the `access` token for authenticated requests in the `Headers` section within GraphQL. The `refresh` token can be used to obtain a new access token when the current one expires.

Example of setting the `Authorization` header:

```json
{
  "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...."
}

## User Profile Operations

### Get Current User

Retrieve the profile of the currently authenticated user.

```graphql
query {
  me {
    id
    username
    email
    firstName
    lastName
    emailVerified
  }
}
```

#### Get Current User Response

```json
{
  "data": {
    "me": {
      "id": "25fe02c3-a3ce-4c36-b5c3-3156ed907858",
      "username": "Collekta",
      "email": "admin@ecommerce.com",
      "firstName": "Festus",
      "lastName": "Aboagye",
      "emailVerified": true
    }
  }
}
```

### Update User Profile

Update the profile of the currently authenticated user.

```graphql
mutation {
  updateProfile(firstName: "Kwame", lastName: "Nkrumah") {
    ok
    errors
    user {
      id
      firstName
      lastName
    }
  }
}
```

#### Update User Profile Response

```json
{
  "data": {
    "updateProfile": {
      "ok": true,
      "errors": [],
      "user": {
        "id": "25fe02c3-a3ce-4c36-b5c3-3156ed907858",
        "firstName": "Kwame",
        "lastName": "Nkrumah"
      }
    }
  }
}
```

## Password Management

### Change Password

Change the password of the currently authenticated user.

```graphql
mutation {
  changePassword(
    oldPassword: "Blackstar233."
    newPassword: "Independence57."
    newPasswordConfirm: "Independence57."
  ) {
    ok
    message
    errors
  }
}
```

#### Change Password Success Response

```json
{
  "data": {
    "changePassword": {
      "ok": true,
      "message": "Password changed successfully.",
      "errors": []
    }
  }
}
```

#### Change Password Error Response

```json
{
  "data": {
    "changePassword": {
      "ok": false,
      "message": null,
      "errors": ["old_password: Current password is incorrect."]
    }
  }
}
```

### Request Password Reset

Request a password reset email.

```graphql
mutation {
  requestPasswordReset(email: "kwame.nkrumah@ghana.com") {
    ok
    message
  }
}
```

#### Request Password Reset Response

```json
{
  "data": {
    "requestPasswordReset": {
      "ok": true,
      "message": "If the email exists in our system, you will receive password reset instructions."
    }
  }
}
```

### Reset Password Confirm

Complete the password reset process using the token from the email.

```graphql
mutation {
  resetPasswordConfirm(
    uid: "YzU1ZmRkMzMtMTA5NC00ZDQ2LTk3MjktYWE0MjQwZjZiOGE3"
    token: "cwc1k8-accd64030a78cf957fd19f0aeb60f576"
    newPassword: "Blackstar233."
  ) {
    ok
    message
    errors
  }
}
```

#### Reset Password Confirm Response

```json
{
  "data": {
    "resetPasswordConfirm": {
      "ok": true,
      "message": "Password has been reset successfully.",
      "errors": []
    }
  }
}
```

## Email Verification

### Request Verification Email

Request a new verification email to be sent.

```graphql
mutation {
  requestVerificationEmail(email: "kwame.nkrumah@ghana.com") {
    ok
    message
  }
}
```

#### Request Verification Email Response

```json
{
  "data": {
    "requestVerificationEmail": {
      "ok": true,
      "message": "Verification email sent successfully."
    }
  }
}
```

## Products API

The Products API provides access to product and category data through GraphQL. This section covers the available queries and their usage.

### Categories

#### Get All Categories

Retrieve a list of all product categories with their hierarchy.

```graphql
query GetAllCategories {
  categories {
    id
    name
    slug
    description
    parent {
      id
      name
    }
    children {
      id
      name
    }
    productCount
    level
    isFeatured
  }
}
```

##### Example Response

```json
{
  "data": {
    "categories": [
      {
        "id": "4656a7db-69cc-4030-b056-0f4ce36b78cb",
        "name": "Electronics",
        "slug": "electronics",
        "description": "Electronic devices and accessories",
        "parent": null,
        "children": [
          {
            "id": "50222937-ea80-4445-949f-7db66627307e",
            "name": "Audio"
          },
          {
            "id": "6781b411-bd08-4699-90c4-ab80d79c4219",
            "name": "Laptops"
          }
        ],
        "productCount": 15,
        "level": 0,
        "isFeatured": true
      }
    ]
  }
}
```

#### Get Filtered Categories

Filter categories by featured status or parent category.

```graphql
query GetFeaturedCategories {
  categories(featured: true) {
    id
    name
    slug
    productCount
  }
}
```

#### Get Root Categories

Retrieve only top-level categories.

```graphql
query GetRootCategories {
  categories(parent: "null") {
    id
    name
    slug
    children {
      id
      isFeatured
    }
  }
}
```

#### Get a Single Categories

```graphql
query GetCategoryById {
  category(id: "CATEGORY_ID") {
    id
    name
    slug
    description
    parent {
      id
      name
    }
    children {
      id
      name
      productCount
    }
    ancestors {
      id
      name
      slug
    }
    level
    productCount
  }
}
```

#### Get a Single Category by Slug Request

```graphql
# By Slug
query GetCategoryBySlug {
  category(slug: "slug") {
    id
    name
    slug
    description
    productCount
  }
}
```

### Products

#### Get All Products

Retrieve a list of products with pagination and filtering options.

```graphql
query GetAllProducts {
  products {
    id
    name
    slug
    price
    compareAtPrice
    discountPercentage
    featuredImage
    category {
      id
      name
    }
    images {
      image
      altText
      isPrimary
    }
  }
}
```

##### Get All Products Response

```json
{
  "data": {
    "products": [
      {
        "id": "f936279a-7f6a-40f4-958e-fa49d8dfa47a",
        "name": "OnePlus 14T",
        "slug": "oneplus-14t-1",
        "price": "400.90",
        "compareAtPrice": null,
        "discountPercentage": 0,
        "featuredImage": "",
        "category": {
          "id": "d5083cf3-4519-4939-8b7b-dc9ebb9b5809",
          "name": "iPhone"
        },
        "images": []
      },
    ]
  }
}
```

#### Get Product by ID or Slug

Retrieve detailed information about a specific product.

```graphql
query GetProduct($id: ID, $slug: String) {
  product(id: $id, slug: $slug) {
    id
    name
    slug
    description
    parent {
      id
      name
    }
    children {
      id
      name
      productCount
    }
    ancestors {
      id
      name
      slug
    }
    level
    productCount
  }
}
```

### Product Mutations (Admin Only)

#### Create a Category

```graphql
mutation CreateRootCategory {
  createCategory(
    input: {
      name: "New Category", 
      description: "Category description", 
      isFeatured: true, 
      sortOrder: 5, 
      metaTitle: "New Category", 
      metaDescription: "Description for SEO"
    }
  ) {
    ok
    category {
      id
      name
      slug
      isFeatured
    }
    errors
  }
}
```

#### Create a Subcategory

```graphql
mutation CreateSubCategory {
  createCategory(
    input: {
      name: "Subcategory Name", 
      description: "Subcategory description", 
      parentId: "PARENT_CATEGORY_ID", 
      isFeatured: true, 
      icon: ""
    }
  ) {
    ok
    category {
      id
      name
      slug
      parent {
        id
        name
      }
    }
    errors
  }
}
```

#### Update a Category

```graphql
mutation UpdateCategory {
  updateCategory(
    id: "CATEGORY_ID"
    input: {
      name: "Updated Category Name", 
      isFeatured: false, 
      sortOrder: 3, 
      metaDescription: "Updated description for SEO"
    }
  ) {
    ok
    category {
      id
      name
      slug
      isFeatured
      sortOrder
      metaDescription
    }
    errors
  }
}
```

#### Create Product

```graphql
mutation CreateProduct {
  createProduct(input: {
    name: "New Product"
    sku: "NEWPROD001"
    slug: "new-product"
    description: "Product description"
    shortDescription: "Short description"
    categoryId: "CATEGORY_ID"
    price: "99.99"
    compareAtPrice: ""
    costPrice: "59.99"
    stockQuantity: 10
    lowStockThreshold: 5
    trackInventory: true
    allowBackorders: false
    weight: "0.5"
    isFeatured: true
    isDigital: false
    requiresShipping: true
    metaTitle: "New Product"
    metaDescription: "Description for SEO"
  }) {
    ok
    product {
      id
      name
      sku
      price
      stockQuantity
      category {
        id
        name
      }
    }
    errors
  }
}
```

#### Update Product

```graphql
mutation UpdateProduct {
  updateProduct(
    id: "PRODUCT_ID"
    input: {
      name: "Updated Product Name"
      sku: "UPDATEDSKU001"
      description: "Updated product description"
      shortDescription: "Updated short description"
      categoryId: "CATEGORY_ID" 
      price: "379.00"
      stockQuantity: 35
      isFeatured: false
      lowStockThreshold: 3
      metaDescription: "Updated description for SEO"
    }
  ) {
    ok
    product {
      id
      name
      price
      compareAtPrice
      stockQuantity
      isFeatured
      isInStock
    }
    errors
  }
}
```

#### Delete Product

```graphql
mutation DeleteProduct($id: ID!) {
  deleteProduct(id: $id) {
    success
    errors
  }
}
```

## Error Handling

All GraphQL operations return an `errors` array that will contain any validation or authentication errors. Each error includes a descriptive message about what went wrong.

Common error responses include:

- **Authentication Required**: When a protected endpoint is accessed without a valid token
- **Invalid Credentials**: When login fails
- **Validation Errors**: When input data doesn't pass validation
- **Permission Denied**: When the user doesn't have permission to perform the action

## Rate Limiting

To prevent abuse, the following rate limits are in place:

- **Authentication Endpoints**: 10 requests per minute
- **API Endpoints**: 1000 requests per hour

If you exceed these limits, you'll receive a `429 Too Many Requests` response.

## Best Practices

1. **Use Pagination**: Always use pagination for product lists to improve performance.
2. **Select Only Needed Fields**: Request only the fields you need to reduce payload size.
3. **Use Variables**: Use GraphQL variables for dynamic queries.
4. **Handle Errors**: Always check for and handle error responses.
5. **Cache Responses**: Implement client-side caching for better performance.
6. **Rate Limiting**: Be aware of API rate limits and implement appropriate backoff strategies.
