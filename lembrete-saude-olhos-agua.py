
# -*- coding: utf-8 -*-
"""
Lembretes de saúde para Windows 11 (sem dependências externas).

- A cada 20 minutos: descanso dos olhos + som.
- A cada 60 minutos: beber água + som.
- A cada 90 minutos: levantar e se alongar + som.

Requer Python 3 e recursos nativos do Windows.

Modo de teste: python lembretes.py --teste
"""

import ctypes
import ctypes.wintypes
import subprocess
import sys
import threading
import time
import winsound

# Modo teste: python lembretes.py --teste
MODO_TESTE = "--teste" in sys.argv

# Intervalos dos lembretes (em segundos)
INTERVALO_OLHOS = 5 if MODO_TESTE else 20 * 60
INTERVALO_AGUA = 12 if MODO_TESTE else 60 * 60
INTERVALO_ALONGAMENTO = 18 if MODO_TESTE else 90 * 60

# Sons diferentes (frequência em Hz, duração em ms)
SOM_OLHOS = [(1000, 200), (1400, 300)]
SOM_AGUA = [(600, 600)]
SOM_ALONGAMENTO = [(800, 250), (1000, 250), (1200, 400)]


def tocar_som(notas):
    """Toca uma sequência de bipes (Hz, duração_ms)."""
    for freq, duracao in notas:
        winsound.Beep(freq, duracao)


class MonitorInfo(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.wintypes.DWORD),
        ("rcMonitor", ctypes.wintypes.RECT),
        ("rcWork", ctypes.wintypes.RECT),
        ("dwFlags", ctypes.wintypes.DWORD),
    ]


def em_tela_cheia():
    """Verifica se a janela em primeiro plano cobre o monitor inteiro."""
    user32 = ctypes.windll.user32
    hwnd = user32.GetForegroundWindow()

    if not hwnd or user32.IsIconic(hwnd):
        return False

    rect = ctypes.wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))

    MONITOR_DEFAULTTONEAREST = 2
    monitor = user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)

    info = MonitorInfo()
    info.cbSize = ctypes.sizeof(MonitorInfo)
    user32.GetMonitorInfoW(monitor, ctypes.byref(info))

    return (
        rect.left <= info.rcMonitor.left
        and rect.top <= info.rcMonitor.top
        and rect.right >= info.rcMonitor.right
        and rect.bottom >= info.rcMonitor.bottom
    )


def notificar(titulo, mensagem):
    """Mostra uma notificação do Windows via PowerShell."""

    # Escapa caracteres especiais para inserir o texto no XML.
    def escapar_xml(texto):
        return (
            texto.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )

    titulo_xml = escapar_xml(titulo)
    mensagem_xml = escapar_xml(mensagem)

    script = f"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom, ContentType = WindowsRuntime] | Out-Null

$AppId = '{{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}}\\WindowsPowerShell\\v1.0\\powershell.exe'

$template = @"
<toast scenario="reminder">
  <visual>
    <binding template="ToastGeneric">
      <text>{titulo_xml}</text>
      <text>{mensagem_xml}</text>
    </binding>
  </visual>
  <audio src="ms-winsoundevent:Notification.Default"/>
</toast>
"@

$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml($template)
$toast = New-Object Windows.UI.Notifications.ToastNotification $xml
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($AppId).Show($toast)
"""

    resultado = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-Command", script,
        ],
        capture_output=True,
        text=True,
        creationflags=0x08000000,  # CREATE_NO_WINDOW
    )

    if resultado.returncode != 0:
        print("ERRO na notificação:", resultado.stderr.strip())


def avisar(titulo, mensagem, notas):
    """Toca o som e evita notificações visuais em tela cheia."""
    tocar_som(notas)

    if em_tela_cheia():
        print(f"[tela cheia] Som apenas: {titulo}")
    else:
        notificar(titulo, mensagem)


def loop_olhos():
    while True:
        time.sleep(INTERVALO_OLHOS)
        avisar(
            "Hora de descansar os olhos! 👀",
            "Olhe para longe por 20 segundos e pisque os olhos.",
            SOM_OLHOS,
        )


def loop_agua():
    while True:
        time.sleep(INTERVALO_AGUA)
        avisar(
            "Beba água! 💧",
            "Lembre-se de beber um copo de água.",
            SOM_AGUA,
        )


def loop_alongamento():
    while True:
        time.sleep(INTERVALO_ALONGAMENTO)
        avisar(
            "Hora de se movimentar! 🧍",
            "Levante-se um pouco, caminhe e faça alguns alongamentos.",
            SOM_ALONGAMENTO,
        )


def formato_intervalo(segundos):
    if segundos >= 3600:
        horas = segundos // 3600
        minutos = (segundos % 3600) // 60
        if minutos:
            return f"{horas}h{minutos:02d}min"
        return f"{horas}h"

    return f"{segundos // 60} min" if segundos >= 60 else f"{segundos} s"


def main():
    if MODO_TESTE:
        print(
            "MODO TESTE: olhos a cada 5s, "
            "água a cada 12s e alongamento a cada 18s."
        )

    print("Lembretes de saúde iniciados. Ctrl+C para sair.")
    print(f" - Olhos       : a cada {formato_intervalo(INTERVALO_OLHOS)}")
    print(f" - Água        : a cada {formato_intervalo(INTERVALO_AGUA)}")
    print(
        " - Alongamento: a cada "
        f"{formato_intervalo(INTERVALO_ALONGAMENTO)}"
    )

    notificar(
        "Lembretes ativados! ✅",
        f"Olhos: {formato_intervalo(INTERVALO_OLHOS)} | "
        f"Água: {formato_intervalo(INTERVALO_AGUA)} | "
        f"Alongamento: {formato_intervalo(INTERVALO_ALONGAMENTO)}.",
    )

    threads = [
        threading.Thread(target=loop_olhos, daemon=True),
        threading.Thread(target=loop_agua, daemon=True),
        threading.Thread(target=loop_alongamento, daemon=True),
    ]

    for thread in threads:
        thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nEncerrado. Até logo!")


if __name__ == "__main__":
    main()
