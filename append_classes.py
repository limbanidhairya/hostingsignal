import os

base = r"c:\Users\Dhairya Limbani\OneDrive\Documents\Hostingsignal\backend\app\services"

files_to_append = {
    "dns_manager.py": """
class DNSManager:
    def list_zones(self): return list_zones()
    def get_zone(self, domain): return get_zone(domain)
    def create_zone(self, domain): return create_zone(domain)
    def add_record(self, domain, name, record_type, content, ttl=3600): return add_record(domain, name, record_type, content, ttl)
    def delete_record(self, domain, name, record_type): return delete_record(domain, name, record_type)
    def delete_zone(self, domain): return delete_zone(domain)
""",
    "database_manager.py": """
class DatabaseManager:
    def list_databases(self): return list_databases()
    def create_database(self, db_name, username=None, password=None): return create_database(db_name, username, password)
    def delete_database(self, db_name, drop_user=None): return delete_database(db_name, drop_user)
    def create_user(self, username, password, db_name=None): return create_user(username, password, db_name)
    def delete_user(self, username): return delete_user(username)
    def change_user_password(self, username, new_password): return change_user_password(username, new_password)
    def export_database(self, db_name, output_path): return export_database(db_name, output_path)
    def import_database(self, db_name, sql_path): return import_database(db_name, sql_path)
    def database_size(self, db_name): return database_size(db_name)
""",
    "backup_manager.py": """
class BackupManager:
    def list_backups(self, domain=None): return list_backups(domain)
    def create_backup(self, domain, include_db=True, include_email=True): return create_backup(domain, include_db, include_email)
    def restore_backup(self, backup_id, domain=None): return restore_backup(backup_id, domain)
    def delete_backup(self, backup_id): return delete_backup(backup_id)
    def setup_schedule(self, domain, frequency="daily", hour=3): return setup_schedule(domain, frequency, hour)
""",
    "email_manager.py": """
class EmailManager:
    def list_accounts(self, domain=None): return list_accounts(domain)
    def create_account(self, email, password, quota_mb=1024): return create_account(email, password, quota_mb)
    def delete_account(self, email): return delete_account(email)
    def change_password(self, email, new_password): return change_password(email, new_password)
    def list_aliases(self, domain=None): return list_aliases(domain)
    def add_alias(self, source, destination): return add_alias(source, destination)
    def delete_alias(self, source): return delete_alias(source)
    def setup_dkim(self, domain): return setup_dkim(domain)
""",
    "firewall_manager.py": """
class FirewallManager:
    def list_rules(self): return list_rules()
    def open_port(self, port, protocol="tcp", zone="public"): return open_port(port, protocol, zone)
    def close_port(self, port, protocol="tcp", zone="public"): return close_port(port, protocol, zone)
    def block_ip(self, ip, reason=""): return block_ip(ip, reason)
    def unblock_ip(self, ip): return unblock_ip(ip)
    def list_blocked_ips(self): return list_blocked_ips()
    def firewall_status(self): return firewall_status()
"""
}

for fname, content in files_to_append.items():
    with open(os.path.join(base, fname), 'a') as f:
        f.write('\n' + content)

print("Appended classes to files successfully.")
