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


def include_urls(urls_path: Path, app_name: str, url_path: str = "") -> None:
    """Include an app's URLs in the project's urls.py."""
    content = urls_path.read_text()

    # Check if already included
    if f"include('{app_name}.urls')" in content or f'include("{app_name}.urls")' in content:
        print(f"[already present] - {app_name}.urls in urlpatterns")
        return

    # Add 'include' to imports if not present
    # Use regex to match actual import line, not comments
    import_pattern = r"^from django\.urls import path$"
    if re.search(import_pattern, content, re.MULTILINE):
        content = re.sub(
            import_pattern,
            "from django.urls import include, path",
            content,
            flags=re.MULTILINE,
        )

    # Add the URL pattern
    pattern = r"(urlpatterns\s*=\s*\[)"
    replacement = f"\\1\n    path('{url_path}', include('{app_name}.urls')),"
    new_content = re.sub(pattern, replacement, content)

    urls_path.write_text(new_content)
    print(f"[Modified] - {urls_path} (added {app_name}.urls)")
