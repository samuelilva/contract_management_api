# ==============================================================================
# ARQUIVO: app/integration_server/utils/nomus_api.py
# DESCRIÇÃO: Centraliza todas as chamadas para a API externa do ERP Nomus.
# v3 (com Debug)
# ==============================================================================
import os
import requests

def _make_nomus_request(method, endpoint, data=None):
    """Função base para fazer requisições à API Nomus."""
    base_url = os.getenv('NOMUS_API_URL')
    api_key = os.getenv('NOMUS_API_KEY')

    if not base_url or not api_key:
        print("DEBUG [Nomus API]: ERRO: Variáveis de ambiente da API Nomus não encontradas.")
        return False, {"error": "Configuração do servidor incompleta."}
    
    headers = {'Content-Type': 'application/json', 'Authorization': f'Basic {api_key}'}
    url = f"{base_url.strip('/')}/{endpoint.strip('/')}"
    
    # --- TRECHO DE DEBUG ADICIONADO ---
    print(f"\nDEBUG [Nomus API]: Enviando requisição...")
    print(f"DEBUG [Nomus API]: URL: {url}")
    print(f"DEBUG [Nomus API]: Método: {method}")
    # ------------------------------------
    
    try:
        response = requests.request(method, url, headers=headers, json=data, timeout=15)
        response.raise_for_status()
        
        # --- TRECHO DE DEBUG ADICIONADO ---
        print(f"DEBUG [Nomus API]: Resposta recebida com sucesso (Status: {response.status_code}).")
        # ------------------------------------
        
        return True, response.json()
    except requests.exceptions.RequestException as e:
        print(f"DEBUG [Nomus API]: ERRO na requisição: {e}")
        if e.response is not None:
            print(f"DEBUG [Nomus API]: Resposta de erro do servidor: {e.response.text}")
        return False, {"error": str(e)}

def get_nomus_conta_receber(conta_id):
    """Busca o status de uma conta a receber específica."""
    return _make_nomus_request("GET", f"rest/contasReceber/{conta_id}")

def get_nomus_pessoa(pessoa_id):
    """Busca dados de uma pessoa (cliente, representante, etc.) pelo ID."""
    if not pessoa_id or pessoa_id == 0:
        print(f"DEBUG [Nomus API]: ID de pessoa inválido ou zero ({pessoa_id}), pulando requisição.")
        return False, {}
    return _make_nomus_request("GET", f"rest/pessoas/{pessoa_id}")

def get_nomus_conta_receber(conta_id):
    """Busca o status de uma conta a receber específica."""
    return _make_nomus_request("GET", f"rest/contasReceber/{conta_id}")

# --- NOVA FUNÇÃO PARA BUSCAR ENTREGAS (ROMANEIOS) ---
def get_nomus_deliveries(sales_order_id):
    """
    Busca todos os documentos de saída (romaneios/entregas) associados
    a um pedido de venda de referência.
    """
    if not sales_order_id:
        return False, {"error": "ID do pedido de venda não fornecido."}
    
    # Endpoint corrigido, copiado da lógica da sua versão anterior.
    endpoint = f"rest/documentosEstoque/pedido/{sales_order_id}"
    
    return _make_nomus_request("GET", endpoint)

def get_nomus_contas_receber(conta_id):
    """Busca o status de uma conta a receber específica na API Nomus."""
    if not conta_id:
        print("DEBUG [Nomus API]: ID de conta a receber inválido, pulando requisição de update")
        return False, None
    return _make_nomus_request("GET", f"rest/contasReceber/{conta_id}")