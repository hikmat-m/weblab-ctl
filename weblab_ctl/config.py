"""
Configuration management for weblab-ctl.
Supports YAML config files and environment variable overrides.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class AppConfig:
    """Configuration for a single pentest app."""
    name: str
    hostname: str
    image: str
    container: str
    ports: list[str]
    url: str
    env: dict[str, str] = field(default_factory=dict)
    volumes: list[str] = field(default_factory=list)
    healthcheck: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> AppConfig:
        return cls(
            name=name,
            hostname=data.get("hostname", f"{name}.lab.local"),
            image=data.get("image", ""),
            container=data.get("container", name),
            ports=data.get("ports", []),
            url=data.get("url", f"http://{data.get('hostname', f'{name}.lab.local')}"),
            env=data.get("env", {}),
            volumes=data.get("volumes", []),
            healthcheck=data.get("healthcheck"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "hostname": self.hostname,
            "image": self.image,
            "container": self.container,
            "ports": self.ports,
            "url": self.url,
            "env": self.env,
            "volumes": self.volumes,
            "healthcheck": self.healthcheck,
        }


@dataclass
class LabConfig:
    """Main lab configuration."""
    domain: str = "lab.local"
    network_name: str = "weblab-ctl_network"
    project_label: str = "weblab-ctl"
    apps: dict[str, AppConfig] = field(default_factory=dict)
    hosts_file: str = "/etc/hosts"
    dnsmasq_conf: str = "/etc/dnsmasq.d/weblab-ctl.conf"
    dnsmasq_enabled: bool = True
    compose_file: str | None = None

    @classmethod
    def default(cls, domain: str = "lab.local") -> LabConfig:
        """Create default configuration with built-in apps."""
        apps = {
            "juice-shop": AppConfig(
                name="juice-shop",
                hostname=f"juice.{domain}",
                image="bkimminich/juice-shop:latest",
                container="juice-shop",
                ports=["3000:3000"],
                url=f"http://juice.{domain}",
            ),
            "dvwa": AppConfig(
                name="dvwa",
                hostname=f"dev.{domain}",
                image="vulnerables/web-dvwa:latest",
                container="dvwa",
                ports=["8080:80"],
                url=f"http://dev.{domain}",
            ),
            "webgoat": AppConfig(
                name="webgoat",
                hostname=f"admin.{domain}",
                image="webgoat/goatandwolf:latest",
                container="webgoat",
                ports=["8081:8080", "9090:9090"],
                url=f"http://admin.{domain}/WebGoat",
            ),
            "mutillidae": AppConfig(
                name="mutillidae",
                hostname=f"www.{domain}",
                image="citizenstig/nowasp-mutillidae:latest",
                container="mutillidae",
                ports=["8082:80"],
                url=f"http://www.{domain}",
            ),
        }
        return cls(domain=domain, apps=apps)

    @classmethod
    def from_file(cls, path: Path) -> LabConfig:
        """Load configuration from YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        
        domain = data.get("domain", "lab.local")
        apps = {}
        for name, app_data in data.get("apps", {}).items():
            # Apply domain substitution if hostname uses default pattern
            if "hostname" not in app_data and domain != "lab.local":
                subdomain = app_data.get("subdomain", name)
                app_data["hostname"] = f"{subdomain}.{domain}"
                app_data["url"] = app_data.get("url", f"http://{subdomain}.{domain}")
            apps[name] = AppConfig.from_dict(name, app_data)
        
        return cls(
            domain=domain,
            network_name=data.get("network_name", "weblab-ctl_network"),
            project_label=data.get("project_label", "weblab-ctl"),
            apps=apps,
            hosts_file=data.get("hosts_file", "/etc/hosts"),
            dnsmasq_conf=data.get("dnsmasq_conf", "/etc/dnsmasq.d/weblab-ctl.conf"),
            dnsmasq_enabled=data.get("dnsmasq_enabled", True),
            compose_file=data.get("compose_file"),
        )

    def to_file(self, path: Path) -> None:
        """Save configuration to YAML file."""
        data = {
            "domain": self.domain,
            "network_name": self.network_name,
            "project_label": self.project_label,
            "hosts_file": self.hosts_file,
            "dnsmasq_conf": self.dnsmasq_conf,
            "dnsmasq_enabled": self.dnsmasq_enabled,
            "compose_file": self.compose_file,
            "apps": {name: app.to_dict() for name, app in self.apps.items()},
        }
        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)


DEFAULT_CONFIG_PATHS = [
    Path.cwd() / "weblab-ctl.yml",
    Path.cwd() / "weblab-ctl.yaml",
    Path.home() / ".config" / "weblab-ctl" / "config.yml",
    Path("/etc/weblab-ctl/config.yml"),
]


def load_config(config_path: Path | None = None, domain: str | None = None) -> LabConfig:
    """Load configuration from file or return defaults."""
    if config_path and config_path.exists():
        config = LabConfig.from_file(config_path)
        if domain:
            config.domain = domain
            # Regenerate hostnames with new domain
            config.apps = LabConfig.default(domain).apps
        return config
    
    for path in DEFAULT_CONFIG_PATHS:
        if path.exists():
            config = LabConfig.from_file(path)
            if domain:
                config.domain = domain
                config.apps = LabConfig.default(domain).apps
            return config
    
    return LabConfig.default(domain or "lab.local")


def get_config_dir() -> Path:
    """Get the config directory, creating if needed."""
    config_dir = Path.home() / ".config" / "weblab-ctl"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir