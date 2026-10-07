# ============================================================
# 📡 MONITOR DE REDE
# ============================================================
# Aplicativo para monitoramento de conexões Wi-Fi e Ethernet,
# disponibilidade da Internet, latência e quedas de conexão.
#
# 👨‍💻 Desenvolvido por: Jorge Alberto de Paula
# 📦 Projeto: MonitorRedesys
# 🚀 Versão: 2.1
# ============================================================

import csv
import os
import socket
import subprocess
import threading
import time
import urllib.request
import tkinter as tk
from datetime import datetime
from tkinter import ttk
import sys
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageTk


# ============================================================
# 🖥️ DPI / ESCALA DO WINDOWS
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
APP_VERSION = "2.1"
AUTOR = "Jorge Alberto de Paula"
MARCA_AUTOR = "🤖 JP"

PASTA = os.path.join(
    os.path.expanduser("~"),
    "MonitorRede"
)

CSV_FILE = os.path.join(
    PASTA,
    "monitor_rede.csv"
)

INTERVALO = 2
MAX_PONTOS = 150


# ============================================================
# 📦 RECURSOS
# ============================================================

def resource_path(relative_path):
    """Localiza arquivos tanto no Python quanto no EXE criado pelo PyInstaller."""

    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(
        base_path,
        relative_path
    )


TEST_URLS = [
    "https://www.msftconnecttest.com/connecttest.txt",
    "https://www.google.com/generate_204",
    "https://www.cloudflare.com/cdn-cgi/trace",
]


# ============================================================
# ⚡ DESTINO DA LATÊNCIA
# ============================================================

LATENCIA_HOST = "1.1.1.1"
LATENCIA_TIMEOUT = 1500


# ============================================================
# 📁 PREPARAÇÃO
# ============================================================

os.makedirs(
    PASTA,
    exist_ok=True
)


# ============================================================
# 📊 VARIÁVEIS
# ============================================================

estado_anterior = None
inicio_queda = None

contador_quedas = 0
contador_testes = 0
contador_sucessos = 0

ultima_queda = "--"
duracao_ultima_queda = "--"
ultimo_evento = "Monitor iniciado"

historico_eventos = []
ultimo_evento_historico = None

pontos = []
historico_online = []

rodando = True


# ============================================================
# 🕐 DATA / HORA
# ============================================================

def agora():
    return datetime.now().strftime(
        "%d/%m/%Y %H:%M:%S"
    )


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
                "Wi-Fi",
                "Ethernet",
                "Internet",
                "IP",
                "Latencia_ms",
                "Duracao_queda"
            ])


def registrar_csv(
    evento,
    wifi,
    ethernet,
    internet,
    ip,
    latencia,
    duracao="--"
):

    inicializar_csv()

    dt = datetime.now()

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
            wifi,
            ethernet,
            internet,
            ip,
            latencia,
            duracao
        ])


# ============================================================
# 🌐 IP LOCAL
# ============================================================

def obter_ip():

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
# 📶 WI-FI + SINAL
# ============================================================

