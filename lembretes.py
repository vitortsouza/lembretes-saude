# -*- coding: utf-8 -*-
"""
Lembretes de saúde para Windows 10/11, sem dependências externas.

- A cada 20 minutos: descanso dos olhos.
- A cada 60 minutos: beber água.
- A cada 90 minutos: levantar e se alongar.
- Em tela cheia, o som e a notificação ficam pendentes.
- Ao sair da tela cheia, o lembrete atrasado é entregue.
- Ícone na bandeja para pausar, fazer uma soneca ou sair.
- Horário de silêncio configurável e atalhos globais.
- Botões "Feito" e "Soneca 15 min" no toast.
- Histórico em JSON Lines e resumo com --estatisticas.

Uso:
    python lembretes.py
    python lembretes.py --teste
    python lembretes.py --config config.json
    python lembretes.py --sem-bandeja --sem-som
    python lembretes.py --estatisticas
"""

import argparse
import copy
import ctypes
import ctypes.wintypes
import json
import subprocess
import sys
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, List, Optional, Sequence, Tuple

E_WINDOWS = sys.platform == "win32"

if E_WINDOWS:
    import winsound
else:
    winsound = None

VERSAO = "2.1.0"

PROTOCOLO_ACOES = "lembretes-saude"

DIAS_SEMANA = {
    "seg": 0,
    "ter": 1,
    "qua": 2,
    "qui": 3,
    "sex": 4,
    "sab": 5,
    "dom": 6,
}

ACOES_TOAST = (
    ("Feito ✅", f"{PROTOCOLO_ACOES}:feito"),
    ("Soneca 15 min", f"{PROTOCOLO_ACOES}:soneca15"),
)

ACOES_VALIDAS = frozenset({"feito", "soneca15"})

# Sons diferentes (frequência em Hz, duração em ms)
SOM_OLHOS = [[1000, 200], [1400, 300]]
SOM_AGUA = [[600, 600]]
SOM_ALONGAMENTO = [[800, 250], [1000, 250], [1200, 400]]

# Valores usados pelo modo --teste
TESTE_INTERVALOS = {
    "olhos": (5, 5),
    "agua": (12, 7),
    "alongamento": (18, 11),
}

# Ordem fixa dos lembretes na configuração e na interface
LEMBRETES_PADRAO = ("olhos", "agua", "alongamento")

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


def diretorio_base() -> Path:
    """Retorna a pasta usada para config e histórico."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parent


def normalizar_acao(valor: str) -> str:
    """Converte uma URI de ação em um nome simples, como ``feito``."""
    if not isinstance(valor, str):
        return ""

    valor = valor.strip().strip('"')
    prefixo = f"{PROTOCOLO_ACOES}:"
    if valor.lower().startswith(prefixo):
        valor = valor[len(prefixo):]

    valor = valor.split("?", 1)[0].split("#", 1)[0]
    return valor.strip().strip("/").lower()


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
            winsound.Beep(int(frequencia), int(duracao))
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


def montar_script_toast(
    titulo: str,
    mensagem: str,
    acoes: Optional[Sequence[Tuple[str, str]]] = None,
) -> str:
    """Monta o script do PowerShell que exibe a notificação."""
    titulo_xml = escapar_xml(titulo)
    mensagem_xml = escapar_xml(mensagem)

    bloco_acoes = ""
    if acoes:
        itens = "\n".join(
            "      <action "
            f'content="{escapar_xml(texto)}" '
            'activationType="protocol" '
            f'arguments="{escapar_xml(argumento)}" />'
            for texto, argumento in acoes
        )
        bloco_acoes = f"\n  <actions>\n{itens}\n  </actions>"

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
  <audio silent="true"/>{bloco_acoes}
</toast>
"@

$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml($template)
$toast = New-Object Windows.UI.Notifications.ToastNotification $xml
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($AppId).Show($toast)
"""


def notificar(
    titulo: str,
    mensagem: str,
    acoes: Optional[Sequence[Tuple[str, str]]] = None,
) -> bool:
    """Mostra uma notificação do Windows via PowerShell."""
    if not E_WINDOWS:
        return False

    script = montar_script_toast(titulo, mensagem, acoes)

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


