HostingSignal WHMCS Plugin Bundle

Contents:
- modules/servers/hostingsignal_whmcs/hostingsignal_whmcs.php
- modules/addons/hostingsignal_whmcs/hostingsignal_whmcs.php

Install steps (WHMCS):
1) Copy modules/servers/hostingsignal_whmcs into WHMCS modules/servers/
2) Copy modules/addons/hostingsignal_whmcs into WHMCS modules/addons/
3) In WHMCS admin, activate addon and configure server module.
4) Set shared token in WHMCS config options and in panel env:
   HSDEV_WHMCS_SHARED_SECRET=<same-token>
5) Use panel API base URL http://<panel-host>:2087

Supported callbacks:
- CreateAccount
- SuspendAccount
- UnsuspendAccount
- TerminateAccount
- TestConnection

Panel endpoints used:
- /api/whmcs/health
- /api/whmcs/package/sync
- /api/whmcs/product-mappings
- /api/whmcs/product-mappings/upsert
- /api/whmcs/product-mappings/delete
- /api/whmcs/product-mappings/resolve
- /api/whmcs/provision/create-account
- /api/whmcs/provision/suspend-account
- /api/whmcs/provision/unsuspend-account
- /api/whmcs/provision/terminate-account

Product mapping behavior:
- Save mapping by WHMCS product ID with plan/plugins/admin_override.
- CreateAccount and package sync auto-resolve mapping when whmcs_product_id is provided.
- If no mapping exists, configured fallback plan/plugins are used.
