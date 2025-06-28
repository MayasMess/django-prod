import importlib
import json
import os
from pathlib import Path

import questionary
import paramiko
from scp import SCPClient
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Deploy to a VPS with Docker"

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

        self.project_root_dir = settings_file.parent.parent

        deployment_target = {}
        if Path(self.project_root_dir / "deployment_target.json").exists():
            with open(Path(self.project_root_dir / "deployment_target.json")) as f:
                deployment_target = json.load(f)

        self.vps_ip = questionary.text(
            "IP address of your VPS:",
            default=deployment_target.get('vps_ip') or ''
        ).ask()
        self.ssh_user = questionary.text(
            "SSH username:",
            default=deployment_target.get('ssh_user') or 'root'
        ).ask()
        self.path_to_ssh_key = questionary.text(
            "Path to your private SSH Key:",
            default=deployment_target.get('path_to_ssh_key') or ''
        ).ask()

        self.remote_path = "/root/app" if self.ssh_user == "root" else f"/home/{self.ssh_user}/app"
        self.create_deployment_target_file()


    def handle(self, *args, **kwargs):
        try:
            self.stdout.write("Connecting to VPS...")
            ssh = self.create_ssh_client()

            self.stdout.write(f"Uploading project to [{self.remote_path}]...")
            self.upload_project(ssh)

            self.stdout.write("Checking Docker...")
            self.ensure_docker(ssh)

            self.stdout.write("Launching app...")
            self.launch_docker_compose(ssh)

            ssh.close()
            self.stdout.write(self.style.SUCCESS("✅ Deployment completed!"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ Deployment failed: {e}"))

    def create_deployment_target_file(self):
        with open(self.project_root_dir / "deployment_target.json", "w") as f:
            json.dump({
                "vps_ip": self.vps_ip,
                "ssh_user": self.ssh_user,
                "path_to_ssh_key": self.path_to_ssh_key,
            }, f)

    def create_ssh_client(self):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(self.vps_ip, username=self.ssh_user, key_filename=self.path_to_ssh_key)
        return ssh

    def upload_project(self, ssh):
        from pathlib import Path

        ignore_dirs = {'venv', '.venv', 'env', '.env', '__pycache__'}

        def _scp_recursive(scp, local_path, remote_path):
            local_path = Path(local_path)
            if local_path.name in ignore_dirs:
                return

            if local_path.is_dir():
                try:
                    ssh.exec_command(f"mkdir -p {remote_path}")
                except:
                    pass
                for item in local_path.iterdir():
                    _scp_recursive(scp, item, f"{remote_path}/{item.name}")
            else:
                scp.put(str(local_path), remote_path=remote_path)

        with SCPClient(ssh.get_transport()) as scp:
            _scp_recursive(scp, os.getcwd(), self.remote_path)

    def ensure_docker(self, ssh):
        exit_code, _, _ = self._run_cmd("docker --version", ssh)
        if exit_code != 0:
            self.stdout.write("🚧 Docker not found. Installing...")
            cmds = [
                "apt update",
                "apt install -y docker.io docker-compose"
            ]
            for cmd in cmds:
                self.stdout.write(f"→ {cmd}")
                self._run_cmd(cmd, ssh, check=True)
        else:
            self.stdout.write("✅ Docker already installed.")

    def launch_docker_compose(self, ssh):
        self.stdout.write("🚀 Running `docker compose up -d --force-recreate --renew-anon-volumes --build`...")

        # Test docker compose
        cmds_to_try = [
            f"cd {self.remote_path} && docker compose up -d --force-recreate --renew-anon-volumes --build",
            f"cd {self.remote_path} && docker-compose up -d --force-recreate --renew-anon-volumes --build"
        ]

        fails = ""
        for cmd in cmds_to_try:
            try:
                exit_code, out, err = self._run_cmd(cmd, ssh, check=True)
                self.stdout.write("✅ App started successfully.")
                if out:
                    self.stdout.write(out)
                if err:
                    self.stdout.write(self.style.WARNING(f"⚠️ stderr:\n{err}"))
                return
            except Exception as e:
                fails += f"{cmd}: {e}\n\n"

        raise Exception(f"❌ All docker compose commands failed: \n{fails}")

    @staticmethod
    def _run_cmd(cmd, ssh, check=False):
        stdin, stdout, stderr = ssh.exec_command(cmd)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode()
        err = stderr.read().decode()
        if check and exit_code != 0:
            raise Exception(f"Command failed: {cmd}\nError:\n{err.strip()}")
        return exit_code, out.strip(), err.strip()
