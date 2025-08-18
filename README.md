

-----

# Automatizador de Atualização do ChromeDriver V2

Este projeto contém um script Python projetado para automatizar todo o ciclo de vida da atualização do **ChromeDriver**. Ele verifica a versão mais recente compatível com o canal Estável do Google Chrome, faz o download, e armazena o artefato de forma versionada em um repositório Git, criando tags para cada nova versão.

## Funcionalidades Principais

  - **Verificação Automática:** Consulta a API oficial do Google para encontrar a última versão estável do ChromeDriver.
  - **Download com Barra de Progresso:** Baixa o arquivo `.zip` exibindo o progresso em tempo real.
  - **Versionamento com Git:** Salva o arquivo baixado e um arquivo de versão (`version.txt`) no repositório.
  - **Criação de Tags:** Cria e envia uma tag Git (ex: `v125.0.6422.78`) para o repositório remoto.
  - **Notificações de Desktop:** Envia uma notificação nativa ao final do processo.
  - **Interface de Linha de Comando Estilizada:** Utiliza cores para diferenciar logs, sucessos, avisos e erros.

## Guia de Instalação e Configuração Detalhada

Siga cada passo atentamente para garantir que o ambiente seja configurado corretamente.

### Parte 1: Pré-requisitos

Antes de começar, garanta que você tem os seguintes softwares instalados e funcionando em seu sistema:

  - **Python** (versão 3.8 ou superior)
  - **Git**

### Parte 2: Configuração do Repositório Remoto (GitHub)

Você precisará de um repositório no GitHub para armazenar as versões do ChromeDriver.

