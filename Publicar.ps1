$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw 'É necessário ter a CLI do GitHub instalada.'
}
$repository = 'leonardoscheitz/pvz-browser'
gh workflow run pages.yml --repo $repository --ref main
if ($LASTEXITCODE -ne 0) { throw 'Falha ao iniciar a publicação do main no GitHub Pages.' }
Write-Host "Acompanhe a publicação em https://github.com/$repository/actions/workflows/pages.yml"
