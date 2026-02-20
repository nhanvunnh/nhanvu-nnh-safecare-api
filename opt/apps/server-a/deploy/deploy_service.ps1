param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet("auth", "sms", "shop", "laydi", "core")]
    [string]$ServiceName,

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ExtraComposeArgs
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Resolve-Path (Join-Path $ScriptDir "..")
$ServiceDir = Join-Path $RootDir "services/$ServiceName"
$ComposeFile = Join-Path $ServiceDir "docker-compose.prod.yml"
$ProjectName = "servera_$ServiceName"
$EnvFile = Join-Path $ServiceDir ".env"

if (-not (Test-Path $ComposeFile)) {
    Write-Error ("Missing compose file for {0}: {1}" -f $ServiceName, $ComposeFile)
}

if (-not (Test-Path $EnvFile)) {
    Write-Error "Missing $EnvFile (container environment variables)."
}

function Ensure-Network {
    param(
        [Parameter(Mandatory = $true)]
        [string]$NetworkName
    )

    docker network inspect $NetworkName *> $null
    if ($LASTEXITCODE -ne 0) {
        docker network create $NetworkName | Out-Null
    }
}

function Get-ContainerNameFromCompose {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath
    )

    $line = Select-String -Path $FilePath -Pattern '^\s*container_name:\s*("?)([^"\r\n]+)\1\s*$' | Select-Object -First 1
    if (-not $line) {
        return $null
    }

    return $line.Matches[0].Groups[2].Value.Trim()
}

function Remove-ConflictingContainer {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ContainerName
    )

    # Docker name filters can behave inconsistently across shells; remove by explicit name.
    # Ignore "not found" so first-time deploys do not fail.
    $oldPref = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        docker rm -f $ContainerName *> $null
    } finally {
        $ErrorActionPreference = $oldPref
    }
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Removed existing container '$ContainerName' to avoid name conflict."
    }
}

Ensure-Network -NetworkName "proxy-network"
Ensure-Network -NetworkName "infra-network"
$ContainerName = Get-ContainerNameFromCompose -FilePath $ComposeFile
if ($ContainerName) {
    Remove-ConflictingContainer -ContainerName $ContainerName
}

$DockerArgs = @("-f", $ComposeFile, "-p", $ProjectName)

Write-Host "Deploying service $ServiceName..."
docker compose @DockerArgs pull @ExtraComposeArgs
if ($LASTEXITCODE -ne 0) {
    Write-Host "(pull step skipped or failed - continuing, build contexts may be used instead)"
}

docker compose @DockerArgs up -d --remove-orphans @ExtraComposeArgs
if ($LASTEXITCODE -ne 0) {
    Write-Error "docker compose up failed for service $ServiceName."
}

Write-Host "Service $ServiceName is up."
