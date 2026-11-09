"""
Main CLI for weblab-ctl.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import LabConfig, get_config_dir, load_config
from .docker import create_docker_manager
from .hosts import create_dnsmasq_manager, create_hosts_manager


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="weblab-ctl",
        description="Centralized Docker manager for vulnerable web app labs with DNS/hosts automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  weblab-ctl start              # Start all containers, configure hosts & DNS
  weblab-ctl start --domain test.local  # Use custom domain (e.g., juice.test.local)
  weblab-ctl stop               # Stop containers, cleanup hosts & DNS
  weblab-ctl down               # Stop, remove containers & network, cleanup all
  weblab-ctl restart            # Restart all containers
  weblab-ctl status             # Show status of all containers
  weblab-ctl pull               # Pull all container images
  weblab-ctl logs               # Show logs for all running containers
  weblab-ctl logs dvwa          # Follow logs for DVWA
  weblab-ctl hosts add          # Add /etc/hosts entries only (requires sudo)
  weblab-ctl hosts remove       # Remove /etc/hosts entries only (requires sudo)
  weblab-ctl hosts show         # Show current /etc/hosts entries
  weblab-ctl dns add            # Add dnsmasq config only (requires sudo)
  weblab-ctl dns remove         # Remove dnsmasq config only (requires sudo)
  weblab-ctl dns show           # Show current dnsmasq config
  weblab-ctl config init        # Create default config file
  weblab-ctl config show        # Show current configuration

Environment Variables:
  WEBLAB_CTL_CONFIG    Path to config file
  WEBLAB_CTL_NETWORK   Override network name
  WEBLAB_CTL_LABEL     Override project label
  WEBLAB_CTL_DOMAIN    Override base domain (default: lab.local)

For more information, see: https://github.com/hikmat-m/weblab-ctl
        """
    )
    parser.add_argument(
        "-c", "--config",
        type=Path,
        help="Path to config file (default: auto-detect)"
    )
    parser.add_argument(
        "-d", "--domain",
        type=str,
        default=None,
        help="Base domain for app hostnames (default: lab.local, e.g., --domain test.local)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 1.0.0"
    )
    
    subparsers = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")
    
    # start
    subparsers.add_parser("start", help="Start all containers and configure hosts/DNS")
    
    # stop
    subparsers.add_parser("stop", help="Stop all containers, cleanup hosts/DNS (keeps containers)")
    
    # down
    subparsers.add_parser("down", help="Stop, remove containers & network, cleanup everything")
    
    # restart
    subparsers.add_parser("restart", help="Restart all containers")
    
    # status
    subparsers.add_parser("status", help="Show status of all containers, hosts, DNS")
    
    # pull
    subparsers.add_parser("pull", help="Pull all container images")
    
    # logs
    logs_parser = subparsers.add_parser("logs", help="Show container logs")
    logs_parser.add_argument("service", nargs="?", help="Specific service to follow")
    logs_parser.add_argument("-f", "--follow", action="store_true", help="Follow logs")
    logs_parser.add_argument("-n", "--tail", type=int, default=50, help="Number of lines to show")
    
    # hosts
    hosts_parser = subparsers.add_parser("hosts", help="Manage /etc/hosts entries")
    hosts_parser.add_argument("action", choices=["add", "remove", "show"], help="Action to perform")
    
    # dns
    dns_parser = subparsers.add_parser("dns", help="Manage dnsmasq config")
    dns_parser.add_argument("action", choices=["add", "remove", "show"], help="Action to perform")
    
    # config
    config_parser = subparsers.add_parser("config", help="Manage configuration")
    config_parser.add_argument("action", choices=["init", "show", "path"], help="Action to perform")
    config_parser.add_argument("--output", "-o", type=Path, help="Output path for init")
    
    return parser


def get_managers(config: LabConfig):
    """Get all managers for the config."""
    docker_mgr = create_docker_manager(config)
    hosts_mgr = create_hosts_manager(config)
    dns_mgr = create_dnsmasq_manager(config)
    return docker_mgr, hosts_mgr, dns_mgr


def cmd_start(args, config: LabConfig) -> int:
    """Start command."""
    docker_mgr, hosts_mgr, dns_mgr = get_managers(config)
    
    if not docker_mgr.start_all():
        return 1
    
    print("Configuring /etc/hosts...")
    if not hosts_mgr.add_entries():
        return 1
    
    if config.dnsmasq_enabled:
        print("Configuring dnsmasq...")
        if not dns_mgr.add_config():
            return 1
    
    print("\nLab started! Access apps at:")
    for app in config.apps.values():
        print(f"  {app.url}")
    return 0


def cmd_stop(args, config: LabConfig) -> int:
    """Stop command."""
    docker_mgr, hosts_mgr, dns_mgr = get_managers(config)
    
    docker_mgr.stop_all()
    
    print("Cleaning /etc/hosts...")
    hosts_mgr.remove_entries()
    
    if config.dnsmasq_enabled:
        print("Cleaning dnsmasq...")
        dns_mgr.remove_config()
    
    print("Lab stopped.")
    return 0


def cmd_down(args, config: LabConfig) -> int:
    """Down command."""
    docker_mgr, hosts_mgr, dns_mgr = get_managers(config)
    
    if not docker_mgr.down_all():
        return 1
    
    print("Cleaning /etc/hosts...")
    hosts_mgr.remove_entries()
    
    if config.dnsmasq_enabled:
        print("Cleaning dnsmasq...")
        dns_mgr.remove_config()
    
    print("Lab completely removed.")
    return 0


