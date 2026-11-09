import os
import tempfile
from pathlib import Path

import pytest

from weblab_ctl.config import AppConfig, LabConfig
from weblab_ctl.hosts import MARKER_END, MARKER_START, DnsmasqManager, HostsManager


class TestAppConfig:
    def test_from_dict(self):
        data = {
            "hostname": "test.local",
            "image": "test:latest",
            "container": "test",
            "ports": ["8080:80"],
            "url": "http://test.local",
        }
        app = AppConfig.from_dict("test", data)
        assert app.name == "test"
        assert app.hostname == "test.local"
        assert app.image == "test:latest"
        assert app.ports == ["8080:80"]
    
    def test_to_dict(self):
        app = AppConfig(
            name="test",
            hostname="test.local",
            image="test:latest",
            container="test",
            ports=["8080:80"],
            url="http://test.local",
        )
        data = app.to_dict()
        assert data["hostname"] == "test.local"
        assert data["image"] == "test:latest"


class TestLabConfig:
    def test_default(self):
        config = LabConfig.default()
        assert len(config.apps) == 4
        assert "juice-shop" in config.apps
        assert "dvwa" in config.apps
        assert "webgoat" in config.apps
        assert "mutillidae" in config.apps
        assert config.domain == "lab.local"
        assert config.network_name == "weblab-ctl_network"
        assert config.project_label == "weblab-ctl"
    
    def test_default_custom_domain(self):
        config = LabConfig.default(domain="test.local")
        assert config.domain == "test.local"
        assert config.apps["juice-shop"].hostname == "juice.test.local"
        assert config.apps["dvwa"].hostname == "dev.test.local"
        assert config.apps["webgoat"].hostname == "admin.test.local"
        assert config.apps["mutillidae"].hostname == "www.test.local"
    
    def test_to_from_file(self):
        config = LabConfig.default()
        with tempfile.NamedTemporaryFile(suffix=".yml", delete=False) as f:
            temp_path = Path(f.name)
        try:
            config.to_file(temp_path)
            loaded = LabConfig.from_file(temp_path)
            assert loaded.network_name == config.network_name
            assert loaded.domain == config.domain
            assert len(loaded.apps) == len(config.apps)
        finally:
            temp_path.unlink()


class TestHostsManager:
    def test_build_section(self):
        config = LabConfig.default()
        manager = HostsManager(config)
        lines = manager._build_managed_section()
        assert lines[0] == MARKER_START
        assert lines[-1] == MARKER_END
        assert len(lines) == 6  # start + 4 apps + end
    
    def test_filter_section(self):
        content = f"""127.0.0.1 localhost
{MARKER_START}
127.0.0.1 test.local
{MARKER_END}
127.0.0.1 other.local"""
        config = LabConfig.default()
        manager = HostsManager(config)
        lines = manager._filter_managed_section(content)
        assert "127.0.0.1 localhost" in lines
        assert "127.0.0.1 other.local" in lines
        assert "test.local" not in '\n'.join(lines)


class TestDnsmasqManager:
    def test_build_config(self):
        config = LabConfig.default()
        manager = DnsmasqManager(config)
        conf = manager._build_config()
        assert "juice.lab.local" in conf
        assert "dev.lab.local" in conf
        assert "admin.lab.local" in conf
        assert "www.lab.local" in conf
        assert "address=/" in conf
        assert "WebLab-CTL" in conf


if __name__ == "__main__":
    pytest.main([__file__, "-v"])