# -*- coding: utf-8 -*-
"""
Ícone nativo na bandeja do Windows, implementado com ctypes.

Não usa bibliotecas externas: utiliza apenas user32, shell32 e kernel32.
"""

import ctypes
import sys
import time
from ctypes import wintypes as wt
from pathlib import Path

WM_NULL = 0x0000
WM_DESTROY = 0x0002
WM_COMMAND = 0x0111
WM_TIMER = 0x0113
WM_CONTEXTMENU = 0x007B
WM_RBUTTONUP = 0x0205
WM_LBUTTONDBLCLK = 0x0203
WM_HOTKEY = 0x0312
WM_USER = 0x0400
WM_TRAYICON = WM_USER + 1
WM_ACAO_TOAST = WM_USER + 2

NOME_CLASSE = "LembretesSaudeTrayWindow"
PROTOCOLO = "lembretes-saude"

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_NOREPEAT = 0x4000

VK_P = 0x50
VK_S = 0x53

ID_HOTKEY_PAUSAR = 1
ID_HOTKEY_SONECA = 2

ACAO_FEITO = 1
ACAO_SONECA_15 = 2

ACOES_MENSAGEM = {
    "feito": ACAO_FEITO,
    "soneca15": ACAO_SONECA_15,
}

NIM_ADD = 0
NIM_MODIFY = 1
NIM_DELETE = 2

NIF_MESSAGE = 0x00000001
NIF_ICON = 0x00000002
NIF_TIP = 0x00000004

CS_DBLCLKS = 0x0008

MF_STRING = 0x00000000
MF_GRAYED = 0x00000001
MF_SEPARATOR = 0x00000800

TPM_RIGHTBUTTON = 0x0002
TPM_NONOTIFY = 0x0080
TPM_RETURNCMD = 0x0100

IDI_APPLICATION = 32512
ERROR_CLASS_ALREADY_EXISTS = 1410

ID_PAUSAR = 1001
ID_RETOMAR = 1002
ID_CANCELAR_SONECA = 1003
ID_SONECA_15 = 1015
ID_SONECA_30 = 1030
ID_SONECA_60 = 1060
ID_SAIR = 1099

SONECAS = {
    ID_SONECA_15: 15 * 60,
    ID_SONECA_30: 30 * 60,
    ID_SONECA_60: 60 * 60,
}

TIMER_ID = 1

user32 = ctypes.WinDLL("user32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

WNDPROC = ctypes.WINFUNCTYPE(
    ctypes.c_ssize_t,
    wt.HWND,
    wt.UINT,
    wt.WPARAM,
    wt.LPARAM,
)


class ErroBandeja(RuntimeError):
    """Indica falha ao criar ou manter o ícone da bandeja."""


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_uint32),
        ("Data2", ctypes.c_uint16),
        ("Data3", ctypes.c_uint16),
        ("Data4", ctypes.c_ubyte * 8),
    ]


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wt.DWORD),
        ("hWnd", wt.HWND),
        ("uID", wt.UINT),
        ("uFlags", wt.UINT),
        ("uCallbackMessage", wt.UINT),
        ("hIcon", wt.HICON),
        ("szTip", wt.WCHAR * 128),
        ("dwState", wt.DWORD),
        ("dwStateMask", wt.DWORD),
        ("szInfo", wt.WCHAR * 256),
        ("uVersion", wt.UINT),
        ("szInfoTitle", wt.WCHAR * 64),
        ("dwInfoFlags", wt.DWORD),
        ("guidItem", GUID),
        ("hBalloonIcon", wt.HICON),
    ]


class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", wt.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wt.HINSTANCE),
        ("hIcon", wt.HICON),
        ("hCursor", wt.HANDLE),
        ("hbrBackground", wt.HBRUSH),
        ("lpszMenuName", wt.LPCWSTR),
        ("lpszClassName", wt.LPCWSTR),
    ]


_configurado = False


