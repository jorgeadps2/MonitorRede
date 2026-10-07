# ============================================================
# WiFi Monitor + Painel Web
# ============================================================

$Porta = 8080
$Pasta = "$HOME\WiFiMonitor"
$CSV = "$Pasta\monitor_wifi.csv"

# Criar pasta
if (!(Test-Path $Pasta)) {
    New-Item -ItemType Directory -Path $Pasta | Out-Null
}

# Criar CSV
if (!(Test-Path $CSV)) {
    "DataHora,SSID,Sinal,Canal,Banda,VelocidadeRecepcao,VelocidadeTransmissao,IP,Gateway,Ping" |
        Out-File $CSV -Encoding UTF8
}

# ============================================================
# FUNÇÃO - INFORMAÇÕES DO WI-FI
# ============================================================

function Get-WifiInfo {

    $wifi = netsh wlan show interfaces 2>$null

    function Get-NetshValue {
        param([string[]]$Texto,[string]$Nome)

        $resultado = $Texto | Select-String -Pattern "^\s*$Nome\s*:"

        if ($resultado) {
            return ($resultado.Line -replace "^\s*$Nome\s*:\s*", "").Trim()
        }

        return "N/D"
    }

    $SSID  = Get-NetshValue $wifi "SSID"
    $Sinal = Get-NetshValue $wifi "Sinal"
    $Canal = Get-NetshValue $wifi "Canal"

    $Radio = "N/D"
    $radioResultado = $wifi | Select-String "Tipo de.*rádio|Radio type"

    if ($radioResultado) {
        $Radio = ($radioResultado.Line -replace ".*:\s*", "").Trim()
    }

    $config = Get-NetIPConfiguration |
        Where-Object {
            $_.InterfaceAlias -eq "Wi-Fi" -and
            $_.NetAdapter.Status -eq "Up"
        } |
        Select-Object -First 1

    if ($config) {
        if ($config.IPv4Address) {
            $IP = $config.IPv4Address.IPAddress
        } else {
            $IP = "N/D"
        }

        if ($config.IPv4DefaultGateway) {
            $Gateway = $config.IPv4DefaultGateway.NextHop
        } else {
            $Gateway = "N/D"
        }
    }
    else {
        $IP = "N/D"
        $Gateway = "N/D"
    }

    $interface = Get-NetAdapter |
        Where-Object {
            $_.Name -eq "Wi-Fi" -and
            $_.Status -eq "Up"
        } |
        Select-Object -First 1

    if ($interface) {

        if ($interface.ReceiveLinkSpeed) {
            $RecepcaoMbps = [math]::Round($interface.ReceiveLinkSpeed / 1MB, 0)
        } else {
            $RecepcaoMbps = 0
        }

        if ($interface.TransmitLinkSpeed) {
            $TransmissaoMbps = [math]::Round($interface.TransmitLinkSpeed / 1MB, 0)
        } else {
            $TransmissaoMbps = 0
        }
    }
    else {
        $RecepcaoMbps = 0
        $TransmissaoMbps = 0
    }

    $Ping = "N/D"

    if ($Gateway -and $Gateway -ne "N/D") {
        try {
            $resultado = Test-Connection -ComputerName $Gateway -Count 1 -ErrorAction Stop

            if ($resultado) {
                $Ping = "$($resultado.ResponseTime) ms"
            }
        }
        catch {
            $Ping = "Falha"
        }
    }

    [PSCustomObject]@{
        DataHora = Get-Date -Format "dd/MM/yyyy HH:mm:ss"
        SSID = $SSID
        Sinal = $Sinal
        Canal = $Canal
        Banda = $Radio
        VelocidadeRecepcao = "$RecepcaoMbps Mbps"
        VelocidadeTransmissao = "$TransmissaoMbps Mbps"
        IP = $IP
        Gateway = $Gateway
        Ping = $Ping
    }
}
# ============================================================
# SERVIDOR WEB
# ============================================================

$listener = New-Object System.Net.HttpListener

$listener.Prefixes.Add("http://+:$Porta/")

$listener.Start()

# ============================================================
# DESCOBRIR IP DO WI-FI
# ============================================================

$IPNotebook = (
    Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object {
        $_.InterfaceAlias -eq "Wi-Fi" -and
        $_.IPAddress -notlike "169.254.*" -and
        $_.IPAddress -notlike "127.*"
    } |
    Select-Object -First 1
).IPAddress

# ============================================================
# MENSAGEM INICIAL
# ============================================================

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "       WIFI MONITOR WEB ATIVO" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Porta: $Porta" -ForegroundColor Yellow

Write-Host ""

Write-Host "No notebook:" -ForegroundColor Cyan
Write-Host "http://localhost:$Porta" -ForegroundColor Yellow

Write-Host ""

Write-Host "ACESSO PELO CELULAR:" -ForegroundColor Green
Write-Host "http://${IPNotebook}:$Porta" -ForegroundColor Yellow

