import importlib
import os
from pathlib import Path

import questionary
from django.core.management.base import BaseCommand
from django.core.management.utils import get_random_secret_key

from django_prod.generator import generate_production_files


class Command(BaseCommand):
    help = "Generates production configuration files for your Django project"

    def __init__(self, *args, **options):
        super().__init__(*args, **options)
        self.settings_module = os.environ.get("DJANGO_SETTINGS_MODULE")

        if not self.settings_module:
            self.stderr.write(self.style.ERROR("DJANGO_SETTINGS_MODULE is not set"))
            return

        try:
            settings_file = Path(importlib.import_module(self.settings_module).__file__)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Could not locate settings module: {e}"))
            return

        self.settings_dir = settings_file.parent
        self.project_dir = self.settings_dir.parent
        self.project_name = self.settings_dir.name
        self.domain = questionary.text(
            "What's the domain name of your application?",
            default="*",
        ).ask()
        self.secret_key = get_random_secret_key()

    def handle(self, *args, **kwargs):
        generate_production_files(
            project_name=self.project_name,
            project_dir=self.project_dir,
            settings_dir=self.settings_dir,
            domain=self.domain,
            secret_key=self.secret_key,
        )
