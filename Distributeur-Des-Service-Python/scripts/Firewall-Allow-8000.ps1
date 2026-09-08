# Ouvre le port TCP 8000 entrant pour que les téléphones sur le Wi-Fi atteignent uvicorn/FastAPI.
# Clic droit → Exécuter avec PowerShell en tant qu'administrateur.

$ruleName = "PFE Distributeur FastAPI 8000"
$existing = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Règle déjà présente : $ruleName"
    exit 0
}

New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8000
Write-Host "Règle pare-feu créée : $ruleName (TCP 8000 entrant)."
