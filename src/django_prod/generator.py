"""
Shared file generation utilities for django-prod.

This module provides template rendering functions that work both in standalone CLI mode
(django-prod startproject) and within Django management commands (django_prod_init).
"""
import re
from pathlib import Path

from django.template import Context, Engine


def render_template(template_content: str, context: dict) -> str:
    """Render a Django template string without full Django configuration."""
    engine = Engine()
    template = engine.from_string(template_content)
    return template.render(Context(context, autoescape=False))


def get_template_content(template_name: str) -> str:
    """Read template content from the package's templates directory."""
    templates_dir = Path(__file__).parent / "templates" / "boilerplate"
    return (templates_dir / template_name).read_text()


def generate_file(template_name: str, output_path: Path, context: dict) -> None:
    """Generate a file from a template."""
    if output_path.exists():
        print(f"[already exists] - {output_path}")
        return

    content = get_template_content(template_name)
    rendered = render_template(content, context)
    output_path.write_text(rendered)
    print(f"[Generated] - {output_path}")


def generate_production_files(
    project_name: str,
    project_dir: Path,
    settings_dir: Path,
    domain: str,
    secret_key: str,
) -> None:
    """Generate all production configuration files."""
    # .env.prod (in settings directory)
    generate_file(".env.prod.txt", settings_dir / ".env.prod", {"secret_key": secret_key})

    # settings_prod.py (in settings directory)
    generate_file(
        "settings_prod.py.txt",
        settings_dir / "settings_prod.py",
        {"domain": domain, "project_name": project_name},
    )

    # docker-compose.yaml (in project root)
    generate_file(
        "docker-compose.yaml.txt",
        project_dir / "docker-compose.yaml",
        {"project_name": project_name},
    )

    # prod.Dockerfile (in project root)
    generate_file("prod.Dockerfile.txt", project_dir / "prod.Dockerfile", {})

    # entrypoint.prod.sh (in project root)
    generate_file("entrypoint.prod.sh.txt", project_dir / "entrypoint.prod.sh", {})

    # requirements.txt (in project root)
    generate_file("requirements.txt", project_dir / "requirements.txt", {})


def add_to_installed_apps(settings_path: Path, app_name: str) -> None:
    """Add an app to INSTALLED_APPS in settings.py."""
    content = settings_path.read_text()

    # Check if already present
    if f'"{app_name}"' in content or f"'{app_name}'" in content:
        print(f"[already present] - {app_name} in INSTALLED_APPS")
        return

    # Add after INSTALLED_APPS opening bracket
    pattern = r"(INSTALLED_APPS\s*=\s*\[)"
    replacement = f'\\1\n    "{app_name}",'
    new_content = re.sub(pattern, replacement, content)

    settings_path.write_text(new_content)
    print(f"[Modified] - {settings_path} (added {app_name} to INSTALLED_APPS)")


def add_welcome_view(urls_path: Path) -> None:
    """Add a simple welcome view to the project's urls.py."""
    content = urls_path.read_text()

    # Check if welcome view already exists
    if "welcome_view" in content or "django-prod" in content:
        print("[already present] - welcome view in urls.py")
        return

    # New urls.py content with inline welcome view
    new_content = '''"""
URL configuration for this project.
"""
from django.contrib import admin
from django.http import HttpResponse
from django.urls import path


def welcome_view(request):
    """Welcome page - remove this when you add your own views."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>django-prod - Ready for Production!</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
                text-align: center;
                color: #333;
            }
            h1 { color: #092e20; }
            .success { color: #28a745; font-size: 1.2em; }
            code {
                background: #f4f4f4;
                padding: 2px 8px;
                border-radius: 4px;
                font-size: 0.9em;
            }
            .next-steps {
                text-align: left;
                background: #f8f9fa;
                padding: 20px;
                border-radius: 8px;
                margin-top: 30px;
            }
            .next-steps li { margin: 10px 0; }
            a { color: #092e20; }
        </style>
    </head>
    <body>
        <h1>Welcome to django-prod!</h1>
        <p class="success">Your project is configured and ready for production deployment.</p>

        <div class="next-steps">
            <h3>Next steps:</h3>
            <ol>
                <li>Create your Django apps: <code>python manage.py startapp myapp</code></li>
                <li>Add your views and models</li>
                <li>Remove this welcome view from <code>urls.py</code></li>
                <li>Deploy: <code>python manage.py django_prod_deploy</code></li>
            </ol>
        </div>

        <p style="margin-top: 30px;">
            <a href="https://docs.djangoproject.com/" target="_blank">Django Documentation</a> |
            <a href="/admin/">Admin Panel</a>
        </p>
    </body>
    </html>
    """
    return HttpResponse(html)


urlpatterns = [
    path("", welcome_view, name="welcome"),
    path("admin/", admin.site.urls),
]
'''

    urls_path.write_text(new_content)
    print(f"[Modified] - {urls_path} (added welcome view)")
