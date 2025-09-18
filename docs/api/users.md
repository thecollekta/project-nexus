# User Management API Reference

This document provides detailed information about the User Management API endpoints, including request/response formats, status codes, and examples.

## Base URL

All endpoints are relative to the base URL:

```http
https://127.0.0.1:8000/api/v1/accounts/ # Local Development

https://api.yourecommerce.com/api/v1/accounts/ # Production
```

## Authentication

All endpoints (except where noted) require authentication using JWT tokens. Include the token in the `Authorization` header:

```http
Authorization: Bearer your_access_token_here
```

## Endpoints

### Get Current User Profile

Retrieve the profile of the currently authenticated user.

```http
GET `/profiles/me/`
```

#### Response

```json
{
  "id": "659e96f9-31c6-4b7a-9db2-73a277a55c6d",
  "created_at": "2025-09-17 12:14:02",
  "updated_at": "2025-09-17 12:14:02",
  "is_active": true,
  "username": "kwams",
  "email": "kwame.nkrumah@ghana.com",
  "first_name": "Kwame",
  "last_name": "Nkrumah",
  "phone_number": "+2332498051198",
  "address_line_1": "Black Star Square",
  "address_line_2": "Opposite Accra Sports Stadium",
  "city": "Accra",
  "state": "Greater Accra",
  "postal_code": "0233",
  "country": "Ghana",
  "full_name": "Kwame Nkrumah",
  "full_address": "Black Star Square, Opposite Accra Sports Stadium, Accra, Greater Accra, 0233, Ghana",
  "is_email_verified": false,
  "bio": "",
  "date_of_birth": null,
  "newsletter_subscription": false,
  "account_status": "PENDING",
  "user_type": "CUSTOMER",
  "date_joined": "2025-09-17 12:14:00",
  "last_login": "2025-09-17 12:16:06"
}
```

### Update User Profile

Update the profile of the currently authenticated user.

```http
PATCH `/profiles/me/`
Content-Type: application/json

```json
{
  "is_active": true,
  "email": "kwame.nkrumah@ghana.com",
  "first_name": "Kwame",
  "last_name": "Nkrumah",
  "phone_number": "+2332498051198",
  "address_line_1": "Black Star Square",
  "address_line_2": "Opposite Accra Sports Stadium",
  "city": "Accra",
  "state": "Greater Accra",
  "postal_code": "GA233",
  "country": "Ghana",
  "bio": "Coming soon",
  "date_of_birth": "1957-03-06",
  "newsletter_subscription": true
}
```

#### Update Profile Response

```json
{
  "message": "Profile updated successfully",
  "user": {
    "id": "659e96f9-31c6-4b7a-9db2-73a277a55c6d",
    "created_at": "2025-09-17 12:14:02",
    "updated_at": "2025-09-17 12:22:27",
    "is_active": true,
    "username": "kwams",
    "email": "kwame.nkrumah@ghana.com",
    "first_name": "Kwame",
    "last_name": "Nkrumah",
    "phone_number": "+2332498051198",
    "address_line_1": "Black Star Square",
    "address_line_2": "Opposite Accra Sports Stadium",
    "city": "Accra",
    "state": "Greater Accra",
    "postal_code": "GA233",
    "country": "Ghana",
    "full_name": "Kwame Nkrumah",
    "full_address": "Black Star Square, Opposite Accra Sports Stadium, Accra, Greater Accra, GA233, Ghana",
    "is_email_verified": false,
    "bio": "Coming soon",
    "date_of_birth": "1957-03-06",
    "newsletter_subscription": true,
    "account_status": "PENDING",
    "user_type": "CUSTOMER",
    "date_joined": "2025-09-17 12:14:00",
    "last_login": "2025-09-17 12:16:06"
  }
}
```

### Change Password

Change the password for the currently authenticated user.

```http
POST `/profiles/change-password/`
Content-Type: application/json

{
  "old_password": "current_password_123",
  "new_password": "new_secure_password_456",
  "new_password_confirm": "new_secure_password_456"
}
```

#### Change Password Response

```json
# Success: Password changed (200)

