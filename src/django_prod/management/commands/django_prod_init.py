import importlib
import os
import subprocess
from pathlib import Path

import questionary
from django.core.management.base import BaseCommand
from django.core.management.utils import get_random_secret_key
from django.template.loader import render_to_string


class Command(BaseCommand):
    help = "Creates a new Django app with additional setup for HTML templates"

    def __init__(self, *args, **options):
        super().__init__(*args, **options)
        self.settings_module = os.environ['DJANGO_SETTINGS_MODULE']

        if not self.settings_module:
            self.stderr.write(self.style.ERROR("DJANGO_SETTINGS_MODULE is not set"))
            return

        try:
            settings_file = Path(importlib.import_module(self.settings_module).__file__)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Could not locate settings module: {e}"))
            return

        self.settings_dir = settings_file.parent
        self.project_name = self.settings_dir.name
        self.domain = questionary.text("What's the domain name of your application?", default="*").ask()
        self.secret_key = get_random_secret_key()

    def handle(self, *args, **kwargs):
        self.create_dot_env_prod(self.secret_key, self.settings_dir)
        self.create_settings_prod(self.settings_dir, self.domain)
        self.create_docker_compose(self.settings_dir, self.project_name)
        self.create_dockerfile(self.settings_dir)
        self.create_entrypoint(self.settings_dir)
        self.create_requirements_if_not_exists(self.settings_dir)

    @staticmethod
    def _create_file_from_template(context, template_file_path, output_file_path):
        env_content = render_to_string(template_file_path, context)
        path = output_file_path
        if path.exists():
            print(f"[already exists] - {path}")
            return
        path.write_text(env_content)
        print(f"[Generated] - {path}")

    @classmethod
    def create_dot_env_prod(cls, secret_key, settings_dir):
        env_context = {
            "secret_key": secret_key,
        }
        output_path = settings_dir / ".env.prod"
        cls._create_file_from_template(env_context, "boilerplate/.env.prod.txt", output_path)

    @classmethod
    def create_settings_prod(cls, settings_dir, domain):
        context = {
            "domain": domain,
        }
        output_path = settings_dir / "settings_prod.py"
        cls._create_file_from_template(context, "boilerplate/settings_prod.py.txt", output_path)

    @classmethod
    def create_docker_compose(cls, settings_dir, project_name):
        context = {
            "project_name": project_name,
        }
        output_path = settings_dir.parent / "docker-compose.yaml"
        cls._create_file_from_template(context, "boilerplate/docker-compose.yaml.txt", output_path)

    @classmethod
    def create_dockerfile(cls, settings_dir):
        output_path = settings_dir.parent / "prod.Dockerfile"
        cls._create_file_from_template({}, "boilerplate/prod.Dockerfile.txt", output_path)

    @classmethod
    def create_entrypoint(cls, settings_dir):
        output_path = settings_dir.parent / "entrypoint.prod.sh"
        cls._create_file_from_template({}, "boilerplate/entrypoint.prod.sh.txt", output_path)

    @classmethod
    def create_requirements_if_not_exists(cls, settings_dir):
        output_path = settings_dir.parent / "requirements.txt"
        if not output_path.exists():
            do_create = questionary.confirm(
                "[WARNING] - 'requirements.txt' not found. Do you want to create a default one? "
                "This will run the command 'pip freeze > requirements.txt'"
            ).ask()
            if do_create:
                try:
                    result = subprocess.run(
                        ["pip", "freeze"],
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    output_path.write_text(result.stdout)
                    print(f"✅ Created requirements.txt at {output_path}")
                except subprocess.CalledProcessError as e:
                    print("❌ Failed to generate requirements.txt")
                    print(e.stderr)
