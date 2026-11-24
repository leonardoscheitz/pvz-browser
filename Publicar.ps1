$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw 'Instale o GitHub CLI oficial em https://cli.github.com/ e faça gh auth login.'
}
gh auth status
if ($LASTEXITCODE -ne 0) { throw 'Faça gh auth login antes de publicar.' }
$account = (gh api user --jq .login).Trim()
if ($LASTEXITCODE -ne 0 -or $account -ne 'leonardoscheitz') { throw 'Use a conta GitHub leonardoscheitz.' }
$repository = 'leonardoscheitz/pvz-browser'
gh repo view $repository *> $null
if ($LASTEXITCODE -eq 0) { throw 'O repositório já existe. Confira o conteúdo antes de publicar.' }
gh repo create $repository --public --description 'Plants vs. Zombies GOTY emulado no navegador com Boxedwine'
if ($LASTEXITCODE -ne 0) { throw 'Não foi possível criar o repositório.' }
git init -b main
if ($LASTEXITCODE -ne 0) { throw 'Falha ao inicializar o Git.' }
git add --all
git -c user.name='leonardoscheitz' -c user.email='211175867+leonardoscheitz@users.noreply.github.com' commit -m 'Adicionar GOTY original com emulação web'
if ($LASTEXITCODE -ne 0) { throw 'Falha ao criar o commit.' }
git remote add origin "https://github.com/$repository.git"
gh auth setup-git
if ($LASTEXITCODE -ne 0) { throw 'Falha ao configurar autenticação Git.' }
git push -u origin main
if ($LASTEXITCODE -ne 0) { throw 'Falha ao enviar os arquivos.' }
gh api --method POST "repos/$repository/pages" -f build_type=workflow
if ($LASTEXITCODE -ne 0) { throw 'Arquivos enviados, mas confira a ativação do Pages nas configurações.' }
Write-Host "Acompanhe: https://github.com/$repository/actions"
Write-Host 'Após o deploy: https://leonardoscheitz.github.io/pvz-browser/'
