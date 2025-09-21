# ==============================================================================
# ARQUIVO: app/integration_server/utils/ipfs_utils.py
# DESCRIÇÃO: Funções de utilidade para interagir com o daemon do IPFS e para
#              realizar operações de encriptação e desencriptação de dados.
# VERSÃO: 3.0
# ==============================================================================

# --- 1. IMPORTAÇÕES ---
import os
import ipfshttpclient
from cryptography.fernet import Fernet

# --- 2. FUNÇÕES DE INTERAÇÃO COM O IPFS ---

def get_ipfs_client():
    """
    Cria e retorna um cliente para a API do IPFS, conectando-se ao daemon
    local com base nas configurações do ficheiro .env.
    """
    # Carrega as configurações de conexão do IPFS a partir das variáveis de ambiente.
    #host = os.getenv('IPFS_API_HOST', '127.0.0.1') trocado
    IPFS_API_HOST = os.getenv('IPFS_API_HOST', 'ipfs')   # nome do serviço no Compose
    IPFS_API_PORT = os.getenv('IPFS_API_PORT', '5001')
    
    try:
        # Tenta conectar-se ao daemon do IPFS.
        client = ipfshttpclient.connect(f"/dns/{IPFS_API_HOST}/tcp/{IPFS_API_PORT}/http") # nome do serviço no Compose
        #client = ipfshttpclient.connect(f'/ip4/{host}/tcp/{port}') trocado
        return client
    except Exception as e:
        print(f"ERRO: Não foi possível conectar com o daemon do IPFS: {e}")
        return None

def add_to_ipfs(data_bytes):
    """
    Adiciona um conjunto de dados (em bytes) ao IPFS.

    Args:
        data_bytes (bytes): Os dados a serem adicionados.

    Returns:
        str: O hash (CID) do conteúdo adicionado, ou None em caso de erro.
    """
    client = get_ipfs_client()
    if not client:
        return None
    
    try:
        # Usa o cliente para adicionar os bytes e retorna o hash resultante.
        result = client.add_bytes(data_bytes)
        print(f"Dados adicionados ao IPFS com hash: {result}")
        return result
    except Exception as e:
        print(f"ERRO: Falha ao adicionar dados ao IPFS: {e}")
        return None

def get_from_ipfs(ipfs_hash):
    """
    Recupera dados do IPFS usando o seu hash (CID).

    Args:
        ipfs_hash (str): O hash do conteúdo a ser recuperado.

    Returns:
        bytes: Os dados recuperados em formato de bytes, ou None em caso de erro.
    """
    client = get_ipfs_client()
    if not client:
        return None
    
    try:
        # Usa o cliente para obter o conteúdo associado ao hash.
        data_bytes = client.cat(ipfs_hash)
        return data_bytes
    except Exception as e:
        print(f"ERRO: Falha ao recuperar dados do IPFS (hash: {ipfs_hash}): {e}")
        return None

# --- 3. FUNÇÕES DE CRIPTOGRAFIA ---

def encrypt_data(data_bytes, key_bytes):
    """
    Encripta um conjunto de dados (em bytes) usando uma chave Fernet fornecida.
    
    Args:
        data_bytes (bytes): Os dados a serem encriptados.
        key_bytes (bytes): A chave de encriptação.

    Returns:
        bytes: Os dados encriptados.
    """
    # A chave é passada como argumento e não gerada aqui.
    f = Fernet(key_bytes)
    encrypted_data = f.encrypt(data_bytes)
    
    # Retorna apenas os dados encriptados, conforme esperado pelo resto do código.
    return encrypted_data

def decrypt_data(encrypted_data_bytes, key_bytes):
    """
    Desencripta dados (em bytes) usando uma chave Fernet (em bytes).
    
    Args:
        encrypted_data_bytes (bytes): Os dados encriptados.
        key_bytes (bytes): A chave usada para a encriptação.

    Returns:
        bytes: Os dados originais desencriptados, ou None em caso de erro.
    """
    try:
        f = Fernet(key_bytes)
        decrypted_data = f.decrypt(encrypted_data_bytes)
        return decrypted_data
    except Exception as e:
        # Este erro ocorre tipicamente se a chave estiver incorreta ou os dados corrompidos.
        print(f"ERRO: Falha ao descriptografar dados: {e}")
        return None
