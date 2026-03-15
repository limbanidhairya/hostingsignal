# Distributed License Cache Flow

1. Read configs/license.cache.
2. If status is active and not expired, allow feature gates.
3. If expired or unknown, call central license API.
4. Persist signed response into cache.
5. If central API unavailable, allow up to 72 hour grace window based on grace_deadline.
