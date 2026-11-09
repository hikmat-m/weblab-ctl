# weblab-ctl

[![PyPI version](https://img.shields.io/pypi/v/weblab-ctl.svg)](https://pypi.org/project/weblab-ctl/)
[![Python versions](https://img.shields.io/pypi/pyversions/weblab-ctl.svg)](https://pypi.org/project/weblab-ctl/)
[![License](https://img.shields.io/pypi/l/weblab-ctl.svg)](https://opensource.org/licenses/MIT)

**Centralized Docker manager for vulnerable web app labs with automatic DNS and hosts file configuration.**

Perfect for security practitioners who want to quickly spin up vulnerable web applications for testing without manually managing containers, ports, and DNS entries.

## Features

- 🐳 **Docker-native** - Uses Docker SDK for reliable container management
- 🌐 **Auto DNS** - Configures `/etc/hosts` and `dnsmasq` for local domains
- ⚡ **Resource efficient** - Start/stop labs on demand, no idle resources
- 🔧 **Configurable** - YAML config for custom apps, ports, images, and domains
- 📦 **Portable** - Single binary install via pipx, works on Linux/macOS
- 🛡 **Secure** - Runs containers on localhost only, isolated network

## Quick Start

```bash
# Install
pipx install weblab-ctl

# Pull images (first time only)
weblab-ctl pull

# Start lab (requires sudo for hosts/DNS)
sudo weblab-ctl start

# Or with a custom domain
sudo weblab-ctl start --domain test.local

# Check status
weblab-ctl status

# Access apps (default domain: lab.local):
#   Juice Shop      → http://juice.lab.local
#   DVWA            → http://dev.lab.local  
#   WebGoat         → http://admin.lab.local/WebGoat
#   Mutillidae II   → http://www.lab.local

# Stop when done (saves resources)
sudo weblab-ctl stop

# Or fully remove
sudo weblab-ctl down
```

## Default Apps

| App | Hostname (default) | URL | Ports | Description |
|-----|-------------------|-----|-------|-------------|
| **Juice Shop** | `juice.lab.local` | http://juice.lab.local | 3000 | Modern OWASP Juice Shop |
| **DVWA** | `dev.lab.local` | http://dev.lab.local | 8080 | Damn Vulnerable Web App |
| **WebGoat** | `admin.lab.local` | http://admin.lab.local/WebGoat | 8081, 9090 | OWASP WebGoat |
| **Mutillidae II** | `www.lab.local` | http://www.lab.local | 8082 | NOWASP Mutillidae |

## Commands

```bash
weblab-ctl start           # Start all + configure hosts/DNS
weblab-ctl start -d test.local  # Use custom domain
weblab-ctl stop            # Stop containers, cleanup hosts/DNS
weblab-ctl down            # Remove containers, network, cleanup all
weblab-ctl restart         # Restart all containers
weblab-ctl status          # Show container status, hosts, DNS
weblab-ctl pull            # Pull all container images
weblab-ctl logs            # Show logs for all running
weblab-ctl logs dvwa       # Follow DVWA logs
weblab-ctl hosts add       # Add /etc/hosts entries (sudo)
weblab-ctl hosts remove    # Remove /etc/hosts entries (sudo)
weblab-ctl hosts show      # Show current entries
weblab-ctl dns add         # Add dnsmasq config (sudo)
weblab-ctl dns remove      # Remove dnsmasq config (sudo)
weblab-ctl dns show        # Show current config
weblab-ctl config init     # Create default config file
weblab-ctl config show     # Show current configuration
```

## Requirements

- **Docker** - Installed and running
- **User in docker group** OR run docker commands with sudo
- **sudo** - Required for `/etc/hosts` and `dnsmasq` management
- **dnsmasq** (optional) - For local DNS resolution of `*.lab.local` (or your custom domain)

### Install dnsmasq (optional, for full DNS)

```bash
# Debian/Ubuntu/Kali
sudo apt-get install dnsmasq
sudo systemctl enable --now dnsmasq

# macOS
brew install dnsmasq
sudo brew services start dnsmasq

# Arch
sudo pacman -S dnsmasq
sudo systemctl enable --now dnsmasq
```

## Configuration

Create a custom config:

```bash
weblab-ctl config init
# Creates ~/.config/weblab-ctl/config.yml
```

Edit `~/.config/weblab-ctl/config.yml`:

```yaml
domain: "test.local"  # Custom domain for all apps
network_name: "weblab-ctl_network"
project_label: "weblab-ctl"
hosts_file: "/etc/hosts"
dnsmasq_conf: "/etc/dnsmasq.d/weblab-ctl.conf"
dnsmasq_enabled: true

apps:
  juice-shop:
    hostname: "juice.test.local"
    image: "bkimminich/juice-shop:latest"
    container: "juice-shop"
    ports: ["3000:3000"]
    url: "http://juice.test.local"

  dvwa:
    hostname: "dev.test.local"
    image: "vulnerables/web-dvwa:latest"
    container: "dvwa"
    ports: ["8080:80"]
    url: "http://dev.test.local"

  # Add your own apps!
  custom-app:
    hostname: "custom.test.local"
    image: "myorg/myapp:latest"
    container: "custom-app"
    ports: ["8083:80"]
    url: "http://custom.test.local"
    env:
      ENV_VAR: "value"
    volumes:
      - "/host/path:/container/path"
```

## Environment Variables

```bash
WEBLAB_CTL_CONFIG    # Path to config file
WEBLAB_CTL_NETWORK   # Override network name
WEBLAB_CTL_LABEL     # Override project label
WEBLAB_CTL_DOMAIN    # Override base domain (default: lab.local)
```

## Why weblab-ctl?

| Manual Approach | weblab-ctl |
|----------------|------------|
| `docker run` x4 with ports | `weblab-ctl start` |
| Edit `/etc/hosts` manually | Automatic |
| Configure dnsmasq manually | Automatic |
| Remember ports/URLs | `weblab-ctl status` |
| Cleanup requires multiple commands | `weblab-ctl down` |
| Hard to share setup | Commit `config.yml` to git |

## Development

```bash
# Clone
git clone https://github.com/hikmat-m/weblab-ctl
cd weblab-ctl

# Install in dev mode
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check .
mypy weblab_ctl
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a PR

## Related Projects

- [OWASP Juice Shop](https://github.com/juice-shop/juice-shop)
- [DVWA](https://github.com/digininja/DVWA)
- [WebGoat](https://github.com/WebGoat/WebGoat)
- [Mutillidae](https://github.com/webpwnized/mutillidae)