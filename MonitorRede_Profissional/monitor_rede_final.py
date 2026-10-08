# ============================================================
# 📡 MONITOR DE REDE - MonitorRedesys
# ============================================================
# Central de monitoramento e diagnóstico de rede
#
# 👨‍💻 Desenvolvido por: Jorge Alberto de Paula
# 🚀 Versão: 3.1
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
import io
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
# ============================================================
# 🖼️ PIL / IMAGEM
# ============================================================
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
APP_VERSION = "3.1"
AUTOR = "Jorge Alberto de Paula"
PASTA = os.path.join(
    os.path.expanduser("~"),
    "MonitorRede"
)
CSV_FILE = os.path.join(
    PASTA,
    "monitor_rede.csv"
)
INTERVALO = 2
MAX_PONTOS = 60
LATENCIA_HOST = "1.1.1.1"
LATENCIA_TIMEOUT = 1500
# ============================================================
# 📐 RESPONSIVIDADE
# ============================================================
TELA_PEQUENA = False
# ============================================================
# 🌐 TESTES DE INTERNET
# ============================================================
TEST_URLS = [
    "https://www.msftconnecttest.com/connecttest.txt",
    "https://www.google.com/generate_204",
    "https://www.cloudflare.com/cdn-cgi/trace",
]
DNS_SERVERS = [
    "1.1.1.1",
    "8.8.8.8"
]
# ============================================================
# 📁 CRIA PASTA
# ============================================================
os.makedirs(
    PASTA,
    exist_ok=True
)
# ============================================================
# 📦 RECURSOS DO PYINSTALLER
# ============================================================
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(
        base_path,
        relative_path
    )

# ============================================================
# 🚀 SPLASH SCREEN
# ============================================================
def mostrar_splash():
    """Mostra a tela de abertura antes do painel principal."""
    splash = tk.Tk()
    splash.overrideredirect(True)
    splash.configure(bg="#08111b")
    w, h = 620, 340
    sw, sh = splash.winfo_screenwidth(), splash.winfo_screenheight()
    x, y = (sw - w) // 2, (sh - h) // 2
    splash.geometry(f"{w}x{h}+{x}+{y}")

    try:
        splash.iconbitmap(resource_path(os.path.join("assets", "monitor_rede.ico")))
    except Exception:
        pass

    card = tk.Frame(
        splash, bg="#0e1823",
        highlightbackground="#1f3a52",
        highlightthickness=1
    )
    card.pack(fill="both", expand=True, padx=2, pady=2)

    try:
        _robo_img = Image.open(resource_path(os.path.join("assets", "robo_jp.png")))
        _robo_img = _robo_img.resize((150, 150), Image.Resampling.LANCZOS)
        _robo_tk = ImageTk.PhotoImage(_robo_img)
        _robo_label = tk.Label(card, image=_robo_tk, bg="#0e1823")
        _robo_label.image = _robo_tk
        _robo_label.pack(pady=(18, 0))
    except Exception:
        tk.Label(
            card, text="JP", bg="#0e1823", fg="#38bdf8",
            font=(FONTE, 38, "bold")
        ).pack(pady=(35, 0))

    tk.Label(
        card, text="MONITOR DE REDE",
        bg="#0e1823", fg="#f8fafc",
        font=(FONTE, 24, "bold")
    ).pack(pady=(4, 0))

    tk.Label(
        card, text=f"Wi-Fi  •  Ethernet  •  Internet   |   versão {APP_VERSION}",
        bg="#0e1823", fg="#94a3b8",
        font=(FONTE, 10)
    ).pack(pady=(6, 0))

    tk.Label(
        card, text=AUTOR,
        bg="#0e1823", fg="#38bdf8",
        font=(FONTE, 9, "bold")
    ).pack(pady=(18, 0))

    barra = ttk.Progressbar(
        card, mode="indeterminate", length=360
    )
    barra.pack(pady=(24, 4))
    barra.start(12)

    tk.Label(
        card, text="Inicializando monitoramento...",
        bg="#0e1823", fg="#64748b",
        font=(FONTE, 8)
    ).pack()

    splash.update()
    splash.after(1800, splash.destroy)
    splash.mainloop()

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
    return datetime.now().strftime(
        "%d/%m/%Y %H:%M:%S"
    )
# ============================================================
# FORMATAR MS
# ============================================================
def formatar_ms(ms):
    if ms is None:
        return "--"
    return f"{ms} ms"
# ============================================================
# FORMATAR DURAÇÃO
# ============================================================
def formatar_duracao(segundos):
    try:
        segundos = max(
            0,
            int(segundos)
        )
    except Exception:
        segundos = 0
    horas, resto = divmod(
        segundos,
        3600
    )
    minutos, segundos = divmod(
        resto,
        60
    )
    if horas:
        return (
            f"{horas:02d}:"
            f"{minutos:02d}:"
            f"{segundos:02d}"
        )
    return (
        f"{minutos:02d}:"
        f"{segundos:02d}"
    )
# ============================================================
# EXECUTAR COMANDO SEM JANELA PRETA
# ============================================================
def executar_comando(
    comando,
    timeout=5,
    encoding="utf-8"
):
    try:
        creationflags = 0
        if sys.platform == "win32":
            creationflags = (
                subprocess.CREATE_NO_WINDOW
            )
        return subprocess.run(
            comando,
            capture_output=True,
            text=True,
            encoding=encoding,
            errors="ignore",
            timeout=timeout,
            creationflags=creationflags
        )
    except Exception:
        return None
# ============================================================
# 📄 CSV
# ============================================================
def inicializar_csv():
    if (
        not os.path.exists(CSV_FILE)
        or os.path.getsize(CSV_FILE) == 0
    ):
        with open(
            CSV_FILE,
            "w",
            newline="",
            encoding="utf-8-sig"
        ) as f:
            csv.writer(
                f,
                delimiter=";"
            ).writerow([
                "Data",
                "Hora",
                "Evento",
                "Diagnostico",
                "Wi-Fi",
                "Sinal_WiFi",
                "Ethernet",
                "Internet",
                "IP",
                "Gateway",
                "Gateway_ms",
                "Latencia_ms",
                "Duracao_queda"
            ])
# ============================================================
# REGISTRAR CSV
# ============================================================
def registrar_csv(
    evento,
    dados=None,
    duracao="--"
):
    inicializar_csv()
    dados = dados or {}
    dt = datetime.now()
    try:
        with open(
            CSV_FILE,
            "a",
            newline="",
            encoding="utf-8-sig"
        ) as f:
            csv.writer(
                f,
                delimiter=";"
            ).writerow([
                dt.strftime("%d/%m/%Y"),
                dt.strftime("%H:%M:%S"),
                evento,
                dados.get(
                    "diagnostico",
                    "--"
                ),
                dados.get(
                    "wifi",
                    "--"
                ),
                dados.get(
                    "sinal_wifi",
                    0
                ),
                dados.get(
                    "ethernet",
                    "--"
                ),
                dados.get(
                    "internet",
                    "--"
                ),
                dados.get(
                    "ip",
                    "--"
                ),
                dados.get(
                    "gateway",
                    "--"
                ),
                dados.get(
                    "gateway_ms",
                    "--"
                ),
                dados.get(
                    "latencia",
                    "--"
                ),
                duracao
            ])
    except Exception as e:
        print(
            f"[CSV] Erro ao registrar: {e}"
        )
# ============================================================
# LER HISTÓRICO
# ============================================================
def ler_historico():
    inicializar_csv()
    try:
        with open(
            CSV_FILE,
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as f:
            linhas = list(
                csv.reader(
                    f,
                    delimiter=";"
                )
            )
        if not linhas:
            return []
        registros = []
        primeiro = [
            str(x).strip()
            for x in linhas[0]
        ]
        tem_cabecalho = (
            "Data" in primeiro
            or "Hora" in primeiro
            or "Evento" in primeiro
        )
        # ====================================================
        # CSV NOVO
        # ====================================================
        if tem_cabecalho:
            cabecalho = primeiro
            for linha in linhas[1:]:
                if not linha:
                    continue
                registro = {}
                for i, coluna in enumerate(
                    cabecalho
                ):
                    registro[coluna] = (
                        linha[i].strip()
                        if i < len(linha)
                        else ""
                    )
                registros.append(
                    registro
                )
            return registros
        # ====================================================
        # CSV ANTIGO
        # ====================================================
        for linha in linhas:
            if not linha:
                continue
            linha = [
                str(x).strip()
                for x in linha
            ]
            if len(linha) >= 9:
                evento = linha[2]
                if evento == "QUEDA_FIM":
                    diagnostico = "NORMAL"
                elif evento == "QUEDA_INICIO":
                    diagnostico = "QUEDA"
                else:
                    diagnostico = ""
                registro = {
                    "Data": linha[0],
                    "Hora": linha[1],
                    "Evento": evento,
                    "Diagnostico": diagnostico,
                    "Wi-Fi": linha[3],
                    "Sinal_WiFi": "",
                    "Ethernet": linha[4],
                    "Internet": linha[5],
                    "IP": linha[6],
                    "Gateway": "",
                    "Gateway_ms": "",
                    "Latencia_ms": linha[7],
                    "Duracao_queda": linha[8]
                }
                registros.append(
                    registro
                )
        return registros
    except Exception as e:
        print(
            f"[HISTÓRICO] Erro: {e}"
        )
        return []
# ============================================================
# 🌐 IP LOCAL
# ============================================================
def obter_ip():
    # ========================================================
    # PRIMEIRA TENTATIVA
    # Obtém o IP associado à rota padrão.
    # ========================================================
    try:
        comando = (
            "Get-NetIPConfiguration | "
            "Where-Object { "
            "$_.NetAdapter.Status -eq 'Up' "
            "-and $_.IPv4DefaultGateway "
            "} | "
            "ForEach-Object { "
            "$_.IPv4Address.IPAddress "
            "} | "
            "Select-Object -First 1"
        )
        resultado = executar_comando(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                comando
            ],
            timeout=5
        )
        if resultado:
            ip = (
                resultado.stdout
                .strip()
                .splitlines()
            )
            if ip:
                valor = ip[0].strip()
                if (
                    valor
                    and valor != "0.0.0.0"
                    and valor != "127.0.0.1"
                ):
                    return valor
    except Exception:
        pass
    # ========================================================
    # FALLBACK SOCKET
    # ========================================================
    s = None
    try:
        s = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM
        )
        s.settimeout(2)
        s.connect(
            ("1.1.1.1", 80)
        )
        ip = s.getsockname()[0]
        if (
            ip
            and ip != "0.0.0.0"
            and ip != "127.0.0.1"
        ):
            return ip
    except Exception:
        pass
    finally:
        if s:
            try:
                s.close()
            except Exception:
                pass
    # ========================================================
    # FALLBACK HOSTNAME
    # ========================================================
    try:
        ip = socket.gethostbyname(
            socket.gethostname()
        )
        if (
            ip
            and ip != "127.0.0.1"
        ):
            return ip
    except Exception:
        pass
    return "--"
