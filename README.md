# ALX E-commerce Backend

A robust, scalable, and secure Django-based e-commerce backend with REST and GraphQL API support.

## Project Overview

A high-performance **E-Commerce Backend API** built with Django and Django REST Framework, designed as part of the ALX ProDev program. This project serves as a robust foundation for building scalable e-commerce platforms with modern development practices.

## Tech Stack

- **Backend Framework**: [Django 5.2.6+](https://www.djangoproject.com/)
- **Database**: [PostgreSQL](https://www.postgresql.org/) (via psycopg)
- **API**:
  - [Django REST Framework](https://www.django-rest-framework.org/) with [SimpleJWT](https://github.com/jazzband/djangorestframework-simplejwt)
  - [Graphene-Django](https://docs.graphene-python.org/projects/django/) for GraphQL API
- **Async Tasks**: [Celery](https://docs.celeryq.dev/) with [Redis](https://redis.io/)
- **Documentation**:
  - [DRF Spectacular](https://drf-spectacular.readthedocs.io/) (OpenAPI 3.0) for REST API
  - Interactive GraphQL Playground
- **Monitoring**: [Sentry SDK](https://docs.sentry.io/)
- **Code Quality**: [Black](https://black.readthedocs.io/), [Ruff](https://beta.ruff.rs/), [mypy](http://mypy-lang.org/)

## Table of Contents

- [ALX E-commerce Backend](#alx-e-commerce-backend)
  - [Project Overview](#project-overview)
  - [Tech Stack](#tech-stack)
  - [Table of Contents](#table-of-contents)
  - [Features](#features)
    - [Core Functionality](#core-functionality)
    - [Security](#security)
    - [API Features](#api-features)
    - [Development Tools](#development-tools)
  - [Project Structure](#project-structure)
    - [Available Endpoints](#available-endpoints)
      - [Authentication](#authentication)
      - [User Profile](#user-profile)
  - [Testing](#testing)
  - [Development Workflow](#development-workflow)
  - [Contributing](#contributing)
  - [License](#license)
  - [Support](#support)

## Features

### Core Functionality

- **Base Models**: `AuditStampedModelBase` with common fields (`created_at`, `updated_at`, `created_by`, `updated_by`, `is_active`)
- **Custom Managers**: `ActiveManager` and `AllObjectsManager` for soft delete functionality
- **Base Views**: `BaseViewSet` and `BaseReadOnlyViewSet` with built-in logging and error handling

### Security

- JWT Authentication with refresh tokens
- Rate limiting and throttling
- CORS and CSRF protection
- Content Security Policy (CSP)
- Secure password validation
- Request/Response logging

### API Features

- **Dual API Support**:
  - **RESTful API** with consistent response formats
  - **GraphQL API** for flexible data querying
- **Authentication**:
  - JWT Authentication with refresh tokens
  - Social authentication (OAuth2) (coming soon)
  - Email verification
  - Password reset flow
- **Advanced Features**:
  - Rate limiting and throttling
  - Request/Response logging
  - Comprehensive error handling
  - CORS and CSRF protection
- **Documentation**:
  - Interactive Swagger/ReDoc for REST API
  - GraphQL Playground with schema introspection
  - Detailed API reference in [docs](./docs/) directory

### Development Tools

- Pre-commit hooks with code formatters and linters
- Comprehensive test suite with pytest
- Code coverage reporting
- Debug toolbar for development
- Type checking with mypy

## Project Structure

```text
project-nexus/
├── apps/
│   ├── accounts/                # User authentication and profile management
│   │   ├── admin.py             # Admin configurations for user models
│   │   ├── apps.py              # App configuration
│   │   ├── backends.py          # Custom Authentication backends
│   │   ├── models.py            # Custom user model and related models
│   │   ├── serializers.py       # Serializers for user data
│   │   └── views.py             # Authentication and profile views
│   └── core/                    # Core application with base functionality
|   ├── management/              # Custom management commands
|           └── commands/
│       ├── __init__.py
│       ├── admin.py             # Admin site configurations
│       ├── apps.py              # App config
│       ├── graphql.py           # GraphQL utility
│       ├── middleware.py        # Custom middleware
│       ├── models.py            # Base models and managers
│       ├── pagination.py        # Custom pagination classes
│       ├── serializers.py       # Base serializers
│       ├── throttling.py        # Rate limiting configurations
│       └── views.py             # Base views and viewsets
├── docs/                        # Documentation
├── ecommerce_backend/           # Main project directory
│   ├── settings/                # Settings split by environment
│   │   ├── __init__.py
│   │   ├── base.py              # Base settings
│   │   ├── development.py       # Development-specific settings
│   │   ├── production.py        # Production settings
│   │   └── testing.py           # Testing settings
│   ├── __init__.py
│   ├── asgi.py
│   ├── celery.py                # 
│   ├── schema.py                # 
│   ├── setting_old.py           # 
│   ├── urls.py                  # Main URL configuration
│   └── wsgi.py
├── logs/                        # Log files directory
├── media/                       # User-uploaded media files
├── requirements/                # Dependency management
│   ├── base.txt                 # Core dependencies
│   ├── development.txt          # Development-specific dependencies
│   └── production.txt           # Production dependencies
├── static/                      # Static files
├── tests/                       # Test files
│   └── unit/                    # Unit tests
├── .dockerignore
├── .env.example                 # Example environment variables
├── .gitignore
├── .safety-project.ini          # Safety configuration
├── docker-compose.yml           # Docker Compose configuration
├── Dockerfile                   # Docker configuration
├── manage.py                    # Django management script
├── pytest.ini                   # Pytest configuration
├── README.md                    # This file
├── redis.conf                   # Redis configuration
└── requirements.txt             # Development dependencies

## API Documentation

### REST API

- **Interactive Documentation**:
  - [Swagger UI](/schema/swagger-ui/)
  - [ReDoc](/schema/redoc/)

### GraphQL API

Access the GraphQL Playground at `/graphql/` for interactive queries and mutations.

Key GraphQL Features:
- Full CRUD operations for all resources
- Real-time updates with subscriptions (coming soon)
- Optimized queries with data loaders
- Comprehensive error handling

For detailed GraphQL documentation, see [GraphQL API Reference](./docs/api/graphql.md).

### Authentication

Both REST and GraphQL APIs use JWT authentication. Include the token in the `Authorization` header:

```http
Authorization: Bearer your_access_token_here
```

### Available Endpoints

#### Authentication

- **REST**:
  - `POST /api/v1/accounts/register/` - Register a new user
  - `POST /api/v1/accounts/login/` - Login and get JWT tokens
  - `POST /api/v1/accounts/logout/` - Invalidate user's refresh token
  - `POST /api/v1/accounts/token/refresh/` - Refresh access token
  - `GET /api/v1/accounts/me/` - Get current user's profile
  - `PUT /api/v1/accounts/me/` - Update current user's profile
  - `PATCH /api/v1/accounts/me/` - Partially update current user's profile
  - `POST /api/v1/accounts/me/change-password/` - Change current user's password
  - `POST /api/v1/accounts/verify-email/` - Request email verification
  - `POST /api/v1/accounts/verify-email/confirm/` - Confirm email verification
  - `POST /api/v1/accounts/reset-password/confirm/` - Confirm password reset

  **Admin Endpoints**:
  - `GET /api/v1/accounts/profiles/` - List all user profiles
  - `GET /api/v1/accounts/profiles/<id>/` - Get specific user profile
  - `PUT /api/v1/accounts/profiles/<id>/` - Update user profile
  - `PATCH /api/v1/accounts/profiles/<id>/` - Partially update user profile
  - `DELETE /api/v1/accounts/profiles/<id>/` - Delete user profile
  - `GET /api/v1/accounts/users/` - Alternative endpoint for user management (same as profiles)

#### User Profile

- **REST**:
  - `GET /api/v1/accounts/me/` - Get current user profile
  - `PATCH /api/v1/accounts/me/` - Update profile
  - `POST /api/v1/accounts/change-password/` - Change password

- **GraphQL**:
  - **Authentication**

    ```graphql
    # Register a new user
    mutation {
      registerUser(
      username: "kwame"
      email: "<kwame.nkrumah@ghana.com>"
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

    # Login

    mutation {
      login(email: "kwame.nkrumah@ghana.com", password: "Blackstar233.") {
        ok
        access
        refresh
        errors
      }
    }

    # Refresh token

    mutation {
      refreshToken(refreshToken: "your-refresh-token") {
        token
        refreshToken
        payload
      }
    }

    ```

For a complete list of available GraphQL queries and mutations, visit the GraphQL Playground at `/graphql/`. Read the full documentation in [GraphQL API Reference](./docs/api/graphql.md).

## Testing

Run the test suite with coverage:

```bash
pytest
```

## Development Workflow

1. Create a new branch for your feature
2. Write tests for your changes
3. Implement your changes
4. Run tests and ensure all pass
5. Create a pull request

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support, please open an issue in the GitHub repository or contact the maintainers.
