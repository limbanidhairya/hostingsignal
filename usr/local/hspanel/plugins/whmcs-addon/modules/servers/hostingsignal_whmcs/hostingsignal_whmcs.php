<?php

if (!defined('WHMCS')) {
    die('This file cannot be accessed directly');
}

function hostingsignal_whmcs_MetaData()
{
    return [
        'DisplayName' => 'HostingSignal WHMCS Provisioning',
        'APIVersion' => '1.1',
        'RequiresServer' => true,
        'DefaultNonSSLPort' => '2087',
        'ServiceSingleSignOnLabel' => 'Login to HostingSignal',
    ];
}

function hostingsignal_whmcs_ConfigOptions()
{
    return [
        'Panel API Base URL' => [
            'Type' => 'text',
            'Size' => '60',
            'Default' => 'http://127.0.0.1:2087',
            'Description' => 'Developer panel API URL',
        ],
        'WHMCS Shared Token' => [
            'Type' => 'password',
            'Size' => '60',
            'Default' => '',
            'Description' => 'Must match HSDEV_WHMCS_SHARED_SECRET',
        ],
        'Package Plan' => [
            'Type' => 'dropdown',
            'Options' => 'starter,professional,business,enterprise',
            'Default' => 'starter',
            'Description' => 'Default HostingSignal plan tier',
        ],
        'Default Plugins (comma-separated slugs)' => [
            'Type' => 'text',
            'Size' => '60',
            'Default' => 'node-app-manager,react-app-manager,python-app-manager',
        ],
        'Admin Override' => [
            'Type' => 'yesno',
            'Description' => 'Allow premium plugin overrides on lower plans',
        ],
    ];
}

function hostingsignal_whmcs_TestConnection(array $params)
{
    $response = hostingsignal_whmcs_call_api($params, '/api/whmcs/health', null, 'GET');
    if (!$response['ok']) {
        return [
            'success' => false,
            'error' => 'Connection failed: ' . $response['message'],
        ];
    }

    return [
        'success' => true,
        'error' => '',
    ];
}

function hostingsignal_whmcs_CreateAccount(array $params)
{
    $pluginList = array_filter(array_map('trim', explode(',', (string)($params['configoption4'] ?? ''))));
    $productId = (int)($params['pid'] ?? $params['packageid'] ?? 0);

    $payload = [
        'service_id' => (int)($params['serviceid'] ?? 0),
        'client_id' => (int)($params['clientsdetails']['id'] ?? 0),
        'domain' => (string)($params['domain'] ?? ''),
        'package_name' => (string)($params['package']['name'] ?? $params['productname'] ?? 'whmcs-package'),
        'plan' => (string)($params['configoption3'] ?? 'starter'),
        'include_plugins' => array_values($pluginList),
        'admin_override' => !empty($params['configoption5']),
        'whmcs_product_id' => $productId > 0 ? $productId : null,
    ];

    $response = hostingsignal_whmcs_call_api($params, '/api/whmcs/provision/create-account', $payload, 'POST');
    if (!$response['ok']) {
        return 'CreateAccount failed: ' . $response['message'];
    }

    return 'success';
}

function hostingsignal_whmcs_SyncProductMapping(array $params, array $mapping)
{
    $response = hostingsignal_whmcs_call_api($params, '/api/whmcs/product-mappings/upsert', $mapping, 'POST');
    if (!$response['ok']) {
        return 'SyncProductMapping failed: ' . $response['message'];
    }
    return 'success';
}

function hostingsignal_whmcs_SuspendAccount(array $params)
{
    $payload = [
        'service_id' => (int)($params['serviceid'] ?? 0),
        'domain' => (string)($params['domain'] ?? ''),
        'reason' => (string)($params['suspendreason'] ?? 'Suspended by WHMCS'),
    ];

    $response = hostingsignal_whmcs_call_api($params, '/api/whmcs/provision/suspend-account', $payload, 'POST');
    if (!$response['ok']) {
        return 'SuspendAccount failed: ' . $response['message'];
    }

    return 'success';
}

function hostingsignal_whmcs_UnsuspendAccount(array $params)
{
    $payload = [
        'service_id' => (int)($params['serviceid'] ?? 0),
        'domain' => (string)($params['domain'] ?? ''),
    ];

    $response = hostingsignal_whmcs_call_api($params, '/api/whmcs/provision/unsuspend-account', $payload, 'POST');
    if (!$response['ok']) {
        return 'UnsuspendAccount failed: ' . $response['message'];
    }

    return 'success';
}

function hostingsignal_whmcs_TerminateAccount(array $params)
{
    $payload = [
        'service_id' => (int)($params['serviceid'] ?? 0),
        'domain' => (string)($params['domain'] ?? ''),
        'reason' => 'Terminated by WHMCS',
    ];

    $response = hostingsignal_whmcs_call_api($params, '/api/whmcs/provision/terminate-account', $payload, 'POST');
    if (!$response['ok']) {
        return 'TerminateAccount failed: ' . $response['message'];
    }

    return 'success';
}

function hostingsignal_whmcs_call_api(array $params, string $path, ?array $payload = null, string $method = 'POST')
{
    $baseUrl = rtrim((string)($params['configoption1'] ?? 'http://127.0.0.1:2087'), '/');
    $token = (string)($params['configoption2'] ?? '');
    $url = $baseUrl . $path;

    $headers = [
        'Content-Type: application/json',
        'X-HS-WHMCS-Token: ' . $token,
    ];

    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 20);
    curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);

    if ($method === 'POST') {
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($payload ?: []));
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
