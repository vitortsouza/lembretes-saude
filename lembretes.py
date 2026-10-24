# -*- coding: utf-8 -*-
"""
Lembretes de saúde para Windows 10/11, sem dependências externas.

- A cada 20 minutos: descanso dos olhos.
- A cada 60 minutos: beber água.
- A cada 90 minutos: levantar e se alongar.
- Em tela cheia, o som e a notificação ficam pendentes.
- Ao sair da tela cheia, o lembrete atrasado é entregue.

Uso:
    python lembretes.py
    python lembretes.py --teste
"""

import ctypes
import ctypes.wintypes
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, List, Optional, Sequence, Tuple

E_WINDOWS = sys.platform == "win32"

if E_WINDOWS:
    import winsound
else:
    winsound = None

# Modo teste: python lembretes.py --teste
MODO_TESTE = "--teste" in sys.argv

# Intervalos dos lembretes (em segundos)
INTERVALO_OLHOS = 5 if MODO_TESTE else 20 * 60
INTERVALO_AGUA = 12 if MODO_TESTE else 60 * 60
INTERVALO_ALONGAMENTO = 18 if MODO_TESTE else 90 * 60

# Atrasos iniciais para distribuir as primeiras notificações
ATRASO_OLHOS = INTERVALO_OLHOS
ATRASO_AGUA = 7 if MODO_TESTE else 25 * 60
ATRASO_ALONGAMENTO = 11 if MODO_TESTE else 35 * 60

# Frequência com que a agenda e o estado de tela cheia são verificados
INTERVALO_VERIFICACAO = 1

# Sons diferentes (frequência em Hz, duração em ms)
SOM_OLHOS = [(1000, 200), (1400, 300)]
SOM_AGUA = [(600, 600)]
SOM_ALONGAMENTO = [(800, 250), (1000, 250), (1200, 400)]

# Janelas do próprio Windows que não devem ser tratadas como tela cheia
CLASSES_SHELL = frozenset(
    {
        "Progman",
        "WorkerW",
        "Shell_TrayWnd",
        "Shell_SecondaryTrayWnd",
    }
)

MONITOR_DEFAULTTONEAREST = 2
CREATE_NO_WINDOW = 0x08000000

_user32 = None


def log(mensagem: str) -> None:
    """Exibe uma mensagem com horário no terminal."""
    print(f"[{datetime.now():%H:%M:%S}] {mensagem}", flush=True)


class MonitorInfo(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.wintypes.DWORD),
        ("rcMonitor", ctypes.wintypes.RECT),
        ("rcWork", ctypes.wintypes.RECT),
        ("dwFlags", ctypes.wintypes.DWORD),
    ]


def _configurar_api():
    """Configura os tipos das funções do Windows usadas na detecção."""
    global _user32

    if _user32 is not None:
        return _user32

    user32 = ctypes.WinDLL("user32", use_last_error=True)

    try:
        user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
        user32.SetProcessDpiAwarenessContext.restype = ctypes.wintypes.BOOL
        user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except (AttributeError, OSError):
        try:
            user32.SetProcessDPIAware.argtypes = []
            user32.SetProcessDPIAware.restype = ctypes.wintypes.BOOL
            user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass

    user32.GetForegroundWindow.restype = ctypes.wintypes.HWND

    user32.IsIconic.argtypes = [ctypes.wintypes.HWND]
    user32.IsIconic.restype = ctypes.wintypes.BOOL

    user32.IsWindowVisible.argtypes = [ctypes.wintypes.HWND]
    user32.IsWindowVisible.restype = ctypes.wintypes.BOOL

    user32.GetWindowRect.argtypes = [
        ctypes.wintypes.HWND,
        ctypes.POINTER(ctypes.wintypes.RECT),
    ]
    user32.GetWindowRect.restype = ctypes.wintypes.BOOL

    user32.GetClassNameW.argtypes = [
        ctypes.wintypes.HWND,
        ctypes.wintypes.LPWSTR,
        ctypes.c_int,
    ]
    user32.GetClassNameW.restype = ctypes.c_int

    user32.MonitorFromWindow.argtypes = [
        ctypes.wintypes.HWND,
        ctypes.wintypes.DWORD,
    ]
    user32.MonitorFromWindow.restype = ctypes.wintypes.HMONITOR

    user32.GetMonitorInfoW.argtypes = [
        ctypes.wintypes.HMONITOR,
        ctypes.POINTER(MonitorInfo),
    ]
    user32.GetMonitorInfoW.restype = ctypes.wintypes.BOOL

    _user32 = user32
    return user32