def config_padrao() -> dict:
    """Retorna a configuração completa com os valores padrão."""
    return {
        "usar_bandeja": True,
        "som_ativo": True,
        "intervalo_verificacao": 1.0,
        "atalhos_globais": True,
        "acoes_toast": True,
        "horario_silencio": {
            "ativo": False,
            "inicio": "22:00",
            "fim": "07:00",
            "dias_semana": list(DIAS_SEMANA),
        },
        "historico": {
            "ativo": True,
            "arquivo": "historico.jsonl",
        },
        "lembretes": {
            "olhos": {
                "ativo": True,
                "nome": "Olhos",
                "intervalo_segundos": 20 * 60,
                "atraso_inicial_segundos": 20 * 60,
                "titulo": "Hora de descansar os olhos! 👀",
                "mensagem": (
                    "Olhe para longe por 20 segundos e pisque os olhos."
                ),
                "notas": copy.deepcopy(SOM_OLHOS),
            },
            "agua": {
                "ativo": True,
                "nome": "Água",
                "intervalo_segundos": 60 * 60,
                "atraso_inicial_segundos": 25 * 60,
                "titulo": "Beba água! 💧",
                "mensagem": "Lembre-se de beber um copo de água.",
                "notas": copy.deepcopy(SOM_AGUA),
            },
            "alongamento": {
                "ativo": True,
                "nome": "Alongamento",
                "intervalo_segundos": 90 * 60,
                "atraso_inicial_segundos": 35 * 60,
                "titulo": "Hora de se movimentar! 🧍",
                "mensagem": (
                    "Levante-se um pouco, caminhe e faça alguns "
                    "alongamentos."
                ),
                "notas": copy.deepcopy(SOM_ALONGAMENTO),
            },
        },
    }


def aplicar_modo_teste(config: dict) -> None:
    """Troca os intervalos pelos valores curtos do modo de teste."""
    for chave, (intervalo, atraso) in TESTE_INTERVALOS.items():
        config["lembretes"][chave]["intervalo_segundos"] = intervalo
        config["lembretes"][chave]["atraso_inicial_segundos"] = atraso


def mesclar_config(base: dict, extra: dict, prefixo: str = "") -> dict:
    """Faz a mesclagem recursiva entre a configuração padrão e a do usuário."""
    if not isinstance(extra, dict):
        raise ValueError(f"{prefixo or 'config'} deve ser um objeto.")

    resultado = copy.deepcopy(base)
    for chave, valor in extra.items():
        caminho = f"{prefixo}{chave}"

        if chave not in resultado:
            raise ValueError(f"Chave desconhecida na configuração: {caminho}")

        atual = resultado[chave]
        if isinstance(atual, dict):
            if not isinstance(valor, dict):
                raise ValueError(f"{caminho} deve ser um objeto.")
            resultado[chave] = mesclar_config(atual, valor, f"{caminho}.")
        else:
            resultado[chave] = valor

    return resultado


def _validar_booleano(valor, nome: str) -> None:
    if not isinstance(valor, bool):
        raise ValueError(f"{nome} deve ser true ou false.")


def _validar_numero(
    valor,
    nome: str,
    minimo: float = None,
    permitir_zero: bool = False,
) -> None:
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise ValueError(f"{nome} deve ser um número.")

    if permitir_zero:
        invalido = valor < 0
    else:
        invalido = valor <= 0

    if invalido:
        if permitir_zero:
            raise ValueError(f"{nome} não pode ser negativo.")
        raise ValueError(f"{nome} deve ser maior que zero.")

    if minimo is not None and valor < minimo:
        raise ValueError(f"{nome} deve ser maior ou igual a {minimo}.")


def _validar_texto(valor, nome: str) -> None:
    if not isinstance(valor, str) or not valor.strip():
        raise ValueError(f"{nome} deve ser um texto não vazio.")


def _validar_hora(valor, nome: str) -> None:
    if not isinstance(valor, str) or len(valor) != 5 or valor[2] != ":":
        raise ValueError(f"{nome} deve estar no formato HH:MM.")

    horas, minutos = valor[:2], valor[3:]
    if not (horas.isdigit() and minutos.isdigit()):
        raise ValueError(f"{nome} deve estar no formato HH:MM.")

    if not (0 <= int(horas) <= 23 and 0 <= int(minutos) <= 59):
        raise ValueError(f"{nome} deve ser um horário válido.")