def obter_wifi_e_sinal():

    wifi = "Desconectado"
    sinal = 0

    try:

        resultado = subprocess.run(
            [
                "netsh",
                "wlan",
                "show",
                "interfaces"
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW
        )

        for linha in resultado.stdout.splitlines():

            normalizada = " ".join(
                linha.strip()
                .lower()
                .split()
            )

            # ------------------------------------------------
            # ESTADO DO WI-FI
            # ------------------------------------------------

            if (
                normalizada.startswith("estado :")
                or
                normalizada.startswith("state :")
            ):

                if (
                    "conectado" in normalizada
                    or
                    "connected" in normalizada
                ):
                    wifi = "Conectado"

                else:
                    wifi = "Desconectado"

            # ------------------------------------------------
            # SINAL DO WI-FI
            # ------------------------------------------------

            if (
                normalizada.startswith("sinal :")
                or
                normalizada.startswith("signal :")
            ):

                try:

                    valor = (
                        linha
                        .split(":", 1)[1]
                        .strip()
                        .replace("%", "")
                    )

                    sinal = int(valor)

                except Exception:
                    sinal = 0

        return wifi, sinal

    except Exception as e:

        print(
            f"Erro ao consultar Wi-Fi: {e}"
        )

        return wifi, sinal


# ============================================================
# 📶 SINAL DO WI-FI
# ============================================================

def obter_sinal_wifi():

    _, sinal = obter_wifi_e_sinal()

    return sinal


# ============================================================
# 📶 VERIFICAR ADAPTADORES
# ============================================================

def verificar_adaptadores():

    wifi, _ = obter_wifi_e_sinal()

    ethernet = "Desconectado"

    # ========================================================
    # 🔌 ETHERNET
    # ========================================================

    try:

        comando = [
            "powershell",
            "-NoProfile",
            "-Command",
            (
                "Get-NetAdapter -Physical "
                "| Select-Object "
                "Name,InterfaceDescription,Status,Virtual "
                "| ConvertTo-Csv -NoTypeInformation"
            )
        ]

        resultado = subprocess.run(
            comando,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW
        )

        linhas = [
            linha.strip()
            for linha in resultado.stdout.splitlines()
            if linha.strip()
        ]

        for linha in linhas[1:]:

            campos = [
                campo.strip().strip('"')
                for campo in linha.split('","')
            ]

            if len(campos) < 4:
                continue

            nome = campos[0]
            descricao = campos[1]
            status = campos[2]
            virtual = campos[3]

            nome_l = nome.lower()
            desc_l = descricao.lower()
            status_l = status.lower()
            virtual_l = virtual.lower()

            eh_virtual = (
                virtual_l in ("true", "1")
                or
                "virtualbox" in desc_l
                or
                "vmware" in desc_l
            )

            eh_ethernet = (
                "ethernet" in nome_l
                or
                "ethernet" in desc_l
                or
                "gigabit" in desc_l
                or
                "realtek usb gbe" in desc_l
            )

            if (
                eh_ethernet
                and not eh_virtual
            ):

                ethernet = (
                    "Conectado"
                    if status_l == "up"
                    else
                    "Desconectado"
                )

                break

    except Exception as e:

        print(
            f"Erro ao consultar Ethernet: {e}"
        )

    return wifi, ethernet


# ============================================================
# 🌎 TESTAR INTERNET
# ============================================================

def testar_internet():

    for url in TEST_URLS:

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

            ms = round(
                (
                    time.perf_counter()
                    - inicio
                ) * 1000
            )

            return True, ms

        except Exception:
            continue

    return False, None


# ============================================================
# ⚡ MEDIR LATÊNCIA
# ============================================================

def medir_latencia():

    try:

        inicio = time.perf_counter()

        resultado = subprocess.run(
            [
                "ping",
                "-n",
                "1",
                "-w",
                str(LATENCIA_TIMEOUT),
                LATENCIA_HOST
            ],
            capture_output=True,
            text=True,
            encoding="cp850",
            errors="ignore",
            timeout=3,
            creationflags=subprocess.CREATE_NO_WINDOW
        )

        if resultado.returncode != 0:
            return None

        tempo_total = (
            time.perf_counter()
            - inicio
        ) * 1000

        # ----------------------------------------------------
        # TENTAR OBTER O VALOR EXATO MOSTRADO PELO PING
        # ----------------------------------------------------

        texto = (
            resultado.stdout
            + "\n"
            + resultado.stderr
        )

        import re

        correspondencia = re.search(
            r"(?:[=<]\s*)(\d+)\s*ms",
            texto,
            re.IGNORECASE
        )

        if correspondencia:

            return int(
                correspondencia.group(1)
            )

        # ----------------------------------------------------
        # FALLBACK
        # ----------------------------------------------------

        return round(
            tempo_total
        )

    except Exception as e:

        print(
            f"Erro ao medir latência: {e}"
        )

        return None


# ============================================================
# ⚡ MEDIÇÃO PARALELA
# ============================================================

def realizar_medicoes():

    with ThreadPoolExecutor(
        max_workers=4
    ) as executor:

        futuro_adaptadores = (
            executor.submit(
                verificar_adaptadores
            )
        )

        futuro_wifi_sinal = (
            executor.submit(
                obter_wifi_e_sinal
            )
        )

        futuro_ip = (
            executor.submit(
                obter_ip
            )
        )

        futuro_internet = (
            executor.submit(
                testar_internet
            )
        )

        futuro_latencia = (
            executor.submit(
                medir_latencia
            )
        )

        # ----------------------------------------------------
        # RESULTADOS
        # ----------------------------------------------------

        try:
            wifi_adaptador, ethernet = (
                futuro_adaptadores.result()
            )

        except Exception as e:

            print(
                f"Erro nos adaptadores: {e}"
            )

            wifi_adaptador = "Desconectado"
            ethernet = "Desconectado"

        try:
            wifi_sinal, sinal_wifi = (
                futuro_wifi_sinal.result()
            )

        except Exception as e:

            print(
                f"Erro no Wi-Fi: {e}"
            )

            wifi_sinal = "Desconectado"
            sinal_wifi = 0

        try:
            ip = futuro_ip.result()

        except Exception:

            ip = "--"

        try:
            online, tempo_internet = (
                futuro_internet.result()
            )

        except Exception:

            online = False
            tempo_internet = None

        try:
            latencia = (
                futuro_latencia.result()
            )

        except Exception:

            latencia = None

    # ========================================================
    # 📶 CORREÇÃO DO WI-FI
    # ========================================================

    wifi = wifi_sinal

    if wifi not in (
        "Conectado",
        "Desconectado"
    ):

        wifi = wifi_adaptador

    # ========================================================
    # 🌐 SE INTERNET ESTIVER OFFLINE
    # ========================================================

    if not online:

        latencia = None

    return (
        wifi,
        sinal_wifi,
        ethernet,
        online,
        ip,
        latencia
    )


# ============================================================
# ⚡ FORMATAR LATÊNCIA
# ============================================================

def formatar_ms(ms):

    if ms is None:
        return "--"

    return f"{ms} ms"


# ============================================================
# ⏱️ FORMATAR DURAÇÃO
# ============================================================

def formatar_duracao(segundos):

    segundos = max(
        0,
        int(segundos)
    )

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
# 📂 ABRIR HISTÓRICO
# ============================================================

def abrir_historico():

    try:

        inicializar_csv()

        os.startfile(
            CSV_FILE
        )

    except Exception as e:

        print(
            f"Não foi possível abrir o histórico: {e}"
        )


# ============================================================
# 📝 ADICIONAR EVENTO AO HISTÓRICO
# ============================================================

def adicionar_evento_historico(evento):

    global ultimo_evento_historico

    if not evento:
        return

    if evento == ultimo_evento_historico:
        return

    ultimo_evento_historico = evento

    registro = (
        f"{datetime.now().strftime('%H:%M:%S')}"
        f"  •  "
        f"{evento}"
    )

    historico_eventos.insert(
        0,
        registro
    )

    if len(historico_eventos) > 3:
        del historico_eventos[3:]


# ============================================================
# 🔄 MONITORAMENTO
# ============================================================

def monitorar():

    global estado_anterior
    global inicio_queda
    global contador_quedas
    global ultima_queda
    global duracao_ultima_queda
    global ultimo_evento
    global contador_testes
    global contador_sucessos

    while rodando:

        inicio_ciclo = time.perf_counter()

        try:

            # =================================================
            # ⚡ TODAS AS MEDIÇÕES OCORREM EM PARALELO
            # =================================================

            (
                wifi,
                sinal_wifi,
                ethernet,
                online,
                ip,
                latencia
            ) = realizar_medicoes()

            contador_testes += 1

            if online:
                contador_sucessos += 1

            estado = online

            # =================================================
            # 🚀 PRIMEIRA VERIFICAÇÃO
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

                    ultima_queda = (
                        inicio_queda.strftime(
                            "%d/%m/%Y %H:%M:%S"
                        )
                    )

                    ultimo_evento = (
                        "Internet caiu"
                    )

                    registrar_csv(
                        "QUEDA_INICIO",
                        wifi,
                        ethernet,
                        "OFFLINE",
                        ip,
                        "--"
                    )

            # =================================================
            # 🔴 QUEDA
            # =================================================

            elif (
                estado_anterior
                and not estado
            ):

                contador_quedas += 1

                inicio_queda = (
                    datetime.now()
                )

                ultima_queda = (
                    inicio_queda.strftime(
                        "%d/%m/%Y %H:%M:%S"
                    )
                )

                ultimo_evento = (
                    "Internet caiu"
                )

                registrar_csv(
                    "QUEDA_INICIO",
                    wifi,
                    ethernet,
                    "OFFLINE",
                    ip,
                    "--"
                )

            # =================================================
            # 🟢 RETORNO
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

                else:

                    duracao_ultima_queda = "--"

                ultimo_evento = (
                    "Internet restabelecida"
                )

                registrar_csv(
                    "QUEDA_FIM",
                    wifi,
                    ethernet,
                    "ONLINE",
                    ip,
                    latencia,
                    duracao_ultima_queda
                )

                inicio_queda = None

            # =================================================
            # 🌐 ESTADO NORMAL
            # =================================================

            else:

                ultimo_evento = (
                    "Internet OK"
                    if online
                    else
                    "Internet indisponível"
                )

            estado_anterior = estado

            # =================================================
            # 📝 HISTÓRICO DE EVENTOS
            # =================================================

            adicionar_evento_historico(
                ultimo_evento
            )

            # =================================================
            # 📊 HISTÓRICO DO GRÁFICO
            # =================================================

            pontos.append(
                latencia
                if (
                    online
                    and
                    latencia is not None
                )
                else
                None
            )

            historico_online.append(
                online
            )

            if len(pontos) > MAX_PONTOS:
                del pontos[:-MAX_PONTOS]

            if len(historico_online) > MAX_PONTOS:
                del historico_online[:-MAX_PONTOS]

            # =================================================
            # 📦 DADOS
            # =================================================

            dados = {
                "wifi": wifi,
                "sinal_wifi": sinal_wifi,
                "ethernet": ethernet,
                "internet": (
                    "ONLINE"
                    if online
                    else
                    "OFFLINE"
                ),
                "ip": ip,
                "latencia": latencia,
                "quedas": contador_quedas,
                "ultima_queda": ultima_queda,
                "duracao": duracao_ultima_queda,
                "evento": ultimo_evento,
                "historico_eventos": list(
                    historico_eventos
                ),
                "disponibilidade": (
                    contador_sucessos
                    / contador_testes
                    * 100
                    if contador_testes
                    else
                    0
                ),
                "pontos": list(pontos),
                "historico_online": list(
                    historico_online
                )
            }

            janela.after(
                0,
                atualizar_interface,
                dados
            )

        except Exception as e:

            print(
                f"Erro no monitoramento: {e}"
            )

        # =====================================================
        # ⏱️ MANTER INTERVALO REAL DE 2 SEGUNDOS
        # =====================================================

        tempo_decorrido = (
            time.perf_counter()
            - inicio_ciclo
        )

        espera = max(
            0.1,
            INTERVALO - tempo_decorrido
        )

        time.sleep(
            espera
        )


# ============================================================
# 🖼️ CRIAR CARD
# ============================================================

def criar_card(
    parent,
    titulo,
    cor_titulo="white"
):

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
            10,
            "bold"
        )
    ).pack(
        anchor="w",
        padx=14,
        pady=(12, 3)
    )

    valor = tk.Label(
        frame,
        text="--",
        bg="#151a21",
        fg="#f1f5f9",
        font=(
            "Segoe UI",
            17,
            "bold"
        )
    )

    valor.pack(
        anchor="w",
        padx=14,
        pady=(0, 8)
    )

    return frame, valor


