# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**django-prod** is a Python package that automates Django project deployment to remote servers over SSH using Docker. It provides:
- **CLI command**: `django-prod startproject <name>` - creates a Django project with all production files in one step
- **Management commands**: `django_prod_init` (generates production config files) and `django_prod_deploy` (deploys via SSH/SCP)

## Build and Development Commands

```bash
# Install dependencies (uses UV package manager)
uv sync

# Build the package
uv build

# Install locally for development
pip install -e .

# Run as CLI (after installation)
django-prod
```

The package is built with Hatchling (PEP 517). Entry point `django-prod` maps to `django_prod:main`.

## Architecture

### Package Structure

```
src/django_prod/
├── __init__.py                    # CLI entry point (main(), startproject)
├── generator.py                   # Shared file generation utilities
├── management/commands/
│   ├── django_prod_init.py        # Generates production files (uses generator.py)
│   └── django_prod_deploy.py      # SSH/SCP deployment to VPS
└── templates/boilerplate/         # Django templates for generated files
    ├── settings_prod.py.txt       # Production Django settings
    ├── docker-compose.yaml.txt    # Docker Compose config
    ├── prod.Dockerfile.txt        # Container definition
    ├── entrypoint.prod.sh.txt     # Container startup script
    ├── .env.prod.txt              # Environment variables
    └── requirements.txt           # Python dependencies
```

### Key Design Patterns

1. **Django Template Engine for Code Generation**: Uses `Engine().from_string()` in `generator.py` to generate production files without requiring full Django setup. Allows dynamic insertion of project name, domain, and secret key.

2. **Interactive CLI via Questionary**: Both commands use `questionary` for user prompts (domain name, VPS IP, SSH credentials).

3. **Deployment State Persistence**: `django_prod_deploy` saves connection details to `deployment_target.json` for subsequent deployments.

4. **SSH Deployment Pipeline**: Uses Paramiko for SSH connections and SCP for file transfer. Automatically excludes `.venv`, `env`, and `__pycache__` directories.

### Technology Choices (Opinionated)

- **Database**: SQLite with production-grade PRAGMA tuning (WAL mode, mmap, cache optimization)
- **Static Files**: WhiteNoise with `CompressedManifestStaticFilesStorage`
- **WSGI Server**: Gunicorn with 3 workers
- **Container**: Python 3.12 Alpine base image
- **Volumes**: Persistent volumes for SQLite database and static files

### Command Flow

**`django-prod startproject <name>`**: Runs `django-admin startproject` → prompts for domain → adds `django_prod` to INSTALLED_APPS → generates all production files

**`django_prod_init`**: Prompts for domain → renders all boilerplate templates → writes production files to project root (for existing projects)

**`django_prod_deploy`**: Prompts for VPS details (or loads from `deployment_target.json`) → SCPs project files → ensures Docker installed on remote → runs `docker compose up -d --build`