def _classe_da_janela(user32, hwnd) -> str:
    buffer = ctypes.create_unicode_buffer(256)
    if user32.GetClassNameW(hwnd, buffer, len(buffer)) == 0:
        return ""
    return buffer.value


def em_tela_cheia() -> bool:
    """Verifica se a janela em primeiro plano cobre o monitor inteiro."""
    if not E_WINDOWS:
        return False

    user32 = _configurar_api()
    hwnd = user32.GetForegroundWindow()

    if not hwnd:
        return False

    if user32.IsIconic(hwnd) or not user32.IsWindowVisible(hwnd):
        return False

    if _classe_da_janela(user32, hwnd) in CLASSES_SHELL:
        return False

    retangulo = ctypes.wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(retangulo)):
        return False

    monitor = user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
    if not monitor:
        return False

    info = MonitorInfo()
    info.cbSize = ctypes.sizeof(MonitorInfo)
    if not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
        return False

    area = info.rcMonitor
    return (
        retangulo.left <= area.left
        and retangulo.top <= area.top
        and retangulo.right >= area.right
        and retangulo.bottom >= area.bottom
    )


def tocar_som(notas: Sequence[Tuple[int, int]]) -> None:
    """Toca uma sequência de bipes (Hz, duração_ms)."""
    if not E_WINDOWS or winsound is None:
        return

    for frequencia, duracao in notas:
        try:
            winsound.Beep(frequencia, duracao)
        except RuntimeError as erro:
            log(f"Não foi possível tocar o som: {erro}")
            return


def escapar_xml(texto: str) -> str:
    """Escapa caracteres especiais para uso no XML da notificação."""
    return (
        texto.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def montar_script_toast(titulo: str, mensagem: str) -> str:
    """Monta o script do PowerShell que exibe a notificação."""
    titulo_xml = escapar_xml(titulo)
    mensagem_xml = escapar_xml(mensagem)

    return f"""
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
  <audio silent="true"/>
</toast>
"@

$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml($template)
$toast = New-Object Windows.UI.Notifications.ToastNotification $xml
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($AppId).Show($toast)
"""


def notificar(titulo: str, mensagem: str) -> bool:
    """Mostra uma notificação do Windows via PowerShell."""
    if not E_WINDOWS:
        return False

    script = montar_script_toast(titulo, mensagem)

    try:
        resultado = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy", "Bypass",
                "-Command", script,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
            creationflags=CREATE_NO_WINDOW,
        )
    except (OSError, subprocess.TimeoutExpired) as erro:
        log(f"ERRO ao executar o PowerShell: {erro}")
        return False

    if resultado.returncode != 0:
        detalhe = (resultado.stderr or "").strip() or "falha desconhecida"
        log(f"ERRO na notificação: {detalhe}")
        return False

    return True


@dataclass
class Lembrete:
    nome: str
    titulo: str
    mensagem: str
    notas: Sequence[Tuple[int, int]]
    intervalo: float
    atraso_inicial: float
    proximo: float = 0.0
    pendente: bool = False


def criar_lembretes() -> List[Lembrete]:
    """Cria os lembretes configurados para esta execução."""
    return [
        Lembrete(
            "Olhos",
            "Hora de descansar os olhos! 👀",
            "Olhe para longe por 20 segundos e pisque os olhos.",
            SOM_OLHOS,
            INTERVALO_OLHOS,
            ATRASO_OLHOS,
        ),
        Lembrete(
            "Água",
            "Beba água! 💧",
            "Lembre-se de beber um copo de água.",
            SOM_AGUA,
            INTERVALO_AGUA,
            ATRASO_AGUA,
        ),
        Lembrete(
            "Alongamento",
            "Hora de se movimentar! 🧍",
            "Levante-se um pouco, caminhe e faça alguns alongamentos.",
            SOM_ALONGAMENTO,
            INTERVALO_ALONGAMENTO,
            ATRASO_ALONGAMENTO,
        ),
    ]


def iniciar_agenda(
    lembretes: List[Lembrete], agora: Optional[float] = None
) -> None:
    """Define os primeiros horários e zera os lembretes pendentes."""
    if agora is None:
        agora = time.monotonic()

    for lembrete in lembretes:
        lembrete.proximo = agora + lembrete.atraso_inicial
        lembrete.pendente = False