# ============================================================
# 📶 INDICADOR DE SINAL WI-FI
# ============================================================

def atualizar_sinal_wifi(sinal):

    wifi_sinal_canvas.delete("all")

    if sinal >= 90:
        barras = 4
        cor = "#22c55e"
        qualidade = "Excelente"

    elif sinal >= 70:
        barras = 3
        cor = "#22c55e"
        qualidade = "Muito bom"

    elif sinal >= 50:
        barras = 2
        cor = "#eab308"
        qualidade = "Bom"

    elif sinal >= 30:
        barras = 1
        cor = "#f97316"
        qualidade = "Fraco"

    else:
        barras = 0
        cor = "#ef4444"
        qualidade = "Sem sinal"

    alturas = [
        8,
        15,
        23,
        32
    ]

    largura_barra = 9
    espacamento = 5
    x_inicial = 8
    base_y = 43

    for i in range(4):

        x1 = (
            x_inicial
            + i * (
                largura_barra
                + espacamento
            )
        )

        x2 = (
            x1
            + largura_barra
        )

        y2 = base_y

        y1 = (
            y2
            - alturas[i]
        )

        if i < barras:
            cor_barra = cor
        else:
            cor_barra = "#26313d"

        wifi_sinal_canvas.create_rectangle(
            x1,
            y1,
            x2,
            y2,
            fill=cor_barra,
            outline=""
        )

    wifi_sinal_canvas.create_text(
        88,
        14,
        text=f"{sinal}%",
        fill="#f8fafc",
        font=(
            "Segoe UI",
            12,
            "bold"
        )
    )

    wifi_sinal_canvas.create_text(
        88,
        36,
        text=qualidade,
        fill=cor,
        font=(
            "Segoe UI",
            8,
            "bold"
        )
    )


