# Project Nexus - E-commerce Backend

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

- [Project Nexus - E-commerce Backend](#project-nexus---e-commerce-backend)
  - [Project Overview](#project-overview)
  - [Tech Stack](#tech-stack)
  - [Table of Contents](#table-of-contents)
  - [Features](#features)
    - [Core Functionality](#core-functionality)
    - [Security](#security)
    - [API Features](#api-features)
    - [Development Tools](#development-tools)
  - [Project Structure](#project-structure)
  - [Getting Started](#getting-started)
    - [Prerequisites](#prerequisites)
    - [Local Development](#local-development)
    - [Running with Docker](#running-with-docker)
  - [Testing](#testing)
  - [API Documentation](#api-documentation)
    - [Authentication](#authentication)
    - [Example API Request](#example-api-request)
  - [Deployment](#deployment)
    - [Production Setup](#production-setup)
    - [Environment Variables](#environment-variables)
  - [Contributing](#contributing)
  - [License](#license)

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
```

## Getting Started

### Prerequisites

- Python 3.13+
- PostgreSQL 17+
- Redis 7.2+ (for Celery)
- Docker & Docker Compose (optional)

### Local Development

1. **Clone the repository**

    ```bash
    git clone https://github.com/yourusername/project-nexus.git
    cd project-nexus
    ```

2. **Set up a virtual environment**

    ```bash
    # Create a virtual environment
    python -m venv .venv

    # Activate the virtual environment
    # On Windows:
    .\.venv\Scripts\activate

    # On Unix or MacOS:
    source .venv/bin/activate
    ```

3. **Install dependencies**

    ```bash
    # Install development dependencies
    pip install -r requirements/development.txt

    # Or install in development mode with all extras
    pip install -e ".[dev]"

    # Set up pre-commit hooks (coming soon)
    pre-commit install
    ```

4. **Set up environment variables**

    ```bash
    # Copy the example environment file
    cp .env.example .env

    # Edit the .env file with your configuration
    # You'll need to set at least these variables:
    # SECRET_KEY
    # DJANGO_ALLOWED_HOSTS
    # DATABASE_URL
    ```

5. **Set up the database**

    ```bash
    # Run migrations
    python manage.py migrate

    # Create a superuser
    python manage.py createsuperuser
    ```

6. **Run the development server**

    ```bash
    python manage.py runserver
    ```

7. **Run Celery worker (in a new terminal)**

    ```bash
    celery -A ecommerce_backend worker -l info
    ```

8. **Run Celery beat (for scheduled tasks)**

    ```bash
    celery -A ecommerce_backend beat -l info
    ```

### Running with Docker

1. **Build and start the services**

    ```bash
    docker-compose up --build
    ```

2. **Run database migrations**

    ```bash
    docker-compose exec web python manage.py migrate
    ```

3. **Create a superuser**

    ```bash
    docker-compose exec web python manage.py createsuperuser
    ```

4. **Access the application**
   - API: <http://localhost:8000/api/>
   - Admin: <http://localhost:8000/admin/>
   - API Docs: <http://localhost:8000/schema/swagger-ui/>
   - GraphQL: <http://localhost:8000/graphql> (Coming Soon)

## Testing

Run the test suite with:

```bash
# Run all tests
pytest

# Run tests with coverage report
pytest --cov=apps --cov-report=html

# Run a specific test file
pytest apps/core/tests/test_views.py

# Run tests with detailed output
pytest -v
```

## API Documentation

API documentation is automatically generated using DRF Spectacular and available at:

- **Swagger UI**: <http://localhost:8000/schema/swagger-ui/>
- **ReDoc**: <http://localhost:8000/schema/redoc/>
- **GraphiQL**: <http://localhost:8000/graphql> (Coming Soon)

### Authentication

Most endpoints require authentication. Include the JWT token in the Authorization header:

```http
Authorization: Bearer your.jwt.token.here
```

### Example API Request

```http
GET /api/v1/products/
Authorization: Bearer your.jwt.token.here
Content-Type: application/json
```

## Deployment

### Production Setup

1. Set `DEBUG=False` in your environment variables
2. Configure your web server (Nginx/Apache) to serve static files
3. Set up a production database (PostgreSQL recommended)
4. Configure a production-ready cache (Redis recommended)
5. Set up monitoring (Sentry etc.) (coming soon)

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DEBUG` | Enable debug mode | `False` | Yes |
| `SECRET_KEY` | Django secret key | - | Yes |
| `DATABASE_URL` | Database connection URL | - | Yes |
| `REDIS_URL` | Redis connection URL | `redis://redis:6379/0` | No |
| `DJANGO_ALLOWED_HOSTS` | List of allowed hosts | `*` | No |
| `CORS_ALLOWED_ORIGINS` | List of allowed CORS origins | `[]` | No |
| `EMAIL_BACKEND` | Email backend | `console` | No |
| `DEFAULT_FROM_EMAIL` | Default sender email | `webmaster@localhost` | No |

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process
for submitting pull requests. (Coming Soon)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. (Coming Soon)