def _configurar_api() -> None:
    global _configurado

    if _configurado:
        return

    kernel32.GetModuleHandleW.argtypes = [wt.LPCWSTR]
    kernel32.GetModuleHandleW.restype = wt.HMODULE

    user32.LoadIconW.argtypes = [wt.HINSTANCE, ctypes.c_void_p]
    user32.LoadIconW.restype = wt.HICON

    user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
    user32.RegisterClassW.restype = wt.ATOM

    user32.CreateWindowExW.argtypes = [
        wt.DWORD,
        wt.LPCWSTR,
        wt.LPCWSTR,
        wt.DWORD,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        wt.HWND,
        wt.HMENU,
        wt.HINSTANCE,
        wt.LPVOID,
    ]
    user32.CreateWindowExW.restype = wt.HWND

    user32.DefWindowProcW.argtypes = [
        wt.HWND,
        wt.UINT,
        wt.WPARAM,
        wt.LPARAM,
    ]
    user32.DefWindowProcW.restype = ctypes.c_ssize_t

    user32.DestroyWindow.argtypes = [wt.HWND]
    user32.DestroyWindow.restype = wt.BOOL

    user32.PostQuitMessage.argtypes = [ctypes.c_int]
    user32.PostQuitMessage.restype = None

    user32.PostMessageW.argtypes = [
        wt.HWND,
        wt.UINT,
        wt.WPARAM,
        wt.LPARAM,
    ]
    user32.PostMessageW.restype = wt.BOOL

    user32.SetForegroundWindow.argtypes = [wt.HWND]
    user32.SetForegroundWindow.restype = wt.BOOL

    user32.SetTimer.argtypes = [
        wt.HWND,
        ctypes.c_size_t,
        wt.UINT,
        ctypes.c_void_p,
    ]
    user32.SetTimer.restype = ctypes.c_size_t

    user32.KillTimer.argtypes = [wt.HWND, ctypes.c_size_t]
    user32.KillTimer.restype = wt.BOOL

    user32.GetMessageW.argtypes = [
        ctypes.POINTER(wt.MSG),
        wt.HWND,
        wt.UINT,
        wt.UINT,
    ]
    user32.GetMessageW.restype = ctypes.c_int

    user32.TranslateMessage.argtypes = [ctypes.POINTER(wt.MSG)]
    user32.TranslateMessage.restype = wt.BOOL

    user32.DispatchMessageW.argtypes = [ctypes.POINTER(wt.MSG)]
    user32.DispatchMessageW.restype = ctypes.c_ssize_t

    user32.CreatePopupMenu.argtypes = []
    user32.CreatePopupMenu.restype = wt.HMENU

    user32.AppendMenuW.argtypes = [
        wt.HMENU,
        wt.UINT,
        ctypes.c_size_t,
        wt.LPCWSTR,
    ]
    user32.AppendMenuW.restype = wt.BOOL

    user32.DestroyMenu.argtypes = [wt.HMENU]
    user32.DestroyMenu.restype = wt.BOOL

    user32.GetCursorPos.argtypes = [ctypes.POINTER(wt.POINT)]
    user32.GetCursorPos.restype = wt.BOOL

    user32.TrackPopupMenu.argtypes = [
        wt.HMENU,
        wt.UINT,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        wt.HWND,
        ctypes.c_void_p,
    ]
    user32.TrackPopupMenu.restype = wt.UINT

    user32.RegisterWindowMessageW.argtypes = [wt.LPCWSTR]
    user32.RegisterWindowMessageW.restype = wt.UINT

    user32.RegisterHotKey.argtypes = [
        wt.HWND,
        ctypes.c_int,
        wt.UINT,
        wt.UINT,
    ]
    user32.RegisterHotKey.restype = wt.BOOL

    user32.UnregisterHotKey.argtypes = [wt.HWND, ctypes.c_int]
    user32.UnregisterHotKey.restype = wt.BOOL

    user32.FindWindowW.argtypes = [wt.LPCWSTR, wt.LPCWSTR]
    user32.FindWindowW.restype = wt.HWND

    shell32.Shell_NotifyIconW.argtypes = [
        wt.DWORD,
        ctypes.POINTER(NOTIFYICONDATAW),
    ]
    shell32.Shell_NotifyIconW.restype = wt.BOOL

    _configurado = True


