$ErrorActionPreference = "Stop"

param(
    [string]$AllowedSubnet = "192.168.1.0/24"
)

$ruleGroup = "TicketsLAN"

function Add-OrReplaceRule {
    param(
        [string]$Name,
        [int]$Port
    )

    $existing = Get-NetFirewallRule -DisplayName $Name -ErrorAction SilentlyContinue
    if ($existing) {
        Remove-NetFirewallRule -DisplayName $Name | Out-Null
    }

    New-NetFirewallRule \
        -DisplayName $Name \
        -Group $ruleGroup \
        -Direction Inbound \
        -Action Allow \
        -Protocol TCP \
        -LocalPort $Port \
        -RemoteAddress $AllowedSubnet \
        -Profile Domain,Private | Out-Null
}

Write-Host "Configurando firewall para TicketsLAN..."
Add-OrReplaceRule -Name "TicketsLAN-HTTP-5555" -Port 5555
Add-OrReplaceRule -Name "TicketsLAN-WS-5556" -Port 5556
Add-OrReplaceRule -Name "TicketsLAN-LIC-8787" -Port 8787

Write-Host "Listo. Reglas aplicadas para subred: $AllowedSubnet"
