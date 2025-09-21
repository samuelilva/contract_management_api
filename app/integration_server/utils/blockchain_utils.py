# ==============================================================================
# ARQUIVO: app/integration_server/utils/blockchain_utils.py
# DESCRIÇÃO: Funções de utilidade para interagir com a API RPC do nó MultiChain.
#              Este módulo abstrai a complexidade da comunicação com a blockchain.
# VERSÃO: 5.0
# ==============================================================================

# --- 1. IMPORTAÇÕES ---
import os
import json
import requests

# --- 2. FUNÇÕES DE COMUNICAÇÃO COM A BLOCKCHAIN ---

def _make_rpc_request(method, params=[]):
    """
    Função base e privada para enviar requisições RPC para o nó MultiChain.
    Todas as outras funções neste módulo utilizam esta para comunicar com a blockchain.

    Args:
        method (str): O nome do método RPC a ser chamado (ex: 'publish', 'liststreams').
        params (list): Uma lista de parâmetros para o método RPC.

    Returns:
        O resultado da chamada RPC, ou None em caso de erro.
    """
    # # Carrega as credenciais de conexão a partir das variáveis de ambiente (.env).
    # user = os.getenv('MULTICHAIN_RPC_USER')
    # password = os.getenv('MULTICHAIN_RPC_PASSWORD')
    # host = os.getenv('MULTICHAIN_RPC_HOST')
    # port = os.getenv('MULTICHAIN_RPC_PORT')
    # Carrega as credenciais de conexão a partir das variáveis do Compose
    user = 'multichainrpc'
    password = '6m82ihLEfAgNRJtM7mWLvdo7B2GwSrUpUXMeojMgQpTW'
    host = '172.18.0.2'  # fallback para 'blockchain'
    port = '6466'


    # Valida se todas as credenciais necessárias estão presentes.
    if not all([user, password, host, port]):
        raise EnvironmentError("Variáveis de ambiente da MultiChain não configuradas: "
                            "MULTICHAIN_RPC_USER, MULTICHAIN_RPC_PASSWORD, "
                            "MULTICHAIN_RPC_HOST, MULTICHAIN_RPC_PORT")
            
    url = f"http://{host}:{port}"
    auth = (user, password)
    headers = {'content-type': 'application/json'}
    
    # Monta o corpo (payload) da requisição no formato JSON-RPC.
    payload = {
        "method": method,
        "params": params,
        "jsonrpc": "2.0",
        "id": 0,
    }

    # Bloco de debug para monitorizar as chamadas à blockchain.
    print(f"\nDEBUG [Blockchain]: A enviar requisição RPC...")
    print(f"DEBUG [Blockchain]: URL: {url}")
    print(f"DEBUG [Blockchain]: Método: {method}")
    print(f"DEBUG [Blockchain]: Parâmetros: {params}")

    try:
        # Envia a requisição para o nó MultiChain.
        response = requests.post(url, data=json.dumps(payload), headers=headers, auth=auth, timeout=20)
        response.raise_for_status() # Lança um erro para respostas HTTP não-2xx.
        res_json = response.json()
        
        print(f"DEBUG [Blockchain]: Resposta recebida (JSON)")

        # Verifica se a resposta da MultiChain contém um erro interno.
        if res_json.get('error'):
            print(f"DEBUG: Erro RPC da Blockchain: {res_json['error']}")
            return None
        
        # Se tudo correu bem, retorna o resultado.
        return res_json.get('result')

    except requests.exceptions.RequestException as e:
        print(f"DEBUG: ERRO: Falha de conexão com a Blockchain: {e}")
        if e.response is not None:
            print(f"DEBUG: Resposta completa da API: {e.response.text}")
        return None

def create_and_subscribe_stream_if_not_exists(stream_name):
    """
    Verifica se uma stream já existe na blockchain. Se não existir,
    cria-a e subscreve-a para que o nó atual possa interagir com ela.
    Esta função é essencial para a inicialização da aplicação.
    """
    try:
        # Tenta listar a stream. Se ela existir, a função retorna uma lista.
        existing_streams = _make_rpc_request('liststreams', [stream_name, True])
        
        if existing_streams and any(s.get('name') == stream_name for s in existing_streams):
            print(f"DEBUG [Blockchain]: A stream '{stream_name}' já existe.")
            return True

        # Se a stream não existir, cria-a.
        print(f"DEBUG [Blockchain]: A stream '{stream_name}' não foi encontrada. A criar...")
        create_txid = _make_rpc_request('create', ['stream', stream_name, True])
        if not create_txid:
            print(f"DEBUG: ERRO: Falha ao criar a stream '{stream_name}'.")
            return False
        
        # Após a criação, subscreve-a.
        print(f"DEBUG [Blockchain]: A subscrever a stream '{stream_name}'...")
        _make_rpc_request('subscribe', [stream_name])
        
        print(f"DEBUG [Blockchain]: A stream '{stream_name}' foi criada e subscrita com sucesso.")
        return True
    except Exception as e:
        print(f"DEBUG: ERRO inesperado ao verificar/criar a stream '{stream_name}': {e}")
        return False