def processar_tick(
    lembretes: List[Lembrete],
    agora: float,
    tela_cheia: bool,
    entregar: Callable[[Lembrete, bool], None],
) -> List[Lembrete]:
    """Processa um instante da agenda e retorna os lembretes adiados."""
    adiados = []

    for lembrete in lembretes:
        if tela_cheia:
            if not lembrete.pendente and agora >= lembrete.proximo:
                lembrete.pendente = True
                lembrete.proximo = agora + lembrete.intervalo
                adiados.append(lembrete)
            continue

        if lembrete.pendente:
            entregar(lembrete, True)
            lembrete.pendente = False

            # Se a próxima data já passou enquanto ele estava pendente,
            # reagenda para evitar uma rajada de notificações antigas.
            if lembrete.proximo <= agora:
                lembrete.proximo = agora + lembrete.intervalo
        elif agora >= lembrete.proximo:
            entregar(lembrete, False)
            lembrete.proximo = agora + lembrete.intervalo

    return adiados


def entregar_lembrete(lembrete: Lembrete, atrasado: bool) -> None:
    """Reproduz o som e exibe a notificação de um lembrete."""
    if atrasado:
        log(f"{lembrete.nome}: entregando lembrete adiado.")
        mensagem = (
            f"{lembrete.mensagem}\n\n"
            "Adiado enquanto você estava em um app em tela cheia."
        )
    else:
        log(f"{lembrete.nome}: lembrete entregue.")
        mensagem = lembrete.mensagem

    tocar_som(lembrete.notas)

    if not notificar(lembrete.titulo, mensagem):
        log("A notificação visual não pôde ser exibida.")


def executar_lembretes(lembretes: List[Lembrete]) -> None:
    """Executa a agenda central até o programa ser interrompido."""
    iniciar_agenda(lembretes)
    tela_cheia_anterior = None

    while True:
        agora = time.monotonic()
        tela_cheia = em_tela_cheia()

        if tela_cheia and tela_cheia_anterior is False:
            log("Tela cheia detectada: som e notificações serão adiados.")
        elif not tela_cheia and tela_cheia_anterior is True:
            log("Tela cheia encerrada: retomando a agenda.")

        tela_cheia_anterior = tela_cheia

        for lembrete in processar_tick(
            lembretes, agora, tela_cheia, entregar_lembrete
        ):
            log(f"{lembrete.nome}: lembrete adiado durante a tela cheia.")

        time.sleep(INTERVALO_VERIFICACAO)


def formato_intervalo(segundos: float) -> str:
    """Formata uma duração em segundos para exibição."""
    segundos = int(segundos)

    if segundos >= 3600:
        horas = segundos // 3600
        minutos = (segundos % 3600) // 60

        if minutos:
            return f"{horas}h{minutos:02d}min"

        return f"{horas}h"

    return f"{segundos // 60} min" if segundos >= 60 else f"{segundos} s"


def mostrar_boas_vindas(lembretes: List[Lembrete]) -> None:
    """Exibe a notificação inicial, exceto quando há tela cheia."""
    if em_tela_cheia():
        log("Notificação de boas-vindas não exibida (tela cheia).")
        return

    resumo = " | ".join(
        f"{lembrete.nome}: {formato_intervalo(lembrete.intervalo)}"
        for lembrete in lembretes
    )
    notificar("Lembretes ativados! ✅", f"Intervalos: {resumo}.")


def main() -> int:
    if not E_WINDOWS:
        print(
            "Este programa requer Windows 10 ou 11.",
            file=sys.stderr,
        )
        return 1

    lembretes = criar_lembretes()

    if MODO_TESTE:
        print(
            "MODO TESTE: olhos a cada 5s, "
            "água a cada 12s e alongamento a cada 18s."
        )
        print("Atrasos iniciais: olhos 5s, água 7s, alongamento 11s.")

    print("Lembretes de saúde iniciados. Ctrl+C para sair.")
    for lembrete in lembretes:
        print(
            f" - {lembrete.nome:<12}: "
            f"a cada {formato_intervalo(lembrete.intervalo)}"
        )
    print(
        "Em tela cheia, som e notificação ficam pendentes até você "
        "sair do app."
    )

    mostrar_boas_vindas(lembretes)

    try:
        executar_lembretes(lembretes)
    except KeyboardInterrupt:
        print("\nEncerrado. Até logo!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