def _validar_inteiro(
    valor, nome: str, minimo: int, maximo: int
) -> None:
    if (
        isinstance(valor, bool)
        or not isinstance(valor, (int, float))
        or int(valor) != valor
    ):
        raise ValueError(f"{nome} deve ser um número inteiro.")

    if not minimo <= int(valor) <= maximo:
        raise ValueError(
            f"{nome} deve estar entre {minimo} e {maximo}."
        )


def validar_config(config: dict) -> None:
    """Valida os tipos e os limites da configuração."""
    _validar_booleano(config["usar_bandeja"], "usar_bandeja")
    _validar_booleano(config["som_ativo"], "som_ativo")
    _validar_booleano(config["atalhos_globais"], "atalhos_globais")
    _validar_booleano(config["acoes_toast"], "acoes_toast")
    _validar_numero(
        config["intervalo_verificacao"],
        "intervalo_verificacao",
        minimo=0.2,
    )

    silencio = config["horario_silencio"]
    if not isinstance(silencio, dict):
        raise ValueError("horario_silencio deve ser um objeto.")

    _validar_booleano(silencio["ativo"], "horario_silencio.ativo")
    _validar_hora(silencio["inicio"], "horario_silencio.inicio")
    _validar_hora(silencio["fim"], "horario_silencio.fim")

    if silencio["inicio"] == silencio["fim"]:
        raise ValueError(
            "horario_silencio.inicio e horario_silencio.fim devem ser "
            "diferentes."
        )

    dias = silencio["dias_semana"]
    if not isinstance(dias, list) or not dias:
        raise ValueError(
            "horario_silencio.dias_semana deve ser uma lista não vazia."
        )

    for indice, dia in enumerate(dias):
        if dia not in DIAS_SEMANA:
            raise ValueError(
                "horario_silencio.dias_semana deve conter apenas "
                "seg, ter, qua, qui, sex, sab e dom."
            )

        if dias.index(dia) != indice:
            raise ValueError(
                "horario_silencio.dias_semana não pode ter dias repetidos."
            )

    historico = config["historico"]
    if not isinstance(historico, dict):
        raise ValueError("historico deve ser um objeto.")

    _validar_booleano(historico["ativo"], "historico.ativo")
    _validar_texto(historico["arquivo"], "historico.arquivo")

    if not isinstance(config.get("lembretes"), dict):
        raise ValueError("lembretes deve ser um objeto.")

    for chave in LEMBRETES_PADRAO:
        dados = config["lembretes"].get(chave)
        prefixo = f"lembretes.{chave}"

        if not isinstance(dados, dict):
            raise ValueError(f"{prefixo} deve ser um objeto.")

        _validar_booleano(dados["ativo"], f"{prefixo}.ativo")
        _validar_texto(dados["nome"], f"{prefixo}.nome")
        _validar_texto(dados["titulo"], f"{prefixo}.titulo")
        _validar_texto(dados["mensagem"], f"{prefixo}.mensagem")
        _validar_numero(
            dados["intervalo_segundos"],
            f"{prefixo}.intervalo_segundos",
        )
        _validar_numero(
            dados["atraso_inicial_segundos"],
            f"{prefixo}.atraso_inicial_segundos",
            permitir_zero=True,
        )

        notas = dados["notas"]
        if not isinstance(notas, list):
            raise ValueError(f"{prefixo}.notas deve ser uma lista.")

        for indice, nota in enumerate(notas):
            caminho = f"{prefixo}.notas[{indice}]"
            if not isinstance(nota, (list, tuple)) or len(nota) != 2:
                raise ValueError(
                    f"{caminho} deve conter [frequencia, duracao_ms]."
                )
            _validar_inteiro(nota[0], f"{caminho}[0]", 37, 32767)
            _validar_inteiro(nota[1], f"{caminho}[1]", 1, 60000)


def _minutos_do_dia(horario: str) -> int:
    return int(horario[:2]) * 60 + int(horario[3:])


