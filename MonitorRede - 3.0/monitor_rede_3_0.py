# ============================================================
# 📡 MONITOR DE REDE - MonitorRedesys
# ============================================================
# Central de monitoramento e diagnóstico de rede
#
# 👨‍💻 Desenvolvido por: Jorge Alberto de Paula
# 🤖 JP
# 🚀 Versão: 3.0
#
# Recursos:
# - Wi-Fi, sinal, SSID, canal e velocidade
# - Ethernet e velocidade
# - IP e gateway
# - Internet / DNS / Gateway
# - Latência com gráfico de barras
# - Estatísticas completas
# - Classificação automática do problema
# - Diagnóstico detalhado
# - Histórico interno
# - Exportação de relatório
# - Configurações
# - Responsivo para telas menores
# - Compatível com PyInstaller
# ============================================================

import csv
import os
import re
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None


# ============================================================
# 🖥️ DPI DO WINDOWS
# ============================================================

if sys.platform == "win32":
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass
    except Exception:
        pass


# ============================================================
# ⚙️ CONFIGURAÇÕES
# ============================================================

APP_NAME = "Monitor de Rede"
APP_VERSION = "3.0"
AUTOR = "Jorge Alberto de Paula"
MARCA_AUTOR = "🤖 JP"

PASTA = os.path.join(os.path.expanduser("~"), "MonitorRede")
CSV_FILE = os.path.join(PASTA, "monitor_rede.csv")

INTERVALO = 2
MAX_PONTOS = 150
LATENCIA_HOST = "1.1.1.1"
LATENCIA_TIMEOUT = 1500

TEST_URLS = [
    "https://www.msftconnecttest.com/connecttest.txt",
    "https://www.google.com/generate_204",
    "https://www.cloudflare.com/cdn-cgi/trace",
]

DNS_SERVERS = ["1.1.1.1", "8.8.8.8"]

os.makedirs(PASTA, exist_ok=True)


# ============================================================
# 📦 RECURSOS
# ============================================================

# ============================================================
# 📦 RECURSOS - PYTHON E PYINSTALLER
# ============================================================

def resource_path(relative_path):
    """
    Localiza arquivos de recursos tanto quando o programa
    roda pelo Python quanto quando roda dentro do EXE
    criado pelo PyInstaller.
    """

    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        # Programa empacotado pelo PyInstaller
        base_path = sys._MEIPASS
    else:
        # Programa rodando normalmente pelo Python
        base_path = os.path.dirname(
            os.path.abspath(__file__)
        )

    return os.path.join(base_path, relative_path)


# ============================================================
# 📊 ESTADO GLOBAL
# ============================================================

estado_anterior = None
inicio_queda = None
contador_quedas = 0
contador_testes = 0
contador_sucessos = 0
contador_falhas = 0

ultima_queda = "--"
duracao_ultima_queda = "--"
maior_queda = 0
tempo_monitoramento_inicio = datetime.now()

ultimo_evento = "Monitor iniciado"
ultimo_diagnostico = "Aguardando diagnóstico"

historico_eventos = []
ultimo_evento_historico = None

pontos = []
historico_online = []

latencias_todas = []
falhas_gateway = 0
falhas_dns = 0
falhas_internet = 0

rodando = True
pausado = False

ultimo_dados = {}


# ============================================================
# 🕐 UTILITÁRIOS
# ============================================================

def agora():
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def formatar_ms(ms):
    return "--" if ms is None else f"{ms} ms"


def formatar_duracao(segundos):
    segundos = max(0, int(segundos))
    horas, resto = divmod(segundos, 3600)
    minutos, segundos = divmod(resto, 60)
    if horas:
        return f"{horas:02d}:{minutos:02d}:{segundos:02d}"
    return f"{minutos:02d}:{segundos:02d}"


