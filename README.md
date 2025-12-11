# django-prod

Quickly deploy over SSH your newly generated django project.

---

This package provides two management commands:

- `django_prod_init` — generates all production files you need.
- `django_prod_deploy` — deploys your project to a remote SERVER over SSH.

---

## 📦 Installation

Install the package:

```bash
pip install django-prod
```

---

## 🛠 Example

Create a new django project:

```bash
django-admin startproject webapp .
```

Add django-prod to installed apps:
```bash
# settings.py
INSTALLED_APPS = [
    ...
    "django_prod",
]
```

Initialize production files:
```bash
python manage.py django_prod_init
```

Deploy to your server:
```bash
python manage.py django_prod_deploy
```
You will be prompted for:

- Server IP address
- SSH username
- Path to your SSH private key

Then the script will:

- Upload your project to the server
- Ensure Docker is installed
- Run your production stack with Docker Compose

---