# ============================================================
# 📊 GRÁFICO DE BARRAS
# ============================================================

def desenhar_grafico():

    grafico.delete("all")

    largura = max(
        grafico.winfo_width(),
        500
    )

    altura = max(
        grafico.winfo_height(),
        260
    )

    margem_esquerda = 60
    margem_direita = 25
    margem_topo = 55
    margem_base = 45

    area_largura = (
        largura
        - margem_esquerda
        - margem_direita
    )

    area_altura = (
        altura
        - margem_topo
        - margem_base
    )

    # ========================================================
    # 📊 TÍTULO
    # ========================================================

    grafico.create_text(
        margem_esquerda,
        18,
        anchor="w",
        text="LATÊNCIA DA INTERNET",
        fill="#f8fafc",
        font=(
            "Segoe UI",
            12,
            "bold"
        )
    )

    # ========================================================
    # 📊 ESTATÍSTICAS
    # ========================================================

    valores_validos = [
        valor
        for valor in pontos
        if valor is not None
    ]

    if valores_validos:

        atual = valores_validos[-1]

        minimo = min(
            valores_validos
        )

        maximo = max(
            valores_validos
        )

        texto_stats = (
            f"Atual: {atual} ms    "
            f"Mín: {minimo} ms    "
            f"Máx: {maximo} ms"
        )

    else:

        texto_stats = (
            "Aguardando medições..."
        )

    grafico.create_text(
        largura - margem_direita,
        19,
        anchor="e",
        text=texto_stats,
        fill="#94a3b8",
        font=(
            "Segoe UI",
            9,
            "bold"
        )
    )

    # ========================================================
    # 📐 ESCALA FIXA
    # ========================================================

    escala_maxima = 300

    def y_pos(valor):

        valor_limitado = min(
            valor,
            escala_maxima
        )

        return (
            margem_topo
            + area_altura
            - (
                valor_limitado
                / escala_maxima
            ) * area_altura
        )

   
    # ========================================================
    # 📏 LINHAS DE ESCALA + GRADE PONTILHADA
    # ========================================================

    passos = 3

    for i in range(
        passos + 1
    ):

        valor = (
            escala_maxima
            / passos
            * i
        )

        y = y_pos(
            valor
        )

        # ----------------------------------------------------
        # LINHA DE GRADE PONTILHADA
        # ----------------------------------------------------

        grafico.create_line(
            margem_esquerda,
            y,
            largura - margem_direita,
            y,
            fill="#334155",
            dash=(3, 5),
            width=1
        )

        # ----------------------------------------------------
        # VALOR DA ESCALA
        # ----------------------------------------------------

        grafico.create_text(
            margem_esquerda - 8,
            y,
            anchor="e",
            text=f"{int(valor)}",
            fill="#64748b",
            font=(
                "Segoe UI",
                8
            )
        )

    # ========================================================
    # 📊 BARRAS
    # ========================================================

    if pontos:

        quantidade = len(
            pontos
        )

        espacamento = (
            area_largura
            / max(
                quantidade,
                1
            )
        )

        largura_barra = max(
            3,
            min(
                14,
                espacamento * 0.65
            )
        )

        for i, valor in enumerate(
            pontos
        ):

            centro_x = (
                margem_esquerda
                + (
                    i + 0.5
                ) * espacamento
            )

            esquerda = (
                centro_x
                - largura_barra / 2
            )

            direita = (
                centro_x
                + largura_barra / 2
            )

            # =================================================
            # 🔴 INTERNET OFFLINE
            # =================================================

            if valor is None:

                y_topo = (
                    margem_topo
                    + area_altura
                    - 20
                )

                y_base = (
                    margem_topo
                    + area_altura
                )

                grafico.create_rectangle(
                    esquerda,
                    y_topo,
                    direita,
                    y_base,
                    fill="#ef4444",
                    outline=""
                )

                if (
                    i == 0
                    or pontos[i - 1] is not None
                ):

                    grafico.create_text(
                        centro_x,
                        y_topo - 10,
                        text="OFF",
                        fill="#ef4444",
                        font=(
                            "Segoe UI",
                            7,
                            "bold"
                        )
                    )

                continue

            # =================================================
            # 📊 BARRA DE LATÊNCIA
            # =================================================

            y_topo = y_pos(
                valor
            )

            y_base = (
                margem_topo
                + area_altura
            )

            # =================================================
            # 🎨 CORES
            # =================================================

            if valor <= 100:
                cor = "#22c55e"

            elif valor <= 200:
                cor = "#eab308"

            else:
                cor = "#ef4444"

            grafico.create_rectangle(
                esquerda,
                y_topo,
                direita,
                y_base,
                fill=cor,
                outline=""
            )

            # =================================================
            # ⭐ ÚLTIMA MEDIÇÃO
            # =================================================

            if i == quantidade - 1:

                grafico.create_rectangle(
                    esquerda - 2,
                    y_topo - 2,
                    direita + 2,
                    y_base,
                    outline="#f8fafc",
                    width=2
                )

                if valor > escala_maxima:

                    grafico.create_text(
                        centro_x,
                        margem_topo - 12,
                        text=f"↑ {valor} ms",
                        fill="#ef4444",
                        font=(
                            "Segoe UI",
                            8,
                            "bold"
                        )
                    )

                else:

                    grafico.create_text(
                        centro_x,
                        y_topo - 12,
                        text=f"{valor} ms",
                        fill="#f8fafc",
                        font=(
                            "Segoe UI",
                            8,
                            "bold"
                        )
                    )

    # ========================================================
    # ⏱️ TEMPO
    # ========================================================

    grafico.create_text(
        margem_esquerda,
        altura - 20,
        anchor="w",
        text="~5 min atrás",
        fill="#64748b",
        font=(
            "Segoe UI",
            8
        )
    )

    grafico.create_text(
        largura - margem_direita,
        altura - 20,
        anchor="e",
        text="agora",
        fill="#64748b",
        font=(
            "Segoe UI",
            8
        )
    )

    # ========================================================
    # 📋 LEGENDA
    # ========================================================

    legenda_x = (
        margem_esquerda + 100
    )

    legenda_y = altura - 20

    # 🟢 Normal

    grafico.create_rectangle(
        legenda_x,
        legenda_y - 5,
        legenda_x + 10,
        legenda_y + 5,
        fill="#22c55e",
        outline=""
    )

    grafico.create_text(
        legenda_x + 16,
        legenda_y,
        anchor="w",
        text="0–100 ms",
        fill="#94a3b8",
        font=(
            "Segoe UI",
            8
        )
    )

    legenda_x += 85

    # 🟡 Atenção

    grafico.create_rectangle(
        legenda_x,
        legenda_y - 5,
        legenda_x + 10,
        legenda_y + 5,
        fill="#eab308",
        outline=""
    )

    grafico.create_text(
        legenda_x + 16,
        legenda_y,
        anchor="w",
        text="100–200 ms",
        fill="#94a3b8",
        font=(
            "Segoe UI",
            8
        )
    )

    legenda_x += 100

    # 🔴 Alta / OFF

    grafico.create_rectangle(
        legenda_x,
        legenda_y - 5,
        legenda_x + 10,
        legenda_y + 5,
        fill="#ef4444",
        outline=""
    )

    grafico.create_text(
        legenda_x + 16,
        legenda_y,
        anchor="w",
        text=">200 ms / OFF",
        fill="#94a3b8",
        font=(
            "Segoe UI",
            8
        )
    )


