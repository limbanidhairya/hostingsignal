import sqlite3
from passlib.context import CryptContext
ctx = CryptContext(schemes=['bcrypt'], deprecated='auto')
con = sqlite3.connect('/usr/local/hspanel/developer-panel/hostingsignal_dev.db')
cur = con.cursor()
row = cur.execute("SELECT password_hash FROM dev_admins WHERE email='admin@hostingsignal.local'").fetchone()
if row is None:
    print('NO ADMIN ROW')
else:
    stored_hash = row[0]
    print('hash_len:', len(stored_hash))
    print('hash_prefix:', stored_hash[:20])
    try:
        result = ctx.verify('Admin@123', stored_hash)
        print('verifies_Admin@123:', result)
    except Exception as e:
        print('verify_error:', e)

    # Re-hash and update with current bcrypt
    new_hash = ctx.hash('Admin@123')
    print('new_hash_len:', len(new_hash))
    print('new_hash_prefix:', new_hash[:20])
    con.execute("UPDATE dev_admins SET password_hash=? WHERE email='admin@hostingsignal.local'", (new_hash,))
    con.commit()
    print('password hash updated')
