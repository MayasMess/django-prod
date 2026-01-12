import importlib
import json
import os
import time
from pathlib import Path

import paramiko
import questionary
from django.core.management.base import BaseCommand
from scp import SCPClient, SCPException


class Command(BaseCommand):
    help = "Deploy to a VPS with Docker"

    def __init__(self, *args, **options):
        super().__init__(*args, **options)
        self.settings_module = os.environ.get("DJANGO_SETTINGS_MODULE")
        self.project_root_dir = None
        self.vps_ip = None
        self.ssh_user = None
        self.path_to_ssh_key = None
        self.remote_path = None

    def handle(self, *args, **kwargs):
        # Validate settings module
        if not self.settings_module:
            self.stderr.write(self.style.ERROR("DJANGO_SETTINGS_MODULE is not set"))
            return

        try:
            settings_file = Path(importlib.import_module(self.settings_module).__file__)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Could not locate settings module: {e}"))
            return

        self.project_root_dir = settings_file.parent.parent

        # Load saved deployment config
        deployment_target = self._load_deployment_config()

        # Prompt for deployment details
        if not self._prompt_deployment_details(deployment_target):
            self.stdout.write("Deployment cancelled.")
            return

        # Validate inputs
        if not self._validate_inputs():
            return

        self.remote_path = "/root/app" if self.ssh_user == "root" else f"/home/{self.ssh_user}/app"

        # Save config for future deployments
        self._save_deployment_config()

        # Execute deployment
        self._deploy()

    def _load_deployment_config(self) -> dict:
        """Load deployment configuration from file if it exists."""
        config_path = self.project_root_dir / "deployment_target.json"
        if config_path.exists():
            try:
                with open(config_path) as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                self.stderr.write(self.style.WARNING(f"Could not load deployment config: {e}"))
        return {}

    def _prompt_deployment_details(self, defaults: dict) -> bool:
        """Prompt user for deployment details. Returns False if cancelled."""
        self.vps_ip = questionary.text(
            "IP address of your VPS:",
            default=defaults.get("vps_ip", ""),
        ).ask()
        if self.vps_ip is None:
            return False

        self.ssh_user = questionary.text(
            "SSH username:",
            default=defaults.get("ssh_user", "root"),
        ).ask()
        if self.ssh_user is None:
            return False

        self.path_to_ssh_key = questionary.text(
            "Path to your private SSH Key:",
            default=defaults.get("path_to_ssh_key", str(Path.home() / ".ssh" / "id_rsa")),
        ).ask()
        if self.path_to_ssh_key is None:
            return False

        return True

    def _validate_inputs(self) -> bool:
        """Validate user inputs before deployment."""
        errors = []

        if not self.vps_ip or not self.vps_ip.strip():
            errors.append("VPS IP address is required")

        if not self.ssh_user or not self.ssh_user.strip():
            errors.append("SSH username is required")

        if not self.path_to_ssh_key or not self.path_to_ssh_key.strip():
            errors.append("SSH key path is required")
        else:
            key_path = Path(self.path_to_ssh_key).expanduser()
            if not key_path.exists():
                errors.append(f"SSH key not found: {key_path}")
            elif not key_path.is_file():
                errors.append(f"SSH key path is not a file: {key_path}")

        if errors:
            for error in errors:
                self.stderr.write(self.style.ERROR(f"  - {error}"))
            return False

        # Normalize path
        self.path_to_ssh_key = str(Path(self.path_to_ssh_key).expanduser())
        return True

    def _save_deployment_config(self):
        """Save deployment configuration for future use."""
        config_path = self.project_root_dir / "deployment_target.json"
        try:
            with open(config_path, "w") as f:
                json.dump(
                    {
                        "vps_ip": self.vps_ip,
                        "ssh_user": self.ssh_user,
                        "path_to_ssh_key": self.path_to_ssh_key,
                    },
                    f,
                    indent=2,
                )
        except IOError as e:
            self.stderr.write(self.style.WARNING(f"Could not save deployment config: {e}"))

    def _deploy(self):
        """Execute the deployment process."""
        ssh = None
        try:
            # Connect to VPS
            self.stdout.write("Connecting to VPS...")
            ssh = self._create_ssh_client()
            self.stdout.write(self.style.SUCCESS("  Connected."))

            # Upload project
            self.stdout.write(f"Uploading project to {self.remote_path}...")
            self._upload_project(ssh)
            self.stdout.write(self.style.SUCCESS("  Upload complete."))

            # Ensure Docker is installed
            self.stdout.write("Checking Docker installation...")
            self._ensure_docker(ssh)

            # Launch with Docker Compose
            self.stdout.write("Launching application...")
            self._launch_docker_compose(ssh)

            self.stdout.write(self.style.SUCCESS("\nDeployment completed successfully!"))
            self.stdout.write(f"Your app should be available at http://{self.vps_ip}:8000")

        except paramiko.AuthenticationException:
            self.stderr.write(self.style.ERROR("Authentication failed. Check your SSH key and username."))
        except paramiko.SSHException as e:
            self.stderr.write(self.style.ERROR(f"SSH connection error: {e}"))
        except TimeoutError:
            self.stderr.write(self.style.ERROR("Connection timed out. Check VPS IP and network."))
        except SCPException as e:
            self.stderr.write(self.style.ERROR(f"File upload failed: {e}"))
        except DeploymentError as e:
            self.stderr.write(self.style.ERROR(f"Deployment failed: {e}"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Unexpected error: {e}"))
        finally:
            if ssh:
                ssh.close()

    def _create_ssh_client(self) -> paramiko.SSHClient:
        """Create and connect SSH client with timeout."""
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=self.vps_ip,
            username=self.ssh_user,
            key_filename=self.path_to_ssh_key,
            timeout=30,
            banner_timeout=30,
            auth_timeout=30,
        )
        return ssh

    def _upload_project(self, ssh: paramiko.SSHClient):
        """Upload project files to remote server."""
        ignore_patterns = {
            "venv",
            ".venv",
            "env",
            ".env",
            "__pycache__",
            ".git",
            ".idea",
            "node_modules",
            "*.pyc",
            ".DS_Store",
        }

        # Create remote directory
        self._run_command(ssh, f"mkdir -p {self.remote_path}")

        # Collect files to upload
        files_to_upload = []
        for item in self.project_root_dir.rglob("*"):
            # Skip ignored patterns
            if any(ignored in item.parts for ignored in ignore_patterns):
                continue
            if item.is_file():
                relative_path = item.relative_to(self.project_root_dir)
                files_to_upload.append((item, relative_path))

        if not files_to_upload:
            raise DeploymentError("No files to upload")

        # Create all necessary directories first
        directories = set()
        for _, relative_path in files_to_upload:
            if relative_path.parent != Path("."):
                directories.add(str(relative_path.parent))

        if directories:
            # Create all directories in one command
            dir_paths = " ".join(f"{self.remote_path}/{d}" for d in sorted(directories))
            self._run_command(ssh, f"mkdir -p {dir_paths}")

        # Upload files
        total_files = len(files_to_upload)
        with SCPClient(ssh.get_transport()) as scp:
            for i, (local_path, relative_path) in enumerate(files_to_upload, 1):
                remote_file_path = f"{self.remote_path}/{relative_path}"
                try:
                    scp.put(str(local_path), remote_path=remote_file_path)
                    if i % 10 == 0 or i == total_files:
                        self.stdout.write(f"  Uploaded {i}/{total_files} files...")
                except SCPException as e:
                    raise DeploymentError(f"Failed to upload {relative_path}: {e}")

    def _ensure_docker(self, ssh: paramiko.SSHClient):
        """Ensure Docker is installed on the remote server."""
        exit_code, _, _ = self._run_command(ssh, "docker --version", check=False)

        if exit_code == 0:
            self.stdout.write(self.style.SUCCESS("  Docker is already installed."))
            return

        self.stdout.write("  Docker not found. Installing...")

        # Detect package manager and install Docker
        install_commands = [
            # Try official Docker installation script (works on most Linux distros)
            "curl -fsSL https://get.docker.com | sh",
            # Start Docker service
            "systemctl start docker || service docker start",
            # Enable Docker to start on boot
            "systemctl enable docker || true",
        ]

        for cmd in install_commands:
            self.stdout.write(f"    Running: {cmd[:50]}...")
            try:
                self._run_command(ssh, cmd, timeout=300)
            except DeploymentError as e:
                self.stderr.write(self.style.WARNING(f"    Warning: {e}"))

        # Verify installation
        exit_code, version, _ = self._run_command(ssh, "docker --version", check=False)
        if exit_code != 0:
            raise DeploymentError("Failed to install Docker. Please install it manually.")

        self.stdout.write(self.style.SUCCESS(f"  Docker installed: {version}"))

    def _launch_docker_compose(self, ssh: paramiko.SSHClient):
        """Launch the application using Docker Compose."""
        # Check which docker compose command is available
        compose_cmd = self._get_compose_command(ssh)

        self.stdout.write(f"  Using: {compose_cmd}")

        # Build and start containers
        cmd = f"cd {self.remote_path} && {compose_cmd} up -d --build --force-recreate --remove-orphans"

        self.stdout.write("  Building and starting containers (this may take a few minutes)...")
        exit_code, stdout, stderr = self._run_command(ssh, cmd, timeout=600, check=False)

        if exit_code != 0:
            # Show logs for debugging
            self.stderr.write(self.style.ERROR(f"  Docker Compose failed (exit code {exit_code})"))
            if stderr:
                self.stderr.write(f"  Error output:\n{stderr}")

            # Try to get container logs
            self.stdout.write("  Fetching container logs for debugging...")
            _, logs, _ = self._run_command(
                ssh, f"cd {self.remote_path} && {compose_cmd} logs --tail=50", check=False, timeout=30
            )
            if logs:
                self.stdout.write(f"  Container logs:\n{logs}")

            raise DeploymentError("Docker Compose failed to start the application")

        self.stdout.write(self.style.SUCCESS("  Application started successfully."))

        # Show running containers
        _, ps_output, _ = self._run_command(ssh, f"cd {self.remote_path} && {compose_cmd} ps", check=False)
        if ps_output:
            self.stdout.write(f"  Running containers:\n{ps_output}")

    def _get_compose_command(self, ssh: paramiko.SSHClient) -> str:
        """Determine which docker compose command to use."""
        # Try docker compose (v2) first
        exit_code, _, _ = self._run_command(ssh, "docker compose version", check=False)
        if exit_code == 0:
            return "docker compose"

        # Fall back to docker-compose (v1)
        exit_code, _, _ = self._run_command(ssh, "docker-compose --version", check=False)
        if exit_code == 0:
            return "docker-compose"

        raise DeploymentError("Neither 'docker compose' nor 'docker-compose' is available")

    def _run_command(
        self,
        ssh: paramiko.SSHClient,
        cmd: str,
        check: bool = True,
        timeout: int = 120,
    ) -> tuple[int, str, str]:
        """
        Execute a command on the remote server.

        Args:
            ssh: SSH client
            cmd: Command to execute
            check: If True, raise exception on non-zero exit code
            timeout: Command timeout in seconds

        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)

        # Wait for command to complete with timeout
        start_time = time.time()
        while not stdout.channel.exit_status_ready():
            if time.time() - start_time > timeout:
                raise DeploymentError(f"Command timed out after {timeout}s: {cmd[:50]}...")
            time.sleep(0.5)

        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()

        if check and exit_code != 0:
            error_msg = err or out or f"Command failed with exit code {exit_code}"
            raise DeploymentError(f"Command failed: {cmd[:50]}...\n{error_msg}")

        return exit_code, out, err


class DeploymentError(Exception):
    """Custom exception for deployment failures."""

    pass