def cmd_restart(args, config: LabConfig) -> int:
    """Restart command."""
    docker_mgr, _, _ = get_managers(config)
    return 0 if docker_mgr.restart_all() else 1


def cmd_status(args, config: LabConfig) -> int:
    """Status command."""
    docker_mgr, hosts_mgr, dns_mgr = get_managers(config)
    
    print("WebLab-CTL Status")
    print("=" * 60)
    
    statuses = docker_mgr.get_status()
    for app_name, app in config.apps.items():
        status = statuses.get(app_name)
        if status:
            icon = "✓" if status.running else "✗"
            print(f"{icon} {app_name:15} ({status.container_name:15}) - {status.status:15} - {app.url}")
        else:
            print(f"✗ {app_name:15} ({app.container:15}) - not_created     - {app.url}")
    
    # Network
    try:
        docker_mgr.client.networks.get(config.network_name)
        net_status = "exists"
    except Exception:
        net_status = "not created"
    print(f"\nNetwork: {net_status} ({config.network_name})")
    
    # Hosts
    print("\n/etc/hosts entries:")
    entries = hosts_mgr.show_entries()
    if entries:
        for entry in entries:
            print(f"  {entry}")
    else:
        print("  (none)")
    
    # DNS
    print("\ndnsmasq config:")
    if dns_mgr.has_config():
        print(f"  {config.dnsmasq_conf} exists")
        if args.verbose:
            print(dns_mgr.show_config())
    else:
        print("  Not configured")
    
    return 0


def cmd_pull(args, config: LabConfig) -> int:
    """Pull command."""
    docker_mgr, _, _ = get_managers(config)
    return 0 if docker_mgr.pull_all() else 1


def cmd_logs(args, config: LabConfig) -> int:
    """Logs command."""
    docker_mgr, _, _ = get_managers(config)
    
    if args.service:
        if args.service not in config.apps:
            print(f"Unknown service: {args.service}")
            print(f"Available: {', '.join(config.apps.keys())}")
            return 1
        logs = docker_mgr.get_logs(args.service, follow=args.follow, tail=args.tail)
        print(logs)
    else:
        # Show logs for all running containers
        statuses = docker_mgr.get_status()
        for app_name, status in statuses.items():
            if status.running:
                print(f"\n=== {app_name} ===")
                logs = docker_mgr.get_logs(app_name, follow=False, tail=args.tail)
                print(logs)
    return 0


def cmd_hosts(args, config: LabConfig) -> int:
    """Hosts command."""
    _, hosts_mgr, _ = get_managers(config)
    
    if args.action == "add":
        if hosts_mgr.add_entries():
            print("Hosts entries added.")
        else:
            return 1
    elif args.action == "remove":
        if hosts_mgr.remove_entries():
            print("Hosts entries removed.")
        else:
            return 1
    elif args.action == "show":
        entries = hosts_mgr.show_entries()
        if entries:
            for entry in entries:
                print(entry)
        else:
            print("No managed entries found.")
    return 0


def cmd_dns(args, config: LabConfig) -> int:
    """DNS command."""
    _, _, dns_mgr = get_managers(config)
    
    if args.action == "add":
        if dns_mgr.add_config():
            print("dnsmasq config added and reloaded.")
        else:
            return 1
    elif args.action == "remove":
        if dns_mgr.remove_config():
            print("dnsmasq config removed and reloaded.")
        else:
            return 1
    elif args.action == "show":
        config_text = dns_mgr.show_config()
        if config_text:
            print(config_text)
        else:
            print("No dnsmasq config found.")
    return 0


def cmd_config(args, config: LabConfig) -> int:
    """Config command."""
    config_dir = get_config_dir()
    
    if args.action == "init":
        output = args.output or config_dir / "config.yml"
        config.to_file(output)
        print(f"Config written to {output}")
    elif args.action == "show":
        import yaml
        print(yaml.dump({
            "domain": config.domain,
            "network_name": config.network_name,
            "project_label": config.project_label,
            "hosts_file": config.hosts_file,
            "dnsmasq_conf": config.dnsmasq_conf,
            "dnsmasq_enabled": config.dnsmasq_enabled,
            "apps": {name: app.to_dict() for name, app in config.apps.items()},
        }, default_flow_style=False, sort_keys=False))
    elif args.action == "path":
        print(config_dir / "config.yml")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args(argv)
    
    # Load config
    config = load_config(args.config, domain=args.domain)
    
    # Apply environment variable overrides
    import os
    if os.getenv("WEBLAB_CTL_NETWORK"):
        config.network_name = os.getenv("WEBLAB_CTL_NETWORK")
    if os.getenv("WEBLAB_CTL_LABEL"):
        config.project_label = os.getenv("WEBLAB_CTL_LABEL")
    if os.getenv("WEBLAB_CTL_DOMAIN"):
        config.domain = os.getenv("WEBLAB_CTL_DOMAIN")
        config.apps = LabConfig.default(config.domain).apps
    
    # Command dispatch
    commands = {
        "start": cmd_start,
        "stop": cmd_stop,
        "down": cmd_down,
        "restart": cmd_restart,
        "status": cmd_status,
        "pull": cmd_pull,
        "logs": cmd_logs,
        "hosts": cmd_hosts,
        "dns": cmd_dns,
        "config": cmd_config,
    }
    
    if args.command not in commands:
        parser.print_help()
        return 1
    
    try:
        return commands[args.command](args, config)
    except KeyboardInterrupt:
        print("\nInterrupted")
        return 130
    except Exception as e:
        if args.verbose:
            import traceback
            traceback.print_exc()
        else:
            print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())