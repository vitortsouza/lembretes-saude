# 💧👀🧍 Lembretes de Saúde — Windows 11

Script em Python puro, sem dependências externas, que envia notificações periódicas no Windows 10/11 para ajudar a manter hábitos saudáveis durante o uso do computador.

- **👀 A cada 20 minutos** — lembrete para olhar para longe por 20 segundos e piscar os olhos, seguindo a regra 20-20-20.
- **💧 A cada 60 minutos** — lembrete para beber água.
- **🧍 A cada 90 minutos (1h30)** — lembrete para se levantar, caminhar um pouco e fazer alongamentos.

Cada lembrete toca um **som distinto**, com bipes em frequências diferentes. A notificação visual só é exibida quando não há um aplicativo em tela cheia. Em jogos, por exemplo, o script toca apenas o som quando detecta uma janela ocupando o monitor inteiro.

Os lembretes possuem temporizadores independentes e **atrasos iniciais configurados para distribuir os horários das primeiras notificações**, reduzindo a possibilidade de avisos simultâneos.

## ✨ Funcionalidades

- ✅ Notificações toast nativas do Windows.
- ✅ Sons diferentes para cada tipo de lembrete, utilizando `winsound.Beep`.
- ✅ Detecção de tela cheia por meio da API do Windows, com `ctypes`.
- ✅ Três lembretes independentes, com intervalos configuráveis.
- ✅ Atrasos iniciais para distribuir os primeiros avisos.
- ✅ Modo de teste com intervalos curtos.
- ✅ Notificação de boas-vindas informando os intervalos configurados.
- ✅ Execução concorrente por meio de threads independentes.
- ✅ Nenhuma dependência externa: utiliza apenas a biblioteca padrão do Python e recursos nativos do Windows.

## 📋 Requisitos

- Windows 10 ou Windows 11.
- Python 3.8 ou superior.
- PowerShell disponível no sistema.
- Notificações do Windows habilitadas, para exibir os avisos visuais.

Não é necessário instalar pacotes adicionais com `pip`.

## 🚀 Como usar

Salve o script Python como `lembrete-saude-olhos-agua.py` ou utilize o nome de arquivo que preferir.

Abra o terminal na pasta do arquivo e execute um dos comandos abaixo.

### Execução normal

```powershell
python lembrete-saude-olhos-agua.py
```

Os intervalos padrão são:

| Lembrete | Intervalo | Atraso inicial |
|---|---:|---:|
| 👀 Descansar os olhos | 20 minutos | 20 minutos |
| 💧 Beber água | 60 minutos | 25 minutos |
| 🧍 Alongamento | 90 minutos | 35 minutos |

Os atrasos iniciais são contados a partir da inicialização do programa. Após o primeiro aviso de cada tipo, o respectivo lembrete se repete conforme seu intervalo configurado.

### Modo de teste

```powershell
python lembrete-saude-olhos-agua.py --teste
```

No modo de teste, os intervalos e atrasos iniciais são reduzidos para permitir verificar o funcionamento rapidamente.

| Lembrete | Intervalo | Atraso inicial |
|---|---:|---:|
| 👀 Descansar os olhos | 5 segundos | 5 segundos |
| 💧 Beber água | 12 segundos | 7 segundos |
| 🧍 Alongamento | 18 segundos | 11 segundos |

**Importante:** o modo de teste utiliza os mesmos mecanismos de notificação e reprodução de sons da execução normal. Portanto, os avisos sonoros e visuais podem ser reproduzidos durante os testes.

### Encerrar o programa

Pressione `Ctrl+C` no terminal para encerrar o programa.

## 🕒 Sobre os horários das notificações

Os temporizadores são independentes. Os atrasos iniciais ajudam a distribuir os primeiros avisos, mas não garantem que todas as notificações permaneçam distantes umas das outras durante toda a execução.

Como os intervalos são de 20, 60 e 90 minutos, algumas notificações podem coincidir posteriormente. Além disso, a duração dos sons e pequenos atrasos de execução podem alterar ligeiramente os horários efetivos.

O script não utiliza um agendador centralizado: cada thread aguarda seu atraso inicial e depois repete o lembrete no intervalo definido.

## 🪟 Iniciar junto com o Windows

Para iniciar os lembretes automaticamente quando você entrar na sua conta do Windows:

1. Pressione `Win + R`.
2. Digite `shell:startup` e pressione `Enter`.
3. Crie um atalho para o script ou para um comando que execute o Python com o caminho completo do arquivo.
4. Se desejar, configure o atalho para iniciar minimizado.