# ============================================================
# 🔄 ATUALIZAR INTERFACE
# ============================================================

def atualizar_interface(dados):

    wifi_valor.config(
        text=dados["wifi"],
        fg=(
            "#2196F3"
            if dados["wifi"] == "Conectado"
            else
            "#EF4444"
        )
    )

    atualizar_sinal_wifi(
        dados["sinal_wifi"]
    )

    ethernet_valor.config(
        text=dados["ethernet"],
        fg=(
            "#2196F3"
            if dados["ethernet"] == "Conectado"
            else
            "#EF4444"
        )
    )

    ip_valor.config(
        text=dados["ip"]
    )

    latencia_valor.config(
        text=formatar_ms(
            dados["latencia"]
        )
    )

    internet_valor.config(
        text=dados["internet"],
        fg=(
            "#22c55e"
            if dados["internet"] == "ONLINE"
            else
            "#ef4444"
        )
    )

    estado_valor.config(
        text=dados["internet"],
        fg=(
            "#22c55e"
            if dados["internet"] == "ONLINE"
            else
            "#ef4444"
        )
    )

    disponibilidade_valor.config(
        text=(
            f'{dados["disponibilidade"]:.1f}%'
        )
    )

    quedas_valor.config(
        text=str(
            dados["quedas"]
        )
    )

    ultima_valor.config(
        text=dados["ultima_queda"]
    )

    duracao_valor.config(
        text=dados["duracao"]
    )

    # ========================================================
    # 📝 ATUALIZAR ÚLTIMOS EVENTOS
    # ========================================================

    eventos = dados.get(
        "historico_eventos",
        []
    )

    for i, label in enumerate(
        evento_labels
    ):

        if i < len(eventos):

            label.config(
                text=eventos[i]
            )

        else:

            label.config(
                text=""
            )

    status_label.config(
        text=(
            f"Última verificação: "
            f"{agora()}"
        )
    )

    desenhar_grafico()


