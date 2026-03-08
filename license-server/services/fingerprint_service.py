"""
HostingSignal License Server — Fingerprint Service
Validates server hardware fingerprints for license binding.
"""
import hashlib
from typing import Optional

from utils.crypto import hash_fingerprint


# Fingerprint fields and their weights for similarity scoring
FINGERPRINT_FIELDS = {
    "cpu_id": 3,       # High weight — CPU rarely changes
    "machine_id": 3,   # High weight — system machine ID
    "disk_uuid": 2,    # Medium weight — disk can be replaced
    "mac_address": 2,  # Medium weight — NIC can change
    "hostname": 1,     # Low weight — hostname changes easily
}


def compute_fingerprint_hash(
    cpu_id: str = "",
    disk_uuid: str = "",
    mac_address: str = "",
    hostname: str = "",
    machine_id: str = "",
) -> str:
    """Compute a SHA-256 hash of the combined hardware fingerprint."""
    return hash_fingerprint(cpu_id, disk_uuid, mac_address, hostname, machine_id)


def compute_similarity_score(
    stored: dict,
    incoming: dict,
) -> float:
    """
    Compute a weighted similarity score between stored and incoming fingerprints.
    Returns a score between 0.0 (completely different) and 1.0 (identical).
    """
    total_weight = sum(FINGERPRINT_FIELDS.values())
    matching_weight = 0

    for field, weight in FINGERPRINT_FIELDS.items():
        stored_val = stored.get(field, "").strip().lower()
        incoming_val = incoming.get(field, "").strip().lower()
        if stored_val and incoming_val and stored_val == incoming_val:
            matching_weight += weight

    return matching_weight / total_weight if total_weight > 0 else 0.0


def validate_fingerprint_match(
    stored: dict,
    incoming: dict,
    tolerance: int = 2,
) -> tuple[bool, float, list]:
    """
    Validate if an incoming fingerprint matches the stored one.
    
    Args:
        stored: Dict of stored fingerprint values
        incoming: Dict of incoming fingerprint values  
        tolerance: Max number of fields that can differ
    
    Returns:
        Tuple of (is_valid, similarity_score, mismatched_fields)
    """
    mismatched = []

    for field in FINGERPRINT_FIELDS:
        stored_val = stored.get(field, "").strip().lower()
        incoming_val = incoming.get(field, "").strip().lower()
        if stored_val and incoming_val and stored_val != incoming_val:
            mismatched.append(field)

    similarity = compute_similarity_score(stored, incoming)
    is_valid = len(mismatched) <= tolerance

    return is_valid, similarity, mismatched


def collect_fingerprint_from_request(data: dict) -> dict:
    """Extract fingerprint fields from a request body."""
    return {
        "cpu_id": data.get("cpu_id", ""),
        "disk_uuid": data.get("disk_uuid", ""),
        "mac_address": data.get("mac_address", ""),
        "hostname": data.get("hostname", ""),
        "machine_id": data.get("machine_id", ""),
    }


# Shell commands to collect fingerprint on Linux servers
FINGERPRINT_COLLECTION_SCRIPT = """#!/bin/bash
# HostingSignal Server Fingerprint Collector
# Collects hardware identifiers for license validation

# CPU ID (from /proc/cpuinfo)
CPU_ID=$(cat /proc/cpuinfo | grep -m1 "model name" | awk -F: '{print $2}' | xargs)
if [ -z "$CPU_ID" ]; then
    CPU_ID=$(dmidecode -t processor 2>/dev/null | grep -m1 "ID:" | awk -F: '{print $2}' | xargs)
fi

# Disk UUID (root partition)
DISK_UUID=$(blkid -s UUID -o value $(df / | tail -1 | awk '{print $1}') 2>/dev/null)
if [ -z "$DISK_UUID" ]; then
    DISK_UUID=$(ls -la /dev/disk/by-uuid/ 2>/dev/null | head -2 | tail -1 | awk '{print $9}')
fi

# MAC Address (primary interface)
MAC_ADDRESS=$(ip link show $(ip route show default | awk '{print $5}' | head -1) 2>/dev/null | grep ether | awk '{print $2}')
if [ -z "$MAC_ADDRESS" ]; then
    MAC_ADDRESS=$(cat /sys/class/net/$(ls /sys/class/net/ | grep -v lo | head -1)/address 2>/dev/null)
fi

# Hostname
HOSTNAME_VAL=$(hostname -f 2>/dev/null || hostname)

# Machine ID
MACHINE_ID=$(cat /etc/machine-id 2>/dev/null)
if [ -z "$MACHINE_ID" ]; then
    MACHINE_ID=$(cat /var/lib/dbus/machine-id 2>/dev/null)
fi

echo "{\"cpu_id\": \"$CPU_ID\", \"disk_uuid\": \"$DISK_UUID\", \"mac_address\": \"$MAC_ADDRESS\", \"hostname\": \"$HOSTNAME_VAL\", \"machine_id\": \"$MACHINE_ID\"}"
"""
