$ErrorActionPreference = 'Stop'
$siteRoot = [System.IO.Path]::GetFullPath($PSScriptRoot)
$listener = [System.Net.HttpListener]::new()
$listener.Prefixes.Add('http://127.0.0.1:8765/')
try {
    $listener.Start()
    Write-Host 'Abra http://127.0.0.1:8765/index.html — Ctrl+C para encerrar.'
    while ($listener.IsListening) {
        $context = $listener.GetContext()
        $relative = [Uri]::UnescapeDataString($context.Request.Url.AbsolutePath).TrimStart('/')
        if (-not $relative) { $relative = 'index.html' }
        $filePath = [System.IO.Path]::GetFullPath((Join-Path $siteRoot $relative))
        $response = $context.Response
        if (-not $filePath.StartsWith($siteRoot + [System.IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase) -or -not (Test-Path -LiteralPath $filePath -PathType Leaf)) {
            $response.StatusCode = 404
            $response.Close()
            continue
        }
        $response.Headers['Cross-Origin-Opener-Policy'] = 'same-origin'
        $response.Headers['Cross-Origin-Embedder-Policy'] = 'require-corp'
        $response.ContentType = switch ([System.IO.Path]::GetExtension($filePath)) {
            '.html' { 'text/html; charset=utf-8' }
            '.js' { 'application/javascript' }
            '.wasm' { 'application/wasm' }
            '.css' { 'text/css' }
            '.png' { 'image/png' }
            '.jpg' { 'image/jpeg' }
            '.txt' { 'text/plain; charset=utf-8' }
            '.log' { 'text/plain; charset=utf-8' }
            default { 'application/octet-stream' }
        }
        $stream = [System.IO.File]::OpenRead($filePath)
        try {
            $response.ContentLength64 = $stream.Length
            $stream.CopyTo($response.OutputStream)
        } catch { Write-Warning $_.Exception.Message } finally {
            $stream.Dispose()
            $response.Close()
        }
    }
} finally { $listener.Close() }
