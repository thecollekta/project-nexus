# E-commerce API Documentation

This directory contains comprehensive documentation for the E-commerce API, designed to help developers integrate with our platform.

## Documentation Structure

- `docs/` - Root documentation directory
  - `api/` - API reference documentation
    - [users.md](./api/users.md) - User management and authentication endpoints
    - [products.md](./api/products.md) - Product catalog and inventory management
  - `guides/` - How-to guides
    - [authentication.md](./guides/authentication.md) - Authentication and user management guide

## Viewing the Documentation

### Online Documentation

Access the interactive API documentation at: [Swagger UI](/schema/swagger-ui/)

### Local Development

To view the documentation locally:

1. Start the development server:

   ```bash
   python manage.py runserver
   ```

2. Access the documentation:

   - Swagger UI: [http://127.0.0.1:8000/schema/swagger-ui/](http://127.0.0.1:8000/schema/swagger-ui/)
   - ReDoc: [http://127.0.0.1:8000/schema/redoc/](http://127.0.0.1:8000/schema/redoc/)

## Documentation Features

- **REST API Documentation**: Complete reference for all REST endpoints
- **Authentication Guide**: Step-by-step authentication flow
- **Code Examples**: Ready-to-use examples for all major operations
- **Error Handling**: Detailed error responses and troubleshooting

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
4. Run tests and linters: `./scripts/test.sh` (Coming soon)
5. Submit a pull request

## License

Coming soon.