def em_horario_silencio(
    horario: dict, momento: Optional[datetime] = None
) -> bool:
    """Indica se o momento atual está dentro do horário de silêncio."""
    if not horario.get("ativo"):
        return False

    if momento is None:
        momento = datetime.now()

    inicio = _minutos_do_dia(horario["inicio"])
    fim = _minutos_do_dia(horario["fim"])
    atual = momento.hour * 60 + momento.minute
    dias = {DIAS_SEMANA[dia] for dia in horario["dias_semana"]}
    dia = momento.weekday()

    if inicio < fim:
        return dia in dias and inicio <= atual < fim

    if atual >= inicio and dia in dias:
        return True

    dia_anterior = (dia - 1) % 7
    return atual < fim and dia_anterior in dias


def caminho_historico(config: dict) -> Path:
    """Resolve o caminho do arquivo de histórico."""
    arquivo = Path(config["historico"]["arquivo"]).expanduser()
    if not arquivo.is_absolute():
        arquivo = diretorio_base() / arquivo

    return arquivo


class Historico:
    """Grava eventos em um arquivo JSON Lines."""

    def __init__(self, caminho) -> None:
        self.caminho = Path(caminho)

    def registrar(self, evento: str, **dados) -> bool:
        registro = {
            "quando": datetime.now().isoformat(timespec="seconds"),
            "evento": evento,
        }
        registro.update(dados)

        try:
            self.caminho.parent.mkdir(parents=True, exist_ok=True)
            with self.caminho.open("a", encoding="utf-8") as arquivo:
                arquivo.write(
                    json.dumps(registro, ensure_ascii=False) + "\n"
                )
        except OSError as erro:
            log(f"Não foi possível gravar o histórico: {erro}")
            return False

        return True


def criar_historico(config: dict) -> Optional[Historico]:
    """Cria o histórico quando ele está ativado na configuração."""
    if not config["historico"]["ativo"]:
        return None

    return Historico(caminho_historico(config))


def _ler_historico(caminho: Path) -> List[dict]:
    registros = []

    try:
        with caminho.open("r", encoding="utf-8") as arquivo:
            for linha in arquivo:
                linha = linha.strip()
                if not linha:
                    continue

                try:
                    item = json.loads(linha)
                except json.JSONDecodeError:
                    continue

                if isinstance(item, dict):
                    registros.append(item)
    except OSError:
        return []

    return registros


def _duracao_evento(item: dict) -> float:
    try:
        return max(0.0, float(item.get("duracao_segundos") or 0))
    except (TypeError, ValueError):
        return 0.0


def mostrar_estatisticas(caminho) -> int:
    """Exibe um resumo dos eventos gravados no histórico."""
    caminho = Path(caminho)

    if not caminho.is_file():
        print(f"Nenhum histórico encontrado em {caminho}.")
        return 0

    registros = _ler_historico(caminho)
    if not registros:
        print(f"Nenhum evento registrado em {caminho}.")
        return 0

    eventos = Counter(item.get("evento", "") for item in registros)
    entregues = [
        item
        for item in registros
        if item.get("evento") == "lembrete_entregue"
    ]
    atrasados = sum(1 for item in entregues if item.get("atrasado"))
    confirmados = eventos.get("lembrete_confirmado", 0)
    pausas = eventos.get("pausa_iniciada", 0)
    sonecas = eventos.get("soneca_iniciada", 0)
    silencios = eventos.get("silencio_iniciado", 0)

    duracao_pausas = sum(
        _duracao_evento(item)
        for item in registros
        if item.get("evento") == "pausa_encerrada"
    )
    duracao_sonecas = sum(
        _duracao_evento(item)
        for item in registros
        if item.get("evento") in ("soneca_encerrada", "soneca_cancelada")
    )
    duracao_silencio = sum(
        _duracao_evento(item)
        for item in registros
        if item.get("evento") == "silencio_encerrado"
    )

    por_lembrete = Counter(
        item.get("nome", "?") for item in entregues if item.get("nome")
    )
    instantes = [
        item["quando"]
        for item in registros
        if isinstance(item.get("quando"), str)
    ]

    print(f"Histórico: {caminho}")
    if instantes:
        print(f"Período: {min(instantes)} a {max(instantes)}")

    print(f"Eventos registrados: {len(registros)}")
    print()
    print(f"Lembretes entregues: {len(entregues)} ({atrasados} adiados)")
    print(f"Confirmados com \"Feito\": {confirmados}")
    print(
        f"Pausas: {pausas} "
        f"({formato_intervalo(duracao_pausas)})"
    )
    print(
        f"Sonecas: {sonecas} "
        f"({formato_intervalo(duracao_sonecas)})"
    )
    print(
        f"Silêncio: {silencios} "
        f"({formato_intervalo(duracao_silencio)})"
    )

    if por_lembrete:
        print()
        print("Entregas por lembrete:")
        for nome, total in por_lembrete.most_common():
            print(f" - {nome}: {total}")

    return 0