Write-Host ""

Write-Host "Adaptador utilizado: Wi-Fi" -ForegroundColor Cyan
Write-Host "IP do Wi-Fi: $IPNotebook" -ForegroundColor Cyan

Write-Host ""
Write-Host "Pressione CTRL+C para encerrar." -ForegroundColor DarkGray
Write-Host ""

# ============================================================
# LOOP DO SERVIDOR
# ============================================================

while ($listener.IsListening) {

    try {

        $context = $listener.GetContext()

        # Obter informações atuais
        $dados = Get-WifiInfo

        # ====================================================
        # GRAVAR NO CSV
        # ====================================================

        $linha = "$($dados.DataHora),$($dados.SSID),$($dados.Sinal),$($dados.Canal),$($dados.Banda),$($dados.VelocidadeRecepcao),$($dados.VelocidadeTransmissao),$($dados.IP),$($dados.Gateway),$($dados.Ping)"

        Add-Content -Path $CSV -Value $linha

        # ====================================================
        # PÁGINA HTML
        # ====================================================

        $html = @"
<!DOCTYPE html>

<html>

<head>

<meta charset="UTF-8">

<meta name="viewport"
content="width=device-width, initial-scale=1.0">

<meta http-equiv="refresh" content="5">

<title>WiFi Monitor - Jorge</title>

<style>

body {
    font-family: Arial, sans-serif;
    background: #111827;
    color: white;
    margin: 0;
    padding: 15px;
}

.container {
    max-width: 900px;
    margin: auto;
}

h1 {
    text-align: center;
    color: #38bdf8;
    margin-bottom: 5px;
}

.subtitulo {
    text-align: center;
    color: #9ca3af;
    margin-bottom: 20px;
}

.card {
    background: #1f2937;
    border-radius: 15px;
    padding: 18px;
    margin: 15px 0;
    box-shadow: 0 4px 15px rgba(0,0,0,.4);
}

.status {
    text-align: center;
    font-size: 20px;
    color: #4ade80;
    font-weight: bold;
}

.item {
    display: flex;
    justify-content: space-between;
    gap: 20px;
    padding: 13px 5px;
    border-bottom: 1px solid #374151;
}

.item:last-child {
    border-bottom: none;
}

.valor {
    color: #38bdf8;
    font-weight: bold;
    text-align: right;
}

.footer {
    text-align: center;
    margin-top: 20px;
    color: #9ca3af;
    font-size: 13px;
}

@media (max-width: 600px) {

    body {
        padding: 10px;
    }

    .item {
        font-size: 14px;
    }

    h1 {
        font-size: 26px;
    }

}

</style>

</head>

<body>

<div class="container">

<h1>📶 Wi-Fi Monitor</h1>

<div class="subtitulo">
NOTE-JORGE
</div>

<div class="card">

<div class="status">
🟢 MONITORAMENTO ATIVO
</div>

</div>

<div class="card">

<div class="item">
<span>📡 SSID</span>
<span class="valor">$($dados.SSID)</span>
</div>

<div class="item">
<span>📶 Sinal</span>
<span class="valor">$($dados.Sinal)</span>
</div>

<div class="item">
<span>📻 Canal</span>
<span class="valor">$($dados.Canal)</span>
</div>

<div class="item">
<span>📡 Rádio</span>
<span class="valor">$($dados.Banda)</span>
</div>

</div>

<div class="card">

<div class="item">
<span>⬇️ Recepção</span>
<span class="valor">$($dados.VelocidadeRecepcao)</span>
</div>

<div class="item">
<span>⬆️ Transmissão</span>
<span class="valor">$($dados.VelocidadeTransmissao)</span>
</div>

</div>

<div class="card">

<div class="item">
<span>💻 IP do Notebook</span>
<span class="valor">$($dados.IP)</span>
</div>

<div class="item">
<span>🌐 Gateway</span>
<span class="valor">$($dados.Gateway)</span>
</div>

<div class="item">
<span>🏓 Ping</span>
<span class="valor">$($dados.Ping)</span>
</div>

</div>

<div class="footer">

Última atualização: $($dados.DataHora)

<br><br>

🔄 Atualização automática a cada 5 segundos

</div>

</div>

</body>

</html>
"@

        # ====================================================
        # ENVIAR PÁGINA
        # ====================================================

        $buffer = [System.Text.Encoding]::UTF8.GetBytes($html)

        $context.Response.ContentType = "text/html; charset=utf-8"
        $context.Response.ContentEncoding = [System.Text.Encoding]::UTF8

        $context.Response.ContentLength64 = $buffer.Length

        $context.Response.OutputStream.Write(
            $buffer,
            0,
            $buffer.Length
        )

        $context.Response.OutputStream.Close()

    }

    catch {

        Write-Host ""
        Write-Host "Erro: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host ""

    }
}
