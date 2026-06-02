param(
    [string]$InterfaceAlias = "Wi-Fi",
    [string]$ResultPath = "C:\Users\asror\OneDrive\Dokumen\crypto_ai_trader\cloudflare-dns-result.json"
)

$ErrorActionPreference = "Stop"

$targetDns = @("1.1.1.1", "1.0.0.1")
$before = (Get-DnsClientServerAddress -InterfaceAlias $InterfaceAlias -AddressFamily IPv4).ServerAddresses
$rolledBackToAutomatic = $false
$tests = [ordered]@{}

try {
    Set-DnsClientServerAddress -InterfaceAlias $InterfaceAlias -ServerAddresses $targetDns
    ipconfig /flushdns | Out-Null

    $after = (Get-DnsClientServerAddress -InterfaceAlias $InterfaceAlias -AddressFamily IPv4).ServerAddresses

    try {
        Resolve-DnsName cloudflare.com -Server 1.1.1.1 -ErrorAction Stop | Out-Null
        $tests.cloudflareDnsVia1111 = $true
    } catch {
        $tests.cloudflareDnsVia1111 = $false
        $tests.cloudflareDnsVia1111Error = $_.Exception.Message
    }

    try {
        Resolve-DnsName cloudflare.com -ErrorAction Stop | Out-Null
        $tests.systemDns = $true
    } catch {
        $tests.systemDns = $false
        $tests.systemDnsError = $_.Exception.Message
    }

    try {
        $tests.cloudflareHttps443 = [bool](Test-NetConnection cloudflare.com -Port 443 -InformationLevel Quiet)
    } catch {
        $tests.cloudflareHttps443 = $false
        $tests.cloudflareHttps443Error = $_.Exception.Message
    }

    try {
        Resolve-DnsName binance.com -ErrorAction Stop | Out-Null
        $tests.binanceDns = $true
    } catch {
        $tests.binanceDns = $false
        $tests.binanceDnsError = $_.Exception.Message
    }

    try {
        $tests.binanceHttps443 = [bool](Test-NetConnection www.binance.com -Port 443 -InformationLevel Quiet)
    } catch {
        $tests.binanceHttps443 = $false
        $tests.binanceHttps443Error = $_.Exception.Message
    }

    if (-not ($tests.cloudflareDnsVia1111 -and $tests.systemDns -and $tests.cloudflareHttps443)) {
        Set-DnsClientServerAddress -InterfaceAlias $InterfaceAlias -ResetServerAddresses
        ipconfig /flushdns | Out-Null
        $rolledBackToAutomatic = $true
        $after = (Get-DnsClientServerAddress -InterfaceAlias $InterfaceAlias -AddressFamily IPv4).ServerAddresses
    }

    $result = [pscustomobject]@{
        ok = -not $rolledBackToAutomatic
        adapter = $InterfaceAlias
        beforeDns = $before
        requestedDns = $targetDns
        currentDns = $after
        rolledBackToAutomatic = $rolledBackToAutomatic
        tests = $tests
        timestamp = (Get-Date).ToString("s")
    }
} catch {
    try {
        Set-DnsClientServerAddress -InterfaceAlias $InterfaceAlias -ResetServerAddresses
        ipconfig /flushdns | Out-Null
        $rolledBackToAutomatic = $true
    } catch {
    }

    $result = [pscustomobject]@{
        ok = $false
        adapter = $InterfaceAlias
        beforeDns = $before
        requestedDns = $targetDns
        currentDns = (Get-DnsClientServerAddress -InterfaceAlias $InterfaceAlias -AddressFamily IPv4).ServerAddresses
        rolledBackToAutomatic = $rolledBackToAutomatic
        error = $_.Exception.Message
        timestamp = (Get-Date).ToString("s")
    }
}

$result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $ResultPath -Encoding UTF8
