"""
Hosts file and dnsmasq management for weblab-ctl.
"""
from __future__ import annotations

import os
from pathlib import Path

from .config import LabConfig

MARKER_START = "# >>> WEBLAB-CTL MANAGED HOSTS >>>"
MARKER_END = "# <<< WEBLAB-CTL MANAGED HOSTS <<<"


class HostsManager:
    """Manages /etc/hosts entries for the pentest lab."""
    
    def __init__(self, config: LabConfig):
        self.config = config
        self.hosts_file = Path(config.hosts_file)
    
    def _read_hosts(self) -> str:
        """Read hosts file content."""
        if self.hosts_file.exists():
            return self.hosts_file.read_text()
        return ""
    
    def _write_hosts(self, content: str) -> bool:
        """Write hosts file content (requires root)."""
        if os.geteuid() != 0:
            return False
        try:
            self.hosts_file.write_text(content)
            return True
        except Exception as e:
            print(f"Error writing hosts file: {e}")
            return False
    
    def _filter_managed_section(self, content: str) -> list[str]:
        """Remove the managed section from hosts content."""
        lines = content.split('\n')
        in_section = False
        result = []
        for line in lines:
            if line.strip() == MARKER_START:
                in_section = True
                continue
            elif line.strip() == MARKER_END:
                in_section = False
                continue
            if not in_section:
                result.append(line)
        return result
    
    def _build_managed_section(self) -> list[str]:
        """Build the managed section lines."""
        lines = [MARKER_START]
        for app in self.config.apps.values():
            lines.append(f"127.0.0.1\t{app.hostname}")
        lines.append(MARKER_END)
        return lines
    
    def add_entries(self) -> bool:
        """Add lab entries to /etc/hosts."""
        if os.geteuid() != 0:
            print("Error: Requires root privileges. Run with sudo.")
            return False
        
        content = self._read_hosts()
        lines = self._filter_managed_section(content)
        lines.extend(self._build_managed_section())
        new_content = '\n'.join(lines).rstrip() + '\n'
        return self._write_hosts(new_content)
    
    def remove_entries(self) -> bool:
        """Remove lab entries from /etc/hosts."""
        if os.geteuid() != 0:
            print("Error: Requires root privileges. Run with sudo.")
            return False
        
        content = self._read_hosts()
        lines = self._filter_managed_section(content)
        new_content = '\n'.join(lines).rstrip() + '\n'
        return self._write_hosts(new_content)
    
    def show_entries(self) -> list[str]:
        """Show current managed entries."""
        content = self._read_hosts()
        lines = content.split('\n')
        in_section = False
        result = []
        for line in lines:
            if line.strip() == MARKER_START:
                in_section = True
                continue
            elif line.strip() == MARKER_END:
                in_section = False
                continue
            if in_section and line.strip():
                result.append(line)
        return result
    
    def has_entries(self) -> bool:
        """Check if managed entries exist."""
        return len(self.show_entries()) > 0


class DnsmasqManager:
    """Manages dnsmasq configuration for local DNS."""
    
    def __init__(self, config: LabConfig):
        self.config = config
        self.dnsmasq_conf = Path(config.dnsmasq_conf)
    
    def _build_config(self) -> str:
        """Build dnsmasq configuration."""
        lines = ["# WebLab-CTL DNS entries"]
        for app in self.config.apps.values():
            lines.append(f"address=/{app.hostname}/127.0.0.1")
        return '\n'.join(lines) + '\n'
    
    def add_config(self) -> bool:
        """Add dnsmasq config and reload."""
        if os.geteuid() != 0:
            print("Error: Requires root privileges. Run with sudo.")
            return False
        
        if not self.config.dnsmasq_enabled:
            return True
        
        try:
            self.dnsmasq_conf.parent.mkdir(parents=True, exist_ok=True)
            self.dnsmasq_conf.write_text(self._build_config())
            self._reload_dnsmasq()
            return True
        except Exception as e:
            print(f"Error writing dnsmasq config: {e}")
            return False
    
    def remove_config(self) -> bool:
        """Remove dnsmasq config and reload."""
        if os.geteuid() != 0:
            print("Error: Requires root privileges. Run with sudo.")
            return False
        
        if not self.config.dnsmasq_enabled:
            return True
        
        try:
            if self.dnsmasq_conf.exists():
                self.dnsmasq_conf.unlink()
            self._reload_dnsmasq()
            return True
        except Exception as e:
            print(f"Error removing dnsmasq config: {e}")
            return False
    
    def show_config(self) -> str:
        """Show current dnsmasq config."""
        if self.dnsmasq_conf.exists():
            return self.dnsmasq_conf.read_text()
        return ""
    
    def has_config(self) -> bool:
        """Check if dnsmasq config exists."""
        return self.dnsmasq_conf.exists()
    
    def _reload_dnsmasq(self) -> None:
        """Reload dnsmasq service."""
        import subprocess
        try:
            subprocess.run(["systemctl", "reload", "dnsmasq"], 
                          check=False, capture_output=True)
        except Exception:
            pass  # Best effort


def create_hosts_manager(config: LabConfig | None = None) -> HostsManager:
    """Factory function to create HostsManager."""
    if config is None:
        config = LabConfig.default()
    return HostsManager(config)


def create_dnsmasq_manager(config: LabConfig | None = None) -> DnsmasqManager:
    """Factory function to create DnsmasqManager."""
    if config is None:
        config = LabConfig.default()
    return DnsmasqManager(config)