# ============================================================
# ❌ FECHAR
# ============================================================

def fechar():

    global rodando

    rodando = False

    janela.destroy()


# ============================================================
# 🚀 INICIALIZAÇÃO
# ============================================================

inicializar_csv()


# ============================================================
# 🖥️ JANELA
# ============================================================

janela = tk.Tk()

janela.title(
    f"{APP_NAME} {APP_VERSION} | "
    f"Desenvolvido por {AUTOR}"
)


# ============================================================
# 📐 DETECÇÃO AUTOMÁTICA DA TELA
# ============================================================

largura_tela = janela.winfo_screenwidth()
altura_tela = janela.winfo_screenheight()


# ============================================================
# 📐 TAMANHO IDEAL
# ============================================================

largura_ideal = 1080
altura_ideal = 700


# ============================================================
# 📐 ÁREA SEGURA
# ============================================================

if altura_tela <= 800:
    altura_maxima = altura_tela - 90
else:
    altura_maxima = altura_tela - 70

largura_maxima = largura_tela - 30


# ============================================================
# 📐 CALCULAR TAMANHO AUTOMÁTICO
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
# 📐 TAMANHO MÍNIMO ADAPTATIVO
# ============================================================

if altura_tela <= 800:

    altura_minima = max(
        500,
        min(
            570,
            altura_maxima
        )
    )

