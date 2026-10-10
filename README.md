# 💧👀 Lembretes de Saúde — Windows 11

Script em Python puro (sem dependências externas) que envia notificações periódicas no Windows 11 para ajudar a manter hábitos saudáveis durante o uso do computador:

- **👀 A cada 20 minutos** — lembrete de olhar para longe e piscar os olhos (regra 20-20-20)
- **💧 A cada 60 minutos** — lembrete de beber água

Cada lembrete toca um **som distinto** (bipes com frequências diferentes), e a notificação só é exibida se **nenhum aplicativo estiver em tela cheia** — em jogos, por exemplo, apenas o som toca, sem interromper a tela.

## ✨ Funcionalidades

- ✅ Notificações toast nativas do Windows 11
- ✅ Sons diferentes para cada tipo de lembrete (`winsound.Beep`)
- ✅ Detecta tela cheia (jogos, vídeos) via API do Windows (`ctypes`) e suprime a notificação, tocando só o som
- ✅ Modo de teste com intervalos curtos
- ✅ Zero dependências — apenas biblioteca padrão do Python

## 🚀 Como usar

Requisitos: Windows 10/11 com Python 3.8+.

```bash
# Uso normal (olhos a cada 20 min, água a cada 60 min)
python lembrete-saude-olhos-agua.py

# Modo teste (olhos a cada 5s, água a cada 12s)
python lembrete-saude-olhos-agua.py --teste
```

Encerre com `Ctrl+C`.

### Iniciar junto com o Windows

1. Pressione `Win+R` e digite `shell:startup`
2. Crie um atalho para o script dentro da pasta aberta
3. (Opcional) Altere o atalho para executar minimizado

## ⚙️ Personalização

Edite as constantes no topo do script:

| Constante | Padrão | Descrição |
|---|---|---|
| `INTERVALO_OLHOS` | `20 * 60` | Segundos entre lembretes dos olhos |
| `INTERVALO_AGUA` | `60 * 60` | Segundos entre lembretes de água |
| `SOM_OLHOS` | `[(1000, 200), (1400, 300)]` | Sequência de `(frequência Hz, duração ms)` |
| `SOM_AGUA` | `[(600, 600)]` | Sequência de `(frequência Hz, duração ms)` |

## 🧠 Notas técnicas

- As notificações usam o **AppUserModelID do PowerShell**, pois o Windows 11 só exibe toasts de apps com AUMID registrado; AUMIDs inventados são descartados silenciosamente.
- A detecção de tela cheia compara o retângulo da janela em primeiro plano com o retângulo do monitor (`GetForegroundWindow` + `MonitorFromWindow` + `GetMonitorInfoW`).
- Se a notificação não aparecer, verifique em **Configurações → Sistema → Notificações** se o PowerShell está permitido e se o Assistência de Foco está desativado.

## 📄 Licença

MIT — use e modifique livremente.