# ============================================================
# 🌐 GATEWAY
# ============================================================
def obter_gateway():
    # ========================================================
    # MÉTODO PRINCIPAL
    # Só considera interfaces:
    # - UP
    # - com gateway IPv4
    # ========================================================
    try:
        comando = (
            "Get-NetIPConfiguration | "
            "Where-Object { "
            "$_.NetAdapter.Status -eq 'Up' "
            "-and $_.IPv4DefaultGateway "
            "} | "
            "ForEach-Object { "
            "$_.IPv4DefaultGateway.NextHop "
            "} | "
            "Select-Object -First 1"
        )
        resultado = executar_comando(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                comando
            ],
            timeout=5
        )
        if resultado:
            linhas = [
                x.strip()
                for x in resultado.stdout.splitlines()
                if x.strip()
            ]
            for gateway in linhas:
                if re.match(
                    r"^\d{1,3}(?:\.\d{1,3}){3}$",
                    gateway
                ):
                    return gateway
    except Exception:
        pass
    # ========================================================
    # FALLBACK - GET-NETROUTE
    # ========================================================
    try:
        comando = (
            "Get-NetRoute "
            "-AddressFamily IPv4 "
            "-DestinationPrefix '0.0.0.0/0' "
            "| Where-Object { "
            "$_.NextHop -and "
            "$_.State -eq 'Alive' "
            "} "
            "| Sort-Object RouteMetric "
            "| Select-Object -First 1 "
            "-ExpandProperty NextHop"
        )
        resultado = executar_comando(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                comando
            ],
            timeout=5
        )
        if resultado:
            gateway = (
                resultado.stdout.strip()
            )
            if re.match(
                r"^\d{1,3}(?:\.\d{1,3}){3}$",
                gateway
            ):
                return gateway
    except Exception:
        pass
    # ========================================================
    # FALLBACK - ROUTE PRINT
    # ========================================================
    try:
        resultado = executar_comando(
            [
                "route",
                "print",
                "-4"
            ],
            timeout=5,
            encoding="cp850"
        )
        if resultado:
            for linha in resultado.stdout.splitlines():
                partes = linha.split()
                if len(partes) >= 3:
                    if (
                        partes[0] == "0.0.0.0"
                        and partes[1] == "0.0.0.0"
                    ):
                        gateway = partes[2]
                        if re.match(
                            r"^\d{1,3}(?:\.\d{1,3}){3}$",
                            gateway
                        ):
                            return gateway
    except Exception:
        pass
    return "--"
# ============================================================
# 📡 PING
# ============================================================
def ping_host(
    host,
    timeout=1000
):
    if not host or host == "--":
        return None
    try:
        inicio = time.perf_counter()
        resultado = executar_comando(
            [
                "ping",
                "-4",
                "-n",
                "1",
                "-w",
                str(timeout),
                host
            ],
            timeout=max(
                2,
                timeout / 1000 + 1
            ),
            encoding="cp850"
        )
        if not resultado:
            return None
        texto = (
            (resultado.stdout or "")
            + "\n"
            + (resultado.stderr or "")
        )
        # ====================================================
        # LATÊNCIA NORMAL
        # ====================================================
        padroes = [
            r"[=<]\s*(\d+)\s*ms",
            r"(?:tempo|time)"
            r"\s*[=<]\s*(\d+)\s*ms"
        ]
        for padrao in padroes:
            encontrado = re.search(
                padrao,
                texto,
                re.IGNORECASE
            )
            if encontrado:
                return int(
                    encontrado.group(1)
                )
        # ====================================================
        # <1 ms
        # ====================================================
        if re.search(
            r"(?:tempo|time)"
            r"\s*<\s*1\s*ms",
            texto,
            re.IGNORECASE
        ):
            return 1
        if resultado.returncode != 0:
            return None
        # ====================================================
        # FALLBACK
        # ====================================================
        return max(
            1,
            round(
                (
                    time.perf_counter()
                    - inicio
                ) * 1000
            )
        )
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
        "criptografia": "--"
    }
    resultado = executar_comando(
        [
            "netsh",
            "wlan",
            "show",
            "interfaces"
        ],
        timeout=5,
        encoding="cp850"
    )
    if not resultado:
        resultado = executar_comando(
            [
                "netsh",
                "wlan",
                "show",
                "interfaces"
            ],
            timeout=5,
            encoding="utf-8"
        )
    if not resultado:
        return dados
    # ========================================================
    # CONVERTE SAÍDA PARA LINHAS
    # ========================================================
    linhas = resultado.stdout.splitlines()
    interface_encontrada = False
    interface_conectada = False
    # ========================================================
    # FUNÇÃO INTERNA PARA NORMALIZAÇÃO
    # ========================================================
    def normalizar(texto):
        texto = (
            texto
            .lower()
            .strip()
        )
        substituicoes = {
            "ã": "a",
            "á": "a",
            "â": "a",
            "à": "a",
            "é": "e",
            "ê": "e",
            "í": "i",
            "ó": "o",
            "ô": "o",
            "ú": "u",
            "ç": "c"
        }
        for antigo, novo in substituicoes.items():
            texto = texto.replace(
                antigo,
                novo
            )
        return " ".join(
            texto.split()
        )
    # ========================================================
    # IDENTIFICA INTERFACE
    # ========================================================
    for linha in linhas:
        original = linha.strip()
        if not original:
            continue
        normalizada = normalizar(
            original
        )
        if ":" not in normalizada:
            continue
        chave, valor = normalizada.split(
            ":",
            1
        )
        valor_original = original.split(
            ":",
            1
        )[1].strip()
        chave = chave.strip()
        valor = valor.strip()
        # ====================================================
        # STATE / ESTADO
        # ====================================================
        if chave in (
            "state",
            "estado"
        ):
            if (
                "connected" in valor
                or "conectado" in valor
            ):
                dados["status"] = "Conectado"
                interface_conectada = True
                interface_encontrada = True
            elif (
                "disconnected" in valor
                or "desconectado" in valor
            ):
                if not interface_conectada:
                    dados["status"] = (
                        "Desconectado"
                    )
        # ====================================================
        # SSID
        # ====================================================
        elif chave == "ssid":
            # IMPORTANTE:
            # BSSID NÃO entra aqui.
            if valor_original:
                dados["ssid"] = (
                    valor_original
                )
        # ====================================================
        # BSSID
        # ====================================================
        elif chave == "bssid":
            if valor_original:
                dados["bssid"] = (
                    valor_original
                )
        # ====================================================
        # SIGNAL / SINAL
        # ====================================================
        elif chave in (
            "signal",
            "sinal"
        ):
            match = re.search(
                r"(\d+)",
                valor_original
            )
            if match:
                try:
                    dados["sinal"] = max(
                        0,
                        min(
                            100,
                            int(
                                match.group(1)
                            )
                        )
                    )
                except Exception:
                    pass
        # ====================================================
        # CHANNEL / CANAL
        # ====================================================
        elif chave in (
            "channel",
            "canal"
        ):
            dados["canal"] = (
                valor_original
                or "--"
            )
        # ====================================================
        # RADIO TYPE
        # ====================================================
        elif (
            "radio type" in chave
            or "tipo de radio" in chave
        ):
            dados["radio"] = (
                valor_original
                or "--"
            )
        # ====================================================
        # RECEIVE RATE
        # ====================================================
        elif (
            "receive rate" in chave
            or "velocidade de recepcao" in chave
        ):
            dados["recepcao"] = (
                valor_original
                or "--"
            )
        # ====================================================
        # TRANSMIT RATE
        # ====================================================
        elif (
            "transmit rate" in chave
            or "velocidade de transmissao" in chave
        ):
            dados["transmissao"] = (
                valor_original
                or "--"
            )
        # ====================================================
        # AUTHENTICATION
        # ====================================================
        elif (
            "authentication" in chave
            or "autenticacao" in chave
        ):
            dados["autenticacao"] = (
                valor_original
                or "--"
            )
        # ====================================================
        # CIPHER
        # ====================================================
        elif (
            "cipher" in chave
            or "criptografia" in chave
        ):
            dados["criptografia"] = (
                valor_original
                or "--"
            )
    # ========================================================
    # GARANTIA FINAL
    # ========================================================
    if interface_conectada:
        dados["status"] = "Conectado"
    elif not interface_encontrada:
        # Caso o Windows não apresente "State"
        # mas exista SSID/BSSID/sinal.
        if (
            dados["ssid"] != "--"
            and dados["bssid"] != "--"
        ):
            dados["status"] = "Conectado"
    return dados