else:

    altura_minima = 600


if largura_tela <= 1000:

    largura_minima = max(
        760,
        largura_tela - 40
    )

else:

    largura_minima = 900


# ============================================================
# 📐 GARANTIR LIMITES
# ============================================================

largura_janela = max(
    largura_janela,
    largura_minima
)

altura_janela = max(
    altura_janela,
    altura_minima
)


# ============================================================
# 📐 GARANTIR QUE NÃO ULTRAPASSE A TELA
# ============================================================

largura_janela = min(
    largura_janela,
    largura_maxima
)

altura_janela = min(
    altura_janela,
    altura_maxima
)


# ============================================================
# 📍 CENTRALIZAR AUTOMATICAMENTE
# ============================================================

pos_x = max(
    0,
    (largura_tela - largura_janela) // 2
)

pos_y = max(
    0,
    (altura_tela - altura_janela) // 2
)


# ============================================================
# 🖥️ APLICAR TAMANHO
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
    font=(
        "Segoe UI",
        10,
        "bold"
    ),
    padding=(
        12,
        8
    )
)


# ============================================================
# 🤖 IMAGEM DO AUTOR
# ============================================================

robo_tk = None

try:

    robo_path = resource_path(
        os.path.join(
            "assets",
            "robo_github.png"
        )
    )

    robo_img = Image.open(
        robo_path
    ).convert(
        "RGBA"
    )

    robo_img.thumbnail(
        (42, 42),
        Image.LANCZOS
    )

    robo_tk = ImageTk.PhotoImage(
        robo_img
    )

except Exception as e:

    print(
        f"Não foi possível carregar o robozinho: {e}"
    )


# ============================================================
# 🧭 CABEÇALHO
# ============================================================

header = tk.Frame(
    janela,
    bg="#11161d",
    height=76
)

header.pack(
    fill="x"
)

header.pack_propagate(
    False
)


# ============================================================
# 🤖 MARCA DO AUTOR
# ============================================================

if robo_tk:

    marca_autor = tk.Label(
        header,
        image=robo_tk,
        bg="#11161d"
    )

else:

    marca_autor = tk.Label(
        header,
        text=MARCA_AUTOR,
        bg="#11161d",
        fg="#ff8c00",
        font=(
            "Segoe UI",
            11,
            "bold"
        )
    )

marca_autor.pack(
    side="left",
    padx=(18, 12),
    pady=8
)


# ============================================================
# 📡 IDENTIFICAÇÃO DO PROGRAMA
# ============================================================

titulo_frame = tk.Frame(
    header,
    bg="#11161d"
)

titulo_frame.pack(
    side="left",
    padx=(0, 24),
    pady=8
)

tk.Label(
    titulo_frame,
    text="MONITOR DE REDE",
    bg="#11161d",
    fg="#f8fafc",
    font=(
        "Segoe UI",
        18,
        "bold"
    )
).pack(
    anchor="w"
)

tk.Label(
    titulo_frame,
    text=f"Desenvolvido por {AUTOR}",
    bg="#11161d",
    fg="#38bdf8",
    font=(
        "Segoe UI",
        9,
        "bold"
    )
).pack(
    anchor="w",
    pady=(1, 0)
)


# ============================================================
# 📂 BOTÃO HISTÓRICO
# ============================================================

tk.Button(
    header,
    text="Abrir histórico",
    command=abrir_historico,
    bg="#1e293b",
    fg="#f8fafc",
    activebackground="#334155",
    activeforeground="#ffffff",
    relief="flat",
    padx=14,
    pady=8
).pack(
    side="right",
    padx=24
)


# ============================================================
# 📦 CONTEÚDO
# ============================================================

conteudo = tk.Frame(
    janela,
    bg="#0b0f14"
)

conteudo.pack(
    fill="both",
    expand=True,
    padx=20,
    pady=(8, 0)
)


# ============================================================
# 🃏 CARDS
# ============================================================

cards = tk.Frame(
    conteudo,
    bg="#0b0f14"
)

cards.pack(
    fill="x",
    expand=False
)


# ============================================================
# 📐 5 COLUNAS NA MESMA LINHA
# ============================================================

for col in range(5):

    cards.grid_columnconfigure(
        col,
        weight=1,
        uniform="cards"
    )


# ============================================================
# 📶 CARD WI-FI
# ============================================================

wifi_card, wifi_valor = criar_card(
    cards,
    "📶  WI-FI"
)

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
    pady=(0, 8)
)

wifi_card.grid(
    row=0,
    column=0,
    sticky="nsew",
    padx=4
)


