# E-commerce API Documentation

This directory contains comprehensive documentation for the E-commerce API, designed to help developers integrate with our platform.

## Documentation Structure

- `api/` - API reference documentation
  - `users.md` - User management and authentication endpoints
- `guides/` - How-to guides
  - `authentication.md` - Authentication and user management guide

## Viewing the Documentation

### Online Documentation

Access the interactive API documentation at: [Swagger UI](/schema/swagger-ui/)

### Local Development

To view the documentation locally:

1. Start the development server:

    ```bash
    python manage.py runserver
    ```

2. Visit <http://127.0.0.1:8000/schema/swagger-ui/> for Swagger UI
3. Visit <http://127.0.0.1:8000/schema/redoc/> for ReDoc

## Current Features

- User registration with email verification
- JWT-based authentication
- User profile management
- Password reset functionality
- Admin interface for user management

## Getting Started

1. Clone the repository
2. Set up a virtual environment
3. Install dependencies: `pip install -r requirements/development.txt`
4. Run migrations: `python manage.py migrate`
5. Create a superuser: `python manage.py createsuperuser`
6. Start the development server: `python manage.py runserver`

## Contributing

To contribute to the project:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linters: `./scripts/test.sh`
5. Submit a pull request

## License

Coming soon.