# ============================================================
# 🔌 ETHERNET
# ============================================================
def obter_ethernet_detalhado():
    dados = {
        "status": "Desconectado",
        "nome": "--",
        "descricao": "--",
        "velocidade": "--",
        "ip": "--"
    }
    comando = (
        "Get-NetAdapter -Physical | "
        "Select-Object "
        "Name,"
        "InterfaceDescription,"
        "Status,"
        "LinkSpeed,"
        "Virtual "
        "| ConvertTo-Csv -NoTypeInformation"
    )
    resultado = executar_comando(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            comando
        ],
        timeout=8
    )
    if not resultado:
        return dados
    try:
        leitor = csv.reader(
            io.StringIO(
                resultado.stdout
            )
        )
        linhas = list(leitor)
    except Exception:
        return dados
    if len(linhas) < 2:
        return dados
    cabecalho = [
        x.strip()
        for x in linhas[0]
    ]
    for linha in linhas[1:]:
        if len(linha) < 4:
            continue
        registro = dict(
            zip(
                cabecalho,
                linha
            )
        )
        nome = registro.get(
            "Name",
            ""
        ).strip()
        descricao = registro.get(
            "InterfaceDescription",
            ""
        ).strip()
        status = registro.get(
            "Status",
            ""
        ).strip()
        velocidade = registro.get(
            "LinkSpeed",
            ""
        ).strip()
        virtual = registro.get(
            "Virtual",
            ""
        ).strip()
        nome_l = nome.lower()
        desc_l = descricao.lower()
        virtual_l = virtual.lower()
        eh_virtual = (
            virtual_l in (
                "true",
                "1"
            )
            or "virtualbox" in desc_l
            or "vmware" in desc_l
            or "hyper-v" in desc_l
            or "vethernet" in desc_l
        )
        eh_ethernet = (
            "ethernet" in nome_l
            or "ethernet" in desc_l
            or "gigabit" in desc_l
            or "realtek usb gbe" in desc_l
            or "usb gbe" in desc_l
            or "gbe family controller" in desc_l
        )
        if (
            eh_ethernet
            and not eh_virtual
        ):
            dados["nome"] = (
                nome or "--"
            )
            dados["descricao"] = (
                descricao or "--"
            )
            dados["velocidade"] = (
                velocidade or "--"
            )
            dados["status"] = (
                "Conectado"
                if status.lower() == "up"
                else "Desconectado"
            )
            break
    return dados
# ============================================================
# ETHERNET SIMPLIFICADO
# ============================================================
def obter_ethernet():
    return obter_ethernet_detalhado()[
        "status"
    ]
# ============================================================
# 🌎 INTERNET
# ============================================================
def testar_url(url):
    inicio = time.perf_counter()
    try:
        requisicao = urllib.request.Request(
            url,
            headers={
                "User-Agent":
                f"MonitorRede/{APP_VERSION}"
            }
        )
        with urllib.request.urlopen(
            requisicao,
            timeout=3
        ) as resposta:
            resposta.read(32)
        return (
            True,
            round(
                (
                    time.perf_counter()
                    - inicio
                ) * 1000
            )
        )
    except Exception:
        return (
            False,
            None
        )
# ============================================================
# TESTAR INTERNET
# ============================================================
def testar_internet():
    with ThreadPoolExecutor(
        max_workers=3
    ) as executor:
        resultados = list(
            executor.map(
                testar_url,
                TEST_URLS
            )
        )
    tempos = []
    for online, ms in resultados:
        if online:
            if ms is not None:
                tempos.append(ms)
    if tempos:
        return (
            True,
            min(tempos)
        )
    return (
        False,
        None
    )
# ============================================================
# DNS
# ============================================================
def testar_dns():
    resultados = {}
    with ThreadPoolExecutor(
        max_workers=2
    ) as executor:
        futuros = {
            servidor:
            executor.submit(
                ping_host,
                servidor,
                1200
            )
            for servidor in DNS_SERVERS
        }
        for servidor, futuro in futuros.items():
            try:
                resultados[servidor] = (
                    futuro.result()
                    is not None
                )
            except Exception:
                resultados[servidor] = False
    return resultados
# ============================================================
# ⚡ LATÊNCIA
# ============================================================
def medir_latencia():
    return ping_host(
        LATENCIA_HOST,
        LATENCIA_TIMEOUT
    )
# ============================================================
# 🔎 DIAGNÓSTICO
# ============================================================
def classificar_problema(dados):
    wifi = dados.get(
        "wifi",
        "Desconectado"
    )
    sinal = dados.get(
        "sinal_wifi",
        0
    )
    ethernet = dados.get(
        "ethernet",
        "Desconectado"
    )
    gateway_ms = dados.get(
        "gateway_ms"
    )
    internet = dados.get(
        "online",
        False
    )
    latencia = dados.get(
        "latencia"
    )
    dns_ok = dados.get(
        "dns_ok",
        True
    )
    # ========================================================
    # INTERNET ONLINE
    # ========================================================
    if internet:
        if (
            latencia is not None
            and latencia > 100
        ):
            return (
                "LATÊNCIA ALTA",
                "A Internet está funcionando, "
                "mas a latência está acima de 100 ms."
            )
        if (
            wifi == "Conectado"
            and sinal < 30
            and ethernet != "Conectado"
        ):
            return (
                "WI-FI MUITO FRACO",
                "O sinal Wi-Fi está muito baixo."
            )
        if (
            wifi == "Conectado"
            and sinal < 50
            and ethernet != "Conectado"
        ):
            return (
                "WI-FI FRACO",
                "O sinal Wi-Fi está abaixo do ideal."
            )
        return (
            "NORMAL",
            "Conexão funcionando normalmente."
        )
    # ========================================================
    # SEM ADAPTADOR
    # ========================================================
    if (
        wifi == "Desconectado"
        and ethernet == "Desconectado"
    ):
        return (
            "ADAPTADORES DESCONECTADOS",
            "Wi-Fi e Ethernet não estão conectados."
        )
    # ========================================================
    # SEM GATEWAY
    # ========================================================
    if gateway_ms is None:
        if (
            ethernet == "Desconectado"
            and wifi == "Desconectado"
        ):
            return (
                "REDE LOCAL INDISPONÍVEL",
                "O computador não possui uma conexão local ativa."
            )
        return (
            "ROTEADOR INACESSÍVEL",
            "O computador não consegue alcançar o gateway."
        )
    # ========================================================
    # DNS
    # ========================================================
    if not dns_ok:
        return (
            "DNS INDISPONÍVEL",
            "O gateway responde, mas os servidores DNS não respondem."
        )
    # ========================================================
    # INTERNET
    # ========================================================
    return (
        "INTERNET INDISPONÍVEL",
        "A rede local responde, mas a Internet não está acessível."
    )
# ============================================================
# ⚡ MEDIÇÕES PARALELAS
# ============================================================
def realizar_medicoes():
    with ThreadPoolExecutor(
        max_workers=7
    ) as executor:
        f_wifi = executor.submit(
            obter_wifi_detalhado
        )
        f_eth = executor.submit(
            obter_ethernet_detalhado
        )
        f_ip = executor.submit(
            obter_ip
        )
        f_gateway = executor.submit(
            obter_gateway
        )
        f_internet = executor.submit(
            testar_internet
        )
        f_latencia = executor.submit(
            medir_latencia
        )
        f_dns = executor.submit(
            testar_dns
        )
        wifi = f_wifi.result()
        ethernet = f_eth.result()
        ip = f_ip.result()
        gateway = f_gateway.result()
        online, tempo_internet = (
            f_internet.result()
        )
        latencia = f_latencia.result()
        dns = f_dns.result()
    # ========================================================
    # PING GATEWAY
    # ========================================================
    gateway_ms = None
    if gateway != "--":
        gateway_ms = ping_host(
            gateway,
            1000
        )
    dns_ok = any(
        dns.values()
    )
    print(
        f"[DEBUG] "
        f"Wi-Fi: {wifi['status']} | "
        f"Sinal: {wifi['sinal']}% | "
        f"SSID: {wifi['ssid']} | "
        f"Ethernet: {ethernet['status']} | "
        f"IP: {ip} | "
        f"Gateway: {gateway} | "
        f"Ping Gateway: {gateway_ms} | "
        f"Internet: {online} | "
        f"Latência: {latencia}"
    )
    # ========================================================
    # SE INTERNET ESTIVER OFFLINE,
    # NÃO MOSTRA LATÊNCIA COMO VÁLIDA.
    # ========================================================
    if not online:
        latencia = None
    dados = {
        "wifi":
            wifi["status"],
        "sinal_wifi":
            wifi["sinal"],
        "ssid":
            wifi["ssid"],
        "bssid":
            wifi["bssid"],
        "canal":
            wifi["canal"],
        "radio":
            wifi["radio"],
        "recepcao":
            wifi["recepcao"],
        "transmissao":
            wifi["transmissao"],
        "autenticacao":
            wifi["autenticacao"],
        "criptografia":
            wifi["criptografia"],
        "ethernet":
            ethernet["status"],
        "ethernet_nome":
            ethernet["nome"],
        "ethernet_descricao":
            ethernet["descricao"],
        "ethernet_velocidade":
            ethernet["velocidade"],
        "online":
            online,
        "internet":
            "ONLINE"
            if online
            else "OFFLINE",
        "internet_ms":
            tempo_internet,
        "ip":
            ip,
        "gateway":
            gateway,
        "gateway_ms":
            gateway_ms,
        "dns":
            dns,
        "dns_ok":
            dns_ok,
        "latencia":
            latencia
    }
    diagnostico, detalhe = (
        classificar_problema(
            dados
        )
    )
    dados["diagnostico"] = (
        diagnostico
    )
    dados["diagnostico_detalhe"] = (
        detalhe
    )
    return dados
