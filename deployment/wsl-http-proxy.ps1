param(
    [string]$Distro = 'Ubuntu-24.04',
    [int]$ListenPort = 2086,
    [int]$TargetPort = 2086
)

function Get-WslIPv4 {
    $raw = & wsl.exe -d $Distro -u root -- hostname -I
    if ($LASTEXITCODE -ne 0 -or -not $raw) {
        throw "Unable to resolve WSL IP for distro '$Distro'."
    }

    $ip = ($raw.Trim() -split '\s+' | Where-Object { $_ -match '^\d+\.\d+\.\d+\.\d+$' } | Select-Object -First 1)
    if (-not $ip) {
        throw "No IPv4 address returned for distro '$Distro'."
    }

    return $ip
}

$targetHost = Get-WslIPv4
$prefix = "http://127.0.0.1:$ListenPort/"
$listener = [System.Net.HttpListener]::new()
$listener.Prefixes.Add($prefix)
$listener.Start()

$handler = {
    param($Context, $RemoteBase)

    $request = $Context.Request
    $response = $Context.Response
    $client = [System.Net.Http.HttpClient]::new([System.Net.Http.HttpClientHandler]@{ AllowAutoRedirect = $false; UseCookies = $false })

    try {
        $targetUri = [Uri]::new($RemoteBase + $request.RawUrl)
        $method = [System.Net.Http.HttpMethod]::new($request.HttpMethod)
        $message = [System.Net.Http.HttpRequestMessage]::new($method, $targetUri)

        foreach ($headerName in $request.Headers.AllKeys) {
            if ($headerName -in @('Host', 'Content-Length', 'Transfer-Encoding', 'Connection')) {
                continue
            }

            $values = $request.Headers.GetValues($headerName)
            if (-not $message.Headers.TryAddWithoutValidation($headerName, $values) -and $null -ne $request.InputStream) {
                if (-not $message.Content) {
                    $message.Content = [System.Net.Http.StreamContent]::new($request.InputStream)
                }
                $message.Content.Headers.TryAddWithoutValidation($headerName, $values) | Out-Null
            }
        }

        if ($request.HasEntityBody -and -not $message.Content) {
            $message.Content = [System.Net.Http.StreamContent]::new($request.InputStream)
        }

        $remoteResponse = $client.SendAsync($message).GetAwaiter().GetResult()
        $response.StatusCode = [int]$remoteResponse.StatusCode

        foreach ($header in $remoteResponse.Headers) {
            foreach ($value in $header.Value) {
                $response.Headers.Add($header.Key, $value)
            }
        }

        if ($remoteResponse.Content) {
            foreach ($header in $remoteResponse.Content.Headers) {
                foreach ($value in $header.Value) {
                    if ($header.Key -eq 'Content-Type') {
                        $response.ContentType = $value
                    } elseif ($header.Key -ne 'Content-Length') {
                        $response.Headers.Add($header.Key, $value)
                    }
                }
            }

            $stream = $remoteResponse.Content.ReadAsStreamAsync().GetAwaiter().GetResult()
            $stream.CopyTo($response.OutputStream)
            $stream.Dispose()
        }
    } catch {
        $response.StatusCode = 502
        $bytes = [System.Text.Encoding]::UTF8.GetBytes("Proxy failure: $($_.Exception.Message)")
        $response.OutputStream.Write($bytes, 0, $bytes.Length)
    } finally {
        $response.OutputStream.Close()
        $response.Close()
        $client.Dispose()
    }
}

$remoteBase = "http://${targetHost}:$TargetPort"
Write-Host "Proxying $prefix to $remoteBase"

while ($listener.IsListening) {
    $context = $listener.GetContext()
    & $handler $context $remoteBase
}