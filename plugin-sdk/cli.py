#!/usr/bin/env python3
"""
HostingSignal Plugin SDK CLI — Scaffolding tool for developing plugins.
Usage:
    python cli.py init <plugin-name>
    python cli.py validate <plugin-dir>
    python cli.py package <plugin-dir>
"""
import os
import sys
import json
import shutil
import tarfile
import hashlib
import argparse
from datetime import datetime

MANIFEST_TEMPLATE = {
    "name": "",
    "version": "1.0.0",
    "description": "",
    "author": "",
    "category": "utility",
    "min_panel_version": "1.0.0",
    "entry_point": "main.py",
    "hooks": [],
    "ui_extensions": [],
    "api_routes": [],
    "permissions": [],
    "dependencies": []
}

MAIN_PY_TEMPLATE = '''"""
{name} — HostingSignal Panel Plugin
{description}
"""
import logging

logger = logging.getLogger("plugin.{slug}")


def register_hooks(event_bus):
    """Called when the plugin is loaded. Register your event handlers here."""
    # event_bus.on("website.created", on_website_created, plugin_name="{slug}")
    logger.info("{name} plugin registered")


# def on_website_created(data):
#     """Example handler — runs when a new website is created."""
#     domain = data.get("domain", "")
#     logger.info(f"New website created: {{domain}}")


def cleanup():
    """Called when the plugin is unloaded. Clean up resources here."""
    logger.info("{name} plugin unloaded")
'''

README_TEMPLATE = '''# {name}

{description}

## Installation

```bash
hsctl plugin install {slug}
```

## Configuration

Add configuration details here.

## Hooks

This plugin listens for the following events:
- (add your hooks here)

## API Routes

- (add your API routes here)

## License

MIT
'''

AVAILABLE_HOOKS = [
    "panel.startup", "panel.shutdown",
    "website.created", "website.deleted", "website.ssl_issued",
    "database.created", "database.deleted",
    "email.account_created",
    "backup.started", "backup.completed",
    "security.alert",
    "user.login", "user.logout",
    "license.validated", "update.available",
    "cron.minutely", "cron.hourly", "cron.daily",
    "plugin.activated", "plugin.deactivated",
]

CATEGORIES = ["security", "backup", "email", "analytics", "optimization", "monitoring", "utility", "integration"]


def init_plugin(args):
    """Scaffold a new plugin project."""
    name = args.name
    slug = name.lower().replace(" ", "_").replace("-", "_")
    plugin_dir = os.path.join(os.getcwd(), name)

    if os.path.exists(plugin_dir):
        print(f"Error: Directory '{name}' already exists")
        sys.exit(1)

    os.makedirs(plugin_dir)
    os.makedirs(os.path.join(plugin_dir, "templates"), exist_ok=True)

    # Create manifest.json
    manifest = {**MANIFEST_TEMPLATE}
    manifest["name"] = slug
    manifest["description"] = f"{name} plugin for HostingSignal Panel"
    manifest["author"] = args.author or os.environ.get("USER", "developer")

    with open(os.path.join(plugin_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    # Create main.py
    with open(os.path.join(plugin_dir, "main.py"), "w") as f:
        f.write(MAIN_PY_TEMPLATE.format(
            name=name, slug=slug,
            description=f"{name} plugin for HostingSignal Panel"
        ))

    # Create README.md
    with open(os.path.join(plugin_dir, "README.md"), "w") as f:
        f.write(README_TEMPLATE.format(
            name=name, slug=slug,
            description=f"{name} plugin for HostingSignal Panel"
        ))

    print(f"✅ Plugin '{name}' created at: {plugin_dir}")
    print(f"   📄 manifest.json")
    print(f"   🐍 main.py")
    print(f"   📖 README.md")
    print(f"   📁 templates/")
    print(f"\nNext steps:")
    print(f"  1. Edit manifest.json to add hooks, UI extensions, and API routes")
    print(f"  2. Implement your plugin logic in main.py")
    print(f"  3. Run: python cli.py validate {name}")
    print(f"  4. Run: python cli.py package {name}")


def validate_plugin(args):
    """Validate a plugin's manifest and structure."""
    plugin_dir = args.path
    errors = []

    if not os.path.isdir(plugin_dir):
        print(f"Error: '{plugin_dir}' is not a directory")
        sys.exit(1)

    manifest_path = os.path.join(plugin_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        errors.append("Missing manifest.json")
    else:
        try:
            with open(manifest_path) as f:
                manifest = json.load(f)

            for field in ["name", "version", "entry_point"]:
                if field not in manifest:
                    errors.append(f"Missing required field: {field}")

            if "category" in manifest and manifest["category"] not in CATEGORIES:
                errors.append(f"Invalid category: {manifest['category']}. Must be one of: {', '.join(CATEGORIES)}")

            entry_point = manifest.get("entry_point", "main.py")
            if not os.path.exists(os.path.join(plugin_dir, entry_point)):
                errors.append(f"Entry point not found: {entry_point}")

            for hook in manifest.get("hooks", []):
                if hook not in AVAILABLE_HOOKS:
                    errors.append(f"Unknown hook: {hook}")

        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON in manifest.json: {e}")

    if errors:
        print(f"❌ Validation failed for '{plugin_dir}':")
        for err in errors:
            print(f"   • {err}")
        sys.exit(1)
    else:
        print(f"✅ Plugin '{plugin_dir}' is valid!")


def package_plugin(args):
    """Package a plugin into a distributable tar.gz archive."""
    plugin_dir = args.path
    if not os.path.isdir(plugin_dir):
        print(f"Error: '{plugin_dir}' is not a directory")
        sys.exit(1)

    manifest_path = os.path.join(plugin_dir, "manifest.json")
    with open(manifest_path) as f:
        manifest = json.load(f)

    slug = manifest["name"]
    version = manifest["version"]
    output_file = f"{slug}-{version}.tar.gz"

    with tarfile.open(output_file, "w:gz") as tar:
        tar.add(plugin_dir, arcname=slug)

    file_hash = hashlib.sha256(open(output_file, "rb").read()).hexdigest()
    file_size = os.path.getsize(output_file)

    print(f"✅ Plugin packaged: {output_file}")
    print(f"   📦 Size: {file_size / 1024:.1f} KB")
    print(f"   🔒 SHA256: {file_hash}")
    print(f"\nTo install: hsctl plugin install {output_file}")


def main():
    parser = argparse.ArgumentParser(description="HostingSignal Plugin SDK CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # init
    init_parser = subparsers.add_parser("init", help="Create a new plugin project")
    init_parser.add_argument("name", help="Plugin name")
    init_parser.add_argument("--author", "-a", help="Plugin author", default="")

    # validate
    validate_parser = subparsers.add_parser("validate", help="Validate a plugin")
    validate_parser.add_argument("path", help="Path to plugin directory")

    # package
    package_parser = subparsers.add_parser("package", help="Package plugin for distribution")
    package_parser.add_argument("path", help="Path to plugin directory")

    args = parser.parse_args()

    if args.command == "init":
        init_plugin(args)
    elif args.command == "validate":
        validate_plugin(args)
    elif args.command == "package":
        package_plugin(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