def _criar_janela(callback: WNDPROC) -> wt.HWND:
    hinst = kernel32.GetModuleHandleW(None)
    if not hinst:
        raise ErroBandeja("GetModuleHandleW falhou.")

    nome_classe = NOME_CLASSE

    classe = WNDCLASSW()
    classe.style = CS_DBLCLKS
    classe.lpfnWndProc = callback
    classe.cbClsExtra = 0
    classe.cbWndExtra = 0
    classe.hInstance = hinst
    classe.hIcon = None
    classe.hCursor = None
    classe.hbrBackground = None
    classe.lpszMenuName = None
    classe.lpszClassName = nome_classe

    atomo = user32.RegisterClassW(ctypes.byref(classe))
    if not atomo:
        erro = ctypes.get_last_error()
        if erro != ERROR_CLASS_ALREADY_EXISTS:
            raise ErroBandeja(
                f"RegisterClassW falhou (erro {erro})."
            )

    hwnd = user32.CreateWindowExW(
        0,
        nome_classe,
        "Lembretes de Saúde",
        0,
        0,
        0,
        0,
        0,
        None,
        None,
        hinst,
        None,
    )

    if not hwnd:
        raise ErroBandeja("CreateWindowExW falhou.")

    return hwnd


def _carregar_icone() -> wt.HICON:
    icone = user32.LoadIconW(None, ctypes.c_void_p(IDI_APPLICATION))
    if not icone:
        raise ErroBandeja("LoadIconW falhou.")
    return icone


def _criar_nid(icone: wt.HICON) -> NOTIFYICONDATAW:
    nid = NOTIFYICONDATAW()
    nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
    nid.uID = 1
    nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
    nid.uCallbackMessage = WM_TRAYICON
    nid.hIcon = icone
    return nid


def _adicionar_icone(nid: NOTIFYICONDATAW, tentativas: int = 10) -> None:
    for tentativa in range(tentativas):
        if shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid)):
            return

        if tentativa + 1 < tentativas:
            time.sleep(1)

    raise ErroBandeja("Shell_NotifyIconW(NIM_ADD) falhou.")


def _atualizar_icone(nid: NOTIFYICONDATAW) -> None:
    if not shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(nid)):
        raise ErroBandeja("Shell_NotifyIconW(NIM_MODIFY) falhou.")


def _comando_protocolo() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --acao "%1"'

    executavel = Path(sys.executable)
    pythonw = executavel.with_name("pythonw.exe")
    if pythonw.is_file():
        executavel = pythonw

    script = Path(__file__).resolve().with_name("lembretes.py")
    return f'"{executavel}" "{script}" --acao "%1"'


def registrar_protocolo(registrar=None) -> bool:
    """Registra o protocolo usado pelos botões do toast."""
    try:
        import winreg

        with winreg.CreateKey(
            winreg.HKEY_CURRENT_USER,
            rf"Software\Classes\{PROTOCOLO}",
        ) as chave:
            winreg.SetValueEx(
                chave, "", 0, winreg.REG_SZ, "URL:Lembretes de Saúde"
            )
            winreg.SetValueEx(chave, "URL Protocol", 0, winreg.REG_SZ, "")

        with winreg.CreateKey(
            winreg.HKEY_CURRENT_USER,
            rf"Software\Classes\{PROTOCOLO}\shell\open\command",
        ) as chave:
            winreg.SetValueEx(
                chave, "", 0, winreg.REG_SZ, _comando_protocolo()
            )
    except OSError as erro:
        if registrar is not None:
            registrar(f"Não foi possível registrar o protocolo: {erro}")
        return False

    return True


def _normalizar_acao(valor: str) -> str:
    if not isinstance(valor, str):
        return ""

    valor = valor.strip().strip('"')
    prefixo = f"{PROTOCOLO}:"
    if valor.lower().startswith(prefixo):
        valor = valor[len(prefixo):]

    valor = valor.split("?", 1)[0].split("#", 1)[0]
    return valor.strip().strip("/").lower()


