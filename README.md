# 💧👀🧍 Lembretes de Saúde — Windows 10/11

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)
![Windows](https://img.shields.io/badge/Windows-10%20%7C%2011-0078D4?logo=windows&logoColor=white)
![Licença](https://img.shields.io/badge/licen%C3%A7a-MIT-green)

[![Testes](https://github.com/vitortsouza/lembretes-saude/actions/workflows/testes.yml/badge.svg)](https://github.com/vitortsouza/lembretes-saude/actions/workflows/testes.yml)
[![Executáveis](https://github.com/vitortsouza/lembretes-saude/actions/workflows/build-exe.yml/badge.svg)](https://github.com/vitortsouza/lembretes-saude/actions/workflows/build-exe.yml)

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

## 🖱️ Ícone na bandeja

O programa cria um ícone nativo na bandeja do Windows, implementado com
`ctypes` e sem bibliotecas externas.

Clique com o **botão direito** no ícone para acessar:

- **Pausar lembretes** — suspende todos os avisos até você retomar.
- **Retomar lembretes** — volta a agenda sem uma rajada de avisos atrasados.
- **Soneca por 15, 30 ou 60 minutos** — silencia tudo por um período.
- **Cancelar soneca** — volta imediatamente à agenda.
- **Sair** — encerra o programa e remove o ícone.

Um **duplo clique** no ícone alterna entre pausar e retomar (ou cancela uma
soneca). O tooltip mostra se os lembretes estão ativos, pausados, em soneca ou
em silêncio.

### Atalhos globais

Com a bandeja ativa, os atalhos funcionam em qualquer aplicativo:

| Atalho | Ação |
|---|---|
| `Ctrl+Alt+P` | Pausa ou retoma os lembretes. Se houver uma soneca, cancela. |
| `Ctrl+Alt+S` | Inicia uma soneca de 15 minutos ou cancela a soneca atual. |

Se outro programa já usar um desses atalhos, o registro falha apenas para ele e
o restante continua funcionando. Desative com `"atalhos_globais": false`.

O ícone é recriado automaticamente se o Explorer reiniciar. Se a bandeja não
estiver disponível, o programa continua funcionando em modo console.

Para executar sem o ícone:

```powershell
python lembretes.py --sem-bandeja
```

## 🌙 Horário de silêncio

É possível definir uma janela diária, por exemplo fora do expediente, em que o
programa não toca som nem mostra notificações:

```json
"horario_silencio": {
  "ativo": true,
  "inicio": "22:00",
  "fim": "07:00",
  "dias_semana": ["seg", "ter", "qua", "qui", "sex"]
}
```

- A janela pode atravessar a meia-noite. No exemplo, o silêncio começa às 22h
  nos dias escolhidos e termina às 7h do dia seguinte.
- Enquanto o silêncio estiver ativo, os horários da agenda são deslocados. Ao
  sair da janela, os lembretes não são entregues em rajada.
- Pausa manual, soneca e silêncio podem se sobrepor sem deslocar a agenda duas
  vezes.
- O tooltip e o console mostram quando o silêncio está ativo.

## 🔔 Botões no toast

Com a bandeja ativa, cada notificação pode exibir dois botões:

- **Feito ✅** — registra a confirmação do lembrete no histórico.
- **Soneca 15 min** — inicia uma soneca de 15 minutos.

Os botões usam o protocolo `lembretes-saude:`, registrado automaticamente em
`HKEY_CURRENT_USER\Software\Classes` na primeira execução com bandeja. Nenhuma
permissão de administrador é necessária. Para desativar:

```json
"acoes_toast": false
```

## ✨ Funcionalidades

- ✅ Notificações toast nativas do Windows.
- ✅ Sons distintos para cada tipo de lembrete.
- ✅ Sem som e sem notificação durante apps em tela cheia.
- ✅ Entrega imediata dos lembretes adiados ao sair da tela cheia.
- ✅ Ícone na bandeja com pausa, retomada, soneca e saída.
- ✅ Atalhos globais `Ctrl+Alt+P` e `Ctrl+Alt+S`.
- ✅ Horário de silêncio configurável por dia da semana.
- ✅ Botões **Feito** e **Soneca 15 min** diretamente no toast.
- ✅ Histórico em JSON Lines e resumo com `--estatisticas`.
- ✅ Configuração por arquivo JSON, sem editar o código.
- ✅ Opções de linha de comando para intervalos, som e bandeja.
- ✅ Agenda central, com horários independentes para cada lembrete.
- ✅ Atrasos iniciais para distribuir os primeiros avisos.
- ✅ Modo de teste com intervalos curtos.
- ✅ Empacotamento em `.exe` com PyInstaller.
- ✅ Nenhuma dependência externa e nenhum acesso à rede.
- ✅ Testes automatizados em Linux e Windows.

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

Para encerrar, use **Sair** no menu da bandeja ou pressione `Ctrl+C` no
terminal.

### Modo de teste

```powershell
python lembretes.py --teste
```

| Lembrete | Intervalo | Primeiro aviso |
|---|---:|---:|
| 👀 Descansar os olhos | 5 segundos | 5 segundos |
| 💧 Beber água | 12 segundos | 7 segundos |
| 🧍 Alongamento | 18 segundos | 11 segundos |

O modo de teste usa os mesmos mecanismos de som, notificação, tela cheia e
bandeja da execução normal.

### Opções de linha de comando

| Opção | Descrição |
|---|---|
| `--teste` | Usa intervalos curtos para testar. |
| `--config ARQUIVO` | Carrega um arquivo JSON de configuração. |
| `--sem-bandeja` | Executa sem o ícone na bandeja. |
| `--sem-som` | Desativa os bipes dos lembretes. |
| `--olhos MINUTOS` | Intervalo do lembrete dos olhos, em minutos. |
| `--agua MINUTOS` | Intervalo do lembrete de água, em minutos. |
| `--alongamento MINUTOS` | Intervalo do alongamento, em minutos. |
| `--estatisticas` | Mostra um resumo do histórico. |
| `--versao` | Mostra a versão do programa. |

Exemplo:

```powershell
python lembretes.py --olhos 25 --agua 45 --alongamento 80
```

### Histórico e estatísticas

O programa grava eventos em `historico.jsonl`, na mesma pasta de
`lembretes.py` (ou do `.exe`). Cada linha é um objeto JSON com data, tipo do
evento e dados como nome do lembrete e duração da pausa.

Para ver um resumo:

```powershell
python lembretes.py --estatisticas
```

O resumo mostra:

- lembretes entregues, incluindo quantos foram adiados por tela cheia;
- confirmações feitas pelo botão **Feito**;
- quantidade e duração total de pausas, sonecas e períodos de silêncio;
- entregas por lembrete e o período coberto pelo histórico.

O histórico é local, não sai do computador e pode ser apagado a qualquer
momento. Para desativar:

```json
"historico": {
  "ativo": false,
  "arquivo": "historico.jsonl"
}
```

## ⚙️ Configuração por JSON

Copie `config.exemplo.json` para `config.json` e ajuste os valores desejados:

```powershell
copy config.exemplo.json config.json
```

O programa carrega `config.json` automaticamente quando ele está na mesma
pasta de `lembretes.py`. Também é possível indicar outro arquivo:

```powershell
python lembretes.py --config meu-config.json
```

Trecho de exemplo:

```json
{
  "usar_bandeja": true,
  "som_ativo": true,
  "intervalo_verificacao": 1.0,
  "atalhos_globais": true,
  "acoes_toast": true,
  "horario_silencio": {
    "ativo": false,
    "inicio": "22:00",
    "fim": "07:00",
    "dias_semana": ["seg", "ter", "qua", "qui", "sex"]
  },
  "historico": {
    "ativo": true,
    "arquivo": "historico.jsonl"
  },
  "lembretes": {
    "olhos": {
      "ativo": true,
      "nome": "Olhos",
      "intervalo_segundos": 1200,
      "atraso_inicial_segundos": 1200,
      "titulo": "Hora de descansar os olhos! 👀",
      "mensagem": "Olhe para longe por 20 segundos e pisque os olhos.",
      "notas": [[1000, 200], [1400, 300]]
    }
  }
}
```

A configuração é mesclada com os valores padrão: você pode informar apenas as
chaves que quiser alterar. Chaves desconhecidas geram erro para evitar erros de
digitação.

| Chave | Descrição |
|---|---|
| `usar_bandeja` | Ativa ou desativa o ícone da bandeja. |
| `som_ativo` | Ativa ou desativa todos os bipes. |
| `intervalo_verificacao` | Frequência de verificação, em segundos (mínimo 0.2). |
| `atalhos_globais` | Ativa os atalhos `Ctrl+Alt+P` e `Ctrl+Alt+S`. |
| `acoes_toast` | Adiciona os botões **Feito** e **Soneca 15 min** ao toast. |
| `horario_silencio.ativo` | Ativa a janela diária de silêncio. |
| `horario_silencio.inicio` | Início da janela, no formato `HH:MM`. |
| `horario_silencio.fim` | Fim da janela, no formato `HH:MM`. |
| `horario_silencio.dias_semana` | Dias em que a janela começa (`seg` a `dom`). |
| `historico.ativo` | Ativa a gravação do histórico. |
| `historico.arquivo` | Nome ou caminho do arquivo JSON Lines. |
| `lembretes.<id>.ativo` | Ativa ou desativa um lembrete específico. |
| `lembretes.<id>.nome` | Nome exibido no console e na notificação inicial. |
| `lembretes.<id>.intervalo_segundos` | Intervalo entre os avisos. |
| `lembretes.<id>.atraso_inicial_segundos` | Tempo até o primeiro aviso. |
| `lembretes.<id>.titulo` | Título da notificação. |
| `lembretes.<id>.mensagem` | Texto da notificação. |
| `lembretes.<id>.notas` | Lista de pares `[frequencia_hz, duracao_ms]`. |

As notas usam frequências entre **37 e 32767 Hz** e durações entre **1 e
60000 ms**. Use uma lista vazia (`[]`) para deixar um lembrete sem som
individual.

A ordem de precedência é:

1. Valores padrão.
2. Arquivo `config.json` (ou `--config`).
3. Opções `--teste`.
4. Opções de linha de comando, como `--olhos` e `--sem-som`.

Os arquivos `config.json` e `historico.jsonl` são ignorados pelo Git, para que
configurações e dados pessoais não sejam enviados ao repositório.

## 🪟 Iniciar junto com o Windows

1. Pressione `Win + R`, digite `shell:startup` e pressione `Enter`.
2. Crie um atalho para o `pythonw.exe` (sem console) com o caminho completo do
   script como argumento:

   ```text
   "C:\Users\SEU_USUARIO\AppData\Local\Programs\Python\Python312\pythonw.exe" "C:\caminho\lembretes.py"
   ```

3. Em **Iniciar em**, informe a pasta do projeto.
4. Entre na conta do Windows e confirme se o ícone aparece na bandeja.

Também é possível criar um atalho para `run_lembrete.bat`, mas nesse caso uma
janela de terminal ficará aberta. Com `pythonw.exe`, o programa roda sem
console e eventuais erros não aparecem na tela.

Se você usa o executável gerado por `build_exe.bat`, crie o atalho diretamente
para `LembretesSaude.exe`. Nesse caso não é necessário manter a pasta do
projeto nem o Python instalado.

## 📦 Gerar um executável

Para gerar dois executáveis com PyInstaller, execute no Windows:

```powershell
build_exe.bat
```

O script instala/atualiza o PyInstaller e gera:

| Arquivo | Uso |
|---|---|
| `dist\LembretesSaude.exe` | Versão normal, sem janela de console. |
| `dist\LembretesSaude-cli.exe` | Versão de console, útil para ver mensagens. |

Os dois são arquivos únicos (`--onefile`) e não precisam de Python instalado
para rodar. A configuração e o histórico ficam na pasta do `.exe`: copie
`config.exemplo.json` como `config.json` ao lado dele para personalizar.

O workflow `.github/workflows/build-exe.yml` gera os mesmos arquivos no GitHub
Actions a partir de **Actions → Gerar executáveis** ou de uma tag `v*`, e os
disponibiliza como artefato `lembretes-saude-windows`.

## 🧠 Como funciona

O programa usa um único laço principal, que verifica a agenda e a tela cheia a
cada segundo. Para cada lembrete:

1. Se o horário chegou e não há tela cheia, o som toca e a notificação aparece.
2. Se há tela cheia, o lembrete é marcado como pendente e o próximo horário é
   reagendado.
3. Quando a tela cheia termina, os lembretes pendentes são entregues e a agenda
   continua normalmente.

Pausa manual, soneca e horário de silêncio compartilham o mesmo estado de
suspensão. Os horários são deslocados uma única vez pelo tempo total em que os
avisos ficaram suspensos. Assim, ao retomar, você não recebe vários lembretes
antigos de uma vez, mesmo que os três modos se sobreponham.

A detecção de tela cheia usa as APIs do Windows via `ctypes`:

- `GetForegroundWindow` para obter a janela ativa.
- `GetWindowRect` e `GetMonitorInfoW` para comparar a janela com o monitor.
- `GetClassNameW` para ignorar janelas do próprio Shell, como a área de
  trabalho.
- `SetProcessDpiAwarenessContext` para evitar erros de coordenadas em telas com
  escala diferente de 100%.

A bandeja também é nativa:

- `Shell_NotifyIconW` cria, atualiza e remove o ícone.
- `CreatePopupMenu` e `TrackPopupMenu` montam o menu de contexto.
- `SetTimer` e `GetMessageW` mantêm o laço de mensagens do Windows.
- `RegisterWindowMessageW("TaskbarCreated")` recria o ícone após reiniciar o
  Explorer.
- `RegisterHotKey`/`UnregisterHotKey` registram os atalhos globais.
- `FindWindowW` e `PostMessageW` enviam as ações do toast para a instância em
  execução.
- O protocolo `lembretes-saude:` é registrado no registro do Windows para que
  os botões do toast possam chamar o programa.

## 🧪 Testes

Os testes cobrem a agenda, a pausa, a soneca, o horário de silêncio, o
histórico, as ações do toast, a configuração e a notificação:

```powershell
python -m unittest discover -s tests -v
```

O workflow em `.github/workflows/testes.yml` executa os testes no GitHub Actions
em **Ubuntu e Windows**, com Python 3.9, 3.11 e 3.13, além de verificar o estilo
do código com Ruff.

Para rodar o lint localmente:

```powershell
python -m pip install ruff
ruff check .
```

## 📁 Estrutura do projeto

```text
.
├── lembretes.py              # Programa principal e agendador
├── tray.py                   # Ícone nativo, atalhos e ações do toast
├── run_lembrete.bat          # Atalho para execução no Windows
├── build_exe.bat             # Geração dos executáveis com PyInstaller
├── config.exemplo.json       # Modelo de configuração
├── pyproject.toml            # Configuração do Ruff
├── tests/
│   ├── test_lembretes.py     # Agenda, configuração, histórico e notificação
│   └── test_tray_windows.py  # Teste de importação da bandeja no Windows
├── .github/workflows/
│   ├── testes.yml            # Integração contínua
│   └── build-exe.yml         # Geração dos executáveis no Windows
├── .gitignore
├── .gitattributes
├── LICENSE
└── README.md
```

## 💡 Ideias para o futuro

- Ícone próprio para o executável e para a bandeja.
- Exportação das estatísticas em CSV.
- Perfis diferentes de intervalos por dia da semana.

## 🛠️ Solução de problemas

### O ícone não aparece na bandeja

- Verifique se o Explorer está em execução.
- Execute no terminal para ver mensagens de erro.
- Teste com `python lembretes.py --sem-bandeja` para confirmar que o restante
  funciona.
- Ao iniciar junto com o Windows, aguarde alguns segundos: o programa tenta
  recriar o ícone se a bandeja ainda não estiver pronta.

### As notificações não aparecem

- Verifique **Configurações → Sistema → Notificações**.
- Confira se **Não incomodar** (Focus Assist) está ativo.
- Execute o script no terminal e observe as mensagens de erro.
- Confirme que o PowerShell está disponível e que a política de execução não
  está bloqueando o comando.

### Os sons não tocam

- Confirme o dispositivo de saída e o volume do Windows.
- Verifique se `som_ativo` está como `true` na configuração.
- `winsound.Beep` depende do dispositivo de áudio; se ele falhar, a notificação
  visual ainda é exibida.
- Durante a tela cheia, o silêncio é intencional.

### A tela cheia não foi detectada

- Confirme que o app realmente cobre o monitor inteiro. Janelas maximizadas
  normalmente deixam a barra de tarefas visível e não contam como tela cheia.
- Execute `python lembretes.py --teste` e acompanhe as mensagens do terminal.
- Alguns apps usam janelas com classes próprias do Shell; se necessário, ajuste
  `CLASSES_SHELL` em `lembretes.py`.

### A configuração não é carregada

- Confirme que o arquivo é um JSON válido e está codificado em UTF-8.
- Verifique se `config.json` está na mesma pasta de `lembretes.py` ou use
  `--config` com o caminho completo.
- O programa informa o caminho exato de chaves inválidas ou desconhecidas.

### Os atalhos globais não funcionam

- Confirme que a bandeja está ativa e que `atalhos_globais` é `true`.
- Outro programa pode já usar `Ctrl+Alt+P` ou `Ctrl+Alt+S`. O console informa
  qual atalho não pôde ser registrado.
- Atalhos globais não funcionam com o programa executado como outro usuário.

### Os botões do toast não aparecem ou não funcionam

- Os botões exigem a bandeja ativa e `"acoes_toast": true`.
- O protocolo é registrado em `HKEY_CURRENT_USER\Software\Classes\lembretes-saude`.
  Se a política da máquina bloquear o registro, o console mostra um aviso.
- O botão **Feito** só registra a confirmação se o lembrete ainda estiver
  associado à última notificação entregue.
- O Windows pode ocultar botões de toast quando **Não incomodar** está ativo.

### O histórico não é gravado

- Verifique `historico.ativo` e se a pasta do programa permite escrita.
- Ao usar o `.exe` em uma pasta protegida, como `Program Files`, copie-o para
  uma pasta do usuário ou ajuste `historico.arquivo` para um caminho gravável.
- Linhas inválidas são ignoradas ao gerar as estatísticas.

### O programa não abre

- Confirme que está no Windows 10/11 e que o Python está instalado.
- Teste com `py lembretes.py` ou `python lembretes.py`.
- Verifique a versão com `python --version` (é necessário Python 3.9+).

## 📄 Licença

Distribuído sob a licença MIT. Consulte [LICENSE](LICENSE).