def carregar_config(caminho: Optional[str] = None) -> dict:
    """Carrega config.json (ou um caminho explícito) e valida o resultado."""
    config = config_padrao()

    if caminho is None:
        padrao = diretorio_base() / "config.json"
        if padrao.is_file():
            caminho = str(padrao)
    elif not Path(caminho).is_file():
        raise FileNotFoundError(
            f"Arquivo de configuração não encontrado: {caminho}"
        )

    if caminho is not None:
        with open(caminho, "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)

        if not isinstance(dados, dict):
            raise ValueError(
                "O arquivo de configuração deve conter um objeto JSON."
            )

        config = mesclar_config(config, dados)

    validar_config(config)
    return config


def criar_lembretes(config: dict) -> List[Lembrete]:
    """Cria os lembretes ativos a partir da configuração validada."""
    lembretes = []

    for chave in LEMBRETES_PADRAO:
        dados = config["lembretes"][chave]
        if not dados["ativo"]:
            continue

        lembretes.append(
            Lembrete(
                nome=dados["nome"].strip(),
                titulo=dados["titulo"].strip(),
                mensagem=dados["mensagem"].strip(),
                notas=tuple(
                    (int(frequencia), int(duracao))
                    for frequencia, duracao in dados["notas"]
                ),
                intervalo=float(dados["intervalo_segundos"]),
                atraso_inicial=float(
                    dados["atraso_inicial_segundos"]
                ),
            )
        )

    return lembretes


def aplicar_cli(config: dict, args: argparse.Namespace) -> None:
    """Aplica as opções de linha de comando sobre a configuração."""
    if args.sem_som:
        config["som_ativo"] = False

    if args.sem_bandeja:
        config["usar_bandeja"] = False

    intervalos = {
        "olhos": args.olhos,
        "agua": args.agua,
        "alongamento": args.alongamento,
    }

    for chave, minutos in intervalos.items():
        if minutos is None:
            continue
        if minutos <= 0:
            raise ValueError(f"--{chave} deve ser maior que zero.")
        config["lembretes"][chave]["intervalo_segundos"] = minutos * 60


def criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Lembretes periódicos de saúde para Windows 10/11."
        )
    )
    parser.add_argument(
        "--teste",
        action="store_true",
        help="usa intervalos curtos para testar o programa.",
    )
    parser.add_argument(
        "--config",
        metavar="ARQUIVO",
        help="carrega um arquivo JSON de configuração.",
    )
    parser.add_argument(
        "--sem-bandeja",
        action="store_true",
        help="executa sem o ícone na bandeja do Windows.",
    )
    parser.add_argument(
        "--sem-som",
        action="store_true",
        help="desativa os bipes dos lembretes.",
    )
    parser.add_argument(
        "--olhos",
        type=float,
        metavar="MINUTOS",
        help="intervalo do lembrete dos olhos, em minutos.",
    )
    parser.add_argument(
        "--agua",
        type=float,
        metavar="MINUTOS",
        help="intervalo do lembrete de água, em minutos.",
    )
    parser.add_argument(
        "--alongamento",
        type=float,
        metavar="MINUTOS",
        help="intervalo do lembrete de alongamento, em minutos.",
    )
    parser.add_argument(
        "--estatisticas",
        action="store_true",
        help="mostra um resumo do histórico de lembretes.",
    )
    parser.add_argument(
        "--acao",
        metavar="ACAO",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--versao",
        action="version",
        version=f"%(prog)s {VERSAO}",
    )
    return parser


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


def entregar_lembrete(
    lembrete: Lembrete,
    atrasado: bool,
    som_ativo: bool = True,
    acoes: Optional[Sequence[Tuple[str, str]]] = None,
) -> None:
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

    if som_ativo:
        tocar_som(lembrete.notas)

    if not notificar(lembrete.titulo, mensagem, acoes):
        log("A notificação visual não pôde ser exibida.")


