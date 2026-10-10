# -*- coding: utf-8 -*-
"""
Lembretes de saúde para Windows 11 (sem dependências externas).

- A cada 20 minutos: notificação "Olhe para longe e pisque os olhos" + som.
- A cada 60 minutos: notificação "Beba água" + som diferente.

Requer apenas Python 3 (usa win10toast? Não — usa apenas biblioteca padrão,
com PowerShell para a notificação e winsound para o som).
"""

import ctypes
import ctypes.wintypes
import subprocess
import sys
import threading
import time
import winsound

# Modo teste: python lembretes.py --teste
# Usa intervalos curtos para você conferir as notificações na hora.
MODO_TESTE = "--teste" in sys.argv

INTERVALO_OLHOS = 5 if MODO_TESTE else 20 * 60   # 20 minutos (5s no teste)
INTERVALO_AGUA = 12 if MODO_TESTE else 60 * 60    # 60 minutos (12s no teste)

# Sons diferentes (frequência em Hz, duração em ms)
# Olhos: dois "bipes" agudos curtos
SOM_OLHOS = [(1000, 200), (1400, 300)]
# Água: um bip mais grave e longo
SOM_AGUA = [(600, 600)]


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
    """Retorna True se a janela em primeiro plano cobre o monitor inteiro
    (jogo ou app em tela cheia). Usa apenas API do Windows via ctypes."""
    user32 = ctypes.windll.user32
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return False

    # Janela minimizada não é tela cheia
    if user32.IsIconic(hwnd):
        return False

    # Retângulo da janela
    rect = ctypes.wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))

    # Retângulo do monitor onde a janela está
    MONITOR_DEFAULTTONEAREST = 2
    monitor = user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
    info = MonitorInfo()
    info.cbSize = ctypes.sizeof(MonitorInfo)
    user32.GetMonitorInfoW(monitor, ctypes.byref(info))

    return (rect.left <= info.rcMonitor.left
            and rect.top <= info.rcMonitor.top
            and rect.right >= info.rcMonitor.right
            and rect.bottom >= info.rcMonitor.bottom)


class MonitorInfo(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.wintypes.DWORD),
        ("rcMonitor", ctypes.wintypes.RECT),
        ("rcWork", ctypes.wintypes.RECT),
        ("dwFlags", ctypes.wintypes.DWORD),
    ]


def notificar(titulo, mensagem):
    """Mostra uma notificação toast do Windows via PowerShell."""
    # Escape de aspas simples para segurança no PowerShell
    titulo_ps = titulo.replace("'", "''")
    msg_ps = mensagem.replace("'", "''")

    # Usa o AppUserModelID do próprio PowerShell: o Windows 11 só exibe
    # toasts de apps com AUMID registrado, e um AUMID inventado é
    # silenciosamente descartado. O AUMID do powershell.exe é aceito.
    script = f"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom, ContentType = WindowsRuntime] | Out-Null

$AppId = '{{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}}\\WindowsPowerShell\\v1.0\\powershell.exe'

$template = @"
<toast scenario="reminder">
  <visual>
    <binding template="ToastGeneric">
      <text>{titulo_ps}</text>
      <text>{msg_ps}</text>
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
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        capture_output=True, text=True,
        creationflags=0x08000000,  # não abre janela do console (CREATE_NO_WINDOW)
    )
    if resultado.returncode != 0:
        print("ERRO na notificação:", resultado.stderr.strip())


def avisar(titulo, mensagem, notas):
    """Toca o som sempre; mostra a notificação apenas se não
    estiver em tela cheia (para não interromper jogos)."""
    tocar_som(notas)
    if em_tela_cheia():
        print(f"[tela cheia] Som apenas: {titulo}")
    else:
        notificar(titulo, mensagem)


def loop_olhos():
    while True:
        time.sleep(INTERVALO_OLHOS)
        avisar("Hora de descansar os olhos! 👀",
               "Olhe para longe por 20 segundos e pisque os olhos.",
               SOM_OLHOS)


def loop_agua():
    while True:
        time.sleep(INTERVALO_AGUA)
        avisar("Beba água! 💧",
              "Lembre-se de beber um copo de água.",
              SOM_AGUA)


def formato_intervalo(segundos):
    return f"{segundos // 60} min" if segundos >= 60 else f"{segundos} s"


def main():
    if MODO_TESTE:
        print("MODO TESTE: olhos a cada 5s, água a cada 12s.")
    print("Lembretes de saúde iniciados. Ctrl+C para sair.")
    print(f" - Olhos: a cada {formato_intervalo(INTERVALO_OLHOS)}")
    print(f" - Água : a cada {formato_intervalo(INTERVALO_AGUA)}")

    # Notificação de boas-vindas confirmando que está funcionando
    notificar("Lembretes ativados! ✅",
              f"Olhos a cada {formato_intervalo(INTERVALO_OLHOS)}, "
              f"água a cada {formato_intervalo(INTERVALO_AGUA)}.")

    t_olhos = threading.Thread(target=loop_olhos, daemon=True)
    t_agua = threading.Thread(target=loop_agua, daemon=True)
    t_olhos.start()
    t_agua.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nEncerrado. Até logo!")


if __name__ == "__main__":
    main()