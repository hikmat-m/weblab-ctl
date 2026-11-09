"""
Docker operations for weblab-ctl.
Uses the Docker SDK for Python for better reliability.
"""
from __future__ import annotations

from dataclasses import dataclass

import docker
from docker.errors import APIError, NotFound

from .config import AppConfig, LabConfig


@dataclass
class ContainerStatus:
    """Status information for a container."""
    name: str
    container_name: str
    running: bool
    status: str
    ports: dict[str, str]
    image: str


class DockerManager:
    """Manages Docker containers for the weblab-ctl."""
    
    def __init__(self, config: LabConfig):
        self.config = config
        self.client = docker.from_env()
    
    def _get_container(self, name: str) -> docker.models.containers.Container | None:
        """Get container by name, return None if not found."""
        try:
            return self.client.containers.get(name)
        except NotFound:
            return None
    
    def _get_lab_containers(self) -> list[docker.models.containers.Container]:
        """Get all containers with the lab label."""
        filters = {"label": f"{self.config.project_label}=true"}
        return self.client.containers.list(all=True, filters=filters)
    
    def ensure_network(self) -> bool:
        """Create the lab network if it doesn't exist."""
        try:
            self.client.networks.get(self.config.network_name)
            return True
        except NotFound:
            try:
                self.client.networks.create(
                    self.config.network_name,
                    driver="bridge",
                    labels={self.config.project_label: "true"}
                )
                return True
            except APIError as e:
                print(f"Failed to create network: {e}")
                return False
    
    def remove_network(self) -> bool:
        """Remove the lab network."""
        try:
            network = self.client.networks.get(self.config.network_name)
            network.remove()
            return True
        except NotFound:
            return True
        except APIError as e:
            print(f"Failed to remove network: {e}")
            return False
    
    def get_status(self) -> dict[str, ContainerStatus]:
        """Get status of all lab containers."""
        statuses = {}
        for app_name, app in self.config.apps.items():
            container = self._get_container(app.container)
            if container:
                ports = {}
                for port_binding in container.ports.get('HostConfig', {}).get('PortBindings', {}).values():
                    if port_binding:
                        ports[port_binding[0]['HostPort']] = port_binding[0]['HostIp']
                
                statuses[app_name] = ContainerStatus(
                    name=app_name,
                    container_name=app.container,
                    running=container.status == "running",
                    status=container.status,
                    ports=ports,
                    image=container.image.tags[0] if container.image.tags else "unknown",
                )
            else:
                statuses[app_name] = ContainerStatus(
                    name=app_name,
                    container_name=app.container,
                    running=False,
                    status="not_created",
                    ports={},
                    image=app.image,
                )
        return statuses
    
    def pull_image(self, app: AppConfig) -> bool:
        """Pull the container image."""
        try:
            print(f"  Pulling {app.image}...")
            self.client.images.pull(app.image)
            return True
        except APIError as e:
            print(f"  Failed to pull {app.image}: {e}")
            return False
    
    def pull_all(self) -> bool:
        """Pull all images."""
        print("Pulling images...")
        all_ok = True
        for app in self.config.apps.values():
            if not self.pull_image(app):
                all_ok = False
        return all_ok
    
    def start_container(self, app: AppConfig) -> bool:
        """Start or create a single container."""
        container = self._get_container(app.container)
        
        if container and container.status == "running":
            print(f"  {app.name}: already running")
            return True
        
        if container:
            print(f"  {app.name}: starting existing container...")
            try:
                container.start()
                return True
            except APIError as e:
                print(f"  {app.name}: failed to start: {e}")
                return False
        
        print(f"  {app.name}: creating and starting...")
        try:
            port_bindings = {}
            for port_spec in app.ports:
                host_port, container_port = port_spec.split(":")
                port_bindings[f"{container_port}/tcp"] = ("127.0.0.1", int(host_port))
            
            self.client.containers.run(
                app.image,
                name=app.container,
                network=self.config.network_name,
                detach=True,
                ports=port_bindings,
                environment=app.env,
                volumes=app.volumes,
                labels={self.config.project_label: "true"},
                restart_policy={"Name": "unless-stopped"},
            )
            return True
        except APIError as e:
            print(f"  {app.name}: failed to create: {e}")
            return False
    
    def stop_container(self, app: AppConfig) -> bool:
        """Stop a single container."""
        container = self._get_container(app.container)
        if not container:
            print(f"  {app.name}: not found")
            return True
        
        if container.status != "running":
            print(f"  {app.name}: already stopped")
            return True
        
        print(f"  {app.name}: stopping...")
        try:
            container.stop(timeout=10)
            return True
        except APIError as e:
            print(f"  {app.name}: failed to stop: {e}")
            return False
    
    def remove_container(self, app: AppConfig) -> bool:
        """Remove a single container."""
        container = self._get_container(app.container)
        if not container:
            return True
        
        print(f"  {app.name}: removing...")
        try:
            container.remove(force=True)
            return True
        except APIError as e:
            print(f"  {app.name}: failed to remove: {e}")
            return False
    
    def start_all(self) -> bool:
        """Start all containers."""
        print("Starting weblab-ctl...")
        if not self.ensure_network():
            return False
        
        all_ok = True
        for app in self.config.apps.values():
            if not self.start_container(app):
                all_ok = False
        
        return all_ok
    
    def stop_all(self) -> bool:
        """Stop all containers."""
        print("Stopping weblab-ctl containers...")
        all_ok = True
        for app in self.config.apps.values():
            if not self.stop_container(app):
                all_ok = False
        return all_ok
    
    def down_all(self) -> bool:
        """Stop and remove all containers and network."""
        print("Removing weblab-ctl containers...")
        all_ok = True
        for app in self.config.apps.values():
            if not self.remove_container(app):
                all_ok = False
        
        if not self.remove_network():
            all_ok = False
        
        return all_ok
    
    def get_logs(self, app_name: str, follow: bool = False, tail: int = 50) -> str:
        """Get logs for a container."""
        if app_name not in self.config.apps:
            return f"Unknown app: {app_name}"
        
        app = self.config.apps[app_name]
        container = self._get_container(app.container)
        if not container:
            return f"Container {app.container} not found"
        
        try:
            logs = container.logs(tail=tail, follow=follow, timestamps=True)
            return logs.decode("utf-8", errors="replace")
        except APIError as e:
            return f"Failed to get logs: {e}"
    
    def restart_all(self) -> bool:
        """Restart all containers."""
        self.stop_all()
        return self.start_all()


def create_docker_manager(config: LabConfig | None = None) -> DockerManager:
    """Factory function to create DockerManager."""
    if config is None:
        config = LabConfig.default()
    return DockerManager(config)