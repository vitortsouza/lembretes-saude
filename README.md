# 💧👀🧍 Lembretes de Saúde — Windows 11

Script em Python puro (sem dependências externas) que envia notificações periódicas no Windows 11 para ajudar a manter hábitos saudáveis durante o uso do computador:

- **👀 A cada 20 minutos** — lembrete para olhar para longe por 20 segundos e piscar os olhos (regra 20-20-20).
- **💧 A cada 60 minutos** — lembrete para beber água.
- **🧍 A cada 90 minutos (1h30)** — lembrete para se levantar, caminhar um pouco e fazer alongamentos.

Cada lembrete toca um **som distinto**, com bipes em frequências diferentes. A notificação visual só é exibida se nenhum aplicativo estiver em tela cheia — em jogos, por exemplo, apenas o som toca, sem interromper a tela.

## ✨ Funcionalidades

- ✅ Notificações toast nativas do Windows 11.
- ✅ Sons diferentes para cada tipo de lembrete (`winsound.Beep`).
- ✅ Detecção de tela cheia via API do Windows (`ctypes`), evitando notificações visuais durante jogos e outros aplicativos em tela cheia.
- ✅ Três lembretes independentes, com intervalos configuráveis.
- ✅ Modo de teste com intervalos curtos para verificar os lembretes rapidamente.
- ✅ Notificação de boas-vindas informando os intervalos configurados.
- ✅ Zero dependências externas — utiliza apenas a biblioteca padrão do Python e recursos nativos do Windows.

## 🚀 Como usar

**Requisitos:** Windows 10/11 com Python 3.8 ou superior.

### Execução normal

```bash
python lembrete-saude-olhos-agua.py
```

Os lembretes serão executados nos seguintes intervalos:

- Olhos: a cada 20 minutos.
- Água: a cada 60 minutos.
- Alongamento: a cada 90 minutos (1h30).

### Modo de teste

```bash
python lembrete-saude-olhos-agua.py --teste
```

No modo de teste, os intervalos são reduzidos:

- 👀 Olhos: a cada 5 segundos.
- 💧 Água: a cada 12 segundos.
- 🧍 Alongamento: a cada 18 segundos.

Encerre o programa com `Ctrl+C`.

> **Observação:** os contadores são independentes e começam quando o programa é iniciado. Por isso, os lembretes podem tocar em horários diferentes.

### Iniciar junto com o Windows

1. Pressione `Win + R` e digite `shell:startup`.
2. Crie um atalho para executar o script dentro da pasta aberta.
3. Opcionalmente, configure o atalho para executar o programa minimizado.

## ⚙️ Personalização

Edite as constantes no início do script para alterar os intervalos e os sons.

| Constante | Padrão | Descrição |
|---|---|---|
| `INTERVALO_OLHOS` | `20 * 60` | Intervalo entre os lembretes dos olhos, em segundos. |
| `INTERVALO_AGUA` | `60 * 60` | Intervalo entre os lembretes de água, em segundos. |
| `INTERVALO_ALONGAMENTO` | `90 * 60` | Intervalo entre os lembretes de alongamento, em segundos. |
| `SOM_OLHOS` | `[(1000, 200), (1400, 300)]` | Sequência de bipes para os olhos. |
| `SOM_AGUA` | `[(600, 600)]` | Som do lembrete de água. |
| `SOM_ALONGAMENTO` | `[(800, 250), (1000, 250), (1200, 400)]` | Sequência de bipes para o alongamento. |

As sequências de som utilizam pares no formato `(frequência em Hz, duração em ms)`.

Para personalizar os intervalos, lembre-se de que os valores são expressos em segundos. Por exemplo, 30 minutos correspondem a `30 * 60`.

## 🧠 Notas técnicas

- **Notificações:** utilizam o `AppUserModelID` do Windows PowerShell para exibir notificações toast nativas.
- **Detecção de tela cheia:** compara o retângulo da janela em primeiro plano com o retângulo do monitor, utilizando `GetForegroundWindow`, `MonitorFromWindow` e `GetMonitorInfoW`.
- **Sons:** são reproduzidos pela função `winsound.Beep`, disponível no Windows.
- **Concorrência:** cada lembrete é executado em uma thread independente, permitindo que os intervalos sejam controlados separadamente.
- **Modo de teste:** utiliza intervalos reduzidos para facilitar a validação sem precisar esperar vários minutos.
- **Solução de problemas:** se as notificações não aparecerem, verifique em **Configurações → Sistema → Notificações** se as notificações do PowerShell estão permitidas e se o recurso Não incomodar não está silenciando os avisos.

## 📄 Licença

MIT — use, modifique e distribua livremente.
