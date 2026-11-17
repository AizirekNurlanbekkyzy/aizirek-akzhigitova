$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$EnvPath = Join-Path $ProjectRoot '.env'

if (Test-Path -LiteralPath $EnvPath) {
    throw '.env already exists. It was left unchanged; edit it yourself if needed.'
}

function New-RandomHex([int]$Bytes) {
    return [Convert]::ToHexString([System.Security.Cryptography.RandomNumberGenerator]::GetBytes($Bytes)).ToLowerInvariant()
}

$Content = @(
    'POSTGRES_DB=fixflow'
    'POSTGRES_USER=fixflow'
    "POSTGRES_PASSWORD=$(New-RandomHex 32)"
    'POSTGRES_PORT=5432'
    "JWT_SECRET=$(New-RandomHex 48)"
    'APP_ENV=development'
    'HOST_BIND=127.0.0.1'
    'CORS_ORIGINS=http://localhost:3000'
    'BACKEND_PORT=8000'
    'WEB_PORT=3000'
)
[IO.File]::WriteAllLines($EnvPath, $Content, [Text.Encoding]::ASCII)
Write-Output 'Created .env with fresh local secrets. The file is ignored by Git.'
