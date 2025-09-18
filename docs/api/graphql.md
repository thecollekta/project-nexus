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

## User Profile Operations

### Get Current User

Retrieve the profile of the currently authenticated user.

```graphql
{
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
