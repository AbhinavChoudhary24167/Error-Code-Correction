param([switch]$ExplicitlyApproved)

$ErrorActionPreference = 'Stop'
if (-not $ExplicitlyApproved) {
    throw 'WSL2/Ubuntu provisioning requires a separate explicit approval. No host change was made.'
}

# This command does not reboot the host. If Windows reports that a reboot is
# required, stop here and ask the user to reboot manually.
wsl.exe --install --distribution Ubuntu-24.04 --no-launch
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Output 'Provisioning command returned. Do not continue if Windows requires a reboot.'
