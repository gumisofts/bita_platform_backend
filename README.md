# Bita Platform Backend

Django backend for Bita Platform with REST API, documentation generation, and deployment configurations.

## Table of Contents

- [Introduction](#introduction)
- [Features](#features)
- [Get Started](#get-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Configuration](#configuration)
- [Locally Running Options](#locally-running-options)
  - [Using Docker Compose](#using-docker-compose)
  - [Without Docker](#without-docker)
- [Deployment](#deployment)
  - [Zappa Deployment](#zappa-deployment)
  - [GitHub Actions](#github-actions)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [Known External Dependencies](#known-external-dependencies)
- [Directory Structure](#directory-structure)
- [License](#license)

## Introduction

This project is a Django-based backend application designed to provide a robust and scalable foundation for the Bita Platform. It includes configurations for RESTful API development, automated API documentation, and deployment strategies.

## Features

- RESTful API endpoints
- User authentication and authorization
- Database models for core entities
- Automated API documentation generation (Swagger UI, ReDoc)
- Docker and Docker Compose support for local development
- Zappa configuration for serverless deployment on AWS Lambda
- GitHub Actions workflows for CI/CD

## Get Started

### Prerequisites

Before you begin, ensure you have the following installed:

- Python 3.12
- pip (Python package installer)
- Docker (if using Docker Compose)
- Zappa (if deploying with Zappa)
- AWS CLI (if deploying with Zappa)
- Node.js (v20.11.0)

### Installation

1.  Clone the repository:

    ```bash
    git clone https://github.com/gumisofts/bita_platform_backend.git
    cd bita_platform_backend
    ```

2.  Create a virtual environment:

    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Linux/macOS
    .venv\Scripts\activate  # On Windows
    ```

3.  Install the dependencies:

    ```bash
    pip install -r requirements.txt
    ```

### Configuration

1.  Create a `.env` file in the `config/` directory.  Populate it with the necessary environment variables.  Example `.env` content:

    ```
    DEBUG=True
    EMAIL_HOST=smtp.example.com
    EMAIL_PORT=587
    EMAIL_HOST_USER=your_email@example.com
    EMAIL_HOST_PASSWORD=your_email_password
    POSTGRES_DB=your_db_name
    POSTGRES_USER=your_db_user
    POSTGRES_PASSWORD=your_db_password
    POSTGRES_HOST=db
    POSTGRES_PORT=5432
    POSTGRES_SSL_MODE=require # or disable if not using SSL
    ```

2.  Configure your database settings in `core/settings.py` using the environment variables.

## Locally Running Options

### Using Docker Compose

1.  Build and run the Docker containers:

    ```bash
    docker compose up --build
    ```

2.  Access the application at `http://localhost:8000`.

### Without Docker

1.  Apply migrations:

    ```bash
    python manage.py migrate
    ```

2.  Run the development server:

    ```bash
    python manage.py runserver
    ```

3.  Access the application at `http://localhost:8000`.

## Deployment

### Zappa Deployment

1.  Install Zappa (It is already in the requirements.txt file):

    ```bash
    pip install zappa
    ```

2.  Configure Zappa:

    ```bash
    zappa init
    ```

    Follow the prompts to configure your AWS credentials and deployment settings.  The `zappa_settings.json` file is used to store these settings.

3.  Deploy the application:

    ```bash
    zappa deploy <environment>
    ```

    Replace `<environment>` with the desired environment (e.g., `dev`, `pro`).

4.  Update the application:

    ```bash
    zappa update <environment>
    ```

### GitHub Actions

The project includes a GitHub Actions workflow (`.github/workflows/deployment.yaml`) for automated deployment to AWS Lambda using Zappa.

1.  Configure AWS credentials as secrets in your GitHub repository settings:
    - `AWS_ACCESS_KEY_ID`
    - `AWS_SECRET_ACCESS_KEY`
    - `AWS_DEFAULT_REGION` (e.g., `eu-north-1`)

2.  Push changes to the `main` branch to trigger the deployment workflow.

## API Documentation

The project uses DRF Spectacular to generate OpenAPI schemas.  API documentation is available in the following formats:

-   **Swagger UI**: Access at `/swagger/`
-   **ReDoc UI**: Access at `/redoc/`
-   **OpenAPI Schema (YAML)**: Access at `/schema/`

A basic HTML page (`notification/templates/index.html`) provides links to these documentation endpoints.

The `api_docs.yaml` workflow in `.github/workflows/` generates and deploys the API documentation to GitHub Pages.

## Testing

Run the tests using the following command:

```bash
python manage.py test
```

## Known External Dependencies
- Django: Web framework
- Django REST Framework: Toolkit for building REST APIs
- DRF Spectacular: OpenAPI schema generator for Django REST Framework
- Zappa: Tool for deploying Python WSGI applications on AWS Lambda and API Gateway
- PostgreSQL: Relational database
- Other dependencies: Listed in `requirements.txt`

## Directory Structure

.
├── .env                      # Environment variables (not committed)
├── .gitignore                # Specifies intentionally untracked files that Git should ignore
├── .isort.cfg                # Configuration file for isort (Python import sorter)
├── docker-compose.yml        # Docker Compose configuration
├── Dockerfile                # Dockerfile for building the application image
├── format.sh                 # Script for formatting code (e.g., using black)
├── LICENSE                   # License file
├── manage.py                 # Django management script
├── README.md                 # This file
├── requirements.txt          # List of Python dependencies
├── zappa_settings.json       # Zappa deployment settings
├── .github/                  # GitHub Actions configuration
│   └── workflows/            # Workflow files
│       ├── api_docs.yaml     # Workflow for generating and deploying API docs
│       └── deployment.yaml   # Workflow for Zappa deployment
│       └── django.yaml       # Workflow for CI to check linting and tests
├── accounts/                 # Django app for user accounts
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── backends.py
│   ├── consumers.py
│   ├── manager.py
│   ├── models.py
│   ├── permissions.py
│   ├── serializers.py
│   ├── tests.py
│   ├── urls.py
│   └── views.py
├── ansible/                  # Ansible configuration for infrastructure management
│   ├── ansible.cfg
│   └── inventory.yaml
│   └── playbook.yaml
│   └── reload.yaml
├── config/                   # Configuration files
├── core/                     # Core Django project settings
├── crm/                      # Django app for CRM functionality
├── deployment/               # Deployment-related scripts and configurations
├── docker/                   # Docker-related files
├── file/                     # Django app for file management
├── finances/               # Django app for financial functionality
├── inventory/                # Django app for inventory management
├── notification/             # Django app for notifications
│   └── templates/
│       └── index.html        # Template for API documentation index

## License

This project is licensed under the terms of the GNU General Public License v3.0. See the `LICENSE` file for details.