class Agendador:
    """Mantém a agenda e o estado de pausa, soneca e silêncio."""

    def __init__(
        self,
        lembretes: List[Lembrete],
        som_ativo: bool = True,
        intervalo_verificacao: float = 1.0,
        obter_tela_cheia: Callable[[], bool] = em_tela_cheia,
        relogio: Callable[[], float] = time.monotonic,
        entregar: Optional[Callable[[Lembrete, bool], None]] = None,
        registrar: Callable[[str], None] = log,
        em_silencio: Optional[Callable[[], bool]] = None,
        historico: Optional[Historico] = None,
        atalhos_globais: bool = False,
        acoes_toast: bool = False,
    ) -> None:
        self.lembretes = lembretes
        self.som_ativo = som_ativo
        self.intervalo_verificacao = intervalo_verificacao
        self._obter_tela_cheia = obter_tela_cheia
        self._relogio = relogio
        self.registrar = registrar
        self._obter_silencio = em_silencio or (lambda: False)
        self.historico = historico
        self.atalhos_globais = atalhos_globais
        self.acoes_toast = acoes_toast
        self.pausado = False
        self.soneca_ate = None
        self.soneca_fim = None
        self.em_silencio = False
        self.suspenso_desde = None
        self.pausa_inicio = None
        self.soneca_inicio = None
        self.silencio_inicio = None
        self.tela_cheia_anterior = None
        self.ultimo_entregue = None

        if entregar is None:
            def realizar(lembrete, atrasado):
                self._registrar_entrega(lembrete, atrasado)
                entregar_lembrete(
                    lembrete,
                    atrasado,
                    som_ativo=self.som_ativo,
                    acoes=ACOES_TOAST if self.acoes_toast else None,
                )
        else:
            def realizar(lembrete, atrasado):
                self._registrar_entrega(lembrete, atrasado)
                entregar(lembrete, atrasado)

        self._entregar = realizar

        iniciar_agenda(lembretes, self._relogio())

    @property
    def sonecando(self) -> bool:
        return self.soneca_ate is not None

    @property
    def suspenso(self) -> bool:
        return self.pausado or self.sonecando or self.em_silencio

    def _registrar_evento(self, evento: str, **dados) -> None:
        if self.historico is not None:
            self.historico.registrar(evento, **dados)

    def _registrar_entrega(self, lembrete, atrasado) -> None:
        self.ultimo_entregue = lembrete
        self._registrar_evento(
            "lembrete_entregue",
            nome=lembrete.nome,
            atrasado=atrasado,
        )

    def _entrar_suspensao(self, agora: float) -> None:
        if self.suspenso_desde is None:
            self.suspenso_desde = agora

    def _encerrar_suspensao(self, agora: float) -> None:
        if self.suspenso_desde is None or self.suspenso:
            return

        decorrido = max(0.0, agora - self.suspenso_desde)
        for lembrete in self.lembretes:
            lembrete.proximo += decorrido

        self.suspenso_desde = None

    def _duracao_desde(
        self, inicio: Optional[float], agora: float
    ) -> float:
        if inicio is None:
            return 0.0

        return round(max(0.0, agora - inicio), 2)

    def _encerrar_soneca(self, agora: float, evento: str) -> None:
        duracao = self._duracao_desde(self.soneca_inicio, agora)
        self.soneca_ate = None
        self.soneca_fim = None
        self.soneca_inicio = None
        self._registrar_evento(evento, duracao_segundos=duracao)

    def _atualizar_silencio(self, agora: float) -> None:
        ativo = bool(self._obter_silencio())
        if ativo == self.em_silencio:
            return

        self.em_silencio = ativo

        if ativo:
            self.silencio_inicio = agora
            self._entrar_suspensao(agora)
            self.registrar(
                "Horário de silêncio iniciado: som e notificações serão "
                "adiados."
            )
            self._registrar_evento("silencio_iniciado")
        else:
            duracao = self._duracao_desde(self.silencio_inicio, agora)
            self.silencio_inicio = None
            self.registrar(
                "Horário de silêncio encerrado: retomando a agenda."
            )
            self._registrar_evento(
                "silencio_encerrado", duracao_segundos=duracao
            )
            self._encerrar_suspensao(agora)

    def pausar(self) -> None:
        if self.pausado:
            return

        agora = self._relogio()
        self._atualizar_silencio(agora)

        if self.sonecando:
            self._encerrar_soneca(agora, "soneca_cancelada")

        self.pausado = True
        self.pausa_inicio = agora
        self._entrar_suspensao(agora)
        self._registrar_evento("pausa_iniciada")
        self.registrar("Lembretes pausados. Use o ícone para retomar.")

    def retomar(self) -> None:
        if not self.pausado:
            return

        agora = self._relogio()
        self.pausado = False
        duracao = self._duracao_desde(self.pausa_inicio, agora)
        self.pausa_inicio = None
        self._registrar_evento("pausa_encerrada", duracao_segundos=duracao)
        self._encerrar_suspensao(agora)

        if self.em_silencio:
            self.registrar(
                "Pausa encerrada. O horário de silêncio continua ativo."
            )
        else:
            self.registrar("Lembretes retomados.")

    def sonecar(self, segundos: float) -> None:
        if segundos <= 0:
            return

        agora = self._relogio()
        self._atualizar_silencio(agora)

        if self.pausado:
            self.pausado = False
            duracao = self._duracao_desde(self.pausa_inicio, agora)
            self.pausa_inicio = None
            self._registrar_evento(
                "pausa_encerrada", duracao_segundos=duracao
            )

        if self.sonecando:
            self._encerrar_soneca(agora, "soneca_encerrada")

        self.soneca_ate = agora + segundos
        self.soneca_fim = datetime.now() + timedelta(seconds=segundos)
        self.soneca_inicio = agora
        self._entrar_suspensao(agora)
        self._registrar_evento(
            "soneca_iniciada", duracao_segundos=round(segundos, 2)
        )
        self.registrar(
            f"Soneca ativada por {formato_intervalo(segundos)}."
        )

    def cancelar_soneca(self) -> None:
        if not self.sonecando:
            return

        agora = self._relogio()
        self._encerrar_soneca(agora, "soneca_cancelada")
        self._encerrar_suspensao(agora)
        self.registrar("Soneca cancelada.")

    def confirmar_lembrete(self) -> None:
        nome = self.ultimo_entregue.nome if self.ultimo_entregue else None

        if nome:
            self.registrar(f"{nome}: lembrete confirmado como feito.")
            self._registrar_evento("lembrete_confirmado", nome=nome)
        else:
            self.registrar("Lembrete confirmado como feito.")
            self._registrar_evento("lembrete_confirmado")

    def texto_status(self) -> str:
        if self.pausado:
            return "Lembretes de Saúde — pausado"

        if self.soneca_fim is not None:
            return (
                "Lembretes de Saúde — soneca até "
                f"{self.soneca_fim:%H:%M}"
            )

        if self.em_silencio:
            return "Lembretes de Saúde — silêncio"

        return "Lembretes de Saúde — ativo"

    def tick(self) -> List[Lembrete]:
        agora = self._relogio()
        self._atualizar_silencio(agora)

        if self.soneca_ate is not None and agora >= self.soneca_ate:
            self._encerrar_soneca(agora, "soneca_encerrada")
            self.registrar("Soneca encerrada.")
            self._encerrar_suspensao(agora)

        if self.suspenso:
            self.tela_cheia_anterior = None
            return []

        tela_cheia = self._obter_tela_cheia()

        if tela_cheia and self.tela_cheia_anterior is False:
            self.registrar(
                "Tela cheia detectada: som e notificações serão adiados."
            )
        elif not tela_cheia and self.tela_cheia_anterior is True:
            self.registrar(
                "Tela cheia encerrada: retomando a agenda."
            )

        self.tela_cheia_anterior = tela_cheia

        adiados = processar_tick(
            self.lembretes, agora, tela_cheia, self._entregar
        )

        for lembrete in adiados:
            self.registrar(
                f"{lembrete.nome}: lembrete adiado durante a tela cheia."
            )

        return adiados


