<?php

if (!defined('WHMCS')) {
    die('This file cannot be accessed directly');
}

function hostingsignal_whmcs_config()
{
    return [
        'name' => 'HostingSignal WHMCS Addon',
        'description' => 'Adds package sync and plugin policy controls for HostingSignal plans.',
        'version' => '1.1.0',
        'author' => 'HostingSignal',
        'language' => 'english',
        'fields' => [
            'panel_api_url' => [
                'FriendlyName' => 'Panel API URL',
                'Type' => 'text',
                'Size' => '60',
                'Default' => 'http://127.0.0.1:2087',
            ],
            'shared_token' => [
                'FriendlyName' => 'WHMCS Shared Token',
                'Type' => 'password',
                'Size' => '60',
                'Default' => '',
                'Description' => 'Must match HSDEV_WHMCS_SHARED_SECRET',
            ],
            'hmac_secret' => [
                'FriendlyName' => 'HMAC Shared Secret (optional)',
                'Type' => 'password',
                'Size' => '60',
                'Default' => '',
                'Description' => 'Must match HSDEV_WHMCS_HMAC_SECRET when enabled',
            ],
        ],
    ];
}

function hostingsignal_whmcs_activate()
{
    return ['status' => 'success', 'description' => 'HostingSignal addon activated'];
}

function hostingsignal_whmcs_deactivate()
{
    return ['status' => 'success', 'description' => 'HostingSignal addon deactivated'];
}

function hostingsignal_whmcs_output($vars)
{
    $message = '';
    $messageType = 'info';

    if ($_SERVER['REQUEST_METHOD'] === 'POST') {
        $action = (string)($_POST['hs_action'] ?? '');

        if ($action === 'upsert_mapping') {
            $productId = (int)($_POST['product_id'] ?? 0);
            $packageName = trim((string)($_POST['package_name'] ?? ''));
            $plan = trim((string)($_POST['plan'] ?? 'starter'));
            $pluginsRaw = trim((string)($_POST['include_plugins'] ?? ''));
            $plugins = array_values(array_filter(array_map('trim', explode(',', $pluginsRaw))));
            $adminOverride = !empty($_POST['admin_override']);

            if ($productId <= 0 || $packageName === '') {
                $message = 'Product ID and package name are required.';
                $messageType = 'error';
            } else {
                $payload = [
                    'product_id' => $productId,
                    'package_name' => $packageName,
                    'plan' => $plan,
                    'include_plugins' => $plugins,
                    'admin_override' => $adminOverride,
                ];
                $resp = hostingsignal_whmcs_addon_call_api($vars, '/api/whmcs/product-mappings/upsert', $payload, 'POST');
                if ($resp['ok']) {
                    $message = 'Mapping saved successfully for product #' . $productId;
                    $messageType = 'success';
                } else {
                    $message = 'Failed to save mapping: ' . $resp['message'];
                    $messageType = 'error';
                }
            }
        }

        if ($action === 'delete_mapping') {
            $productId = (int)($_POST['delete_product_id'] ?? 0);
            if ($productId <= 0) {
                $message = 'Valid product ID required for delete.';
                $messageType = 'error';
            } else {
                $payload = [
                    'product_id' => $productId,
                    'fallback_plan' => 'starter',
                    'fallback_package_name' => 'whmcs-package',
                    'fallback_plugins' => [],
                    'fallback_admin_override' => false,
                ];
                $resp = hostingsignal_whmcs_addon_call_api($vars, '/api/whmcs/product-mappings/delete', $payload, 'POST');
                if ($resp['ok']) {
                    $message = 'Mapping deleted (if existed) for product #' . $productId;
                    $messageType = 'success';
                } else {
                    $message = 'Failed to delete mapping: ' . $resp['message'];
                    $messageType = 'error';
                }
            }
        }
    }

    $listResponse = hostingsignal_whmcs_addon_call_api($vars, '/api/whmcs/product-mappings', null, 'GET');
    $mappings = [];
    if ($listResponse['ok'] && is_array($listResponse['body']) && isset($listResponse['body']['mappings'])) {
        $mappings = (array)$listResponse['body']['mappings'];
    }

    echo '<h2>HostingSignal WHMCS Addon</h2>';
    echo '<p>Manage product-level package mappings used during HostingSignal provisioning.</p>';

    if ($message !== '') {
        $bg = $messageType === 'success' ? '#e8f8ee' : ($messageType === 'error' ? '#fdeaea' : '#eef3ff');
        $color = $messageType === 'success' ? '#1f7a3a' : ($messageType === 'error' ? '#b42318' : '#1e3a8a');
        echo '<div style="margin:12px 0;padding:10px 12px;border-radius:6px;background:' . $bg . ';color:' . $color . ';">'
            . htmlspecialchars($message, ENT_QUOTES, 'UTF-8') . '</div>';
    }

    echo '<div style="display:flex;gap:24px;flex-wrap:wrap;align-items:flex-start;">';

    echo '<div style="min-width:360px;max-width:520px;flex:1;border:1px solid #ddd;border-radius:8px;padding:14px;">';
    echo '<h3 style="margin-top:0;">Upsert Product Mapping</h3>';
    echo '<form method="post">';
    echo '<input type="hidden" name="hs_action" value="upsert_mapping" />';
    echo '<p><label>Product ID<br><input type="number" name="product_id" min="1" required style="width:100%;padding:6px;"></label></p>';
    echo '<p><label>Package Name<br><input type="text" name="package_name" required style="width:100%;padding:6px;"></label></p>';
    echo '<p><label>Plan<br>';
    echo '<select name="plan" style="width:100%;padding:6px;">';
    echo '<option value="starter">starter</option>';
    echo '<option value="professional">professional</option>';
    echo '<option value="business">business</option>';
    echo '<option value="enterprise">enterprise</option>';
    echo '</select></label></p>';
    echo '<p><label>Plugins (comma-separated slugs)<br><input type="text" name="include_plugins" placeholder="wordpress-manager,node-app-manager" style="width:100%;padding:6px;"></label></p>';
    echo '<p><label><input type="checkbox" name="admin_override" value="1"> Allow admin override</label></p>';
    echo '<p><button type="submit" style="padding:8px 12px;">Save Mapping</button></p>';
    echo '</form>';
    echo '</div>';

    echo '<div style="min-width:280px;max-width:360px;flex:1;border:1px solid #ddd;border-radius:8px;padding:14px;">';
    echo '<h3 style="margin-top:0;">Delete Mapping</h3>';
    echo '<form method="post">';
    echo '<input type="hidden" name="hs_action" value="delete_mapping" />';
    echo '<p><label>Product ID<br><input type="number" name="delete_product_id" min="1" required style="width:100%;padding:6px;"></label></p>';
    echo '<p><button type="submit" style="padding:8px 12px;">Delete Mapping</button></p>';
    echo '</form>';
    echo '</div>';

    echo '</div>';

    echo '<h3>Current Mappings</h3>';
    if (empty($mappings)) {
        echo '<p>No product mappings configured yet.</p>';
        return;
    }

    echo '<table cellspacing="0" cellpadding="8" border="1" style="border-collapse:collapse;width:100%;max-width:1200px;">';
    echo '<thead><tr style="background:#f6f8fb;">';
    echo '<th align="left">Product ID</th><th align="left">Package</th><th align="left">Plan</th><th align="left">Plugins</th><th align="left">Admin Override</th><th align="left">Updated</th>';
    echo '</tr></thead><tbody>';

    foreach ($mappings as $productId => $cfg) {
        $plugins = [];
        if (is_array($cfg) && isset($cfg['include_plugins']) && is_array($cfg['include_plugins'])) {
            $plugins = $cfg['include_plugins'];
        }
        $pluginText = implode(', ', $plugins);
        echo '<tr>';
        echo '<td>' . htmlspecialchars((string)$productId, ENT_QUOTES, 'UTF-8') . '</td>';
        echo '<td>' . htmlspecialchars((string)($cfg['package_name'] ?? ''), ENT_QUOTES, 'UTF-8') . '</td>';
        echo '<td>' . htmlspecialchars((string)($cfg['plan'] ?? ''), ENT_QUOTES, 'UTF-8') . '</td>';
        echo '<td>' . htmlspecialchars($pluginText, ENT_QUOTES, 'UTF-8') . '</td>';
        echo '<td>' . (!empty($cfg['admin_override']) ? 'yes' : 'no') . '</td>';
        echo '<td>' . htmlspecialchars((string)($cfg['updated_at'] ?? ''), ENT_QUOTES, 'UTF-8') . '</td>';
        echo '</tr>';
    }
    echo '</tbody></table>';
}