Se utilizar um ambiente virtual ou o `uv`, configure o atalho com o interpretador Python e o ambiente corretos.

**Observação:** adicionar um atalho à pasta Inicializar não garante, por si só, que o programa execute corretamente em qualquer configuração. Teste o atalho e confirme se as notificações aparecem após entrar no Windows.

## ⚙️ Personalização

Os intervalos, atrasos e sons podem ser alterados nas constantes definidas no início do script.

| Constante | Padrão (execução normal) | Descrição |
|---|---|---|
| `INTERVALO_OLHOS` | `20 * 60` | Intervalo entre os avisos para descansar os olhos, em segundos. |
| `INTERVALO_AGUA` | `60 * 60` | Intervalo entre os avisos para beber água, em segundos. |
| `INTERVALO_ALONGAMENTO` | `90 * 60` | Intervalo entre os avisos para alongamento, em segundos. |
| `ATRASO_OLHOS` | `INTERVALO_OLHOS` | Tempo até o primeiro aviso dos olhos. |
| `ATRASO_AGUA` | `25 * 60` | Tempo até o primeiro aviso de água. |
| `ATRASO_ALONGAMENTO` | `35 * 60` | Tempo até o primeiro aviso de alongamento. |
| `SOM_OLHOS` | `[(1000, 200), (1400, 300)]` | Sequência de bipes para os olhos. |
| `SOM_AGUA` | `[(600, 600)]` | Som do lembrete de água. |
| `SOM_ALONGAMENTO` | `[(800, 250), (1000, 250), (1200, 400)]` | Sequência de bipes para o alongamento. |

Os valores dos intervalos e atrasos são expressos em segundos. Por exemplo:

```python
# Intervalo de 30 minutos
INTERVALO_OLHOS = 30 * 60

# Primeiro aviso após 10 minutos
ATRASO_OLHOS = 10 * 60
```

Os valores definidos para o modo de teste são selecionados automaticamente quando o argumento `--teste` é informado. Para modificar os intervalos de teste, edite as expressões condicionais correspondentes no início do script.

### Personalizar os sons

Cada som é composto por uma lista de pares no formato:

```python
(frequencia_em_hz, duracao_em_ms)
```

Exemplo:

```python
SOM_AGUA = [(700, 300), (900, 300)]
```

Esse exemplo reproduz dois bipes de frequências diferentes.

## 🧠 Notas técnicas

- **Notificações:** o script utiliza as APIs de notificações do Windows por meio do PowerShell e do identificador de aplicativo configurado no código.
- **Detecção de tela cheia:** compara o retângulo da janela em primeiro plano com a área do monitor, utilizando `GetForegroundWindow`, `MonitorFromWindow` e `GetMonitorInfoW`.
- **Sons:** são reproduzidos com `winsound.Beep`, disponível no Windows.
- **Concorrência:** cada lembrete é executado em uma thread independente, permitindo controlar os intervalos separadamente.
- **Atrasos iniciais:** definem quando ocorre o primeiro aviso de cada lembrete, sem alterar o intervalo de repetição.
- **Modo de teste:** reduz os intervalos e os atrasos iniciais para facilitar a validação.
- **Precisão temporal:** os horários são aproximados. A duração dos sons, o tempo gasto para criar notificações e o agendamento das threads podem introduzir pequenos atrasos.

## 🛠️ Solução de problemas

### As notificações visuais não aparecem

- Verifique se as notificações estão habilitadas em **Configurações → Sistema → Notificações**.
- Confira se o recurso **Não incomodar** está silenciando os avisos.
- Execute o script no terminal e verifique se aparece alguma mensagem de erro.
- Confirme se o PowerShell está disponível e se a execução do comando de notificação funciona no seu ambiente.

### Os sons não são reproduzidos

- Confirme se o dispositivo de saída de áudio está funcionando.
- Verifique o volume do Windows.
- Lembre-se de que os sons são reproduzidos antes da verificação de tela cheia e devem tocar mesmo quando a notificação visual é suprimida.

### O programa parece não fazer nada

- Confirme se executou o arquivo correto.
- Utilize `python lembrete-saude-olhos-agua.py --teste` para verificar o comportamento sem esperar os intervalos normais.
- Mantenha o terminal aberto durante a execução e observe as mensagens de erro.

## 📄 Licença

MIT — use, modifique e distribua livremente, respeitando os termos da licença.