def executar_acao(acao: str) -> bool:
    """Envia uma ação de toast para a instância em execução."""
    codigo = ACOES_MENSAGEM.get(_normalizar_acao(acao))
    if codigo is None:
        return False

    _configurar_api()
    hwnd = user32.FindWindowW(NOME_CLASSE, None)
    if not hwnd:
        return False

    return bool(user32.PostMessageW(hwnd, WM_ACAO_TOAST, codigo, 0))


def executar_com_bandeja(agendador) -> None:
    """Executa o agendador com um ícone na bandeja do Windows."""
    _configurar_api()

    mensagem_taskbar_criada = user32.RegisterWindowMessageW(
        "TaskbarCreated"
    )

    icone = _carregar_icone()
    nid = _criar_nid(icone)
    estado_tooltip = {"texto": agendador.texto_status()[:127]}
    nid.szTip = estado_tooltip["texto"]

    def atualizar_tooltip() -> None:
        texto = agendador.texto_status()[:127]
        if texto == estado_tooltip["texto"]:
            return

        estado_tooltip["texto"] = texto
        nid.szTip = texto
        nid.uFlags = NIF_TIP

        try:
            _atualizar_icone(nid)
        except ErroBandeja as erro:
            agendador.registrar(str(erro))
        finally:
            nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP

    def alternar_pausa() -> None:
        if agendador.pausado:
            agendador.retomar()
        elif agendador.sonecando:
            agendador.cancelar_soneca()
        else:
            agendador.pausar()

    def alternar_soneca() -> None:
        if agendador.sonecando:
            agendador.cancelar_soneca()
        else:
            agendador.sonecar(15 * 60)

    def executar_comando(comando: int, hwnd: wt.HWND) -> None:
        if comando == ID_PAUSAR:
            agendador.pausar()
        elif comando == ID_RETOMAR:
            agendador.retomar()
        elif comando == ID_CANCELAR_SONECA:
            agendador.cancelar_soneca()
        elif comando in SONECAS:
            agendador.sonecar(SONECAS[comando])
        elif comando == ID_SAIR:
            user32.DestroyWindow(hwnd)
            return

        atualizar_tooltip()

    def mostrar_menu(hwnd: wt.HWND) -> None:
        menu = user32.CreatePopupMenu()
        if not menu:
            return

        try:
            user32.AppendMenuW(
                menu,
                MF_STRING | MF_GRAYED,
                0,
                agendador.texto_status(),
            )
            user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)

            if agendador.pausado:
                user32.AppendMenuW(
                    menu, MF_STRING, ID_RETOMAR, "Retomar lembretes"
                )
            elif agendador.sonecando:
                user32.AppendMenuW(
                    menu, MF_STRING, ID_CANCELAR_SONECA, "Cancelar soneca"
                )
            else:
                user32.AppendMenuW(
                    menu, MF_STRING, ID_PAUSAR, "Pausar lembretes"
                )

            user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)
            user32.AppendMenuW(
                menu, MF_STRING, ID_SONECA_15, "Soneca por 15 minutos"
            )
            user32.AppendMenuW(
                menu, MF_STRING, ID_SONECA_30, "Soneca por 30 minutos"
            )
            user32.AppendMenuW(
                menu, MF_STRING, ID_SONECA_60, "Soneca por 60 minutos"
            )
            user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)
            user32.AppendMenuW(menu, MF_STRING, ID_SAIR, "Sair")

            ponto = wt.POINT()
            user32.GetCursorPos(ctypes.byref(ponto))
            user32.SetForegroundWindow(hwnd)

            comando = user32.TrackPopupMenu(
                menu,
                TPM_RETURNCMD | TPM_RIGHTBUTTON | TPM_NONOTIFY,
                ponto.x,
                ponto.y,
                0,
                hwnd,
                None,
            )
            user32.PostMessageW(hwnd, WM_NULL, 0, 0)

            if comando:
                executar_comando(comando, hwnd)
        finally:
            user32.DestroyMenu(menu)

    def tratar_mensagem(hwnd, mensagem, wparam, lparam):
        if (
            mensagem_taskbar_criada
            and mensagem == mensagem_taskbar_criada
        ):
            try:
                _adicionar_icone(nid)
            except ErroBandeja as erro:
                agendador.registrar(str(erro))
            return 0

        if mensagem == WM_TRAYICON:
            evento = int(lparam) & 0xFFFF

            if evento in (WM_RBUTTONUP, WM_CONTEXTMENU):
                mostrar_menu(hwnd)
            elif evento == WM_LBUTTONDBLCLK:
                alternar_pausa()
                atualizar_tooltip()

            return 0

        if mensagem == WM_COMMAND:
            executar_comando(int(wparam) & 0xFFFF, hwnd)
            return 0

        if mensagem == WM_HOTKEY:
            if int(wparam) == ID_HOTKEY_PAUSAR:
                alternar_pausa()
            elif int(wparam) == ID_HOTKEY_SONECA:
                alternar_soneca()

            atualizar_tooltip()
            return 0

        if mensagem == WM_ACAO_TOAST:
            codigo = int(wparam)
            if codigo == ACAO_FEITO:
                agendador.confirmar_lembrete()
            elif codigo == ACAO_SONECA_15:
                agendador.sonecar(15 * 60)

            atualizar_tooltip()
            return 0

        if mensagem == WM_TIMER:
            try:
                agendador.tick()
            except Exception as erro:
                agendador.registrar(f"ERRO no agendador: {erro}")

            atualizar_tooltip()
            return 0

        if mensagem == WM_DESTROY:
            shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(nid))
            user32.PostQuitMessage(0)
            return 0

        return user32.DefWindowProcW(hwnd, mensagem, wparam, lparam)

    def ao_receber_mensagem(hwnd, mensagem, wparam, lparam):
        try:
            return tratar_mensagem(hwnd, mensagem, wparam, lparam)
        except Exception as erro:
            agendador.registrar(f"ERRO na bandeja: {erro}")
            return 0

    callback = WNDPROC(ao_receber_mensagem)
    hwnd = _criar_janela(callback)
    nid.hWnd = hwnd

    icone_adicionado = False
    timer = 0
    hotkeys_registrados = []

    try:
        if getattr(agendador, "atalhos_globais", False):
            for identificador, tecla, rotulo in (
                (ID_HOTKEY_PAUSAR, VK_P, "Ctrl+Alt+P"),
                (ID_HOTKEY_SONECA, VK_S, "Ctrl+Alt+S"),
            ):
                if user32.RegisterHotKey(
                    hwnd,
                    identificador,
                    MOD_CONTROL | MOD_ALT | MOD_NOREPEAT,
                    tecla,
                ):
                    hotkeys_registrados.append(identificador)
                else:
                    agendador.registrar(
                        f"Não foi possível registrar o atalho {rotulo}."
                    )

        if getattr(agendador, "acoes_toast", False):
            if not registrar_protocolo(agendador.registrar):
                agendador.registrar(
                    "As ações no toast ficarão indisponíveis."
                )

        _adicionar_icone(nid)
        icone_adicionado = True

        intervalo_ms = max(
            200, int(agendador.intervalo_verificacao * 1000)
        )
        timer = user32.SetTimer(hwnd, TIMER_ID, intervalo_ms, None)

        if not timer:
            raise ErroBandeja("SetTimer falhou.")

        mensagem = wt.MSG()
        while True:
            resultado = user32.GetMessageW(
                ctypes.byref(mensagem), None, 0, 0
            )

            if resultado == 0:
                break

            if resultado == -1:
                raise ErroBandeja("GetMessageW falhou.")

            user32.TranslateMessage(ctypes.byref(mensagem))
            user32.DispatchMessageW(ctypes.byref(mensagem))
    except KeyboardInterrupt:
        agendador.registrar("Encerrando pela bandeja...")
    finally:
        for identificador in hotkeys_registrados:
            user32.UnregisterHotKey(hwnd, identificador)

        if timer:
            user32.KillTimer(hwnd, timer)

        if icone_adicionado:
            shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(nid))

        user32.DestroyWindow(hwnd)