1.  **Crie um Repositório no GitHub:**

      * Acesse o [GitHub](https://github.com) e faça login.
      * Clique em **"New"** para criar um novo repositório.
      * Dê um nome a ele (ex: `repositorio-chromedriver`).
      * Mantenha-o **"Public"** (Público) ou **"Private"** (Privado), conforme sua preferência.
      * **Importante:** Não inicialize com arquivos `README`, `.gitignore` ou licença. Faremos isso manualmente.
      * Clique em **"Create repository"**.

2.  **Copie a URL do Repositório:**

      * Na página do seu novo repositório, copie a URL HTTPS. Ela será semelhante a: `https://github.com/seu-usuario/repositorio-chromedriver.git`.

### Parte 3: Configuração do Ambiente Local

Agora, vamos preparar a pasta do projeto em seu computador.

1.  **Crie a Pasta do Projeto:**

      * Abra seu terminal (Prompt de Comando, PowerShell ou Terminal).
      * Crie uma pasta e navegue para dentro dela:
        ```bash
        mkdir projeto-autodriver
        cd projeto-autodriver
        ```

2.  **Inicialize o Git Localmente:**

      * Transforme a pasta em um repositório Git:
        ```bash
        git init
        ```

3.  **Conecte o Repositório Local ao Remoto:**

      * Use a URL que você copiou do GitHub para linkar os dois repositórios. Lembre-se de usar a sua URL.
        ```bash
        git remote add origin https://github.com/seu-usuario/repositorio-chromedriver.git
        ```

### Parte 4: Criação dos Arquivos do Projeto

Dentro da pasta `projeto-autodriver`, crie os seguintes arquivos com o conteúdo exato fornecido abaixo.

**1. `atualiza_chromedriver.py`**

```python
# -*- coding: utf-8 -*-
import os
import requests
import subprocess
import hashlib
import colorama
from contextlib import contextmanager
from datetime import datetime
from dotenv import load_dotenv
from plyer import notification
from typing import Optional, Tuple

# Inicializa colorama
colorama.init(autoreset=True)

class Style:
    RESET, BOLD, RED, GREEN, YELLOW, BLUE, CYAN = '\033[0m', '\033[1m', '\033[91m', '\033[92m', '\033[93m', '\033[94m', '\033[96m'

# Configuração
load_dotenv()
CHROMEDRIVER_PATH = os.getenv('CHROMEDRIVER_PATH')
ZIP_NAME, VERSION_FILE = 'chromedriver-win64.zip', 'version.txt'
JSON_URL, CHUNK_SIZE = 'https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json', 1024 * 1024

# Funções Utilitárias
def log(msg: str, style: str = ""):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {style}{msg}")

@contextmanager
def change_dir(path: str):
    original_path = os.getcwd()
    try: os.chdir(path); yield
    finally: os.chdir(original_path)

def calcular_sha256(caminho_arquivo: str) -> str:
    sha256 = hashlib.sha256()
    with open(caminho_arquivo, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''): sha256.update(chunk)
    return sha256.hexdigest()

# Fluxo Principal
def obter_ultima_versao_e_url() -> Tuple[str, str]:
    log("Consultando o JSON de versões...", style=Style.CYAN)
    response = requests.get(JSON_URL, timeout=15)
    response.raise_for_status()
    data = response.json()
    stable_channel = data["channels"]["Stable"]
    win64_download = next((item for item in stable_channel["downloads"]["chromedriver"] if item["platform"] == "win64"), None)
    if not win64_download: raise ValueError("URL do chromedriver-win64 não encontrada!")
    return stable_channel["version"], win64_download["url"]

def ler_versao_salva(path: str) -> Optional[str]:
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f: return f.read().strip()
    return None

def salvar_versao(path: str, version: str):
    with open(path, 'w', encoding='utf-8') as f: f.write(version)

def baixar_arquivo_com_progresso(url: str, path: str):
    response, total_size = requests.get(url, stream=True, timeout=60), int(response.headers.get('Content-Length', 0))
    response.raise_for_status()
    downloaded_size = 0
    with open(path, 'wb') as f:
        print()
        for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
            if chunk:
                f.write(chunk); downloaded_size += len(chunk)
                percent = (downloaded_size / total_size) * 100 if total_size > 0 else 0
                print(f"\r{Style.BLUE}Baixando: {percent:.2f}%", end='', flush=True)
    print("\n"); log("Download concluído.", style=Style.GREEN)

def git_push_com_tag(repo_path: str, files_to_add: list, tag: str, message: str):
    try:
        with change_dir(repo_path):
            status_result = subprocess.run(['git', 'status', '--porcelain'] + files_to_add, capture_output=True, text=True, check=True)
            if not status_result.stdout.strip():
                log("Nenhuma alteração detectada nos arquivos. Pulando commit.", style=Style.YELLOW)
            else:
                log("Alterações detectadas. Enviando para o repositório...", style=Style.CYAN)
                subprocess.run(['git', 'add'] + files_to_add, check=True)
                subprocess.run(['git', 'commit', '-m', message], check=True)
                subprocess.run(['git', 'push'], check=True)
                log("Commit enviado com sucesso.", style=Style.GREEN)

            tags_result = subprocess.run(['git', 'tag'], capture_output=True, text=True, check=True)
            if tag in tags_result.stdout.splitlines():
                log(f"A tag '{Style.BOLD}{tag}{Style.RESET}{Style.YELLOW}' já existe.", style=Style.YELLOW)
            else:
                log(f"Criando e enviando a tag '{Style.BOLD}{tag}{Style.RESET}{Style.CYAN}'...", style=Style.CYAN)
                subprocess.run(['git', 'tag', tag], check=True)
                subprocess.run(['git', 'push', 'origin', tag], check=True)
                log(f"Tag '{Style.BOLD}{tag}{Style.RESET}{Style.GREEN}' enviada com sucesso.", style=Style.GREEN)
    except FileNotFoundError: log("ERRO: 'git' não encontrado. Verifique a instalação.", style=Style.RED)
    except subprocess.CalledProcessError as e:
        log(f"ERRO ao executar comandos Git: {e}", style=Style.RED)
        if e.stderr: log(f"Stderr: {e.stderr}", style=Style.RED)
        raise e

def notificar(titulo: str, mensagem: str):
    try: notification.notify(title=titulo, message=mensagem, timeout=10)
    except Exception as e: log(f"Falha ao enviar notificação: {e}", style=Style.YELLOW)

def main():
    if not CHROMEDRIVER_PATH:
        log("ERRO: Variável 'CHROMEDRIVER_PATH' não definida no arquivo .env.", style=Style.RED); return
    os.makedirs(CHROMEDRIVER_PATH, exist_ok=True)
    caminho_zip, caminho_version = os.path.join(CHROMEDRIVER_PATH, ZIP_NAME), os.path.join(CHROMEDRIVER_PATH, VERSION_FILE)
    try:
        versao_recente, url_chromedriver = obter_ultima_versao_e_url()
        log(f"Última versão estável: {Style.BOLD}{versao_recente}", style=Style.GREEN)
        versao_salva = ler_versao_salva(caminho_version)
        log(f"Versão local: {Style.BOLD}{versao_salva or 'Nenhuma'}", style=Style.CYAN)
        if versao_salva == versao_recente:
            log("Você já possui a última versão.", style=Style.YELLOW); return
        log("Nova versão detectada. Iniciando download...", style=Style.BLUE)
        baixar_arquivo_com_progresso(url_chromedriver, caminho_zip)
        salvar_versao(caminho_version, versao_recente)
        tag, commit_message = f'v{versao_recente}', f"Atualiza ChromeDriver para a versão {versao_recente}"
        git_push_com_tag(repo_path=CHROMEDRIVER_PATH, files_to_add=[ZIP_NAME, VERSION_FILE], tag=tag, message=commit_message)
        notificar("ChromeDriver Atualizado", f"Versão {versao_recente} baixada e enviada.")
    except (requests.RequestException, subprocess.CalledProcessError, ValueError, KeyError) as e:
        log(f"O processo foi interrompido por um erro. Detalhes: {e}", style=Style.RED)
        return
    log("Processo concluído com sucesso!", style=Style.BOLD + Style.GREEN)

if __name__ == "__main__":
    main()
```

**2. `requirements.txt`**

```
requests
python-dotenv
plyer
colorama
```

**3. `.gitignore`**

```
# Ambiente Virtual
venv/

# Cache do Python
__pycache__/
*.pyc

# Arquivo de configuração de ambiente
.env

# Arquivos de IDE
.vscode/
.idea/
```

**4. `.env.example`** (Arquivo de exemplo)

```
# Copie este arquivo para .env e substitua pelo caminho absoluto para a pasta do projeto.
CHROMEDRIVER_PATH="/caminho/absoluto/para/a/pasta/do/projeto"
```

### Parte 5: Configuração Final do Ambiente

1.  **Crie e Ative o Ambiente Virtual:**

    ```bash
    # Para Windows
    python -m venv venv
    venv\Scripts\activate

    # Para macOS/Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

2.  **Instale as Dependências:**

    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure sua Variável de Ambiente:**

      * Crie uma cópia do arquivo de exemplo:
        ```bash
        # Windows
        copy .env.example .env
        # macOS/Linux
        cp .env.example .env
        ```
      * Abra o novo arquivo `.env` e edite a variável `CHROMEDRIVER_PATH`. Você precisa do **caminho absoluto** para a pasta `projeto-autodriver`.
      * *Dica para encontrar o caminho:* no seu terminal, dentro da pasta do projeto, use o comando `pwd` (Linux/macOS) ou `cd` (Windows) para ver o caminho atual.

### Parte 6: Primeira Execução e Solução de Problemas

Na primeira vez que você executar, talvez precise fazer uma configuração inicial do Git.

1.  **Execute o Script:**

    ```bash
    python atualiza_chromedriver.py
    ```

2.  **Possível Erro 1: Autenticação (Exit Code 128)**

      * **Problema:** O GitHub não aceita mais senhas de conta via terminal.
      * **Solução:** Crie um **Personal Access Token (PAT)**.
        1.  Vá em seu GitHub \> Settings \> Developer settings \> Personal access tokens \> Tokens (classic).
        2.  Clique em "Generate new token".
        3.  Dê um nome, uma validade e marque a permissão **`repo`**.
        4.  Copie o token gerado.
        5.  Execute `git push` manualmente no terminal. Quando pedir a senha (`Password`), **cole o token**.

3.  **Possível Erro 2: "No Upstream Branch"**

      * **Problema:** O Git local não sabe a qual branch remota se conectar.
      * **Solução:** Execute o comando que o próprio Git sugere. Use `main` ou `master` dependendo do nome da sua branch principal.
        ```bash
        git push --set-upstream origin main
        ```

Após resolver esses dois pontos, o script deverá rodar sem erros.

### Uso Contínuo

Depois da configuração inicial, basta navegar até a pasta do projeto, ativar o ambiente virtual (`venv\Scripts\activate` ou `source venv/bin/activate`) e rodar o script para verificar se há novas versões do ChromeDriver.

```bash
python atualiza_chromedriver.py
```
