# Authentication Guide

This guide explains how to authenticate with the E-commerce API using JWT (JSON Web Tokens).

## Authentication Flow

1. **Register** a new user account
2. **Verify** your email address (required for full access)
3. **Login** with your credentials to obtain access and refresh tokens
4. **Use the access token** to authenticate API requests
5. **Refresh the access token** when it expires

## Registration

To create a new account, send a POST request to `/api/v1/accounts/register/` with the required user information.

### Register Request

```http
POST `/api/v1/accounts/register/`
Content-Type: application/json

```json
{
  "username": "Kwams",
  "email": "kwame.nkrumah@ghana.com",
  "password": "Blackstar233.",
  "password_confirm": "Blackstar233.",
  "first_name": "Kwame",
  "last_name": "Nkrumah",
  "phone_number": "+2332498051198",
  "address_line_1": "Black Star Square",
  "address_line_2": "Opposite Accra Sports Stadium",
  "city": "Accra",
  "state": "Greater Accra",
  "postal_code": "0233",
  "country": "Ghana",
  "accept_terms": true
}
```

### Register Response

```json
{
  "message": "Account created successfully. Please check your email to verify your account.",
  "user": {
    "id": "659e96f9-31c6-4b7a-9db2-73a277a55c6d",
    "username": "kwams",
    "email": "kwame.nkrumah@ghana.com",
    "full_name": "Kwame Nkrumah"
  },
  "next_step": "email_verification"
}
```

## Email Verification

After registration, you'll receive an email with a verification link. Click the link or use the verification token in the API.

### Verify Email with Token

```http
POST `/api/v1/accounts/verify-email/`
Content-Type: application/json

### Verify Email Request

```json
{
  "token": "iNKR2qKEdVdWS5852xYXuDxUGuFz37qyNVSBCc2g0MnljsaP4MdDCpViNKr4CEjh",
  "email": "kwame.nkrumah@ghana.com"
}
```

### Verify Email Response

```json
{
  "message": "Email verified successfully. Your account is now active."
}
```

## Login

After verifying your email, you can obtain an access token by logging in:

```http
POST /api/v1/accounts/login/
Content-Type: application/json

### Login Request

```json
{
  "email": "kwame.nkrumah@ghana.com",
  "password": "Blackstar233.",
  "remember_me": true
}
```

### Login Response

```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "659e96f9-31c6-4b7a-9db2-73a277a55c6d",
    "created_at": "2025-09-17 12:14:02",
    "updated_at": "2025-09-17 12:14:02",
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
    "newsletter_subscription": false
  }
}
```

## Making Authenticated Requests

Include the access token in the `Authorization` header of your requests:

```http
GET `/api/v1/accounts/me/`
Authorization: Bearer your_access_token_here
```

## Refreshing Tokens

Access tokens expire after a set period. Use the refresh token to get a new access token:

```http
POST `/api/v1/accounts/token/refresh/`
Content-Type: application/json

### Refresh Token Request

```json 
{
  "refresh": "your_refresh_token_here"
}
```

### Refresh Token Response

```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

## Password Reset

### Request Password Reset

```http
POST `/api/v1/accounts/profiles/request-password-reset/`
Content-Type: application/json

#### Request Password Reset Request

```json
{
  "email": "kwame.nkrumah@ghana.com"
}
```

#### Request Password Reset Response

```json
{
  "message": "If the email exists in our system, you will receive password reset instructions."
}
```

#### Email Message Sample

```html
MIME-Version: 1.0
Content-Type: multipart/alternative;
 boundary="===============4718208076344061899=="
MIME-Version: 1.0
Subject: Password Reset Request
From: <festus233@gmail.com>
To: <kwame.nkrumah@ghana.com>
Date: Wed, 17 Sep 2025 14:15:14 -0000
Message-ID: <175811851441.82612.6901922752009398036@MSI>

--===============4718208076344061899==
Content-Type: text/plain; charset="utf-8"
MIME-Version: 1.0
Content-Transfer-Encoding: 7bit

<!DOCTYPE html>
<html>

<head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Password Reset - ALX E-Commerce</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 0;
            background-color: #f5f5f5;
        }

        .container {
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }

        .header {
            background-color: #4a6fa5;
            color: white;
            padding: 20px 0;
            text-align: center;
            border-radius: 5px 5px 0 0;
        }

        .content {
            background-color: #ffffff;
            padding: 30px;
            border-radius: 0 0 5px 5px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
        }

        .button {
            display: inline-block;
            padding: 12px 24px;
            margin: 20px 0;
            background-color: #4a6fa5;
            color: white !important;
            text-decoration: none;
            border-radius: 4px;
            font-weight: bold;
        }

        .footer {
            margin-top: 30px;
            font-size: 12px;
            color: #777;
            text-align: center;
        }

        .reset-link {
            word-break: break-all;
            color: #4a6fa5;
            text-decoration: none;
        }
    </style>
</head>

<body>
    <div class="container">
        <div class="header">
            <h1>Password Reset Request</h1>
        </div>
        <div class="content">
            <p>Hello Kwame Nkrumah,</p>

            <p>You're receiving this email because you requested a password reset for your ALX E-Commerce account.</p>        

            <p>Please click the button below to reset your password:</p>

            <p style="text-align: center;">
                <a href="http://localhost:3000  # Your frontend URL/reset-password/NjU5ZTk2ZjktMzFjNi00YjdhLTlkYjItNzNhMjc3YTU1YzZk/cwa29e-e0c47bf982c9d82c303c357e80d95dcb/" class="button">Reset Password</a>
            </p>

            <p>Or copy and paste this link into your browser:</p>
            <p><a href="http://localhost:3000  # Your frontend URL/reset-password/NjU5ZTk2ZjktMzFjNi00YjdhLTlkYjItNzNhMjc3YTU1YzZk/cwa29e-e0c47bf982c9d82c303c357e80d95dcb/" class="reset-link">http://localhost:3000  # Your frontend URL/reset-password/NjU5ZTk2ZjktMzFjNi00YjdhLTlkYjItNzNhMjc3YTU1YzZk/cwa29e-e0c47bf982c9d82c303c357e80d95dcb/</a></p>

            <p>This link will expire in 24 hours for security reasons.</p>

            <p>If you didn't request this password reset, please ignore this email. Your password will remain unchanged.      
            </p>

            <p>Thanks,<br>The ALX E-Commerce Team</p>

            <div class="footer">
                <p>This is an automated message, please do not reply to this email.</p>
                <p>&copy; 2025 ALX E-Commerce. All rights reserved.</p>
            </div>
        </div>
    </div>
</body>

</html>

--===============4718208076344061899==
```

## Security Best Practices

1. **Never expose** your access token or refresh token in client-side code
2. **Store tokens securely** using HTTP-only cookies or secure storage
3. **Implement token rotation** using refresh tokens
4. **Handle token expiration** gracefully in your application

## Rate Limiting

Authentication endpoints are rate-limited to prevent abuse:

- Registration: 5 requests per hour per IP
- Login: 10 requests per minute per IP
- Token refresh: 20 requests per minute per IP

## Error Handling

Common authentication errors:

| Status Code | Error Code | Description |
|-------------|------------|-------------|
| 400 | invalid_credentials | Incorrect email or password |
| 400 | email_not_verified | Email address not verified |
| 401 | token_not_valid | Invalid or expired token |
| 403 | account_disabled | Account is disabled |
| 429 | throttled | Too many requests |

## Need Help?

If you encounter any issues with authentication, please contact our support team at <support@ecommerce-api.com>.