```json
{
  "message": "Password changed successfully.",
  "next_steps": [
    "You have been logged out of all other devices.",
    "Please log in again with your new password."
  ]
}

# Error: Bad request (400)

```json
{
  "message": "Password change failed. Please check the errors below.",
  "errors": {
    "old_password": [
      "Current password is incorrect."
    ]
  }
}

```

### Request Email Verification

Request a new verification email to be sent.

```http
POST `/profiles/request-verification-email/`
```

#### Request Email Verification Request

```json
{
  "email": "kwame.nkrumah@ghana.com"
}


#### Request Email Verification Response

```json
# Success: Email sent (200)

```json
{
  "message": "Verification email sent successfully"
}

# Error: Bad Request (400)

```json
{
  "message": "Email is already verified."
}

```

### Verify Email

Verify an email address using a verification token.

```http
POST `/profiles/verify-email/`
Content-Type: application/json

#### Verify Email Request

```json
{
  "token": "iNKR2qKEdVdWS5852xYXuDxUGuFz37qyNVSBCc2g0MnljsaP4MdDCpViNKr4CEjh",
  "email": "kwame.nkrumah@ghana.com"
}
```

#### Verify Email Response

```json
{
  "message": "Email verified successfully. Your account is now active."
}
```

## Admin Endpoints (Admin Only)

The following endpoints are only accessible to users with admin privileges.

### List All Users (Admin)

```http
GET `/users/`
```

#### List All Users Response

```json
{
  "count": 1,
  "total_pages": 1,
  "current_page": 1,
  "page_size": 20,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "25fe02c3-a3ce-4c36-b5c3-3156ed907858",
      "created_at": "2025-09-17 12:12:14",
      "updated_at": "2025-09-17 15:30:58",
      "created_by": null,
      "updated_by": "Festus Aboagye",
      "is_active": true,
      "username": "Collekta",
      "email": "admin@ecommerce.com",
      "first_name": "Festus",
      "last_name": "Aboagye",
      "phone_number": "",
      "address_line_1": "",
      "address_line_2": "",
      "city": "",
      "state": "",
      "postal_code": "",
      "country": "Ghana",
      "full_name": "Festus Aboagye",
      "full_address": "Ghana",
      "is_email_verified": true,
      "bio": "Super admin",
      "date_of_birth": "1989-07-06",
      "newsletter_subscription": false,
      "account_status": "active",
      "user_type": "ADMIN",
      "date_joined": "2025-09-17 12:12:13",
      "last_login": "2025-09-17 18:01:01"
    }
  ],
  "_meta": {
    "has_next": false,
    "has_previous": false,
    "start_index": 1,
    "end_index": 2
  }
}
```

### Get User by ID (Admin)

```http
GET `/users/{user_id}/`
Replace `{user_id}` with the UUID of the user.
```

Content-Type: application/json

#### Get User by ID Response

```json
{
  "id": "25fe02c3-a3ce-4c36-b5c3-3156ed907858",
  "created_at": "2025-09-17 12:12:14",
  "updated_at": "2025-09-17 15:30:58",
  "created_by": null,
  "updated_by": "Festus Aboagye",
  "is_active": true,
  "username": "Collekta",
  "email": "admin@ecommerce.com",
  "first_name": "Festus",
  "last_name": "Aboagye",
  "phone_number": "",
  "address_line_1": "",
  "address_line_2": "",
  "city": "",
  "state": "",
  "postal_code": "",
  "country": "Ghana",
  "full_name": "Festus Aboagye",
  "full_address": "Ghana",
  "is_email_verified": true,
  "bio": "Super admin",
  "date_of_birth": "1989-07-06",
  "newsletter_subscription": false,
  "account_status": "active",
  "user_type": "ADMIN",
  "date_joined": "2025-09-17 12:12:13",
  "last_login": "2025-09-17 18:01:01"
}
```

### Update User (Admin)

```http
PATCH `/users/{user_id}/`
Replace `{user_id}` with the UUID of the user.
```

Content-Type: application/json

#### Update User Request

```json
{
  "postal_code": "GA233",
  "country": "string",
  "newsletter_subscription": false
}
```

#### Update User Response

```json
{
  "id": "25fe02c3-a3ce-4c36-b5c3-3156ed907858",
  "created_at": "2025-09-17 12:12:14",
  "updated_at": "2025-09-17 18:09:21",
  "created_by": null,
  "updated_by": "Festus Aboagye",
  "is_active": true,
  "username": "Collekta",
  "email": "admin@ecommerce.com",
  "first_name": "Festus",
  "last_name": "Aboagye",
  "phone_number": "",
  "address_line_1": "",
  "address_line_2": "",
  "city": "",
  "state": "",
  "postal_code": "GA233",
  "country": "string",
  "full_name": "Festus Aboagye",
  "full_address": "GA233, string",
  "is_email_verified": true,
  "bio": "Super admin",
  "date_of_birth": "1989-07-06",
  "newsletter_subscription": false,
  "account_status": "active",
  "user_type": "ADMIN",
  "date_joined": "2025-09-17 12:12:13",
  "last_login": "2025-09-17 18:01:01"
}
```

### Activate User (Admin)

```http
POST `/users/{user_id}/activate/`
Replace `{user_id}` with the UUID of the user.
```

#### Activate User Request

```json
{
  "email": "kwame.nkrumah@ghana.com",
  "first_name": "Kwame",
  "last_name": "Nkrumah",
  "phone_number": "+2332498051198",
  "address_line_1": "Black Star Square",
  "address_line_2": "Opposite Accra Sports Stadium",
  "city": "Accra",
  "state": "Greater Accra",
  "postal_code": "GA233",
  "country": "Ghana",
  "bio": "Coming soon",
  "date_of_birth": "1957-03-06",
  "newsletter_subscription": true
}
```

#### Activate User Response

Success: User activated (200)

```json
{
  "detail": "User account activated successfully"
}
```

Error: Forbidden (403)

```json
{
  "detail": "You do not have permission to perform this action."
}
```

Error: Not Found (404)

```json
{
  "detail": "Not found."
}
```

Error: Internal Server Error (500)

```json
{
  "detail": "An error occurred while activating the account"
} 
```

### Suspend User (Admin)

```http
POST `/users/{user_id}/suspend/`
Replace `{user_id}` with the UUID of the user.
```

#### Suspend User Request

```json
{
  "email": "kwame.nkrumah@ghana.com",
  "first_name": "Kwame",
  "last_name": "Nkrumah",
  "phone_number": "+2332498051198",
  "address_line_1": "Black Star Square",
  "address_line_2": "Opposite Accra Sports Stadium",
  "city": "Accra",
  "state": "Greater Accra",
  "postal_code": "GA233",
  "country": "Ghana",
  "bio": "Coming soon",
  "date_of_birth": "1957-03-06",
  "newsletter_subscription": true
}
```

##### Suspend User Response

Success: User suspended (200)

```json
{
  "message": "User kwams has been suspended"
}
```

Error: Forbidden (403)

```json
{
  "detail": "You do not have permission to perform this action."
}
```

## Error Responses

### Common Error Responses

#### 400 Bad Request

```json
{
  "field_name": ["Error message"]
}
```

#### 401 Unauthorized

```json
{
  "detail": "Authentication credentials were not provided."
}
```

#### 403 Forbidden

```json
{
  "detail": "You do not have permission to perform this action."
}
```

#### 404 Not Found

```json
{
  "detail": "Not found."
}
```

#### 429 Too Many Requests

```json
{
  "detail": "Request was throttled. Expected available in 60 seconds."
}
```

## Rate Limiting

- Regular endpoints: 1000 requests per hour per IP
- Authentication endpoints: 10 requests per minute per IP
- Admin endpoints: 100 requests per minute per IP

## Best Practices

1. Always check the response status code before processing the response
2. Handle token expiration gracefully
3. Implement retry logic for rate-limited requests
4. Cache responses when appropriate
5. Always use HTTPS for all requests to ensure data security and integrity in production environments
