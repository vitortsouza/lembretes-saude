# 💧👀🧍 Lembretes de Saúde — Windows 10/11

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)
![Windows](https://img.shields.io/badge/Windows-10%20%7C%2011-0078D4?logo=windows&logoColor=white)
![Licença](https://img.shields.io/badge/licen%C3%A7a-MIT-green)

Script em Python puro, **sem dependências externas**, que envia lembretes
periódicos de saúde enquanto você usa o computador.

- **👀 A cada 20 minutos** — olhe para longe por 20 segundos e pisque os
  olhos, seguindo a regra 20-20-20.
- **💧 A cada 60 minutos** — beba um copo de água.
- **🧍 A cada 90 minutos** — levante-se, caminhe um pouco e se alongue.

Cada lembrete tem um som próprio, feito com bipes em frequências diferentes.
As notificações usam o sistema nativo de toast do Windows.

## 🎮 Comportamento em tela cheia

Quem joga, assiste a vídeos ou apresenta em tela cheia não é interrompido:

| Situação | Som | Notificação | O que acontece |
|---|:---:|:---:|---|
| Uso normal | Toca | Exibe | O lembrete é entregue na hora. |
| App em tela cheia | **Não toca** | **Não exibe** | O lembrete fica pendente. |
| Acabou de sair da tela cheia | Toca | Exibe | O lembrete pendente é entregue imediatamente. |

Se vários lembretes vencerem durante o mesmo período em tela cheia, cada um
deles é entregue uma única vez ao sair. Isso evita uma rajada de notificações
antigas depois de um filme ou de uma partida longa. O próximo horário de cada
lembrete é recalculado a partir da saída da tela cheia.

A detecção considera a janela em primeiro plano e o monitor em que ela está.
Janelas maximizadas normalmente **não** são tratadas como tela cheia; apenas
janelas que cobrem o monitor inteiro.

## ✨ Funcionalidades

- ✅ Notificações toast nativas do Windows.
- ✅ Sons distintos para cada tipo de lembrete.
- ✅ **Sem som e sem notificação durante apps em tela cheia.**
- ✅ **Entrega imediata dos lembretes adiados ao sair da tela cheia.**
- ✅ Agenda central, com horários independentes para cada lembrete.
- ✅ Atrasos iniciais para distribuir os primeiros avisos.
- ✅ Modo de teste com intervalos curtos.
- ✅ Notificação de boas-vindas com os intervalos configurados.
- ✅ Nenhuma dependência externa e nenhum acesso à rede.
- ✅ Testes automatizados da lógica de agendamento.

## 📋 Requisitos

- Windows 10 ou Windows 11.
- Python 3.9 ou superior.
- PowerShell disponível no sistema.
- Notificações do Windows habilitadas.

Não é necessário instalar nada com `pip`.

## 🚀 Como usar

Abra o terminal na pasta do projeto e execute:

```powershell
python lembretes.py
```

Ou dê um duplo clique em `run_lembrete.bat`.

Os intervalos padrão são:

| Lembrete | Intervalo | Primeiro aviso |
|---|---:|---:|
| 👀 Descansar os olhos | 20 minutos | 20 minutos |
| 💧 Beber água | 60 minutos | 25 minutos |
| 🧍 Alongamento | 90 minutos | 35 minutos |

Os atrasos iniciais são contados a partir da inicialização. Depois do primeiro
aviso de cada tipo, o lembrete se repete conforme seu intervalo.

Para encerrar, pressione `Ctrl+C` no terminal.

### Modo de teste

```powershell
python lembretes.py --teste
```

| Lembrete | Intervalo | Primeiro aviso |
|---|---:|---:|
| 👀 Descansar os olhos | 5 segundos | 5 segundos |
| 💧 Beber água | 12 segundos | 7 segundos |
| 🧍 Alongamento | 18 segundos | 11 segundos |

O modo de teste usa os mesmos mecanismos de som, notificação e detecção de
tela cheia da execução normal.

## 🪟 Iniciar junto com o Windows

1. Pressione `Win + R`, digite `shell:startup` e pressione `Enter`.
2. Crie um atalho para o `pythonw.exe` (sem console) com o caminho completo do
   script como argumento:

   ```text
   "C:\Users\SEU_USUARIO\AppData\Local\Programs\Python\Python312\pythonw.exe" "C:\caminho\lembretes.py"
   ```

3. Em **Iniciar em**, informe a pasta do projeto.
4. Entre na conta do Windows e confirme se os lembretes funcionam.

Também é possível criar um atalho para `run_lembrete.bat`, mas nesse caso uma
janela de terminal ficará aberta. Com `pythonw.exe`, o programa roda sem
console e eventuais erros não aparecem na tela.

## ⚙️ Personalização

Os intervalos, atrasos e sons ficam nas constantes do início de
`lembretes.py`.

| Constante | Padrão | Descrição |
|---|---|---|
| `INTERVALO_OLHOS` | `20 * 60` | Intervalo dos avisos para os olhos, em segundos. |
| `INTERVALO_AGUA` | `60 * 60` | Intervalo dos avisos para beber água. |
| `INTERVALO_ALONGAMENTO` | `90 * 60` | Intervalo dos avisos para alongamento. |
| `ATRASO_OLHOS` | `INTERVALO_OLHOS` | Tempo até o primeiro aviso dos olhos. |
| `ATRASO_AGUA` | `25 * 60` | Tempo até o primeiro aviso de água. |
| `ATRASO_ALONGAMENTO` | `35 * 60` | Tempo até o primeiro aviso de alongamento. |
| `INTERVALO_VERIFICACAO` | `1` | Frequência de verificação da agenda e da tela cheia. |
| `SOM_OLHOS` | `[(1000, 200), (1400, 300)]` | Bipes do lembrete dos olhos. |
| `SOM_AGUA` | `[(600, 600)]` | Som do lembrete de água. |
| `SOM_ALONGAMENTO` | `[(800, 250), (1000, 250), (1200, 400)]` | Bipes do alongamento. |

Exemplo:

```python
# Intervalo de 30 minutos e primeiro aviso após 10 minutos
INTERVALO_OLHOS = 30 * 60
ATRASO_OLHOS = 10 * 60
```

Cada som é uma lista de pares:

```python
(frequencia_em_hz, duracao_em_ms)
```

```python
SOM_AGUA = [(700, 300), (900, 300)]
```

As notificações são exibidas **sem som próprio**; o áudio vem apenas dos bipes
configurados. Assim, o Windows não toca dois sons ao mesmo tempo.

## 🧠 Como funciona

O programa usa um único laço principal, que verifica a agenda e a tela cheia a
cada segundo. Para cada lembrete:

1. Se o horário chegou e não há tela cheia, o som toca e a notificação aparece.
2. Se há tela cheia, o lembrete é marcado como pendente e o próximo horário é
   reagendado.
3. Quando a tela cheia termina, os lembretes pendentes são entregues e a agenda
   continua normalmente.

A detecção de tela cheia usa as APIs do Windows via `ctypes`:

- `GetForegroundWindow` para obter a janela ativa.
- `GetWindowRect` e `GetMonitorInfoW` para comparar a janela com o monitor.
- `GetClassNameW` para ignorar janelas do próprio Shell, como a área de
  trabalho.
- `SetProcessDpiAwarenessContext` para evitar erros de coordenadas em telas com
  escala diferente de 100%.

## 🧪 Testes

Os testes cobrem a lógica de agendamento sem depender do Windows:

```powershell
python -m unittest discover -s tests -v
```

O workflow em `.github/workflows/testes.yml` executa os testes no GitHub Actions
em Python 3.9, 3.11 e 3.13.

## 📁 Estrutura do projeto

```text
.
├── lembretes.py              # Programa principal
├── run_lembrete.bat          # Atalho para execução no Windows
├── tests/
│   └── test_lembretes.py     # Testes da agenda e da notificação
├── .github/workflows/
│   └── testes.yml            # Integração contínua
├── .gitignore
├── .gitattributes
├── LICENSE
└── README.md
```

## 🛠️ Solução de problemas

### As notificações não aparecem

- Verifique **Configurações → Sistema → Notificações**.
- Confira se **Não incomodar** (Focus Assist) está ativo.
- Execute o script no terminal e observe as mensagens de erro.
- Confirme que o PowerShell está disponível e que a política de execução não
  está bloqueando o comando.

### Os sons não tocam

- Confirme o dispositivo de saída e o volume do Windows.
- `winsound.Beep` depende do dispositivo de áudio; se ele falhar, a notificação
  visual ainda é exibida.
- Durante a tela cheia, o silêncio é intencional.

### A tela cheia não foi detectada

- Confirme que o app realmente cobre o monitor inteiro. Janelas maximizadas
  normalmente deixam a barra de tarefas visível e não contam como tela cheia.
- Execute `python lembretes.py --teste` e acompanhe as mensagens do terminal.
- Alguns apps usam janelas com classes próprias do Shell; se necessário, ajuste
  `CLASSES_SHELL`.

### O programa não abre

- Confirme que está no Windows 10/11 e que o Python está instalado.
- Teste com `py lembretes.py` ou `python lembretes.py`.
- Verifique a versão com `python --version` (é necessário Python 3.9+).

## 📄 Licença

Distribuído sob a licença MIT. Consulte [LICENSE](LICENSE).