# ============================================================
# 📝 HISTÓRICO DE EVENTOS
# ============================================================
def adicionar_evento_historico(
    evento
):
    global ultimo_evento_historico
    if (
        not evento
        or evento == ultimo_evento_historico
    ):
        return
    ultimo_evento_historico = (
        evento
    )
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
    global estado_anterior
    global inicio_queda
    global contador_quedas
    global contador_testes
    global contador_sucessos
    global contador_falhas
    global ultima_queda
    global duracao_ultima_queda
    global maior_queda
    global ultimo_evento
    global ultimo_diagnostico
    global falhas_gateway
    global falhas_dns
    global falhas_internet
    global ultimo_dados
    while rodando:
        if pausado:
            time.sleep(0.5)
            continue
        inicio_ciclo = (
            time.perf_counter()
        )
        try:
            dados = realizar_medicoes()
            ultimo_dados = (
                dados.copy()
            )
            online = dados[
                "online"
            ]
            contador_testes += 1
            # =================================================
            # REGISTRA MONITORAMENTO
            # =================================================
            registrar_csv(
                "MONITORAMENTO",
                dados
            )
            # =================================================
            # SUCESSOS / FALHAS
            # =================================================
            if online:
                contador_sucessos += 1
            else:
                contador_falhas += 1
            # =================================================
            # FALHAS DE GATEWAY
            # =================================================
            if (
                dados["gateway_ms"]
                is None
            ):
                falhas_gateway += 1
            # =================================================
            # FALHAS DNS
            # =================================================
            if not dados["dns_ok"]:
                falhas_dns += 1
            # =================================================
            # FALHAS INTERNET
            # =================================================
            if not online:
                falhas_internet += 1
            # =================================================
            # LATÊNCIAS
            # =================================================
            if (
                dados["latencia"]
                is not None
            ):
                latencias_todas.append(
                    dados["latencia"]
                )
                if len(
                    latencias_todas
                ) > 1000:
                    del latencias_todas[
                        :-1000
                    ]
            # =================================================
            # ESTADO
            # =================================================
            estado = online
            # =================================================
            # PRIMEIRA MEDIÇÃO
            # =================================================
            if estado_anterior is None:
                estado_anterior = estado
                if online:
                    ultimo_evento = (
                        "Internet conectada"
                    )
                else:
                    contador_quedas += 1
                    inicio_queda = (
                        datetime.now()
                    )
                    ultima_queda = agora()
                    ultimo_evento = (
                        "Internet caiu"
                    )
                    registrar_csv(
                        "QUEDA_INICIO",
                        dados
                    )
            # =================================================
            # INTERNET CAIU
            # =================================================
            elif (
                estado_anterior
                and not estado
            ):
                contador_quedas += 1
                inicio_queda = (
                    datetime.now()
                )
                ultima_queda = agora()
                ultimo_evento = (
                    "Internet caiu"
                )
                registrar_csv(
                    "QUEDA_INICIO",
                    dados
                )
            # =================================================
            # INTERNET VOLTOU
            # =================================================
            elif (
                not estado_anterior
                and estado
            ):
                if inicio_queda:
                    duracao = (
                        datetime.now()
                        - inicio_queda
                    ).total_seconds()
                    duracao_ultima_queda = (
                        formatar_duracao(
                            duracao
                        )
                    )
                    maior_queda = max(
                        maior_queda,
                        duracao
                    )
                else:
                    duracao_ultima_queda = (
                        "--"
                    )
                ultimo_evento = (
                    "Internet restabelecida"
                )
                registrar_csv(
                    "QUEDA_FIM",
                    dados,
                    duracao_ultima_queda
                )
                inicio_queda = None
            # =================================================
            # SEM MUDANÇA
            # =================================================
            else:
                ultimo_evento = (
                    "Internet OK"
                    if online
                    else
                    "Internet indisponível"
                )
            estado_anterior = estado
            ultimo_diagnostico = (
                dados["diagnostico"]
            )
            adicionar_evento_historico(
                f"{ultimo_evento} "
                f"[{dados['diagnostico']}]"
            )
            # =================================================
            # GRÁFICO
            # =================================================
            pontos.append(
                dados["latencia"]
                if (
                    online
                    and dados["latencia"]
                    is not None
                )
                else None
            )
            historico_online.append(
                online
            )
            if len(pontos) > MAX_PONTOS:
                del pontos[
                    :-MAX_PONTOS
                ]
            if len(
                historico_online
            ) > MAX_PONTOS:
                del historico_online[
                    :-MAX_PONTOS
                ]
            # =================================================
            # DISPONIBILIDADE
            # =================================================
            disponibilidade = (
                contador_sucessos
                / contador_testes
                * 100
                if contador_testes
                else 0
            )
            dados.update({
                "quedas":
                    contador_quedas,
                "ultima_queda":
                    ultima_queda,
                "duracao":
                    duracao_ultima_queda,
                "maior_queda":
                    maior_queda,
                "evento":
                    ultimo_evento,
                "diagnostico":
                    ultimo_diagnostico,
                "historico_eventos":
                    list(
                        historico_eventos
                    ),
                "disponibilidade":
                    disponibilidade,
                "pontos":
                    list(pontos),
                "historico_online":
                    list(
                        historico_online
                    )
            })
            # =================================================
            # ATUALIZA UI
            # =================================================
            if janela.winfo_exists():
                janela.after(
                    0,
                    atualizar_interface,
                    dados
                )
        except Exception as e:
            print(
                f"[MONITOR] "
                f"Erro no monitoramento: {e}"
            )
        tempo = (
            time.perf_counter()
            - inicio_ciclo
        )
        time.sleep(
            max(
                0.1,
                INTERVALO - tempo
            )
        )

# ============================================================
# 🎨 INTERFACE PROFISSIONAL - DASHBOARD
# ============================================================

CORES = {
    "bg": "#0a0f16",
    "surface": "#111923",
    "surface2": "#16212d",
    "border": "#243344",
    "text": "#f1f5f9",
    "muted": "#8291a5",
    "blue": "#38bdf8",
    "green": "#22c55e",
    "yellow": "#f59e0b",
    "red": "#ef4444",
    "purple": "#a78bfa",
    "cyan": "#22d3ee",
}

FONTE = "Segoe UI"

mostrar_splash()

def cor_status(ok, alerta="#f59e0b"):
    return CORES["green"] if ok else alerta


def criar_frame(parent, bg=None, border=True, **kwargs):
    return tk.Frame(
        parent,
        bg=bg or CORES["surface"],
        highlightbackground=CORES["border"] if border else (bg or CORES["surface"]),
        highlightthickness=1 if border else 0,
        **kwargs
    )


def criar_titulo(parent, titulo, subtitulo=None):
    bloco = tk.Frame(parent, bg=CORES["surface"])
    tk.Label(
        bloco, text=titulo,
        bg=CORES["surface"], fg=CORES["text"],
        font=(FONTE, 11, "bold")
    ).pack(anchor="w")
    if subtitulo:
        tk.Label(
            bloco, text=subtitulo,
            bg=CORES["surface"], fg=CORES["muted"],
            font=(FONTE, 8)
        ).pack(anchor="w", pady=(2, 0))
    return bloco


def criar_badge(parent, texto="AGUARDANDO", cor=None):
    lbl = tk.Label(
        parent,
        text=texto,
        bg=cor or CORES["surface2"],
        fg=CORES["text"],
        font=(FONTE, 8, "bold"),
        padx=9,
        pady=4
    )
    return lbl


def criar_card_profissional(parent, titulo, icone, valor_inicial="--"):
    card = criar_frame(parent)
    top = tk.Frame(card, bg=CORES["surface"])
    top.pack(fill="x", padx=14, pady=(12, 3))

    tk.Label(
        top, text=icone,
        bg=CORES["surface"], fg=CORES["blue"],
        font=(FONTE, 13)
    ).pack(side="left")

    tk.Label(
        top, text=titulo.upper(),
        bg=CORES["surface"], fg=CORES["muted"],
        font=(FONTE, 8, "bold")
    ).pack(side="left", padx=7)

    valor = tk.Label(
        card,
        text=valor_inicial,
        bg=CORES["surface"],
        fg=CORES["text"],
        font=(FONTE, 17, "bold")
    )
    valor.pack(anchor="w", padx=14, pady=(3, 12))

    return card, valor


def criar_linha_detalhe(parent, nome, valor="--"):
    linha = tk.Frame(parent, bg=CORES["surface"])
    linha.pack(fill="x", padx=14, pady=5)

    tk.Label(
        linha, text=nome,
        bg=CORES["surface"], fg=CORES["muted"],
        font=(FONTE, 8)
    ).pack(side="left")

    lbl = tk.Label(
        linha, text=valor,
        bg=CORES["surface"], fg=CORES["text"],
        font=(FONTE, 8, "bold")
    )
    lbl.pack(side="right")
    return lbl


def formatar_taxa(valor):
    if valor is None:
        return "--"
    return str(valor)


def atualizar_sinal_wifi(sinal):
    wifi_sinal_canvas.delete("all")

    if sinal >= 90:
        barras, cor, qualidade = 4, CORES["green"], "EXCELENTE"
    elif sinal >= 70:
        barras, cor, qualidade = 3, CORES["green"], "MUITO BOM"
    elif sinal >= 50:
        barras, cor, qualidade = 2, CORES["yellow"], "BOM"
    elif sinal >= 30:
        barras, cor, qualidade = 1, "#f97316", "FRACO"
    else:
        barras, cor, qualidade = 0, CORES["red"], "SEM SINAL"

    alturas = [9, 16, 24, 33]
    base = 42 if not TELA_PEQUENA else 34

    for i, altura in enumerate(alturas):
        x1 = 8 + i * 14
        x2 = x1 + 9
        y2 = base
        y1 = y2 - altura
        wifi_sinal_canvas.create_rectangle(
            x1, y1, x2, y2,
            fill=cor if i < barras else "#273442",
            outline=""
        )

    wifi_sinal_canvas.create_text(
        93, 14,
        text=f"{sinal}%",
        fill=CORES["text"],
        font=(FONTE, 13, "bold")
    )
    wifi_sinal_canvas.create_text(
        93, 31,
        text=qualidade,
        fill=cor,
        font=(FONTE, 7, "bold")
    )


