"""
Script para automatizar a verificação, download e versionamento do ChromeDriver.

Este script:
1.  Verifica a última versão estável do ChromeDriver para Windows (64-bit).
2.  Compara com a versão localmente salva para ver se há uma atualização.
3.  Se houver uma nova versão, faz o download do arquivo .zip.
4.  Salva o novo arquivo .zip e um arquivo de texto com a versão.
5.  Adiciona os novos arquivos a um repositório Git, cria um commit e uma tag.
6.  Envia o commit e a tag para o repositório remoto.
7.  Envia uma notificação no desktop sobre a atualização.

Pré-requisitos:
- Python 3
- Git instalado e configurado no PATH do sistema.

Dependências (instalar com 'pip install'):
- requests
- python-dotenv
- plyer
- colorama (para estilos de cor no terminal)
"""

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

# === INICIALIZAÇÃO DE ESTILOS ===
# Inicializa colorama para funcionar no Windows e reseta a cor após cada print
colorama.init(autoreset=True)

class Style:
    """Contém os códigos de escape ANSI para estilizar o texto do terminal."""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'

# === CONFIGURAÇÃO ===
load_dotenv()
CHROMEDRIVER_PATH = os.getenv('CHROMEDRIVER_PATH')
ZIP_NAME = 'chromedriver-win64.zip'
VERSION_FILE = 'version.txt'
JSON_URL = 'https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json'
CHUNK_SIZE = 1024 * 1024  # 1MB


# === FUNÇÕES UTILITÁRIAS ===
def log(msg: str, style: str = "") -> None:
    """Imprime uma mensagem de log com timestamp e estilo opcional."""
    timestamp = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]"
    print(f"{timestamp} {style}{msg}") # O autoreset do colorama cuida do Style.RESET

@contextmanager
def change_dir(path: str):
    """Context manager para mudar de diretório temporariamente."""
    original_path = os.getcwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(original_path)