# ============================================================
# 🔌 CARD ETHERNET
# ============================================================

ethernet_card, ethernet_valor = criar_card(
    cards,
    "🔌  ETHERNET"
)

ethernet_card.grid(
    row=0,
    column=1,
    sticky="nsew",
    padx=4
)


# ============================================================
# 🌐 CARD IP
# ============================================================

ip_card, ip_valor = criar_card(
    cards,
    "🌐  IP LOCAL"
)

ip_card.grid(
    row=0,
    column=2,
    sticky="nsew",
    padx=4
)


# ============================================================
# ⚡ CARD LATÊNCIA
# ============================================================

lat_card, latencia_valor = criar_card(
    cards,
    "⚡  LATÊNCIA"
)

lat_card.grid(
    row=0,
    column=3,
    sticky="nsew",
    padx=4
)


# ============================================================
# 🌎 CARD INTERNET
# ============================================================

internet_card, internet_valor = criar_card(
    cards,
    "INTERNET",
    "#38bdf8"
)

internet_card.grid(
    row=0,
    column=4,
    sticky="nsew",
    padx=4
)


# ============================================================
# 📊 ÁREA PRINCIPAL
# ============================================================

main = tk.Frame(
    conteudo,
    bg="#0b0f14"
)

main.pack(
    fill="both",
    expand=True,
    pady=(8, 0)
)

main.grid_columnconfigure(
    0,
    weight=3
)

main.grid_columnconfigure(
    1,
    weight=1
)

main.grid_rowconfigure(
    0,
    weight=1
)


# ============================================================
# 📊 GRÁFICO
# ============================================================

grafico = tk.Canvas(
    main,
    bg="#0b0f14",
    highlightthickness=0
)

grafico.grid(
    row=0,
    column=0,
    sticky="nsew",
    padx=(0, 8)
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
    font=(
        "Segoe UI",
        12,
        "bold"
    )
).pack(
    anchor="w",
    padx=18,
    pady=(18, 14)
)


# ============================================================
# 📋 ITEM DO RESUMO
# ============================================================

def item_resumo(nome):

    linha = tk.Frame(
        painel,
        bg="#151a21"
    )

    linha.pack(
        fill="x",
        padx=18,
        pady=7
    )

    tk.Label(
        linha,
        text=nome,
        bg="#151a21",
        fg="#94a3b8",
        font=(
            "Segoe UI",
            9
        )
    ).pack(
        side="left"
    )

    valor = tk.Label(
        linha,
        text="--",
        bg="#151a21",
        fg="#f8fafc",
        font=(
            "Segoe UI",
            9,
            "bold"
        )
    )

    valor.pack(
        side="right"
    )

    return valor


quedas_valor = item_resumo(
    "Total de quedas"
)

ultima_valor = item_resumo(
    "Última queda"
)

duracao_valor = item_resumo(
    "Duração última"
)

estado_valor = item_resumo(
    "Estado atual"
)

disponibilidade_valor = item_resumo(
    "Disponibilidade"
)


linha = tk.Frame(
    painel,
    bg="#2b3440",
    height=1
)

linha.pack(
    fill="x",
    padx=18,
    pady=12
)


# ============================================================
# 📝 ÚLTIMOS EVENTOS
# ============================================================

tk.Label(
    painel,
    text="ÚLTIMOS EVENTOS",
    bg="#151a21",
    fg="#64748b",
    font=(
        "Segoe UI",
        8,
        "bold"
    )
).pack(
    anchor="w",
    padx=18,
    pady=(0, 5)
)


eventos_frame = tk.Frame(
    painel,
    bg="#151a21"
)

eventos_frame.pack(
    fill="x",
    padx=18
)


evento_labels = []


for i in range(3):

    label = tk.Label(
        eventos_frame,
        text="",
        bg="#151a21",
        fg="#f8fafc",
        font=(
            "Segoe UI",
            8,
            "bold"
        ),
        anchor="w",
        justify="left",
        wraplength=220
    )

    label.pack(
        fill="x",
        pady=(2, 4)
    )

    evento_labels.append(
        label
    )


# ============================================================
# 🕐 RODAPÉ
# ============================================================

status_label = tk.Label(
    janela,
    text="Iniciando monitoramento...",
    bg="#080b0f",
    fg="#64748b",
    font=(
        "Segoe UI",
        9
    ),
    anchor="w",
    padx=20,
    pady=7
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
    font=(
        "Segoe UI",
        8
    ),
    anchor="center",
    pady=4
)

rodape.pack(
    fill="x",
    side="bottom"
)

status_label.pack(
    fill="x",
    side="bottom"
)


# ============================================================
# 🧵 THREAD DE MONITORAMENTO
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