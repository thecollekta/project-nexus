# ALX E-commerce Backend

A robust, scalable, and secure Django-based e-commerce backend with REST and GraphQL API support.

## Project Overview

A high-performance **E-Commerce Backend API** built with Django and Django REST Framework, designed as
part of the ALX ProDev program. This project serves as a robust foundation for building scalable
e-commerce platforms with modern development practices.

## Tech Stack

- **Backend Framework**: [Django 5.2.6+](https://www.djangoproject.com/)
- **Database**: [PostgreSQL](https://www.postgresql.org/) (via psycopg)
- **API**: [Django REST Framework](https://www.django-rest-framework.org/) with [SimpleJWT](https://github.com/jazzband/djangorestframework-simplejwt)
- **Async Tasks**: [Celery](https://docs.celeryq.dev/) with [Redis](https://redis.io/)
- **Documentation**: [DRF Spectacular](https://drf-spectacular.readthedocs.io/) (OpenAPI 3.0)
- **GraphQL**: [Graphene-Django](https://docs.graphene-python.org/projects/django/)
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
  - [API Documentation](#api-documentation)
    - [Interactive Documentation](#interactive-documentation)
    - [Authentication](#authentication)
    - [Available Endpoints](#available-endpoints)
      - [Available Endpoints Authentication](#available-endpoints-authentication)
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

- RESTful API design with consistent response formats
- Advanced filtering, searching, and sorting
- Pagination support
- GraphQL endpoint (Coming Soon)
- Comprehensive API documentation (Swagger/ReDoc)

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
│       ├── admin.py             # Admin site configurations
│       ├── apps.py              # App config
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
│   │   └── production.py        # Production settings
│   ├── __init__.py
│   ├── asgi.py
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
│       └── core/                # Core app tests
├── .dockerignore
├── .env.example                 # Example environment variables
├── .gitignore
├── .safety-project.ini          # Safety configuration
├── docker-compose.yml           # Docker Compose configuration
├── Dockerfile                   # Docker configuration
├── manage.py                    # Django management script
├── pytest.ini                   # Pytest configuration
├── README.md                    # This file
└── requirements.txt             # Development dependencies

## Accounts API Endpoints

This document provides a comprehensive overview of the API endpoints available for user account management. Read the full documentation in [API Docs](docs/api_docs.md).

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL 13+
- Redis 6.0+
- Docker and Docker Compose (optional)

### Local Development Setup

1. **Clone the repository**

      ```bash
      git clone https://github.com/yourusername/project-nexus.git
      cd project-nexus
      ```

2. **Set up Python virtual environment**

      ```bash
      python -m venv venv
      source venv/bin/activate  # On Windows: venv\Scripts\activate
      ```

3. **Install dependencies**

      ```bash
      pip install -r requirements/development.txt
      ```

4. **Set up environment variables**

      ```bash
      cp .env.example .env
      # Edit .env with your configuration
      ```

5. **Set up the database**

      ```bash
      python manage.py migrate
      python manage.py createsuperuser
      ```

6. **Run the development server**

      ```bash
      python manage.py runserver
      ```

### Running with Docker

```bash
docker-compose up -d --build
```

## API Documentation

### Interactive Documentation

- **Swagger UI**: [/api/docs/](http://localhost:8000/api/docs/)
- **ReDoc**: [/api/redoc/](http://localhost:8000/api/redoc/)

### Authentication

All API endpoints (except public ones) require JWT authentication. Include the token in the Authorization header:

```json
Authorization: Bearer your.jwt.token.here
```

### Available Endpoints

#### Available Endpoints Authentication

- `POST /api/v1/accounts/register/` - Register a new user
- `POST /api/v1/accounts/login/` - Obtain JWT token
- `POST /api/v1/accounts/token/refresh/` - Refresh JWT token
- `POST /api/v1/accounts/password/reset/` - Request password reset

#### User Profile

- `GET /api/v1/accounts/profile/` - Get current user profile
- `PUT /api/v1/accounts/profile/` - Update profile
- `PATCH /api/v1/accounts/profile/` - Partial update profile

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

For support, please open an issue in the GitHub repository.