def calcular_sha256(caminho_arquivo: str) -> str:
    """Calcula o hash SHA256 de um arquivo."""
    sha256 = hashlib.sha256()
    with open(caminho_arquivo, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


# === FLUXO PRINCIPAL ===
def obter_ultima_versao_e_url() -> Tuple[str, str]:
    """Obtém a versão e a URL de download do último ChromeDriver estável."""
    log("Consultando o API de versões do ChromeDriver...", style=Style.CYAN)
    response = requests.get(JSON_URL, timeout=15)
    response.raise_for_status()
    data = response.json()
    
    stable_channel = data["channels"]["Stable"]
    version = stable_channel["version"]
    downloads = stable_channel["downloads"]["chromedriver"]
    
    win64_download = next((item for item in downloads if item["platform"] == "win64"), None)
    
    if not win64_download:
        raise ValueError("URL do chromedriver-win64.zip não encontrada no JSON!")
        
    return version, win64_download["url"]


def ler_versao_salva(path: str) -> Optional[str]:
    """Lê a versão salva localmente do arquivo de texto."""
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    return None


def salvar_versao(path: str, version: str) -> None:
    """Salva a string da versão em um arquivo de texto."""
    with open(path, 'w', encoding='utf-8') as f:
        f.write(version)


def baixar_arquivo_com_progresso(url: str, path: str) -> None:
    """Baixa um arquivo exibindo uma barra de progresso."""
    response = requests.get(url, stream=True, timeout=60)
    response.raise_for_status()
    total_size = int(response.headers.get('Content-Length', 0))
    downloaded_size = 0

    with open(path, 'wb') as f:
        print() # Adiciona uma linha em branco para a barra de progresso
        for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
            if chunk:
                f.write(chunk)
                downloaded_size += len(chunk)
                percent = (downloaded_size / total_size) * 100 if total_size > 0 else 0
                progress_bar = f"\r{Style.BLUE}Baixando: {percent:.2f}% ({downloaded_size / (1024*1024):.2f}MB / {total_size / (1024*1024):.2f}MB)"
                print(progress_bar, end='', flush=True)
    print() # Garante que o próximo log comece em uma nova linha
    log("Download concluído.", style=Style.GREEN)


def git_push_com_tag(repo_path: str, files_to_add: list, tag: str, message: str) -> None:
    """Verifica alterações, faz commit, cria e envia uma tag para o repositório Git."""
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
                log(f"A tag '{Style.BOLD}{tag}{Style.RESET}{Style.YELLOW}' já existe. Não será criada novamente.", style=Style.YELLOW)
            else:
                log(f"Criando e enviando a tag '{Style.BOLD}{tag}{Style.RESET}{Style.CYAN}'...", style=Style.CYAN)
                subprocess.run(['git', 'tag', tag], check=True)
                subprocess.run(['git', 'push', 'origin', tag], check=True)
                log(f"Tag '{Style.BOLD}{tag}{Style.RESET}{Style.GREEN}' criada e enviada com sucesso.", style=Style.GREEN)

    except FileNotFoundError:
        log("ERRO: O 'git' não foi encontrado. Verifique se ele está instalado e no PATH do sistema.", style=Style.RED)
    except subprocess.CalledProcessError as e:
        log(f"ERRO ao executar comandos Git: {e}", style=Style.RED)
        log(f"Stderr: {e.stderr}", style=Style.RED)


def notificar(titulo: str, mensagem: str) -> None:
    """Envia uma notificação para o desktop."""
    try:
        notification.notify(title=titulo, message=mensagem, timeout=10)
    except Exception as e:
        log(f"Falha ao enviar notificação: {e}", style=Style.YELLOW)


def main():
    """Função principal de orquestração do script."""
    if not CHROMEDRIVER_PATH:
        log("ERRO: A variável de ambiente 'CHROMEDRIVER_PATH' não está definida.", style=Style.RED)
        log("Por favor, crie um arquivo .env e adicione a linha: CHROMEDRIVER_PATH=/caminho/para/seu/repositorio", style=Style.YELLOW)
        return

    os.makedirs(CHROMEDRIVER_PATH, exist_ok=True)
    caminho_zip = os.path.join(CHROMEDRIVER_PATH, ZIP_NAME)
    caminho_version = os.path.join(CHROMEDRIVER_PATH, VERSION_FILE)

    try:
        log("Iniciando verificação de versão do ChromeDriver...", style=Style.BLUE)
        versao_recente, url_chromedriver = obter_ultima_versao_e_url()
        log(f"Última versão estável encontrada: {Style.BOLD}{versao_recente}", style=Style.GREEN)

        versao_salva = ler_versao_salva(caminho_version)
        log(f"Versão salva localmente: {Style.BOLD}{versao_salva or 'Nenhuma'}", style=Style.CYAN)

        if versao_salva == versao_recente:
            log("Você já possui a última versão. Nenhuma ação necessária.", style=Style.YELLOW)
            return

        log(f"Nova versão detectada. Iniciando download...", style=Style.BLUE)
        baixar_arquivo_com_progresso(url_chromedriver, caminho_zip)

        sha256 = calcular_sha256(caminho_zip)
        log(f"SHA256 do arquivo baixado: {Style.BOLD}{sha256}", style=Style.CYAN)

        salvar_versao(caminho_version, versao_recente)
        log(f"Arquivo de versão atualizado para '{Style.BOLD}{versao_recente}{Style.RESET}{Style.CYAN}'.", style=Style.CYAN)

        tag = f'v{versao_recente}'
        commit_message = f"Atualiza ChromeDriver para a versão {versao_recente}"
        
        git_push_com_tag(
            repo_path=CHROMEDRIVER_PATH,
            files_to_add=[ZIP_NAME, VERSION_FILE],
            tag=tag,
            message=commit_message
        )

        notificar("ChromeDriver Atualizado", f"Versão {versao_recente} baixada e enviada para o GitHub.")
        log("Processo concluído com sucesso!", style=Style.BOLD + Style.GREEN)

    except requests.exceptions.RequestException as e:
        log(f"ERRO DE REDE: Não foi possível conectar à URL de download. Detalhes: {e}", style=Style.RED)
    except (ValueError, KeyError) as e:
        log(f"ERRO DE PROCESSAMENTO DE DADOS: Não foi possível processar os dados do JSON. Detalhes: {e}", style=Style.RED)
    except Exception as e:
        log(f"Ocorreu um erro inesperado: {e}", style=Style.RED)


if __name__ == "__main__":
    main()