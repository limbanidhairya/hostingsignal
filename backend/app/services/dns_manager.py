"""
HostingSignal — PowerDNS Manager
DNS zone and record management via PowerDNS API or direct database access.
"""
from .server_utils import run_cmd, write_file, read_file, DEV_MODE, logger, get_server_ip
import json

PDNS_API_URL = "http://127.0.0.1:8081/api/v1"
PDNS_API_KEY = "hostingsignal-pdns-key"  # Set during install

# Demo data
DEMO_ZONES = [
    {
        "domain": "example.com",
        "records": [
            {"name": "example.com", "type": "A", "content": "192.168.1.100", "ttl": 3600},
            {"name": "example.com", "type": "MX", "content": "10 mail.example.com", "ttl": 3600},
            {"name": "www.example.com", "type": "CNAME", "content": "example.com", "ttl": 3600},
            {"name": "mail.example.com", "type": "A", "content": "192.168.1.100", "ttl": 3600},
            {"name": "example.com", "type": "TXT", "content": "v=spf1 mx ~all", "ttl": 3600},
            {"name": "example.com", "type": "NS", "content": "ns1.hostingsignal.com", "ttl": 86400},
            {"name": "example.com", "type": "NS", "content": "ns2.hostingsignal.com", "ttl": 86400},
        ],
    },
]


def _pdns_request(method: str, path: str, data: dict | None = None) -> dict:
    """Make a request to the PowerDNS API."""
    if DEV_MODE:
        logger.info(f"[DEV] PDNS {method} {path}")
        return {"status": "ok", "dev_mode": True}
    payload = f"-d '{json.dumps(data)}'" if data else ""
    result = run_cmd(
        f"curl -s -X {method} -H 'X-API-Key: {PDNS_API_KEY}' "
        f"-H 'Content-Type: application/json' {payload} "
        f"'{PDNS_API_URL}{path}'"
    )
    if result.success and result.stdout:
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return {"raw": result.stdout}
    return {"error": result.stderr}


def list_zones() -> list[dict]:
    """List all DNS zones."""
    if DEV_MODE:
        return DEMO_ZONES
    result = _pdns_request("GET", "/servers/localhost/zones")
    if isinstance(result, list):
        return [{"domain": z.get("name", "").rstrip("."), "records": []} for z in result]
    return []


def get_zone(domain: str) -> dict | None:
    """Get zone details with all records."""
    if DEV_MODE:
        for z in DEMO_ZONES:
            if z["domain"] == domain:
                return z
        return None
    result = _pdns_request("GET", f"/servers/localhost/zones/{domain}.")
    if "error" in result:
        return None
    records = []
    for rrset in result.get("rrsets", []):
        for rec in rrset.get("records", []):
            records.append({
                "name": rrset["name"].rstrip("."),
                "type": rrset["type"],
                "content": rec["content"],
                "ttl": rrset.get("ttl", 3600),
            })
    return {"domain": domain, "records": records}


def create_zone(domain: str) -> dict:
    """Create a new DNS zone with default records."""
    server_ip = get_server_ip()
    zone_data = {
        "name": f"{domain}.",
        "kind": "Native",
        "nameservers": [f"ns1.hostingsignal.com.", f"ns2.hostingsignal.com."],
        "rrsets": [
            {
                "name": f"{domain}.",
                "type": "A",
                "ttl": 3600,
                "changetype": "REPLACE",
                "records": [{"content": server_ip, "disabled": False}],
            },
            {
                "name": f"www.{domain}.",
                "type": "CNAME",
                "ttl": 3600,
                "changetype": "REPLACE",
                "records": [{"content": f"{domain}.", "disabled": False}],
            },
            {
                "name": f"mail.{domain}.",
                "type": "A",
                "ttl": 3600,
                "changetype": "REPLACE",
                "records": [{"content": server_ip, "disabled": False}],
            },
            {
                "name": f"{domain}.",
                "type": "MX",
                "ttl": 3600,
                "changetype": "REPLACE",
                "records": [{"content": f"10 mail.{domain}.", "disabled": False}],
            },
            {
                "name": f"{domain}.",
                "type": "TXT",
                "ttl": 3600,
                "changetype": "REPLACE",
                "records": [{"content": '"v=spf1 mx ~all"', "disabled": False}],
            },
        ],
    }
    result = _pdns_request("POST", "/servers/localhost/zones", zone_data)
    return {"domain": domain, "status": "created", "result": result}


def add_record(domain: str, name: str, record_type: str, content: str, ttl: int = 3600) -> dict:
    """Add a DNS record to a zone."""
    rrset = {
        "rrsets": [{
            "name": f"{name}." if not name.endswith(".") else name,
            "type": record_type.upper(),
            "ttl": ttl,
            "changetype": "REPLACE",
            "records": [{"content": content, "disabled": False}],
        }]
    }
    result = _pdns_request("PATCH", f"/servers/localhost/zones/{domain}.", rrset)
    return {"status": "added", "record": {"name": name, "type": record_type, "content": content, "ttl": ttl}}


def delete_record(domain: str, name: str, record_type: str) -> dict:
    """Delete a DNS record from a zone."""
    rrset = {
        "rrsets": [{
            "name": f"{name}." if not name.endswith(".") else name,
            "type": record_type.upper(),
            "changetype": "DELETE",
            "records": [],
        }]
    }
    result = _pdns_request("PATCH", f"/servers/localhost/zones/{domain}.", rrset)
    return {"status": "deleted"}


def delete_zone(domain: str) -> dict:
    """Delete an entire DNS zone."""
    result = _pdns_request("DELETE", f"/servers/localhost/zones/{domain}.")
    return {"status": "deleted", "domain": domain}