def publish_to_blockchain(stream_name, key, data_dict):
    """
    Publica um dicionário de dados (JSON) numa stream com uma chave específica.
    Os dados são convertidos para hexadecimal antes de serem publicados.
    """
    # Garante que a stream existe antes de tentar publicar.
    if not create_and_subscribe_stream_if_not_exists(stream_name):
        return None
    
    # Converte o dicionário Python para uma string JSON, depois para bytes e finalmente para hexadecimal.
    hex_data = json.dumps(data_dict).encode('utf-8').hex()
    return _make_rpc_request('publish', [stream_name, key, hex_data])

def get_last_item_from_stream_key(stream_name, key):
    """
    Busca o item mais recente publicado numa stream com uma chave específica.
    Útil para obter o estado atual de um item (ex: o stock de um produto).
    """
    # Pede à blockchain apenas o último item (-1) para a chave especificada.
    items = _make_rpc_request('liststreamkeyitems', [stream_name, key, False, 1])
    if items and len(items) > 0:
        # Descodifica os dados de hexadecimal de volta para um dicionário Python.
        hex_data = items[-1].get('data', '')
        return json.loads(bytes.fromhex(hex_data).decode('utf-8'))
    return None

def get_all_items_from_stream(stream_name):
    """
    Busca o estado mais recente de todos os itens numa stream, retornando uma
    lista. Esta é a forma correta e robusta de ler a stream de pedidos.
    """
    # ALTERAÇÃO: O método liststreamitems não retorna a 'key' do item.
    # Para obter os dados mais recentes de cada item com sua chave,
    # primeiro listamos todas as chaves da stream e depois buscamos
    # o último item de cada chave.
    print(f"DEBUG [Blockchain]: A buscar o estado mais recente da stream '{stream_name}'...")
    
    # Passo 1: Obter todas as chaves únicas na stream.
    keys = _make_rpc_request('liststreamkeys', [stream_name])
    if not keys:
        print(f"DEBUG [Blockchain]: Nenhuma chave encontrada na stream '{stream_name}'.")
        return []

    latest_items = []
    # Passo 2: Para cada chave, busca apenas o último (mais recente) item.
    for key_obj in keys:
        key = key_obj.get('key')
        if not key:
            continue
        
        # O get_last_item_from_stream_key já decodifica os dados.
        latest_item_data = get_last_item_from_stream_key(stream_name, key)
        if latest_item_data:
            # ALTERAÇÃO: Adiciona a chave de volta ao objeto para que
            # a rota de listagem de pedidos possa processá-la.
            latest_item_data['key'] = key
            latest_items.append(latest_item_data)

    print(f"DEBUG [Blockchain]: Estado da stream '{stream_name}' carregado com {len(latest_items)} itens únicos.")
    return latest_items

def get_latest_stream_state(stream_name, key_field="product_code"):
    """
    Busca o estado mais recente de todos os itens numa stream, retornando um
    dicionário. Esta é a forma correta e robusta de ler o inventário,
    garantindo que não há inconsistências com dados antigos.
    """
    print(f"DEBUG [Blockchain]: A buscar o estado mais recente da stream '{stream_name}'...")
    
    # Passo 1: Obter todas as chaves únicas na stream (ex: todos os códigos de produto).
    keys = _make_rpc_request('liststreamkeys', [stream_name])
    if not keys:
        print(f"DEBUG [Blockchain]: Nenhuma chave encontrada na stream '{stream_name}'.")
        return {}

    state_dict = {}
    # Passo 2: Para cada chave, busca apenas o último (mais recente) item.
    for key_obj in keys:
        key = key_obj.get('key')
        if not key: continue
        
        latest_item = get_last_item_from_stream_key(stream_name, key)
        if latest_item and key_field in latest_item:
            # Usa o valor do campo chave (ex: "PA 00950") como a chave do dicionário de retorno.
            item_key = latest_item[key_field]
            state_dict[item_key] = latest_item

    print(f"DEBUG [Blockchain]: Estado da stream '{stream_name}' carregado com {len(state_dict)} itens únicos.")
    return state_dict