def desenhar_grafico():
    grafico.delete("all")
    largura = max(grafico.winfo_width(), 560)
    altura = max(grafico.winfo_height(), 285)

    margem_esq = 48
    margem_dir = 18
    topo = 45
    base = altura - 35
    area_largura = max(100, largura - margem_esq - margem_dir)
    area_altura = max(80, base - topo)

    # título
    grafico.create_text(
        18, 18,
        anchor="w",
        text="LATÊNCIA EM TEMPO REAL",
        fill=CORES["text"],
        font=(FONTE, 11, "bold")
    )

    valores = [v for v in pontos if v is not None]
    if valores:
        media = sum(valores) / len(valores)
        resumo = (
            f"Atual {valores[-1]} ms   •   "
            f"Média {media:.0f} ms   •   "
            f"Mín {min(valores)} ms   •   Máx {max(valores)} ms"
        )
    else:
        resumo = "Aguardando medições..."

    grafico.create_text(
        largura - 18, 18,
        anchor="e",
        text=resumo,
        fill=CORES["muted"],
        font=(FONTE, 8, "bold")
    )

    # Escala vertical de 10 em 10 ms.
    # O limite superior acompanha as medições e é arredondado para 10.
    maior_valor = max(valores, default=0)

    if maior_valor <= 50:
        escala = 50
    elif maior_valor <= 100:
        escala = 100
    elif maior_valor <= 200:
        escala = 200
    elif maior_valor <= 300:
        escala = 300
    elif maior_valor <= 500:
        escala = 500
    else:
        escala = int(((maior_valor + 99) // 100) * 100)

    def y_pos(v):
        v = min(v, escala)
        return base - (v / escala) * area_altura

    # grade
    passos = int(escala // 10)
    for i in range(passos + 1):
        v = i * 10
        y = y_pos(v)
        grafico.create_line(
            margem_esq, y,
            largura - margem_dir, y,
            fill="#1d2a38",
            dash=(2, 4)
        )
        grafico.create_text(
            margem_esq - 8, y,
            anchor="e",
            text=f"{int(v)}",
            fill="#596a7e",
            font=(FONTE, 7)
        )

    if not pontos:
        grafico.create_text(
            largura / 2,
            altura / 2,
            text="Aguardando dados do monitor...",
            fill=CORES["muted"],
            font=(FONTE, 10)
        )
        return

    qtd = len(pontos)
    espacamento = area_largura / max(qtd, 1)
    largura_barra = max(2, min(11, espacamento * 0.62))

    for i, valor in enumerate(pontos):
        centro = margem_esq + (i + 0.5) * espacamento
        esquerda = centro - largura_barra / 2
        direita = centro + largura_barra / 2

        if valor is None:
            grafico.create_rectangle(
                esquerda, base - 14, direita, base,
                fill=CORES["red"], outline=""
            )
            continue

        if valor <= 20:
            cor = "#065af4"
        elif valor <= 50:
            cor = "#0b9e12"
        elif valor <= 100:
            cor = "#facc15"
        else:
            cor = "#ef4444"

        topo_barra = y_pos(valor)
        grafico.create_rectangle(
            esquerda, topo_barra,
            direita, base,
            fill=cor, outline=""
        )

        if i == qtd - 1:
            grafico.create_rectangle(
                esquerda - 2, topo_barra - 2,
                direita + 2, base,
                outline=CORES["text"], width=2
            )

    grafico.create_text(
        margem_esq, altura - 14,
        anchor="w",
        text="histórico",
        fill="#596a7e",
        font=(FONTE, 7)
    )
    grafico.create_text(
        largura - margem_dir, altura - 14,
        anchor="e",
        text="agora",
        fill="#596a7e",
        font=(FONTE, 7)
    )


def abrir_diagnostico():
    dados = ultimo_dados.copy()
    janela_diag = tk.Toplevel(janela)
    janela_diag.title("Monitor de Rede • Diagnóstico")
    janela_diag.geometry("820x680")
    janela_diag.minsize(700, 560)
    janela_diag.configure(bg=CORES["bg"])

    header = tk.Frame(janela_diag, bg=CORES["surface2"], height=78)
    header.pack(fill="x")
    header.pack_propagate(False)

    tk.Label(
        header, text="DIAGNÓSTICO DE REDE",
        bg=CORES["surface2"], fg=CORES["text"],
        font=(FONTE, 18, "bold")
    ).pack(anchor="w", padx=22, pady=(14, 0))

    tk.Label(
        header, text="Análise de Wi-Fi, Ethernet, gateway, DNS e Internet",
        bg=CORES["surface2"], fg=CORES["muted"],
        font=(FONTE, 9)
    ).pack(anchor="w", padx=22)

    resultado = criar_frame(janela_diag)
    resultado.pack(fill="x", padx=22, pady=16)

    diag_nome = tk.Label(
        resultado,
        text=dados.get("diagnostico", "AGUARDANDO"),
        bg=CORES["surface"], fg=CORES["green"],
        font=(FONTE, 16, "bold")
    )
    diag_nome.pack(anchor="w", padx=18, pady=(14, 2))

    diag_desc = tk.Label(
        resultado,
        text=dados.get("diagnostico_detalhe", "Execute uma análise."),
        bg=CORES["surface"], fg=CORES["muted"],
        font=(FONTE, 9),
        wraplength=740,
        justify="left"
    )
    diag_desc.pack(anchor="w", padx=18, pady=(0, 14))

    texto = tk.Text(
        janela_diag,
        bg="#0d141d",
        fg="#dbeafe",
        insertbackground="white",
        relief="flat",
        font=("Consolas", 9),
        padx=16, pady=14
    )
    texto.pack(fill="both", expand=True, padx=22, pady=(0, 12))

    def preencher(d):
        dns = d.get("dns", {})
        linhas = [
            "STATUS GERAL",
            f"  Diagnóstico       : {d.get('diagnostico', '--')}",
            f"  Detalhe           : {d.get('diagnostico_detalhe', '--')}",
            "",
            "WI-FI",
            f"  Estado            : {d.get('wifi', '--')}",
            f"  SSID              : {d.get('ssid', '--')}",
            f"  Sinal             : {d.get('sinal_wifi', 0)}%",
            f"  Canal             : {d.get('canal', '--')}",
            f"  Rádio             : {d.get('radio', '--')}",
            f"  Recepção          : {d.get('recepcao', '--')}",
            f"  Transmissão       : {d.get('transmissao', '--')}",
            f"  Autenticação      : {d.get('autenticacao', '--')}",
            f"  Criptografia      : {d.get('criptografia', '--')}",
            "",
            "ETHERNET",
            f"  Estado            : {d.get('ethernet', '--')}",
            f"  Adaptador         : {d.get('ethernet_nome', '--')}",
            f"  Velocidade        : {d.get('ethernet_velocidade', '--')}",
            "",
            "REDE LOCAL",
            f"  IP                : {d.get('ip', '--')}",
            f"  Gateway           : {d.get('gateway', '--')}",
            f"  Ping gateway      : {formatar_ms(d.get('gateway_ms'))}",
            "",
            "INTERNET / DNS",
            f"  Internet          : {d.get('internet', '--')}",
            f"  Latência          : {formatar_ms(d.get('latencia'))}",
            f"  Teste HTTP        : {formatar_ms(d.get('internet_ms'))}",
            f"  DNS 1.1.1.1       : {'OK' if dns.get('1.1.1.1') else 'FALHA'}",
            f"  DNS 8.8.8.8       : {'OK' if dns.get('8.8.8.8') else 'FALHA'}",
        ]
        texto.delete("1.0", "end")
        texto.insert("1.0", "\n".join(linhas))

    preencher(dados)

    def executar_novo():
        botao.config(state="disabled", text="ANALISANDO...")
        def trabalho():
            try:
                novo = realizar_medicoes()
                janela_diag.after(0, lambda: atualizar_diag(novo))
            finally:
                janela_diag.after(
                    0,
                    lambda: botao.config(
                        state="normal",
                        text="EXECUTAR NOVO DIAGNÓSTICO"
                    )
                )

        threading.Thread(target=trabalho, daemon=True).start()

    def atualizar_diag(d):
        preencher(d)
        diag_nome.config(text=d.get("diagnostico", "--"))
        diag_desc.config(text=d.get("diagnostico_detalhe", "--"))

    botao = tk.Button(
        janela_diag,
        text="EXECUTAR NOVO DIAGNÓSTICO",
        command=executar_novo,
        bg=CORES["blue"], fg="#071018",
        activebackground="#7dd3fc",
        activeforeground="#071018",
        relief="flat", bd=0,
        font=(FONTE, 9, "bold"),
        padx=16, pady=9,
        cursor="hand2"
    )
    botao.pack(pady=(0, 18))


def limpar_historico(janela_hist=None, recarregar=None):
    """Apaga o histórico salvo e reinicia as estatísticas da sessão."""
    confirmar = messagebox.askyesno(
        "Limpar histórico",
        "Tem certeza que deseja apagar todo o histórico?\n\n"
        "Os registros do monitor_rede.csv serão removidos e o histórico da sessão será reiniciado.",
        icon="warning",
        parent=janela_hist or janela
    )
    if not confirmar:
        return

    global historico_eventos, ultimo_evento_historico
    global pontos, historico_online, latencias_todas
    global contador_quedas, contador_testes, contador_sucessos, contador_falhas
    global falhas_gateway, falhas_dns, falhas_internet
    global ultima_queda, duracao_ultima_queda, maior_queda
    global tempo_monitoramento_inicio

    try:
        inicializar_csv()
        with open(CSV_FILE, "w", newline="", encoding="utf-8-sig") as f:
            csv.writer(f, delimiter=";").writerow([
                "Data", "Hora", "Evento", "Diagnostico", "Wi-Fi",
                "Sinal_WiFi", "Ethernet", "Internet", "IP", "Gateway",
                "Gateway_ms", "Latencia_ms", "Duracao_queda"
            ])

        historico_eventos = []
        ultimo_evento_historico = None
        pontos = []
        historico_online = []
        latencias_todas = []
        contador_quedas = 0
        contador_testes = 0
        contador_sucessos = 0
        contador_falhas = 0
        falhas_gateway = 0
        falhas_dns = 0
        falhas_internet = 0
        ultima_queda = "--"
        duracao_ultima_queda = "--"
        maior_queda = 0
        tempo_monitoramento_inicio = datetime.now()

        if recarregar:
            recarregar()
        messagebox.showinfo(
            "Histórico limpo",
            "O histórico foi apagado com sucesso. O monitor começará um novo histórico a partir de agora.",
            parent=janela_hist or janela
        )
    except Exception as e:
        messagebox.showerror(
            "Erro ao limpar histórico",
            f"Não foi possível limpar o histórico.\n\n{e}",
            parent=janela_hist or janela
        )


def abrir_historico_interno():
    janela_hist = tk.Toplevel(janela)
    janela_hist.title("Monitor de Rede • Histórico")
    janela_hist.geometry("1180x650")
    janela_hist.minsize(850, 500)
    janela_hist.configure(bg=CORES["bg"])

    tk.Label(
        janela_hist, text="HISTÓRICO DE MONITORAMENTO",
        bg=CORES["bg"], fg=CORES["text"],
        font=(FONTE, 17, "bold")
    ).pack(anchor="w", padx=22, pady=(18, 3))

    tk.Label(
        janela_hist,
        text="Registros gravados no monitor_rede.csv",
        bg=CORES["bg"], fg=CORES["muted"],
        font=(FONTE, 9)
    ).pack(anchor="w", padx=22, pady=(0, 12))

    controles = tk.Frame(janela_hist, bg=CORES["bg"])
    controles.pack(fill="x", padx=22, pady=(0, 10))

    tk.Label(
        controles, text="Período",
        bg=CORES["bg"], fg=CORES["muted"],
        font=(FONTE, 9, "bold")
    ).pack(side="left")

    periodo = ttk.Combobox(
        controles,
        values=["Hoje", "Últimos 7 dias", "Últimos 30 dias", "Tudo"],
        state="readonly", width=18
    )
    periodo.set("Tudo")
    periodo.pack(side="left", padx=8)

    tabela_frame = criar_frame(janela_hist, border=False, bg=CORES["bg"])
    tabela_frame.pack(fill="both", expand=True, padx=22, pady=4)

    colunas = (
        "Data", "Hora", "Evento", "Diagnóstico",
        "Wi-Fi", "Sinal", "Ethernet", "Internet",
        "IP", "Gateway", "Ping Gateway", "Latência"
    )

    tabela = ttk.Treeview(tabela_frame, columns=colunas, show="headings")
    larguras = {
        "Data": 85, "Hora": 70, "Evento": 135,
        "Diagnóstico": 165, "Wi-Fi": 85, "Sinal": 55,
        "Ethernet": 90, "Internet": 80, "IP": 110,
        "Gateway": 110, "Ping Gateway": 100, "Latência": 80
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
        selecionado = periodo.get()

        for registro in registros:
            try:
                data = datetime.strptime(
                    registro.get("Data", ""), "%d/%m/%Y"
                ).date()
            except Exception:
                continue

            if selecionado == "Hoje" and data != hoje:
                continue
            if selecionado == "Últimos 7 dias" and data < hoje - timedelta(days=7):
                continue
            if selecionado == "Últimos 30 dias" and data < hoje - timedelta(days=30):
                continue

            tabela.insert(
                "", "end",
                values=(
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
                    registro.get("Gateway_ms", ""),
                    registro.get("Latencia_ms", "")
                )
            )

    botoes_hist = tk.Frame(janela_hist, bg=CORES["bg"])
    botoes_hist.pack(fill="x", padx=22, pady=(8, 16))

    btn_limpar = tk.Button(
        botoes_hist,
        text="🗑️  Limpar Histórico",
        command=lambda: limpar_historico(janela_hist, carregar),
        bg="#7f1d1d",
        fg="#ffffff",
        activebackground="#dc2626",
        activeforeground="#ffffff",
        relief="flat", bd=0,
        font=(FONTE, 9, "bold"),
        padx=14, pady=8,
        cursor="hand2"
    )
    btn_limpar.pack(side="left")

    periodo.bind("<<ComboboxSelected>>", lambda e: carregar())
    carregar()


def abrir_estatisticas():
    janela_est = tk.Toplevel(janela)
    janela_est.title("Monitor de Rede • Estatísticas")
    janela_est.geometry("720x610")
    janela_est.minsize(600, 500)
    janela_est.configure(bg=CORES["bg"])

    tk.Label(
        janela_est, text="ESTATÍSTICAS",
        bg=CORES["bg"], fg=CORES["text"],
        font=(FONTE, 18, "bold")
    ).pack(anchor="w", padx=22, pady=(20, 3))

    tk.Label(
        janela_est,
        text="Desempenho da sessão atual",
        bg=CORES["bg"], fg=CORES["muted"],
        font=(FONTE, 9)
    ).pack(anchor="w", padx=22, pady=(0, 14))

    disponibilidade = (
        contador_sucessos / contador_testes * 100
        if contador_testes else 0
    )
    media = (
        sum(latencias_todas) / len(latencias_todas)
        if latencias_todas else 0
    )
    minimo = min(latencias_todas) if latencias_todas else 0
    maximo = max(latencias_todas) if latencias_todas else 0
    tempo = datetime.now() - tempo_monitoramento_inicio

    cards_est = tk.Frame(janela_est, bg=CORES["bg"])
    cards_est.pack(fill="x", padx=22)
    for i in range(3):
        cards_est.grid_columnconfigure(i, weight=1)

    for i, (titulo, valor, cor) in enumerate([
        ("DISPONIBILIDADE", f"{disponibilidade:.2f}%", CORES["green"]),
        ("QUEDAS", str(contador_quedas), CORES["yellow"]),
        ("LATÊNCIA MÉDIA", f"{media:.0f} ms", CORES["blue"]),
    ]):
        card = criar_frame(cards_est)
        card.grid(row=0, column=i, sticky="nsew", padx=4)
        tk.Label(
            card, text=titulo,
            bg=CORES["surface"], fg=CORES["muted"],
            font=(FONTE, 8, "bold")
        ).pack(anchor="w", padx=14, pady=(12, 3))
        tk.Label(
            card, text=valor,
            bg=CORES["surface"], fg=cor,
            font=(FONTE, 18, "bold")
        ).pack(anchor="w", padx=14, pady=(0, 12))

    corpo = criar_frame(janela_est)
    corpo.pack(fill="both", expand=True, padx=22, pady=16)

    dados = [
        ("Testes realizados", contador_testes),
        ("Testes com Internet", contador_sucessos),
        ("Falhas", contador_falhas),
        ("Latência mínima", f"{minimo} ms"),
        ("Latência máxima", f"{maximo} ms"),
        ("Maior queda", formatar_duracao(maior_queda)),
        ("Última queda", ultima_queda),
        ("Duração última queda", duracao_ultima_queda),
        ("Falhas de gateway", falhas_gateway),
        ("Falhas de DNS", falhas_dns),
        ("Falhas de Internet", falhas_internet),
        ("Tempo desta sessão", formatar_duracao(tempo.total_seconds())),
    ]

    for nome, valor in dados:
        criar_linha_detalhe(corpo, nome, str(valor))


def exportar_relatorio():
    disponibilidade = (
        contador_sucessos / contador_testes * 100
        if contador_testes else 0
    )
    media = (
        sum(latencias_todas) / len(latencias_todas)
        if latencias_todas else 0
    )

    nome_arquivo = (
        "relatorio_monitor_rede_"
        f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    )

    caminho = filedialog.asksaveasfilename(
        title="Salvar relatório",
        defaultextension=".txt",
        filetypes=[("Relatório de texto", "*.txt")],
        initialfile=nome_arquivo
    )
    if not caminho:
        return

    linhas = [
        "=" * 64,
        "              MONITOR DE REDE - RELATÓRIO",
        "=" * 64,
        "",
        f"Data do relatório : {agora()}",
        f"Aplicativo        : {APP_NAME}",
        f"Versão            : {APP_VERSION}",
        f"Desenvolvido por  : {AUTOR}",
        "",
        "STATUS ATUAL",
        "-" * 64,
        f"Diagnóstico       : {ultimo_dados.get('diagnostico', '--')}",
        f"Detalhe           : {ultimo_dados.get('diagnostico_detalhe', '--')}",
        f"Wi-Fi             : {ultimo_dados.get('wifi', '--')}",
        f"Sinal Wi-Fi       : {ultimo_dados.get('sinal_wifi', 0)}%",
        f"SSID              : {ultimo_dados.get('ssid', '--')}",
        f"Canal Wi-Fi       : {ultimo_dados.get('canal', '--')}",
        f"Rádio             : {ultimo_dados.get('radio', '--')}",
        f"Ethernet          : {ultimo_dados.get('ethernet', '--')}",
        f"Adaptador         : {ultimo_dados.get('ethernet_nome', '--')}",
        f"Velocidade        : {ultimo_dados.get('ethernet_velocidade', '--')}",
        f"IP local          : {ultimo_dados.get('ip', '--')}",
        f"Gateway           : {ultimo_dados.get('gateway', '--')}",
        f"Ping gateway      : {formatar_ms(ultimo_dados.get('gateway_ms'))}",
        f"Internet          : {ultimo_dados.get('internet', '--')}",
        f"Latência          : {formatar_ms(ultimo_dados.get('latencia'))}",
        f"Teste Internet    : {formatar_ms(ultimo_dados.get('internet_ms'))}",
        "",
        "ESTATÍSTICAS",
        "-" * 64,
        f"Testes realizados : {contador_testes}",
        f"Testes sucesso    : {contador_sucessos}",
        f"Falhas            : {contador_falhas}",
        f"Disponibilidade   : {disponibilidade:.2f}%",
        f"Total de quedas   : {contador_quedas}",
        f"Última queda      : {ultima_queda}",
        f"Duração última    : {duracao_ultima_queda}",
        f"Maior queda       : {formatar_duracao(maior_queda)}",
        f"Latência média    : {media:.0f} ms",
        f"Latência mínima   : {min(latencias_todas) if latencias_todas else '--'} ms",
        f"Latência máxima   : {max(latencias_todas) if latencias_todas else '--'} ms",
        f"Falhas gateway    : {falhas_gateway}",
        f"Falhas DNS        : {falhas_dns}",
        f"Falhas Internet   : {falhas_internet}",
        "",
        "ÚLTIMOS EVENTOS",
        "-" * 64,
    ]

    linhas.extend(historico_eventos or ["Nenhum evento registrado."])
    linhas.extend([
        "",
        "=" * 64,
        f"Arquivo CSV: {CSV_FILE}",
        "=" * 64
    ])

    try:
        with open(caminho, "w", encoding="utf-8") as f:
            f.write("\n".join(linhas))
        messagebox.showinfo(
            "Relatório",
            f"Relatório salvo com sucesso!\n\n{caminho}"
        )
    except Exception as e:
        messagebox.showerror(
            "Relatório",
            f"Não foi possível salvar o relatório:\n\n{e}"
        )


def abrir_configuracoes():
    global INTERVALO, MAX_PONTOS, LATENCIA_HOST, LATENCIA_TIMEOUT

    janela_cfg = tk.Toplevel(janela)
    janela_cfg.title("Monitor de Rede • Configurações")
    janela_cfg.geometry("570x500")
    janela_cfg.minsize(500, 430)
    janela_cfg.configure(bg=CORES["bg"])

    tk.Label(
        janela_cfg, text="CONFIGURAÇÕES",
        bg=CORES["bg"], fg=CORES["text"],
        font=(FONTE, 18, "bold")
    ).pack(anchor="w", padx=22, pady=(20, 3))

    tk.Label(
        janela_cfg,
        text="Ajuste a frequência e os parâmetros de diagnóstico",
        bg=CORES["bg"], fg=CORES["muted"],
        font=(FONTE, 9)
    ).pack(anchor="w", padx=22, pady=(0, 14))

    frame = criar_frame(janela_cfg)
    frame.pack(fill="both", expand=True, padx=22, pady=4)

    def campo(nome, valor):
        linha = tk.Frame(frame, bg=CORES["surface"])
        linha.pack(fill="x", padx=18, pady=10)
        tk.Label(
            linha, text=nome,
            bg=CORES["surface"], fg=CORES["muted"],
            font=(FONTE, 9)
        ).pack(side="left")

        entrada = tk.Entry(
            linha,
            bg="#0c141d", fg=CORES["text"],
            insertbackground="white",
            relief="flat", width=20,
            font=(FONTE, 9)
        )
        entrada.insert(0, str(valor))
        entrada.pack(side="right", ipady=5)
        return entrada

    entrada_intervalo = campo("Intervalo de monitoramento (s)", INTERVALO)
    entrada_pontos = campo("Quantidade de pontos do gráfico", MAX_PONTOS)
    entrada_host = campo("Host de latência", LATENCIA_HOST)
    entrada_timeout = campo("Timeout de ping (ms)", LATENCIA_TIMEOUT)

    def salvar():
        global INTERVALO, MAX_PONTOS, LATENCIA_HOST, LATENCIA_TIMEOUT
        try:
            novo_intervalo = float(entrada_intervalo.get().replace(",", "."))
            novo_pontos = int(entrada_pontos.get())
            novo_timeout = int(entrada_timeout.get())
            novo_host = entrada_host.get().strip() or "1.1.1.1"

            if novo_intervalo < 0.5:
                raise ValueError("O intervalo mínimo é 0,5 segundo.")
            if novo_pontos < 20:
                raise ValueError("Use pelo menos 20 pontos.")
            if novo_timeout < 500:
                raise ValueError("O timeout mínimo é 500 ms.")

            INTERVALO = novo_intervalo
            MAX_PONTOS = novo_pontos
            LATENCIA_HOST = novo_host
            LATENCIA_TIMEOUT = novo_timeout

            if len(pontos) > MAX_PONTOS:
                del pontos[:-MAX_PONTOS]

            janela_cfg.destroy()
        except Exception as e:
            messagebox.showerror("Configuração inválida", str(e))

    tk.Button(
        janela_cfg,
        text="SALVAR CONFIGURAÇÕES",
        command=salvar,
        bg=CORES["blue"], fg="#071018",
        activebackground="#7dd3fc",
        relief="flat", bd=0,
        font=(FONTE, 9, "bold"),
        padx=18, pady=9,
        cursor="hand2"
    ).pack(pady=16)


def abrir_historico_csv():
    inicializar_csv()
    try:
        if sys.platform == "win32":
            os.startfile(CSV_FILE)
        else:
            messagebox.showinfo("Histórico CSV", CSV_FILE)
    except Exception as e:
        messagebox.showerror(
            "Histórico CSV",
            f"Não foi possível abrir o arquivo:\n{e}"
        )


def alternar_pausa():
    global pausado
    pausado = not pausado
    if pausado:
        pausa_botao.config(text="▶ RETOMAR", fg=CORES["yellow"])
        status_operacao.config(text="MONITORAMENTO PAUSADO", fg=CORES["yellow"])
    else:
        pausa_botao.config(text="Ⅱ PAUSAR", fg=CORES["text"])
        status_operacao.config(text="MONITORAMENTO ATIVO", fg=CORES["green"])


def fechar():
    global rodando
    rodando = False
    try:
        janela.destroy()
    except Exception:
        pass


# ============================================================
# 🖥️ JANELA PRINCIPAL
# ============================================================
inicializar_csv()

janela = tk.Tk()
try:
    janela.iconbitmap(resource_path(os.path.join("assets", "monitor_rede.ico")))
except Exception:
    pass
janela.title(
    f"{APP_NAME} {APP_VERSION} • {AUTOR}"
)
janela.configure(bg=CORES["bg"])

# DPI
janela.update_idletasks()
largura_tela = janela.winfo_screenwidth()
altura_tela = janela.winfo_screenheight()

TELA_PEQUENA = altura_tela <= 800

if TELA_PEQUENA:
    largura_janela = min(largura_tela, 1440)
    altura_janela = max(680, altura_tela - 35)
    janela.geometry(f"{largura_janela}x{altura_janela}+0+0")
    janela.minsize(1000, 650)
else:
    largura_janela = min(1380, largura_tela - 40)
    altura_janela = min(820, altura_tela - 70)
    largura_janela = max(1100, largura_janela)
    altura_janela = max(650, altura_janela)
    pos_x = max((largura_tela - largura_janela) // 2, 0)
    pos_y = max((altura_tela - altura_janela) // 2, 0)
    janela.geometry(f"{largura_janela}x{altura_janela}+{pos_x}+{pos_y}")
    janela.minsize(1100, 650)

style = ttk.Style()
try:
    style.theme_use("clam")
except tk.TclError:
    pass

style.configure(
    "Treeview",
    background="#0e151e",
    foreground="#e2e8f0",
    fieldbackground="#0e151e",
    rowheight=28,
    borderwidth=0
)
style.configure(
    "Treeview.Heading",
    background="#1b2938",
    foreground="#f8fafc",
    font=(FONTE, 9, "bold")
)
style.map(
    "Treeview",
    background=[("selected", "#164e63")],
    foreground=[("selected", "#ffffff")]
)
style.configure(
    "TCombobox",
    fieldbackground="#0d141d",
    background="#1b2938",
    foreground="#f8fafc"
)

# ============================================================
# CABEÇALHO
# ============================================================
header = tk.Frame(janela, bg=CORES["surface2"], height=82)
header.pack(fill="x")
header.pack_propagate(False)

# Marca
marca = tk.Frame(header, bg=CORES["surface2"])
marca.pack(side="left", padx=(18, 12), pady=10)

if Image is not None:
    try:
        robo_path = resource_path(os.path.join("assets", "robo_jp.png"))
        robo_img = Image.open(robo_path).convert("RGBA")
        robo_img.thumbnail((58, 58), Image.LANCZOS)
        robo_tk = ImageTk.PhotoImage(robo_img)
        tk.Label(marca, image=robo_tk, bg=CORES["surface2"]).pack()
    except Exception:
        tk.Label(
            marca, text="JP",
            bg=CORES["blue"], fg="#071018",
            font=(FONTE, 13, "bold"),
            width=4, height=2
        ).pack()
else:
    tk.Label(
        marca, text="JP",
        bg=CORES["blue"], fg="#071018",
        font=(FONTE, 13, "bold"),
        width=4, height=2
    ).pack()

titulo = tk.Frame(header, bg=CORES["surface2"])
titulo.pack(side="left", fill="y", pady=10)

tk.Label(
    titulo,
    text="MONITOR DE REDE",
    bg=CORES["surface2"], fg=CORES["text"],
    font=(FONTE, 18, "bold")
).pack(anchor="w")

tk.Label(
    titulo,
    text=f"{AUTOR}   •  •   versão {APP_VERSION}",
    bg=CORES["surface2"], fg=CORES["muted"],
    font=(FONTE, 8, "bold")
).pack(anchor="w", pady=(1, 0))

# Status da aplicação
status_box = tk.Frame(header, bg=CORES["surface2"])
status_box.pack(side="left", padx=25)

status_dot = tk.Label(
    status_box, text="●",
    bg=CORES["surface2"], fg=CORES["green"],
    font=(FONTE, 15)
)
status_dot.pack(side="left")

status_operacao = tk.Label(
    status_box,
    text="MONITORAMENTO ATIVO",
    bg=CORES["surface2"], fg=CORES["green"],
    font=(FONTE, 8, "bold")
)
status_operacao.pack(side="left", padx=5)

# Menu profissional
menu = tk.Frame(header, bg=CORES["surface2"])
menu.pack(side="right", padx=12, pady=9)

def botao_menu(texto, comando):
    btn = tk.Button(
        menu,
        text=texto,
        command=comando,
        bg="#182333",
        fg="#f8fafc",
        activebackground="#2563eb",
        activeforeground="#ffffff",
        relief="flat",
        bd=0,
        highlightthickness=1,
        highlightbackground="#2b3b52",
        highlightcolor="#38bdf8",
        font=(FONTE, 9, "bold"),
        padx=11,
        pady=8,
        cursor="hand2",
        takefocus=True
    )

    def entrar(event):
        btn.configure(
            bg="#2563eb",
            highlightbackground="#38bdf8"
        )

    def sair(event):
        btn.configure(
            bg="#182333",
            highlightbackground="#2b3b52"
        )

    btn.bind("<Enter>", entrar)
    btn.bind("<Leave>", sair)
    return btn

for texto, comando in [
    ("🔎  Diagnóstico", abrir_diagnostico),
    ("📜  Histórico", abrir_historico_interno),
    ("📊  Estatísticas", abrir_estatisticas),
    ("📄  Relatório", exportar_relatorio),
    ("⚙  Configurações", abrir_configuracoes),
    ("📁  Dados CSV", abrir_historico_csv),
]:
    botao_menu(texto, comando).pack(side="left", padx=3)

# ============================================================
# CONTEÚDO
# ============================================================
conteudo = tk.Frame(janela, bg=CORES["bg"])
conteudo.pack(fill="both", expand=True, padx=16, pady=10)

# Cards superiores
cards = tk.Frame(conteudo, bg=CORES["bg"])
cards.pack(fill="x")

for i in range(6):
    cards.grid_columnconfigure(i, weight=1, uniform="statuscards")

wifi_card, wifi_valor = criar_card_profissional(
    cards, "Wi-Fi", "◉"
)
wifi_card.grid(row=0, column=0, sticky="nsew", padx=3)

wifi_sinal_canvas = tk.Canvas(
    wifi_card, width=135, height=52,
    bg=CORES["surface"], highlightthickness=0
)
wifi_sinal_canvas.pack(anchor="w", padx=12, pady=(0, 7))

ethernet_card, ethernet_valor = criar_card_profissional(
    cards, "Ethernet", "▣"
)
ethernet_card.grid(row=0, column=1, sticky="nsew", padx=3)

ip_card, ip_valor = criar_card_profissional(
    cards, "IP local", "⌁"
)
ip_card.grid(row=0, column=2, sticky="nsew", padx=3)

gateway_card, gateway_valor = criar_card_profissional(
    cards, "Gateway", "◆"
)
gateway_card.grid(row=0, column=3, sticky="nsew", padx=3)

lat_card, latencia_valor = criar_card_profissional(
    cards, "Latência", "↯"
)
lat_card.grid(row=0, column=4, sticky="nsew", padx=3)

internet_card, internet_valor = criar_card_profissional(
    cards, "Internet", "◎"
)
internet_card.grid(row=0, column=5, sticky="nsew", padx=3)

# ============================================================
# ÁREA PRINCIPAL
# ============================================================
principal = tk.Frame(conteudo, bg=CORES["bg"])
principal.pack(fill="both", expand=True, pady=(10, 0))

principal.grid_columnconfigure(0, weight=3)
principal.grid_columnconfigure(1, weight=2)
principal.grid_rowconfigure(0, weight=1)

# Gráfico
grafico_card = criar_frame(principal)
grafico_card.grid(
    row=0, column=0, sticky="nsew", padx=(0, 5)
)

grafico = tk.Canvas(
    grafico_card,
    bg=CORES["surface"],
    highlightthickness=0
)
grafico.pack(fill="both", expand=True, padx=8, pady=8)

grafico.bind("<Configure>", lambda event: desenhar_grafico())

# Legenda compacta da latência
legenda_latencia = tk.Frame(
    grafico_card,
    bg=CORES["surface"]
)
legenda_latencia.pack(
    fill="x",
    padx=14,
    pady=(0, 10)
)

# ==========================================================
# LEGENDA DE LATÊNCIA — CENTRALIZADA
# ==========================================================

legenda_centro = tk.Frame(
    legenda_latencia,
    bg=CORES["surface"]
)

legenda_centro.pack(
    anchor="center"
)

def item_legenda(cor, texto):
    frame = tk.Frame(
        legenda_centro,
        bg=CORES["surface"]
    )

    frame.pack(
        side="left",
        padx=10
    )

    # quadrado desenhada

    quadrado = tk.Canvas(
        frame,
        width=18,
        height=18,
        bg=CORES["surface"],
        highlightthickness=0
    )

    quadrado.pack(
        side="left",
        padx=(0, 6)
    )

    quadrado.create_rectangle(
        2, 2,
        18, 18,
        fill=cor,
        outline=cor
    )

    # Texto
    tk.Label(
        frame,
        text=texto,
        bg=CORES["surface"],
        fg=CORES["muted"],
        font=(FONTE, 8, "bold")
    ).pack(
        side="left"
    )


item_legenda("#065af4", "< 20 ms")
item_legenda("#0b9e12", "20–50 ms")
item_legenda("#facc15", "50–100 ms")
item_legenda("#ef4444", "> 100 ms")

# ============================================================
# COLUNA DIREITA
# ============================================================
direita = tk.Frame(principal, bg=CORES["bg"])
direita.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

direita.grid_columnconfigure(0, weight=1)
direita.grid_rowconfigure(0, weight=1)
direita.grid_rowconfigure(1, weight=1)

# Diagnóstico atual
diag_card = criar_frame(direita)
diag_card.grid(row=0, column=0, sticky="nsew", pady=(0, 5))

tk.Label(
    diag_card,
    text="DIAGNÓSTICO ATUAL",
    bg=CORES["surface"], fg=CORES["text"],
    font=(FONTE, 10, "bold")
).pack(anchor="w", padx=15, pady=(13, 2))

diagnostico_valor = tk.Label(
    diag_card,
    text="Aguardando...",
    bg=CORES["surface"], fg=CORES["green"],
    font=(FONTE, 15, "bold")
)
diagnostico_valor.pack(anchor="w", padx=15, pady=(0, 2))

diagnostico_detalhe = tk.Label(
    diag_card,
    text="Coletando informações da rede...",
    bg=CORES["surface"], fg=CORES["muted"],
    font=(FONTE, 8),
    wraplength=410,
    justify="left"
)
diagnostico_detalhe.pack(anchor="w", padx=15, pady=(0, 9))

diagnostico_botao = tk.Button(
    diag_card,
    text="ABRIR DIAGNÓSTICO COMPLETO",
    command=abrir_diagnostico,
    bg=CORES["surface2"], fg=CORES["blue"],
    activebackground="#24384b",
    activeforeground="#7dd3fc",
    relief="flat", bd=0,
    font=(FONTE, 8, "bold"),
    padx=9, pady=6,
    cursor="hand2"
)
diagnostico_botao.pack(anchor="w", padx=15, pady=(0, 12))

# Resumo técnico
info_card = criar_frame(direita)
info_card.grid(row=1, column=0, sticky="nsew", pady=(5, 0))

tk.Label(
    info_card,
    text="INFORMAÇÕES DA CONEXÃO",
    bg=CORES["surface"], fg=CORES["text"],
    font=(FONTE, 10, "bold")
).pack(anchor="w", padx=15, pady=(13, 5))

ssid_valor = criar_linha_detalhe(info_card, "SSID")
canal_valor = criar_linha_detalhe(info_card, "Canal")
recepcao_valor = criar_linha_detalhe(info_card, "Recepção")
transmissao_valor = criar_linha_detalhe(info_card, "Transmissão")
ping_gateway_valor = criar_linha_detalhe(info_card, "Ping gateway")
disponibilidade_valor = criar_linha_detalhe(info_card, "Disponibilidade")
quedas_valor = criar_linha_detalhe(info_card, "Quedas")

# ============================================================
# BARRA INFERIOR
# ============================================================
rodape_area = tk.Frame(janela, bg="#070b10", height=42)
rodape_area.pack(fill="x", side="bottom")
rodape_area.pack_propagate(False)

status_label = tk.Label(
    rodape_area,
    text="Iniciando monitoramento...",
    bg="#070b10", fg=CORES["muted"],
    font=(FONTE, 7),
    anchor="w"
)
status_label.pack(side="left", padx=16)

pausa_botao = tk.Button(
    rodape_area,
    text="Ⅱ PAUSAR",
    command=alternar_pausa,
    bg="#16212d", fg=CORES["text"],
    activebackground="#253548",
    activeforeground="#ffffff",
    relief="flat", bd=0,
    font=(FONTE, 8, "bold"),
    padx=10, pady=4,
    cursor="hand2"
)
pausa_botao.pack(side="right", padx=10, pady=5)

csv_botao = tk.Button(
    rodape_area,
    text="CSV",
    command=abrir_historico_csv,
    bg="#16212d", fg=CORES["muted"],
    activebackground="#253548",
    activeforeground="#ffffff",
    relief="flat", bd=0,
    font=(FONTE, 8, "bold"),
    padx=10, pady=4,
    cursor="hand2"
)
csv_botao.pack(side="right", padx=(0, 2), pady=5)

tk.Label(
    rodape_area,
    text=f"© 2026 {AUTOR} • {APP_NAME} v{APP_VERSION}",
    bg="#070b10", fg="#536276",
    font=(FONTE, 7)
).pack(side="right", padx=14)

# ============================================================
# ATUALIZAÇÃO DA INTERFACE
# ============================================================
def atualizar_interface(dados):
    try:
        wifi_ok = dados.get("wifi") == "Conectado"
        eth_ok = dados.get("ethernet") == "Conectado"
        online = bool(dados.get("online"))

        wifi_valor.config(
            text=dados.get("wifi", "--"),
            fg=CORES["green"] if wifi_ok else CORES["red"]
        )
        ethernet_valor.config(
            text=dados.get("ethernet", "--"),
            fg=CORES["green"] if eth_ok else CORES["red"]
        )
        ip_valor.config(text=dados.get("ip", "--"))
        gateway_valor.config(
            text=dados.get("gateway", "--")
        )

        lat = dados.get("latencia")
        latencia_valor.config(
            text=formatar_ms(lat),
            fg=(
                CORES["green"] if lat is not None and lat <= 50
                else CORES["yellow"] if lat is not None and lat <= 100
                else CORES["red"] if lat is not None
                else CORES["muted"]
            )
        )

        internet_valor.config(
            text=dados.get("internet", "--"),
            fg=CORES["green"] if online else CORES["red"]
        )

        atualizar_sinal_wifi(dados.get("sinal_wifi", 0))

        diagnostico = dados.get("diagnostico", "--")
        diag_ok = diagnostico == "NORMAL"
        diagnostico_valor.config(
            text=diagnostico,
            fg=CORES["green"] if diag_ok else CORES["yellow"]
        )
        diagnostico_detalhe.config(
            text=dados.get("diagnostico_detalhe", "--")
        )

        ssid_valor.config(text=dados.get("ssid", "--"))
        canal_valor.config(text=dados.get("canal", "--"))
        recepcao_valor.config(text=dados.get("recepcao", "--"))
        transmissao_valor.config(text=dados.get("transmissao", "--"))
        ping_gateway_valor.config(
            text=formatar_ms(dados.get("gateway_ms"))
        )
        disponibilidade_valor.config(
            text=f"{dados.get('disponibilidade', 0):.1f}%"
        )
        quedas_valor.config(
            text=str(dados.get("quedas", 0))
        )

        status_dot.config(
            fg=CORES["green"] if online else CORES["red"]
        )
        status_operacao.config(
            text="INTERNET ONLINE" if online else "INTERNET OFFLINE",
            fg=CORES["green"] if online else CORES["red"]
        )

        status_label.config(
            text=(
                f"Última verificação: {agora()}   •   "
                f"IP {dados.get('ip', '--')}   •   "
                f"Gateway {dados.get('gateway', '--')}   •   "
                f"Ping {formatar_ms(dados.get('gateway_ms'))}"
            )
        )

        desenhar_grafico()

    except Exception as e:
        print(f"[UI] Erro ao atualizar interface: {e}")


# ============================================================
# FECHAMENTO
# ============================================================
janela.protocol("WM_DELETE_WINDOW", fechar)

# ============================================================
# THREAD DE MONITORAMENTO
# ============================================================
thread = threading.Thread(
    target=monitorar,
    daemon=True
)
thread.start()

janela.after(100, desenhar_grafico)

# ============================================================
# INICIAR
# ============================================================
janela.mainloop()