function hostingsignal_whmcs_addon_call_api(array $vars, string $path, ?array $payload = null, string $method = 'POST')
{
    $baseUrl = rtrim((string)($vars['panel_api_url'] ?? 'http://127.0.0.1:2087'), '/');
    $token = (string)($vars['shared_token'] ?? '');
    $hmacSecret = (string)($vars['hmac_secret'] ?? '');
    $url = $baseUrl . $path;
    $method = strtoupper($method);
    $bodyJson = $method === 'POST' ? json_encode($payload ?: []) : '';
    $timestamp = (string)time();
    $nonce = '';

    $headers = [
        'Content-Type: application/json',
        'X-HS-WHMCS-Token: ' . $token,
    ];

    if ($hmacSecret !== '') {
        try {
            $nonce = bin2hex(random_bytes(8));
        } catch (Exception $e) {
            $nonce = md5((string)microtime(true));
        }
        $signature = hash_hmac('sha256', $timestamp . '.' . $bodyJson, $hmacSecret);
        $headers[] = 'X-HS-WHMCS-Timestamp: ' . $timestamp;
        $headers[] = 'X-HS-WHMCS-Signature: ' . $signature;
        $headers[] = 'X-HS-WHMCS-Nonce: ' . $nonce;
    }

    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 20);
    curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);

    if ($method === 'POST') {
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, $bodyJson);
    } else {
        curl_setopt($ch, CURLOPT_CUSTOMREQUEST, 'GET');
    }

    $raw = curl_exec($ch);
    $errno = curl_errno($ch);
    $error = curl_error($ch);
    $code = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    if ($errno) {
        return ['ok' => false, 'message' => 'cURL error: ' . $error, 'code' => 0, 'body' => null];
    }

    $decoded = json_decode((string)$raw, true);
    if ($code < 200 || $code >= 300) {
        $detail = is_array($decoded) && isset($decoded['detail']) ? $decoded['detail'] : (string)$raw;
        return ['ok' => false, 'message' => (string)$detail, 'code' => $code, 'body' => $decoded];
    }

    return ['ok' => true, 'message' => '', 'code' => $code, 'body' => $decoded];
}
