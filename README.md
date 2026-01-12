# django-prod

Quickly deploy your Django project to production over SSH.

---

## Installation

```bash
pip install django-prod
```

---

## Quick Start (New Projects)

Create a new Django project with production-ready configuration in one command:

```bash
django-prod startproject myapp
```

You will be prompted for your domain name. This creates:
- A standard Django project
- Production settings (`settings_prod.py`) with optimized SQLite configuration
- Docker and Docker Compose files
- Gunicorn configuration
- WhiteNoise for static files

Then deploy to your server:

```bash
cd myapp
python manage.py django_prod_deploy
```

---

## Existing Projects

If you already have a Django project, you can add production configuration:

1. Add `django_prod` to your installed apps:

```python
# settings.py
INSTALLED_APPS = [
    "django_prod",
    ...
]
```

2. Generate production files:

```bash
python manage.py django_prod_init
```

3. Deploy:

```bash
python manage.py django_prod_deploy
```

---

## Deployment

When you run `django_prod_deploy`, you will be prompted for:

- Server IP address
- SSH username
- Path to your SSH private key

![Prompted With](doc_images/prompted.png)

The script will:

- Upload your project to the server
- Install Docker if needed
- Build and run your production stack with Docker Compose

Your app will be available at `http://your-server-ip:8000`

---

## Technology Choices

This project is **opinionated** and uses the simplest technologies to move from development to production quickly:

- **SQLite** as the production database, with optimized PRAGMA settings for performance (WAL mode, memory-mapped I/O, tuned cache). For those who consider SQLite a "toy database," check out the configuration in `settings_prod.py`.

- **WhiteNoise** for static files. Performance is excellent once assets are cached, especially behind a CDN like Cloudflare.

- **Docker** and **Docker Compose** for containerization.

- **Gunicorn** as the WSGI application server.

---

## Generated Files

| File | Description |
|------|-------------|
| `settings_prod.py` | Production Django settings |
| `.env.prod` | Environment variables (SECRET_KEY) |
| `docker-compose.yaml` | Container orchestration |
| `prod.Dockerfile` | Docker image definition |
| `entrypoint.prod.sh` | Container startup script |
| `requirements.txt` | Python dependencies |
