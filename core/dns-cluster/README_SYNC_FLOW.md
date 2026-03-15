# DNS Cluster Sync Flow

1. Zone create/update/delete enters queue.
2. Master updates zone in PowerDNS/BIND.
3. Replication worker syncs to slave nodes from configs/dns-cluster.yaml.
4. Health monitor checks slave propagation and raises alert on drift.