def executar_sem_bandeja(agendador: Agendador) -> None:
    """Executa a agenda em primeiro plano, sem ícone na bandeja."""
    while True:
        agendador.tick()
        time.sleep(agendador.intervalo_verificacao)


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


def mostrar_boas_vindas(
    lembretes: List[Lembrete], bandeja_ativa: bool
) -> None:
    """Exibe a notificação inicial, exceto quando há tela cheia."""
    if em_tela_cheia():
        log("Notificação de boas-vindas não exibida (tela cheia).")
        return

    resumo = " | ".join(
        f"{lembrete.nome}: {formato_intervalo(lembrete.intervalo)}"
        for lembrete in lembretes
    )

    mensagem = f"Intervalos: {resumo}."
    if bandeja_ativa:
        mensagem += (
            " Use o botão direito no ícone da bandeja para pausar, "
            "fazer uma soneca ou sair."
        )

    notificar("Lembretes ativados! ✅", mensagem)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = criar_parser()
    args = parser.parse_args(argv)

    if args.acao:
        if not E_WINDOWS:
            print(
                "Este programa requer Windows 10 ou 11.",
                file=sys.stderr,
            )
            return 1

        from tray import executar_acao

        acao = normalizar_acao(args.acao)
        if acao not in ACOES_VALIDAS:
            print(f"Ação desconhecida: {args.acao}", file=sys.stderr)
            return 2

        if not executar_acao(acao):
            print(
                "Não foi possível enviar a ação para o programa em "
                "execução.",
                file=sys.stderr,
            )
            return 1

        return 0

    try:
        config = carregar_config(args.config)
    except (OSError, ValueError) as erro:
        print(f"Erro ao carregar configuração: {erro}", file=sys.stderr)
        return 1

    if args.estatisticas:
        return mostrar_estatisticas(caminho_historico(config))

    if not E_WINDOWS:
        print(
            "Este programa requer Windows 10 ou 11.",
            file=sys.stderr,
        )
        return 1

    if args.teste:
        aplicar_modo_teste(config)

    try:
        aplicar_cli(config, args)
        validar_config(config)
    except ValueError as erro:
        parser.error(str(erro))

    lembretes = criar_lembretes(config)

    if not lembretes:
        print(
            "Nenhum lembrete ativo. Verifique a configuração.",
            file=sys.stderr,
        )
        return 1

    agendador = Agendador(
        lembretes,
        som_ativo=config["som_ativo"],
        intervalo_verificacao=config["intervalo_verificacao"],
        em_silencio=lambda: em_horario_silencio(
            config["horario_silencio"]
        ),
        historico=criar_historico(config),
        atalhos_globais=(
            config["atalhos_globais"] and config["usar_bandeja"]
        ),
        acoes_toast=config["acoes_toast"] and config["usar_bandeja"],
    )

    if args.teste:
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
    if config["usar_bandeja"]:
        print(
            "Bandeja ativa: clique com o botão direito no ícone para "
            "pausar, fazer soneca ou sair."
        )
    else:
        print("Bandeja desativada (--sem-bandeja).")

    silencio = config["horario_silencio"]
    if silencio["ativo"]:
        dias = ", ".join(silencio["dias_semana"])
        print(
            "Horário de silêncio: "
            f"{silencio['inicio']}–{silencio['fim']} ({dias})."
        )

    if config["usar_bandeja"] and config["atalhos_globais"]:
        print(
            "Atalhos globais: Ctrl+Alt+P pausa/retoma; "
            "Ctrl+Alt+S soneca/cancela."
        )

    if config["usar_bandeja"] and config["acoes_toast"]:
        print("Ações no toast: Feito e Soneca 15 min.")

    if config["historico"]["ativo"]:
        print(f"Histórico: {caminho_historico(config)}")

    mostrar_boas_vindas(lembretes, config["usar_bandeja"])

    try:
        if config["usar_bandeja"]:
            try:
                from tray import ErroBandeja, executar_com_bandeja
            except ImportError as erro:
                log(f"Bandeja indisponível: {erro}")
                agendador.acoes_toast = False
                agendador.atalhos_globais = False
                executar_sem_bandeja(agendador)
            else:
                try:
                    executar_com_bandeja(agendador)
                except ErroBandeja as erro:
                    log(
                        f"Não foi possível iniciar a bandeja: {erro}. "
                        "Continuando sem ícone."
                    )
                    agendador.acoes_toast = False
                    agendador.atalhos_globais = False
                    executar_sem_bandeja(agendador)
        else:
            executar_sem_bandeja(agendador)
    except KeyboardInterrupt:
        print("\nEncerrado. Até logo!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