def executar_comando(comando, timeout=5, encoding="utf-8"):
    try:
        return subprocess.run(
            comando,
            capture_output=True,
            text=True,
            encoding=encoding,
            errors="ignore",
            timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
    except Exception:
        return None


# ============================================================
# 📄 CSV
# ============================================================

def inicializar_csv():
    if not os.path.exists(CSV_FILE) or os.path.getsize(CSV_FILE) == 0:
        with open(CSV_FILE, "w", newline="", encoding="utf-8-sig") as f:
            csv.writer(f, delimiter=";").writerow([
                "Data", "Hora", "Evento", "Diagnostico",
                "Wi-Fi", "Sinal_WiFi", "Ethernet",
                "Internet", "IP", "Gateway", "Latencia_ms",
                "Duracao_queda"
            ])


def registrar_csv(evento, dados=None, duracao="--"):
    inicializar_csv()
    dados = dados or {}
    dt = datetime.now()

    with open(CSV_FILE, "a", newline="", encoding="utf-8-sig") as f:
        csv.writer(f, delimiter=";").writerow([
            dt.strftime("%d/%m/%Y"),
            dt.strftime("%H:%M:%S"),
            evento,
            dados.get("diagnostico", "--"),
            dados.get("wifi", "--"),
            dados.get("sinal_wifi", 0),
            dados.get("ethernet", "--"),
            dados.get("internet", "--"),
            dados.get("ip", "--"),
            dados.get("gateway", "--"),
            dados.get("latencia", "--"),
            duracao
        ])


def ler_historico():
    inicializar_csv()
    try:
        with open(CSV_FILE, "r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f, delimiter=";"))
    except Exception:
        return []


# ============================================================
# 🌐 IP / GATEWAY
# ============================================================

def obter_ip():
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(2)
        s.connect(("1.1.1.1", 80))
        ip = s.getsockname()[0]
        if ip and ip != "0.0.0.0":
            return ip
    except Exception:
        pass
    finally:
        if s:
            try:
                s.close()
            except Exception:
                pass

    try:
        ip = socket.gethostbyname(socket.gethostname())
        if ip and ip != "127.0.0.1":
            return ip
    except Exception:
        pass
    return "--"


def obter_gateway():
    resultado = executar_comando(["ipconfig"], timeout=5, encoding="cp850")
    if not resultado:
        return "--"

    for linha in resultado.stdout.splitlines():
        normalizada = linha.strip().lower()
        if "gateway padrão" in normalizada or "default gateway" in normalizada:
            partes = linha.split(":", 1)
            if len(partes) == 2:
                valor = partes[1].strip()
                if re.match(r"^\d+\.\d+\.\d+\.\d+$", valor):
                    return valor
    return "--"


def ping_host(host, timeout=1000):
    try:
        inicio = time.perf_counter()
        resultado = executar_comando(
            ["ping", "-n", "1", "-w", str(timeout), host],
            timeout=max(2, timeout / 1000 + 1),
            encoding="cp850"
        )
        if not resultado or resultado.returncode != 0:
            return None

        texto = resultado.stdout + "\n" + resultado.stderr
        m = re.search(r"(?:[=<]\s*)(\d+)\s*ms", texto, re.I)
        if m:
            return int(m.group(1))

        return round((time.perf_counter() - inicio) * 1000)
    except Exception:
        return None


# ============================================================
# 📶 WI-FI
# ============================================================

def obter_wifi_detalhado():
    dados = {
        "status": "Desconectado",
        "ssid": "--",
        "bssid": "--",
        "sinal": 0,
        "canal": "--",
        "radio": "--",
        "recepcao": "--",
        "transmissao": "--",
        "autenticacao": "--",
        "criptografia": "--",
    }

    resultado = executar_comando(
        ["netsh", "wlan", "show", "interfaces"],
        timeout=5,
        encoding="utf-8"
    )

    if not resultado:
        return dados

    for linha in resultado.stdout.splitlines():
        original = linha.strip()
        normalizada = " ".join(original.lower().split())

        if normalizada.startswith("state :") or normalizada.startswith("estado :"):
            dados["status"] = "Conectado" if (
                "connected" in normalizada or "conectado" in normalizada
            ) else "Desconectado"

        elif normalizada.startswith("ssid :"):
            dados["ssid"] = original.split(":", 1)[1].strip()

        elif normalizada.startswith("bssid :"):
            dados["bssid"] = original.split(":", 1)[1].strip()

        elif normalizada.startswith("signal :") or normalizada.startswith("sinal :"):
            try:
                dados["sinal"] = int(
                    original.split(":", 1)[1].strip().replace("%", "")
                )
            except Exception:
                pass

        elif normalizada.startswith("channel :") or normalizada.startswith("canal :"):
            dados["canal"] = original.split(":", 1)[1].strip()

        elif "radio type" in normalizada or "tipo de rádio" in normalizada:
            dados["radio"] = original.split(":", 1)[1].strip()

        elif "receive rate" in normalizada or "velocidade de recepção" in normalizada:
            dados["recepcao"] = original.split(":", 1)[1].strip()

        elif "transmit rate" in normalizada or "velocidade de transmissão" in normalizada:
            dados["transmissao"] = original.split(":", 1)[1].strip()

        elif "authentication" in normalizada or "autenticação" in normalizada:
            dados["autenticacao"] = original.split(":", 1)[1].strip()

        elif "cipher" in normalizada or "criptografia" in normalizada:
            dados["criptografia"] = original.split(":", 1)[1].strip()

    return dados


def obter_wifi_e_sinal():
    dados = obter_wifi_detalhado()
    return dados["status"], dados["sinal"]


# ============================================================
# 🔌 ETHERNET
# ============================================================

def obter_ethernet_detalhado():
    dados = {
        "status": "Desconectado",
        "nome": "--",
        "descricao": "--",
        "velocidade": "--",
        "ip": "--",
    }

    comando = (
        "Get-NetAdapter -Physical | "
        "Select-Object Name,InterfaceDescription,Status,LinkSpeed,Virtual | "
        "ConvertTo-Csv -NoTypeInformation"
    )

    resultado = executar_comando(
        ["powershell", "-NoProfile", "-Command", comando],
        timeout=8
    )

    if not resultado:
        return dados

    linhas = [x.strip() for x in resultado.stdout.splitlines() if x.strip()]

    for linha in linhas[1:]:
        try:
            campos = [x.strip().strip('"') for x in linha.split('","')]
            if len(campos) < 5:
                continue

            nome, descricao, status, velocidade, virtual = campos[:5]
            nome_l = nome.lower()
            desc_l = descricao.lower()
            virtual_l = virtual.lower()

            eh_virtual = (
                virtual_l in ("true", "1")
                or "virtualbox" in desc_l
                or "vmware" in desc_l
                or "hyper-v" in desc_l
            )

            eh_ethernet = (
                "ethernet" in nome_l
                or "ethernet" in desc_l
                or "gigabit" in desc_l
                or "realtek usb gbe" in desc_l
            )

            if eh_ethernet and not eh_virtual:
                dados["nome"] = nome
                dados["descricao"] = descricao
                dados["velocidade"] = velocidade
                dados["status"] = "Conectado" if status.lower() == "up" else "Desconectado"
                break
        except Exception:
            continue

    return dados


def obter_ethernet():
    return obter_ethernet_detalhado()["status"]


# ============================================================
# 🌎 INTERNET
# ============================================================

def testar_url(url):
    inicio = time.perf_counter()
    try:
        requisicao = urllib.request.Request(
            url,
            headers={"User-Agent": f"MonitorRede/{APP_VERSION}"}
        )
        with urllib.request.urlopen(requisicao, timeout=3) as resposta:
            resposta.read(32)

        return True, round((time.perf_counter() - inicio) * 1000)
    except Exception:
        return False, None


def testar_internet():
    with ThreadPoolExecutor(max_workers=3) as executor:
        resultados = list(executor.map(testar_url, TEST_URLS))

    for online, ms in resultados:
        if online:
            return True, ms

    return False, None


def testar_dns():
    resultados = {}
    for servidor in DNS_SERVERS:
        resultados[servidor] = ping_host(servidor, 1200) is not None
    return resultados


# ============================================================
# ⚡ LATÊNCIA
# ============================================================

def medir_latencia():
    return ping_host(LATENCIA_HOST, LATENCIA_TIMEOUT)


# ============================================================
# 🔎 DIAGNÓSTICO AUTOMÁTICO
# ============================================================

def classificar_problema(dados):
    wifi = dados.get("wifi", "Desconectado")
    sinal = dados.get("sinal_wifi", 0)
    ethernet = dados.get("ethernet", "Desconectado")
    gateway_ms = dados.get("gateway_ms")
    internet = dados.get("online", False)
    latencia = dados.get("latencia")
    dns_ok = dados.get("dns_ok", True)

    if internet:
        if latencia is not None and latencia > 200:
            return "LATÊNCIA ALTA", "A Internet está funcionando, mas a latência está acima de 200 ms."

        if wifi == "Conectado" and sinal < 30 and ethernet != "Conectado":
            return "WI-FI MUITO FRACO", "O sinal Wi-Fi está muito baixo."

        if wifi == "Conectado" and sinal < 50 and ethernet != "Conectado":
            return "WI-FI FRACO", "O sinal Wi-Fi está abaixo do ideal."

        return "NORMAL", "Conexão funcionando normalmente."

    if wifi == "Desconectado" and ethernet == "Desconectado":
        return "ADAPTADORES DESCONECTADOS", "Wi-Fi e Ethernet não estão conectados."

    if gateway_ms is None:
        if ethernet == "Desconectado" and wifi == "Desconectado":
            return "REDE LOCAL INDISPONÍVEL", "O computador não possui uma conexão local ativa."
        return "ROTEADOR INACESSÍVEL", "O computador não consegue alcançar o gateway."

    if not dns_ok:
        return "DNS INDISPONÍVEL", "O gateway responde, mas os servidores DNS não respondem."

    return "INTERNET INDISPONÍVEL", "A rede local responde, mas a Internet não está acessível."


# ============================================================
# ⚡ MEDIÇÕES PARALELAS
# ============================================================

def realizar_medicoes():
    with ThreadPoolExecutor(max_workers=7) as executor:
        f_wifi = executor.submit(obter_wifi_detalhado)
        f_eth = executor.submit(obter_ethernet_detalhado)
        f_ip = executor.submit(obter_ip)
        f_gateway = executor.submit(obter_gateway)
        f_internet = executor.submit(testar_internet)
        f_latencia = executor.submit(medir_latencia)
        f_dns = executor.submit(testar_dns)

        wifi = f_wifi.result()
        ethernet = f_eth.result()
        ip = f_ip.result()
        gateway = f_gateway.result()
        online, tempo_internet = f_internet.result()
        latencia = f_latencia.result()
        dns = f_dns.result()

    gateway_ms = ping_host(gateway, 1000) if gateway != "--" else None
    dns_ok = any(dns.values())

    if not online:
        latencia = None

    dados = {
        "wifi": wifi["status"],
        "sinal_wifi": wifi["sinal"],
        "ssid": wifi["ssid"],
        "bssid": wifi["bssid"],
        "canal": wifi["canal"],
        "radio": wifi["radio"],
        "recepcao": wifi["recepcao"],
        "transmissao": wifi["transmissao"],
        "autenticacao": wifi["autenticacao"],
        "criptografia": wifi["criptografia"],
        "ethernet": ethernet["status"],
        "ethernet_nome": ethernet["nome"],
        "ethernet_descricao": ethernet["descricao"],
        "ethernet_velocidade": ethernet["velocidade"],
        "online": online,
        "internet": "ONLINE" if online else "OFFLINE",
        "internet_ms": tempo_internet,
        "ip": ip,
        "gateway": gateway,
        "gateway_ms": gateway_ms,
        "dns": dns,
        "dns_ok": dns_ok,
        "latencia": latencia,
    }

    diagnostico, detalhe = classificar_problema(dados)
    dados["diagnostico"] = diagnostico
    dados["diagnostico_detalhe"] = detalhe

    return dados


# ============================================================
# 📝 EVENTOS
# ============================================================

def adicionar_evento_historico(evento):
    global ultimo_evento_historico

    if not evento or evento == ultimo_evento_historico:
        return

    ultimo_evento_historico = evento
    historico_eventos.insert(
        0,
        f"{datetime.now().strftime('%H:%M:%S')}  •  {evento}"
    )

    if len(historico_eventos) > 5:
        del historico_eventos[5:]


# ============================================================
# 🔄 MONITORAMENTO
# ============================================================

def monitorar():
    global estado_anterior, inicio_queda
    global contador_quedas, contador_testes, contador_sucessos
    global contador_falhas, ultima_queda, duracao_ultima_queda
    global maior_queda, ultimo_evento, ultimo_diagnostico
    global falhas_gateway, falhas_dns, falhas_internet
    global ultimo_dados

    while rodando:
        if pausado:
            time.sleep(0.5)
            continue

        inicio_ciclo = time.perf_counter()

        try:
            dados = realizar_medicoes()
            ultimo_dados = dados.copy()

            online = dados["online"]
            contador_testes += 1

            if online:
                contador_sucessos += 1
            else:
                contador_falhas += 1

            if dados["gateway_ms"] is None:
                falhas_gateway += 1

            if not dados["dns_ok"]:
                falhas_dns += 1

            if not online:
                falhas_internet += 1

            if dados["latencia"] is not None:
                latencias_todas.append(dados["latencia"])
                if len(latencias_todas) > 1000:
                    del latencias_todas[:-1000]

            estado = online

            if estado_anterior is None:
                estado_anterior = estado

                if online:
                    ultimo_evento = "Internet conectada"
                else:
                    contador_quedas += 1
                    inicio_queda = datetime.now()
                    ultima_queda = agora()
                    ultimo_evento = "Internet caiu"

                    registrar_csv("QUEDA_INICIO", dados)

            elif estado_anterior and not estado:
                contador_quedas += 1
                inicio_queda = datetime.now()
                ultima_queda = agora()
                ultimo_evento = "Internet caiu"

                registrar_csv("QUEDA_INICIO", dados)

            elif not estado_anterior and estado:
                if inicio_queda:
                    duracao = (datetime.now() - inicio_queda).total_seconds()
                    duracao_ultima_queda = formatar_duracao(duracao)
                    maior_queda = max(maior_queda, duracao)
                else:
                    duracao_ultima_queda = "--"

                ultimo_evento = "Internet restabelecida"
                registrar_csv("QUEDA_FIM", dados, duracao_ultima_queda)
                inicio_queda = None

            else:
                ultimo_evento = "Internet OK" if online else "Internet indisponível"

            estado_anterior = estado
            ultimo_diagnostico = dados["diagnostico"]

            adicionar_evento_historico(
                f"{ultimo_evento} [{dados['diagnostico']}]"
            )

            pontos.append(
                dados["latencia"] if online and dados["latencia"] is not None else None
            )
            historico_online.append(online)

            if len(pontos) > MAX_PONTOS:
                del pontos[:-MAX_PONTOS]

            if len(historico_online) > MAX_PONTOS:
                del historico_online[:-MAX_PONTOS]

            disponibilidade = (
                contador_sucessos / contador_testes * 100
                if contador_testes else 0
            )

            dados.update({
                "quedas": contador_quedas,
                "ultima_queda": ultima_queda,
                "duracao": duracao_ultima_queda,
                "maior_queda": maior_queda,
                "evento": ultimo_evento,
                "diagnostico": ultimo_diagnostico,
                "historico_eventos": list(historico_eventos),
                "disponibilidade": disponibilidade,
                "pontos": list(pontos),
                "historico_online": list(historico_online),
            })

            janela.after(0, atualizar_interface, dados)

        except Exception as e:
            print(f"Erro no monitoramento: {e}")

        tempo = time.perf_counter() - inicio_ciclo
        time.sleep(max(0.1, INTERVALO - tempo))


# ============================================================
# 🃏 CARD
# ============================================================

def criar_card(parent, titulo, cor_titulo="white"):

    frame = tk.Frame(
        parent,
        bg="#151a21",
        highlightbackground="#2b3440",
        highlightthickness=1
    )

    tk.Label(
        frame,
        text=titulo,
        bg="#151a21",
        fg=cor_titulo,
        font=(
            "Segoe UI",
            9 if MODO_COMPACTO else 10,
            "bold"
        )
    ).pack(
        anchor="w",
        padx=10 if MODO_COMPACTO else 14,
        pady=(
            6 if MODO_COMPACTO else 10,
            1
        )
    )

    valor = tk.Label(
        frame,
        text="--",
        bg="#151a21",
        fg="#f1f5f9",
        font=(
            "Segoe UI",
            13 if MODO_COMPACTO else 16,
            "bold"
        )
    )

    valor.pack(
        anchor="w",
        padx=10 if MODO_COMPACTO else 14,
        pady=(
            0,
            5 if MODO_COMPACTO else 7
        )
    )

    return frame, valor

# ============================================================
# 📶 SINAL WI-FI
# ============================================================

def atualizar_sinal_wifi(sinal):
    wifi_sinal_canvas.delete("all")

    if sinal >= 90:
        barras, cor, qualidade = 4, "#22c55e", "Excelente"
    elif sinal >= 70:
        barras, cor, qualidade = 3, "#22c55e", "Muito bom"
    elif sinal >= 50:
        barras, cor, qualidade = 2, "#eab308", "Bom"
    elif sinal >= 30:
        barras, cor, qualidade = 1, "#f97316", "Fraco"
    else:
        barras, cor, qualidade = 0, "#ef4444", "Sem sinal"

    alturas = [8, 15, 23, 32]
    largura_barra = 9
    espacamento = 5
    base_y = 43

    for i in range(4):
        x1 = 8 + i * (largura_barra + espacamento)
        x2 = x1 + largura_barra
        y2 = base_y
        y1 = y2 - alturas[i]
        wifi_sinal_canvas.create_rectangle(
            x1, y1, x2, y2,
            fill=cor if i < barras else "#26313d",
            outline=""
        )

    wifi_sinal_canvas.create_text(
        88, 14,
        text=f"{sinal}%",
        fill="#f8fafc",
        font=("Segoe UI", 12, "bold")
    )

    wifi_sinal_canvas.create_text(
        88, 36,
        text=qualidade,
        fill=cor,
        font=("Segoe UI", 8, "bold")
    )


# ============================================================
# 📊 GRÁFICO DE BARRAS
# ============================================================

def desenhar_grafico():
    grafico.delete("all")

    largura = max(grafico.winfo_width(), 500)
    altura = max(grafico.winfo_height(), 260)

    margem_esquerda = 60
    margem_direita = 25
    margem_topo = 55
    margem_base = 45    

    area_largura = largura - margem_esquerda - margem_direita
    area_altura = altura - margem_topo - margem_base

    grafico.create_text(
        margem_esquerda, 18,
        anchor="w",
        text="LATÊNCIA DA INTERNET",
        fill="#f8fafc",
        font=("Segoe UI", 12, "bold")
    )

    valores_validos = [x for x in pontos if x is not None]

    if valores_validos:
        texto_stats = (
            f"Atual: {valores_validos[-1]} ms    "
            f"Mín: {min(valores_validos)} ms    "
            f"Máx: {max(valores_validos)} ms"
        )
    else:
        texto_stats = "Aguardando medições..."

    grafico.create_text(
        largura - margem_direita, 19,
        anchor="e",
        text=texto_stats,
        fill="#94a3b8",
        font=("Segoe UI", 9, "bold")
    )

    escala_maxima = 300

    def y_pos(valor):
        valor = min(valor, escala_maxima)
        return (
            margem_topo + area_altura
            - (valor / escala_maxima) * area_altura
        )

    for valor in range(0, escala_maxima + 1, 50):

        y = y_pos(valor)

        grafico.create_line(
            margem_esquerda,
            y,
            largura - margem_direita,
            y,
            fill="#334155",
            dash=(3, 5)
        )

        grafico.create_text(
            margem_esquerda - 8,
            y,
            anchor="e",
            text=f"{valor}",
            fill="#64748b",
            font=("Segoe UI", 8)
        )

    if pontos:
        quantidade = len(pontos)
        espacamento = area_largura / max(quantidade, 1)
        largura_barra = max(3, min(14, espacamento * 0.65))
        base = margem_topo + area_altura

        for i, valor in enumerate(pontos):
            centro = margem_esquerda + (i + 0.5) * espacamento
            esquerda = centro - largura_barra / 2
            direita = centro + largura_barra / 2

            if valor is None:
                topo = base - 20
                grafico.create_rectangle(
                    esquerda, topo, direita, base,
                    fill="#ef4444", outline=""
                )
                if i == 0 or pontos[i - 1] is not None:
                    grafico.create_text(
                        centro, topo - 10,
                        text="OFF",
                        fill="#ef4444",
                        font=("Segoe UI", 7, "bold")
                    )
                continue

            topo = y_pos(valor)

            if valor <= 100:
                cor = "#22c55e"
            elif valor <= 200:
                cor = "#eab308"
            else:
                cor = "#dc582c" 

            grafico.create_rectangle(
                esquerda, topo, direita, base,
                fill=cor, outline=""
            )

            if i == quantidade - 1:
                grafico.create_rectangle(
                    esquerda - 2, topo - 2,
                    direita + 2, base,
                    outline="#f8fafc", width=2
                )
                texto = f"↑ {valor} ms" if valor > escala_maxima else f"{valor} ms"
                grafico.create_text(
                    centro, max(32, topo - 12),
                    text=texto,
                    fill="#f8fafc" if valor <= escala_maxima else "#ef4444",
                    font=("Segoe UI", 8, "bold")
                )

    grafico.create_text(
        margem_esquerda, altura - 20,
        anchor="w",
        text="~5 min atrás",
        fill="#64748b",
        font=("Segoe UI", 8)
    )

    grafico.create_text(
        largura - margem_direita, altura - 20,
        anchor="e",
        text="agora",
        fill="#64748b",
        font=("Segoe UI", 8)
    )

    # ========================================================
    # 🟢🟡🔴 LEGENDA DO GRÁFICO
    # ========================================================

    legenda_x = margem_esquerda + 95
    legenda_y = altura - 20

    legenda = [
        ("#22c55e", "0–100 ms", 105),
        ("#eab308", "101–200 ms", 120),
        ("#dc582c", ">200 ms", 90),
        ("#ef4444", "OFF", 60),
    ]

    for cor, texto, espacamento in legenda:

        grafico.create_rectangle(
            legenda_x,
            legenda_y - 5,
            legenda_x + 9,
            legenda_y + 5,
            fill=cor,
            outline=""
        )

        grafico.create_text(
            legenda_x + 15,
            legenda_y,
            anchor="w",
            text=texto,
            fill="#94a3b8",
            font=("Segoe UI", 8)
        )

        # Espaço maior entre os resultados
        legenda_x += espacamento

# ============================================================
# 🧪 JANELA DE DIAGNÓSTICO
# ============================================================

def abrir_diagnostico():
    dados = ultimo_dados.copy()

    janela_diag = tk.Toplevel(janela)
    janela_diag.title("Diagnóstico de Rede")
    janela_diag.geometry("720x600")
    janela_diag.minsize(620, 500)
    janela_diag.configure(bg="#0b0f14")

    tk.Label(
        janela_diag,
        text="DIAGNÓSTICO DE REDE",
        bg="#0b0f14",
        fg="#f8fafc",
        font=("Segoe UI", 18, "bold")
    ).pack(anchor="w", padx=22, pady=(20, 2))

    tk.Label(
        janela_diag,
        text="Análise da conexão local, gateway, DNS e Internet",
        bg="#0b0f14",
        fg="#64748b",
        font=("Segoe UI", 9)
    ).pack(anchor="w", padx=22, pady=(0, 15))

    resultado_frame = tk.Frame(
        janela_diag,
        bg="#151a21",
        highlightbackground="#2b3440",
        highlightthickness=1
    )
    resultado_frame.pack(fill="x", padx=22, pady=(0, 12))

    diag_nome = tk.Label(
        resultado_frame,
        text=dados.get("diagnostico", "Aguardando"),
        bg="#151a21",
        fg="#38bdf8",
        font=("Segoe UI", 16, "bold")
    )
    diag_nome.pack(anchor="w", padx=18, pady=(14, 2))

    diag_desc = tk.Label(
        resultado_frame,
        text=dados.get("diagnostico_detalhe", "Execute uma nova análise."),
        bg="#151a21",
        fg="#cbd5e1",
        font=("Segoe UI", 10),
        wraplength=650,
        justify="left"
    )
    diag_desc.pack(anchor="w", padx=18, pady=(0, 14))

    texto = tk.Text(
        janela_diag,
        bg="#0f141b",
        fg="#dbeafe",
        insertbackground="white",
        relief="flat",
        font=("Consolas", 10),
        padx=15,
        pady=15
    )
    texto.pack(fill="both", expand=True, padx=22, pady=8)

    def preencher(d):
        linhas = [
            "=== RESULTADO DO DIAGNÓSTICO ===",
            "",
            f"Classificação : {d.get('diagnostico', '--')}",
            f"Detalhe       : {d.get('diagnostico_detalhe', '--')}",
            "",
            "=== CONEXÃO ===",
            f"Wi-Fi         : {d.get('wifi', '--')}",
            f"Sinal Wi-Fi   : {d.get('sinal_wifi', 0)}%",
            f"SSID          : {d.get('ssid', '--')}",
            f"BSSID         : {d.get('bssid', '--')}",
            f"Canal         : {d.get('canal', '--')}",
            f"Rádio         : {d.get('radio', '--')}",
            f"Recepção      : {d.get('recepcao', '--')}",
            f"Transmissão   : {d.get('transmissao', '--')}",
            "",
            "=== ETHERNET ===",
            f"Status        : {d.get('ethernet', '--')}",
            f"Adaptador     : {d.get('ethernet_nome', '--')}",
            f"Descrição     : {d.get('ethernet_descricao', '--')}",
            f"Velocidade    : {d.get('ethernet_velocidade', '--')}",
            "",
            "=== REDE ===",
            f"IP local      : {d.get('ip', '--')}",
            f"Gateway       : {d.get('gateway', '--')}",
            f"Ping gateway  : {formatar_ms(d.get('gateway_ms'))}",
            "",
            "=== INTERNET / DNS ===",
            f"Internet      : {d.get('internet', '--')}",
            f"Latência      : {formatar_ms(d.get('latencia'))}",
            f"Teste Internet: {formatar_ms(d.get('internet_ms'))}",
            f"DNS 1.1.1.1   : {'OK' if d.get('dns', {}).get('1.1.1.1') else 'FALHA'}",
            f"DNS 8.8.8.8   : {'OK' if d.get('dns', {}).get('8.8.8.8') else 'FALHA'}",
        ]

        texto.delete("1.0", "end")
        texto.insert("1.0", "\n".join(linhas))

    preencher(dados)

    def executar_novo():
        botao.config(state="disabled", text="Analisando...")
        janela_diag.update_idletasks()

        def trabalho():
            try:
                novo = realizar_medicoes()
                janela.after(0, lambda: atualizar_diag(novo))
            finally:
                janela.after(0, lambda: botao.config(
                    state="normal", text="Executar diagnóstico"
                ))

        threading.Thread(target=trabalho, daemon=True).start()

    def atualizar_diag(d):
        preencher(d)
        diag_nome.config(text=d.get("diagnostico", "--"))
        diag_desc.config(text=d.get("diagnostico_detalhe", "--"))

    botao = tk.Button(
        janela_diag,
        text="Executar diagnóstico",
        command=executar_novo,
        bg="#1e293b",
        fg="#f8fafc",
        activebackground="#334155",
        activeforeground="#ffffff",
        relief="flat",
        padx=18,
        pady=9
    )
    botao.pack(pady=(4, 18))


# ============================================================
# 📜 JANELA DE HISTÓRICO
# ============================================================

def abrir_historico_interno():
    janela_hist = tk.Toplevel(janela)
    janela_hist.title("Histórico - Monitor de Rede")
    janela_hist.geometry("950x600")
    janela_hist.minsize(750, 450)
    janela_hist.configure(bg="#0b0f14")

    tk.Label(
        janela_hist,
        text="HISTÓRICO DE MONITORAMENTO",
        bg="#0b0f14",
        fg="#f8fafc",
        font=("Segoe UI", 17, "bold")
    ).pack(anchor="w", padx=20, pady=(18, 10))

    controles = tk.Frame(janela_hist, bg="#0b0f14")
    controles.pack(fill="x", padx=20, pady=(0, 10))

    tk.Label(
        controles, text="Período:",
        bg="#0b0f14", fg="#94a3b8"
    ).pack(side="left")

    periodo = ttk.Combobox(
        controles,
        values=["Hoje", "Últimos 7 dias", "Últimos 30 dias", "Tudo"],
        state="readonly",
        width=18
    )
    periodo.set("Tudo")
    periodo.pack(side="left", padx=8)

    tabela_frame = tk.Frame(janela_hist, bg="#0b0f14")
    tabela_frame.pack(fill="both", expand=True, padx=20, pady=5)

    colunas = (
        "Data", "Hora", "Evento", "Diagnostico",
        "Wi-Fi", "Sinal", "Ethernet", "Internet",
        "IP", "Gateway", "Latencia"
    )

    tabela = ttk.Treeview(
        tabela_frame,
        columns=colunas,
        show="headings"
    )

    larguras = {
        "Data": 85, "Hora": 70, "Evento": 125,
        "Diagnostico": 155, "Wi-Fi": 90, "Sinal": 55,
        "Ethernet": 90, "Internet": 80, "IP": 105,
        "Gateway": 105, "Latencia": 75
    }

    for coluna in colunas:
        tabela.heading(coluna, text=coluna)
        tabela.column(
            coluna,
            width=larguras.get(coluna, 90),
            anchor="center"
        )

    scroll_y = ttk.Scrollbar(
        tabela_frame, orient="vertical", command=tabela.yview
    )
    scroll_x = ttk.Scrollbar(
        tabela_frame, orient="horizontal", command=tabela.xview
    )

    tabela.configure(
        yscrollcommand=scroll_y.set,
        xscrollcommand=scroll_x.set
    )

    tabela.grid(row=0, column=0, sticky="nsew")
    scroll_y.grid(row=0, column=1, sticky="ns")
    scroll_x.grid(row=1, column=0, sticky="ew")

    tabela_frame.grid_rowconfigure(0, weight=1)
    tabela_frame.grid_columnconfigure(0, weight=1)

    def carregar():
        tabela.delete(*tabela.get_children())
        registros = ler_historico()

        hoje = datetime.now().date()

        for registro in registros:
            try:
                data = datetime.strptime(
                    registro.get("Data", ""), "%d/%m/%Y"
                ).date()
            except Exception:
                continue

            selecionado = periodo.get()

            if selecionado == "Hoje" and data != hoje:
                continue

            if selecionado == "Últimos 7 dias" and data < hoje - timedelta(days=7):
                continue

            if selecionado == "Últimos 30 dias" and data < hoje - timedelta(days=30):
                continue

            tabela.insert("", "end", values=(
                registro.get("Data", ""),
                registro.get("Hora", ""),
                registro.get("Evento", ""),
                registro.get("Diagnostico", ""),
                registro.get("Wi-Fi", ""),
                registro.get("Sinal_WiFi", ""),
                registro.get("Ethernet", ""),
                registro.get("Internet", ""),
                registro.get("IP", ""),
                registro.get("Gateway", ""),
                registro.get("Latencia_ms", ""),
            ))

    periodo.bind("<<ComboboxSelected>>", lambda e: carregar())
    carregar()


# ============================================================
# 📊 ESTATÍSTICAS
# ============================================================

def abrir_estatisticas():
    registros = ler_historico()

    janela_est = tk.Toplevel(janela)
    janela_est.title("Estatísticas")
    janela_est.geometry("620x500")
    janela_est.minsize(520, 420)
    janela_est.configure(bg="#0b0f14")

    tk.Label(
        janela_est,
        text="ESTATÍSTICAS DO MONITOR",
        bg="#0b0f14",
        fg="#f8fafc",
        font=("Segoe UI", 18, "bold")
    ).pack(anchor="w", padx=22, pady=(20, 15))

    disponibilidade = (
        contador_sucessos / contador_testes * 100
        if contador_testes else 0
    )

    if latencias_todas:
        media = sum(latencias_todas) / len(latencias_todas)
        minimo = min(latencias_todas)
        maximo = max(latencias_todas)
    else:
        media = minimo = maximo = 0

    tempo_monitorado = datetime.now() - tempo_monitoramento_inicio

    dados = [
        ("Testes realizados", contador_testes),
        ("Testes com Internet", contador_sucessos),
        ("Falhas", contador_falhas),
        ("Disponibilidade", f"{disponibilidade:.2f}%"),
        ("Total de quedas", contador_quedas),
        ("Latência média", f"{media:.0f} ms"),
        ("Latência mínima", f"{minimo} ms"),
        ("Latência máxima", f"{maximo} ms"),
        ("Maior queda", formatar_duracao(maior_queda)),
        ("Tempo desta sessão", formatar_duracao(tempo_monitorado.total_seconds())),
        ("Falhas de gateway", falhas_gateway),
        ("Falhas de DNS", falhas_dns),
        ("Falhas de Internet", falhas_internet),
    ]

    frame = tk.Frame(janela_est, bg="#151a21")
    frame.pack(fill="both", expand=True, padx=22, pady=5)

    for nome, valor in dados:
        linha = tk.Frame(frame, bg="#151a21")
        linha.pack(fill="x", padx=18, pady=6)

        tk.Label(
            linha, text=nome,
            bg="#151a21", fg="#94a3b8",
            font=("Segoe UI", 10)
        ).pack(side="left")

        tk.Label(
            linha, text=str(valor),
            bg="#151a21", fg="#f8fafc",
            font=("Segoe UI", 10, "bold")
        ).pack(side="right")


# ============================================================
# 📤 RELATÓRIO
# ============================================================

def exportar_relatorio():
    caminho = filedialog.asksaveasfilename(
        title="Salvar relatório",
        defaultextension=".txt",
        filetypes=[
            ("Relatório de texto", "*.txt"),
            ("CSV", "*.csv")
        ],
        initialfile="relatorio_monitor_rede.txt"
    )

    if not caminho:
        return

    disponibilidade = (
        contador_sucessos / contador_testes * 100
        if contador_testes else 0
    )

    media = (
        sum(latencias_todas) / len(latencias_todas)
        if latencias_todas else 0
    )

    linhas = [
        "============================================================",
        " MONITOR DE REDE - RELATÓRIO",
        "============================================================",
        f"Data do relatório : {agora()}",
        f"Aplicativo        : {APP_NAME}",
        f"Versão            : {APP_VERSION}",
        f"Desenvolvido por  : {AUTOR}",
        "",
        "=== STATUS ATUAL ===",
        f"Diagnóstico       : {ultimo_dados.get('diagnostico', '--')}",
        f"Wi-Fi             : {ultimo_dados.get('wifi', '--')}",
        f"Sinal Wi-Fi       : {ultimo_dados.get('sinal_wifi', 0)}%",
        f"SSID              : {ultimo_dados.get('ssid', '--')}",
        f"Ethernet          : {ultimo_dados.get('ethernet', '--')}",
        f"IP local          : {ultimo_dados.get('ip', '--')}",
        f"Gateway           : {ultimo_dados.get('gateway', '--')}",
        f"Ping gateway      : {formatar_ms(ultimo_dados.get('gateway_ms'))}",
        f"Internet          : {ultimo_dados.get('internet', '--')}",
        f"Latência          : {formatar_ms(ultimo_dados.get('latencia'))}",
        "",
        "=== ESTATÍSTICAS ===",
        f"Testes            : {contador_testes}",
        f"Sucessos          : {contador_sucessos}",
        f"Falhas            : {contador_falhas}",
        f"Disponibilidade   : {disponibilidade:.2f}%",
        f"Quedas            : {contador_quedas}",
        f"Latência média    : {media:.0f} ms",
        f"Maior queda       : {formatar_duracao(maior_queda)}",
        f"Falhas gateway    : {falhas_gateway}",
        f"Falhas DNS        : {falhas_dns}",
        f"Falhas Internet   : {falhas_internet}",
        "",
        "=== ÚLTIMOS EVENTOS ===",
    ]

    linhas.extend(historico_eventos)

    with open(caminho, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas))

    messagebox.showinfo(
        "Relatório",
        f"Relatório salvo com sucesso:\n\n{caminho}"
    )


# ============================================================
# ⚙️ CONFIGURAÇÕES
# ============================================================

def abrir_configuracoes():
    global INTERVALO, MAX_PONTOS, LATENCIA_HOST, LATENCIA_TIMEOUT

    janela_cfg = tk.Toplevel(janela)
    janela_cfg.title("Configurações")
    janela_cfg.geometry("520x430")
    janela_cfg.minsize(450, 380)
    janela_cfg.configure(bg="#0b0f14")

    tk.Label(
        janela_cfg,
        text="CONFIGURAÇÕES",
        bg="#0b0f14",
        fg="#f8fafc",
        font=("Segoe UI", 18, "bold")
    ).pack(anchor="w", padx=22, pady=(20, 18))

    frame = tk.Frame(janela_cfg, bg="#151a21")
    frame.pack(fill="both", expand=True, padx=22, pady=5)

    def campo(nome, valor):
        linha = tk.Frame(frame, bg="#151a21")
        linha.pack(fill="x", padx=18, pady=10)

        tk.Label(
            linha, text=nome,
            bg="#151a21", fg="#cbd5e1",
            font=("Segoe UI", 10)
        ).pack(side="left")

        entrada = tk.Entry(
            linha,
            bg="#0f141b",
            fg="#f8fafc",
            insertbackground="white",
            relief="flat",
            width=18
        )
        entrada.insert(0, str(valor))
        entrada.pack(side="right")

        return entrada

    entrada_intervalo = campo("Intervalo de monitoramento (segundos)", INTERVALO)
    entrada_pontos = campo("Quantidade de barras", MAX_PONTOS)
    entrada_host = campo("Host de latência", LATENCIA_HOST)
    entrada_timeout = campo("Timeout de ping (ms)", LATENCIA_TIMEOUT)

    def salvar():
        global INTERVALO, MAX_PONTOS, LATENCIA_HOST, LATENCIA_TIMEOUT

        try:
            novo_intervalo = float(entrada_intervalo.get().replace(",", "."))
            novo_pontos = int(entrada_pontos.get())
            novo_timeout = int(entrada_timeout.get())

            if novo_intervalo < 0.5:
                raise ValueError("O intervalo mínimo é 0,5 segundo.")

            if novo_pontos < 20:
                raise ValueError("Use pelo menos 20 pontos.")

            if novo_timeout < 500:
                raise ValueError("O timeout mínimo é 500 ms.")

            INTERVALO = novo_intervalo
            MAX_PONTOS = novo_pontos
            LATENCIA_HOST = entrada_host.get().strip() or "1.1.1.1"
            LATENCIA_TIMEOUT = novo_timeout

            if len(pontos) > MAX_PONTOS:
                del pontos[:-MAX_PONTOS]

            messagebox.showinfo(
                "Configurações",
                "Configurações salvas."
            )
            janela_cfg.destroy()

        except Exception as e:
            messagebox.showerror(
                "Configuração inválida",
                str(e)
            )

    tk.Button(
        janela_cfg,
        text="Salvar configurações",
        command=salvar,
        bg="#1e293b",
        fg="#f8fafc",
        activebackground="#334155",
        activeforeground="#ffffff",
        relief="flat",
        padx=18,
        pady=9
    ).pack(pady=15)


# ============================================================
# 📂 ABRIR CSV
# ============================================================

def abrir_historico_csv():
    inicializar_csv()
    try:
        if sys.platform == "win32":
            os.startfile(CSV_FILE)
        else:
            messagebox.showinfo("Histórico", CSV_FILE)
    except Exception as e:
        messagebox.showerror(
            "Histórico",
            f"Não foi possível abrir o arquivo:\n{e}"
        )


# ============================================================
# 📋 PAINEL RESUMO
# ============================================================

def item_resumo(nome):
    linha = tk.Frame(painel, bg="#151a21")
    linha.pack(fill="x", padx=18, pady=6)

    tk.Label(
        linha,
        text=nome,
        bg="#151a21",
        fg="#94a3b8",
        font=("Segoe UI", 9)
    ).pack(side="left")

    valor = tk.Label(
        linha,
        text="--",
        bg="#151a21",
        fg="#f8fafc",
        font=("Segoe UI", 9, "bold")
    )
    valor.pack(side="right")

    return valor


# ============================================================
# 🔄 INTERFACE
# ============================================================

def atualizar_interface(dados):
    wifi_valor.config(
        text=dados["wifi"],
        fg="#2196F3" if dados["wifi"] == "Conectado" else "#EF4444"
    )

    atualizar_sinal_wifi(dados["sinal_wifi"])

    ethernet_valor.config(
        text=dados["ethernet"],
        fg="#2196F3" if dados["ethernet"] == "Conectado" else "#EF4444"
    )

    ip_valor.config(text=dados["ip"])

    latencia_valor.config(
        text=formatar_ms(dados["latencia"]),
        fg=(
            "#22c55e" if dados["latencia"] is not None and dados["latencia"] <= 100
            else "#eab308" if dados["latencia"] is not None and dados["latencia"] <= 200
            else "#ef4444" if dados["latencia"] is not None
            else "#94a3b8"
        )
    )

    internet_valor.config(
        text=dados["internet"],
        fg="#22c55e" if dados["online"] else "#ef4444"
    )

    estado_valor.config(
        text=dados["diagnostico"],
        fg="#22c55e" if dados["diagnostico"] == "NORMAL" else "#f59e0b"
    )

    disponibilidade_valor.config(
        text=f'{dados["disponibilidade"]:.1f}%'
    )

    quedas_valor.config(text=str(dados["quedas"]))
    ultima_valor.config(text=dados["ultima_queda"])
    duracao_valor.config(text=dados["duracao"])
    gateway_valor.config(
        text=formatar_ms(dados.get("gateway_ms"))
    )
    sinal_resumo_valor.config(
        text=f'{dados["sinal_wifi"]}%'
    )

    diagnostico_valor.config(
        text=dados["diagnostico"],
        fg="#22c55e" if dados["diagnostico"] == "NORMAL" else "#f59e0b"
    )

    eventos = dados.get("historico_eventos", [])

    for i, label in enumerate(evento_labels):
        label.config(text=eventos[i] if i < len(eventos) else "")

    status_label.config(
        text=(
            f"Última verificação: {agora()}   •   "
            f"Diagnóstico: {dados['diagnostico']}   •   "
            f"Gateway: {formatar_ms(dados.get('gateway_ms'))}"
        )
    )

    desenhar_grafico()


# ============================================================
# ❌ FECHAR
# ============================================================

def fechar():
    global rodando
    rodando = False
    try:
        janela.destroy()
    except Exception:
        pass


# ============================================================
# 🖥️ JANELA - RESPONSIVA
# ============================================================

inicializar_csv()

janela = tk.Tk()
janela.title(
    f"{APP_NAME} {APP_VERSION} | Desenvolvido por {AUTOR}"
)

# ============================================================
# 📐 DETECTAR ÁREA ÚTIL REAL DO WINDOWS
# ============================================================

def obter_area_util_windows():
    """
    Retorna a área realmente disponível para a janela,
    descontando barra de tarefas e outras áreas reservadas
    pelo Windows.
    """

    largura = janela.winfo_screenwidth()
    altura = janela.winfo_screenheight()

    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            class RECT(ctypes.Structure):
                _fields_ = [
                    ("left", ctypes.c_long),
                    ("top", ctypes.c_long),
                    ("right", ctypes.c_long),
                    ("bottom", ctypes.c_long),
                ]

            class MONITORINFO(ctypes.Structure):
                _fields_ = [
                    ("cbSize", ctypes.c_ulong),
                    ("rcMonitor", RECT),
                    ("rcWork", RECT),
                    ("dwFlags", ctypes.c_ulong),
                ]

            user32 = ctypes.windll.user32

            ponto = wintypes.POINT()
            user32.GetCursorPos(ctypes.byref(ponto))

            monitor = user32.MonitorFromPoint(
                ponto,
                2  # MONITOR_DEFAULTTONEAREST
            )

            info = MONITORINFO()
            info.cbSize = ctypes.sizeof(MONITORINFO)

            if user32.GetMonitorInfoW(
                monitor,
                ctypes.byref(info)
            ):
                work = info.rcWork

                largura = work.right - work.left
                altura = work.bottom - work.top

                return (
                    largura,
                    altura,
                    work.left,
                    work.top
                )

        except Exception:
            pass

    return largura, altura, 0, 0


largura_tela, altura_tela, area_x, area_y = (
    obter_area_util_windows()
)

# ============================================================
# 📱 DIMENSIONAMENTO AUTOMÁTICO
# ============================================================

# Detecta automaticamente telas pequenas.
# Exemplo: notebook 1366x768.

MODO_COMPACTO = (
    largura_tela <= 1400
    or altura_tela <= 800
)

if MODO_COMPACTO:

    # ========================================================
    # 💻 NOTEBOOK / TELA PEQUENA
    # ========================================================

    # Usa praticamente toda a área útil disponível.
    # Isso evita que a parte inferior fique escondida.

    largura_ideal = largura_tela
    altura_ideal = altura_tela

    margem_horizontal = 0
    margem_vertical = 0

else:

    # ========================================================
    # 🖥️ MONITOR GRANDE
    # ========================================================

    largura_ideal = int(
        largura_tela * 0.94
    )

    altura_ideal = int(
        altura_tela * 0.94
    )

    margem_horizontal = 20
    margem_vertical = 15


# ============================================================
# 📐 TAMANHO MÁXIMO DISPONÍVEL
# ============================================================

largura_maxima = largura_tela

altura_maxima = altura_tela


# ============================================================
# 🖥️ TAMANHO FINAL DA JANELA
# ============================================================

largura_janela = min(
    largura_ideal,
    largura_maxima
)

altura_janela = min(
    altura_ideal,
    altura_maxima
)


# ============================================================
# 🔒 TAMANHO MÍNIMO
# ============================================================

largura_minima = min(
    760,
    largura_tela
)

altura_minima = min(
    500,
    altura_tela
)


# ============================================================
# 📍 POSIÇÃO
# ============================================================

pos_x = (
    area_x
    + max(
        0,
        (largura_tela - largura_janela) // 2
    )
)

pos_y = (
    area_y
    + max(
        0,
        (altura_tela - altura_janela) // 2
    )
)


# ============================================================
# 📐 TAMANHO MÁXIMO DISPONÍVEL
# ============================================================

largura_maxima = max(
    760,
    largura_tela - margem_horizontal
)

altura_maxima = max(
    520,
    altura_tela - margem_vertical
)


# ============================================================
# 🖥️ TAMANHO DA JANELA
# ============================================================

largura_janela = min(
    largura_ideal,
    largura_maxima
)

altura_janela = min(
    altura_ideal,
    altura_maxima
)


# ============================================================
# 🔒 GARANTIR QUE A JANELA CAIBA
# ============================================================

if MODO_COMPACTO:

    largura_minima = min(
        760,
        largura_maxima
    )

    altura_minima = min(
        520,
        altura_maxima
    )

else:

    largura_minima = min(
        900,
        largura_maxima
    )

    altura_minima = min(
        600,
        altura_maxima
    )


# ============================================================
# 📍 CENTRALIZAR NA ÁREA ÚTIL
# ============================================================

pos_x = (
    area_x
    + max(0, (largura_tela - largura_janela) // 2)
)

pos_y = (
    area_y
    + max(0, (altura_tela - altura_janela) // 2)
)


# ============================================================
# 🪟 APLICAR GEOMETRIA
# ============================================================

janela.geometry(
    f"{largura_janela}x{altura_janela}"
    f"+{pos_x}+{pos_y}"
)

janela.minsize(
    largura_minima,
    altura_minima
)

janela.configure(
    bg="#0b0f14"
)

janela.protocol(
    "WM_DELETE_WINDOW",
    fechar
)

# ============================================================
# 🎨 ESTILO
# ============================================================

style = ttk.Style()

try:
    style.theme_use("clam")
except tk.TclError:
    pass

style.configure(
    "TButton",
    font=("Segoe UI", 10, "bold"),
    padding=(10, 7)
)

style.configure(
    "Treeview",
    background="#11161d",
    foreground="#e2e8f0",
    fieldbackground="#11161d",
    rowheight=28
)

style.configure(
    "Treeview.Heading",
    background="#1e293b",
    foreground="#f8fafc",
    font=("Segoe UI", 9, "bold")
)

# ============================================================
# 🤖 ROBOZINHO JP
# ============================================================

robo_tk = None

if Image is not None and ImageTk is not None:

    try:

        # ----------------------------------------------------
        # 📁 CAMINHO DA IMAGEM
        # ----------------------------------------------------

        robo_path = resource_path(
            os.path.join(
                "assets",
                "robo_github.png"
            )
        )

        print(
            f"[ROBO] Procurando imagem em:\n{robo_path}"
        )

        # ----------------------------------------------------
        # 🖼️ CARREGAR IMAGEM
        # ----------------------------------------------------

        if os.path.exists(robo_path):

            robo_img = Image.open(
                robo_path
            ).convert("RGBA")

            # ------------------------------------------------
            # 📐 TAMANHO RESPONSIVO
            # ------------------------------------------------

            tamanho_robo = (
                (34, 34)
                if MODO_COMPACTO
                else (42, 42)
            )

            robo_img.thumbnail(
                tamanho_robo,
                Image.LANCZOS
            )

            # ------------------------------------------------
            # 🖼️ CONVERTER PARA TKINTER
            # ------------------------------------------------

            robo_tk = ImageTk.PhotoImage(
                robo_img
            )

            print(
                "[ROBO] Imagem carregada com sucesso."
            )

        else:

            print(
                f"[ROBO] ERRO: arquivo não encontrado:\n"
                f"{robo_path}"
            )

    except Exception as e:

        print(
            f"[ROBO] ERRO ao carregar imagem: {e}"
        )

else:

    print(
        "[ROBO] Pillow/ImageTk não disponível."
    )


# ============================================================
# 🧭 CABEÇALHO
# ============================================================

header = tk.Frame(
    janela,
    bg="#11161d",
    height=64 if MODO_COMPACTO else 78
)

header.pack(fill="x")
header.pack_propagate(False)

# ============================================================
# 🤖 MARCA DO AUTOR
# ============================================================

if robo_tk:

    marca_autor = tk.Label(
        header,
        image=robo_tk,
        bg="#11161d"
    )

    # Mantém a referência da imagem viva
    marca_autor.image = robo_tk

else:

    marca_autor = tk.Label(
        header,
        text=MARCA_AUTOR,
        bg="#11161d",
        fg="#ff8c00",
        font=("Segoe UI", 11, "bold")
    )

marca_autor.pack(
    side="left",
    padx=(18, 12),
    pady=8
)
marca_autor.pack(
    side="left",
    padx=(18, 12),
    pady=8
)

titulo_frame = tk.Frame(header, bg="#11161d")
titulo_frame.pack(
    side="left",
    padx=(0, 15),
    pady=8
)

tk.Label(
    titulo_frame,
    text="MONITOR DE REDE",
    bg="#11161d",
    fg="#f8fafc",
    font=("Segoe UI", 15 if MODO_COMPACTO else 18, "bold")
).pack(anchor="w")

tk.Label(
    titulo_frame,
    text=f"Desenvolvido por {AUTOR}",
    bg="#11161d",
    fg="#38bdf8",
    font=("Segoe UI", 9, "bold")
).pack(anchor="w")


# ============================================================
# 🧭 MENU - ESTILO PROFISSIONAL
# ============================================================

menu_frame = tk.Frame(
    header,
    bg="#11161d"
)

menu_frame.pack(
    side="right",
    padx=10 if MODO_COMPACTO else 15,
    pady=4
)

botoes_menu = [
    ("🔎  Diagnóstico", abrir_diagnostico),
    ("📊  Estatísticas", abrir_estatisticas),
    ("📋  Histórico", abrir_historico_interno),
    ("📄  Relatório", exportar_relatorio),
    ("⚙  Configurações", abrir_configuracoes),
]


def criar_botao_menu(parent, texto, comando):

    botao = tk.Button(
        parent,
        text=texto,
        command=comando,

        # ----------------------------------------------------
        # 🎨 APARÊNCIA
        # ----------------------------------------------------

        bg="#1b2430",
        fg="#e2e8f0",

        activebackground="#334155",
        activeforeground="#ffffff",

        relief="flat",
        bd=0,

        padx=(
            5 if MODO_COMPACTO else 9
        ),

        pady=(
            3 if MODO_COMPACTO else 5
        ),

        font=(
            "Segoe UI",
            7 if MODO_COMPACTO else 8,
            "bold"
        ),

        cursor="hand2"
    )

    # --------------------------------------------------------
    # 🖱️ EFEITO AO PASSAR O MOUSE
    # --------------------------------------------------------

    def mouse_entrou(event):
        botao.configure(
            bg="#2d3b4f",
            fg="#ffffff"
        )

    def mouse_saiu(event):
        botao.configure(
            bg="#1b2430",
            fg="#e2e8f0"
        )

    botao.bind(
        "<Enter>",
        mouse_entrou
    )

    botao.bind(
        "<Leave>",
        mouse_saiu
    )

    # --------------------------------------------------------
    # 📐 POSICIONAMENTO
    # --------------------------------------------------------

    botao.pack(
        side="left",
        padx=2
    )

    return botao


# ============================================================
# 🔘 CRIAR BOTÕES
# ============================================================

for texto, comando in botoes_menu:

    criar_botao_menu(
        menu_frame,
        texto,
        comando
    )
    
# ============================================================
# 📦 CONTEÚDO
# ============================================================

conteudo = tk.Frame(janela, bg="#0b0f14")
conteudo.pack(
    fill="both",
    expand=True,
    padx=8 if MODO_COMPACTO else 18,
    pady=(3 if MODO_COMPACTO else 7, 0
    )
)


# ============================================================
# 🃏 CARDS
# ============================================================

cards = tk.Frame(conteudo, bg="#0b0f14")
cards.pack(fill="x")

for col in range(5):
    cards.grid_columnconfigure(
        col,
        weight=1,
        uniform="cards"
    )

wifi_card, wifi_valor = criar_card(cards, "📶  WI-FI")
wifi_sinal_canvas = tk.Canvas(
    wifi_card,
    width=125,
    height=55,
    bg="#151a21",
    highlightthickness=0
)
wifi_sinal_canvas.pack(
    anchor="w",
    padx=14,
    pady=(0, 6)
)
wifi_card.grid(row=0, column=0, sticky="nsew", padx=3)

ethernet_card, ethernet_valor = criar_card(cards, "🔌  ETHERNET")
ethernet_card.grid(row=0, column=1, sticky="nsew", padx=3)

ip_card, ip_valor = criar_card(cards, "🌐  IP LOCAL")
ip_card.grid(row=0, column=2, sticky="nsew", padx=3)

lat_card, latencia_valor = criar_card(cards, "⚡  LATÊNCIA")
lat_card.grid(row=0, column=3, sticky="nsew", padx=3)

internet_card, internet_valor = criar_card(
    cards, "🌎  INTERNET", "#38bdf8"
)
internet_card.grid(row=0, column=4, sticky="nsew", padx=3)


# ============================================================
# 📊 ÁREA PRINCIPAL
# ============================================================

main = tk.Frame(conteudo, bg="#0b0f14")
main.pack(fill="both", expand=True, pady=(7, 0))

main.grid_columnconfigure(0, weight=3)
main.grid_columnconfigure(1, weight=1)
main.grid_rowconfigure(0, weight=1)

grafico = tk.Canvas(
    main,
    bg="#0b0f14",
    highlightthickness=0
)
grafico.grid(
    row=0,
    column=0,
    sticky="nsew",
    padx=(0, 7)
)
grafico.bind(
    "<Configure>",
    lambda event: desenhar_grafico()
)


# ============================================================
# 📋 PAINEL RESUMO
# ============================================================

painel = tk.Frame(
    main,
    bg="#151a21",
    highlightbackground="#2b3440",
    highlightthickness=1
)
painel.grid(
    row=0,
    column=1,
    sticky="nsew"
)

tk.Label(
    painel,
    text="RESUMO",
    bg="#151a21",
    fg="#f8fafc",
    font=("Segoe UI", 12, "bold")
).pack(
    anchor="w",
    padx=18,
    pady=(15, 10)
)

quedas_valor = item_resumo("Total de quedas")
ultima_valor = item_resumo("Última queda")
duracao_valor = item_resumo("Duração última")
estado_valor = item_resumo("Estado atual")
disponibilidade_valor = item_resumo("Disponibilidade")
gateway_valor = item_resumo("Ping gateway")
sinal_resumo_valor = item_resumo("Sinal Wi-Fi")
diagnostico_valor = item_resumo("Diagnóstico")

tk.Frame(
    painel,
    bg="#2b3440",
    height=1
).pack(fill="x", padx=18, pady=9)

tk.Label(
    painel,
    text="ÚLTIMOS EVENTOS",
    bg="#151a21",
    fg="#64748b",
    font=("Segoe UI", 8, "bold")
).pack(
    anchor="w",
    padx=18,
    pady=(0, 4)
)

eventos_frame = tk.Frame(painel, bg="#151a21")
eventos_frame.pack(fill="x", padx=18)

evento_labels = []

for _ in range(5):
    label = tk.Label(
        eventos_frame,
        text="",
        bg="#151a21",
        fg="#f8fafc",
        font=("Segoe UI", 8, "bold"),
        anchor="w",
        justify="left",
        wraplength=250
    )
    label.pack(fill="x", pady=(2, 3))
    evento_labels.append(label)


# ============================================================
# 🕐 RODAPÉ
# ============================================================

status_label = tk.Label(
    janela,
    text="Iniciando monitoramento...",
    bg="#080b0f",
    fg="#64748b",
    font=("Segoe UI", 8),
    anchor="w",
    padx=18,
    pady=5
)

rodape = tk.Label(
    janela,
    text=(
        f"© 2026 {AUTOR}  •  "
        f"{APP_NAME}  •  "
        f"v{APP_VERSION}  •  "
        "monitoramento contínuo"
    ),
    bg="#080b0f",
    fg="#e7e2e2",
    font=("Segoe UI", 8),
    anchor="center",
    pady=3
)

rodape.pack(fill="x", side="bottom")
status_label.pack(fill="x", side="bottom")


# ============================================================
# 🧵 THREAD
# ============================================================

thread = threading.Thread(
    target=monitorar,
    daemon=True
)
thread.start()


# ============================================================
# 📊 PRIMEIRO DESENHO
# ============================================================

desenhar_grafico()


# ============================================================
# 🚀 INICIAR
# ============================================================

janela.mainloop()
