"""
django-prod CLI entry point.

Provides commands for creating and deploying Django projects with production configuration.
"""
import argparse
import subprocess
import sys
from pathlib import Path

import questionary
from django.core.management.utils import get_random_secret_key

from .generator import add_to_installed_apps, generate_production_files, include_urls


def startproject(name: str, directory: str | None = None) -> None:
    """Create a new Django project with production configuration files."""
    # Determine target directory
    if directory:
        target_dir = Path(directory).resolve()
        project_dir = target_dir
    else:
        target_dir = Path.cwd()
        project_dir = target_dir / name

    # Build django-admin command
    cmd = ["django-admin", "startproject", name]
    if directory:
        cmd.append(directory)

    print(f"Creating Django project '{name}'...")

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error creating Django project: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("Error: django-admin not found. Make sure Django is installed.")
        sys.exit(1)

    # Prompt for domain
    domain = questionary.text(
        "What's the domain name of your application?",
        default="*",
    ).ask()

    if domain is None:
        print("Aborted.")
        sys.exit(1)

    # Settings directory is project_dir/name/
    settings_dir = project_dir / name

    # Add django_prod to INSTALLED_APPS
    settings_path = settings_dir / "settings.py"
    add_to_installed_apps(settings_path, "django_prod")

    # Include django_prod URLs for welcome page
    urls_path = settings_dir / "urls.py"
    include_urls(urls_path, "django_prod")

    # Generate production files
    secret_key = get_random_secret_key()
    print("Generating production files...")
    generate_production_files(
        project_name=name,
        project_dir=project_dir,
        settings_dir=settings_dir,
        domain=domain,
        secret_key=secret_key,
    )

    print(f"\nProject '{name}' created successfully!")
    print("\nNext steps:")
    print(f"  cd {project_dir.name}")
    print("  python manage.py django_prod_deploy  # Deploy to your server")


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="django-prod",
        description="Django production deployment tool",
    )
    subparsers = parser.add_subparsers(dest="command")

    # startproject command
    sp = subparsers.add_parser(
        "startproject",
        help="Create a new Django project with production files",
    )
    sp.add_argument("name", help="Name of the project")
    sp.add_argument(
        "directory",
        nargs="?",
        help="Optional destination directory",
    )

    args = parser.parse_args()

    if args.command == "startproject":
        startproject(args.name, args.directory)
    else:
        parser.print_help()
