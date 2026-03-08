# HostingSignal Plugin SDK

Build plugins for the HostingSignal Panel.

## Quick Start

```bash
mkdir my-plugin && cd my-plugin
hsctl plugin init my-plugin
```

## Plugin Structure

```
my-plugin/
├── manifest.json     # Plugin metadata, hooks, UI extensions, API routes
├── main.py           # Entry point — must export register_hooks(event_bus)
├── templates/        # Optional UI templates
└── README.md
```

## manifest.json

```json
{
  "name": "my_plugin",
  "version": "1.0.0",
  "description": "My awesome plugin",
  "author": "Your Name",
  "category": "utility",
  "min_panel_version": "1.0.0",
  "entry_point": "main.py",
  "hooks": ["website.created", "cron.daily"],
  "ui_extensions": [],
  "api_routes": [],
  "permissions": [],
  "dependencies": []
}
```

## Available Hooks

| Hook | Trigger |
|---|---|
| `panel.startup` | Panel starts |
| `panel.shutdown` | Panel stops |
| `website.created` | New website created |
| `website.deleted` | Website deleted |
| `website.ssl_issued` | SSL certificate issued |
| `database.created` | Database created |
| `database.deleted` | Database deleted |
| `email.account_created` | Email account created |
| `backup.started` | Backup job started |
| `backup.completed` | Backup completed |
| `security.alert` | Security alert triggered |
| `user.login` | User logs in |
| `user.logout` | User logs out |
| `license.validated` | License validated |
| `update.available` | Panel update available |
| `cron.minutely` | Every minute |
| `cron.hourly` | Every hour |
| `cron.daily` | Every day |

## Entry Point (main.py)

```python
def register_hooks(event_bus):
    """Called when plugin is loaded."""
    event_bus.on("website.created", on_website_created)

def on_website_created(data):
    domain = data.get("domain")
    print(f"New website: {domain}")

def cleanup():
    """Called when plugin is unloaded."""
    pass
```

## UI Extensions

Add sidebar items, dashboard widgets, or settings panels:

```json
{
  "ui_extensions": [
    {"type": "sidebar_item", "label": "My Plugin", "icon": "🔌", "route": "/plugins/my-plugin"},
    {"type": "dashboard_widget", "label": "My Widget", "component": "MyWidget"}
  ]
}
```

## API Routes

Register custom API endpoints:

```json
{
  "api_routes": [
    {"method": "GET", "path": "/api/plugins/my-plugin/data", "handler": "get_data"}
  ]
}
```

## CLI Installation

```bash
# Install from marketplace
hsctl plugin install my-plugin

# Install from local archive
hsctl plugin install /path/to/my-plugin.tar.gz

# Remove
hsctl plugin remove my-plugin

# List installed
hsctl plugin list
```

## Categories

- `security` — Security scanning, firewall rules
- `backup` — Backup providers, strategies
- `email` — Email management extensions
- `analytics` — Usage analytics, reporting
- `optimization` — Caching, performance
- `monitoring` — Custom metrics, alerting
- `utility` — General utilities
