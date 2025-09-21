# ==============================================================================
# ARQUIVO:    utils/first_initialization.py
# DESCRIÇÃO:  Script para a configuração inicial da aplicação em ambiente Docker.
#             Prepara as chaves de segurança, cria as streams na blockchain,
#             concede permissões aos nós da rede e popula com dados iniciais.
# VERSÃO:     6.0 (Adaptado para Multi-Nó com Docker)
# ==============================================================================

# --- 1. IMPORTAÇÕES E CONFIGURAÇÃO DO AMBIENTE ---
import os
import sys
import json
import glob
import time
import datetime
from cryptography.fernet import Fernet

# Adiciona o diretório da aplicação ao path do Python para permitir importações.
# No ambiente Docker, o código da aplicação reside em /app.
sys.path.insert(0, '/app/nomus_blockchain')

try:
    from app.integration_server.utils import blockchain_utils, ipfs_utils
except ImportError as e:
    print(f"ERRO CRÍTICO: Não foi possível importar os módulos da aplicação. Verifique a estrutura de pastas.")
    print(f"Detalhes: {e}")
    sys.exit(1)

# --- 2. CONSTANTES DE CONFIGURAÇÃO ---
# Caminhos de ficheiros e nomes de streams centralizados para fácil manutenção.
# Os caminhos são absolutos dentro do contêiner Docker.
APP_ROOT = '/app/nomus_blockchain'
PRODUCT_CATALOG_PATH = os.path.join(APP_ROOT, 'app/integration_server/config/product_catalog.json')
CONTRACT_PDF_PATH = os.path.join(APP_ROOT, 'app/integration_server/config/CONTRATO_MODELO.pdf')
ENCRYPTED_CONTRACT_PATH = os.path.join(APP_ROOT, 'app/integration_server/config/CONTRATO_MODELO.pdf.enc')
DELIVERIES_PDF_DIR = os.path.join(APP_ROOT, 'app/integration_server/config/deliveries')
ENV_FILE_PATH = os.path.join(APP_ROOT, '.env')

STREAMS_TO_CREATE = [
    'config_stream', 'inventory_stream', 'financial_stream',
    'orders_stream', 'deliveries_stream', 'notes_stream'
]

# --- 3. FUNÇÕES DE INICIALIZAÇÃO ---

def initialize_security_keys():
    """
    Gera e guarda as chaves de encriptação para o contrato e para as entregas
    no ficheiro .env, se ainda não existirem. Também encripta o contrato modelo.
    """
    print("\n--- PASSO 1: A INICIAR SETUP DE SEGURANÇA ---")
    
    # Garante que o ficheiro .env existe.
    if not os.path.exists(ENV_FILE_PATH):
        open(ENV_FILE_PATH, 'a').close()
        print(f"Ficheiro '{ENV_FILE_PATH}' criado.")

    with open(ENV_FILE_PATH, 'r+') as f_env:
        env_content = f_env.read()
        
        # Processa a chave do contrato.
        if "CONTRACT_DECRYPTION_KEY" not in env_content:
            print("  - A gerar chave para o CONTRATO...")
            key_contract = Fernet.generate_key()
            f_env.write('\n# Chave de encriptação para o contrato principal\n')
            f_env.write(f'CONTRACT_DECRYPTION_KEY="{key_contract.decode("utf-8")}"\n')
            print("    -> Chave do contrato adicionada ao .env com sucesso!")
        else:
            print("  - AVISO: Chave do contrato já existe no .env. A pular.")

        # Processa a chave das entregas.
        if "DELIVERIES_DECRYPTION_KEY" not in env_content:
            print("  - A gerar chave para as ENTREGAS...")
            key_deliveries = Fernet.generate_key()
            f_env.write('\n# Chave de encriptação para os PDFs de entregas\n')
            f_env.write(f'DELIVERIES_DECRYPTION_KEY="{key_deliveries.decode("utf-8")}"\n')
            print("    -> Chave das entregas adicionada ao .env com sucesso!")
        else:
            print("  - AVISO: Chave das entregas já existe no .env. A pular.")

    # Encripta o ficheiro de contrato modelo, se ainda não tiver sido feito.
    if not os.path.exists(ENCRYPTED_CONTRACT_PATH) and os.path.exists(CONTRACT_PDF_PATH):
        print("\n  - A encriptar o ficheiro de contrato modelo...")
        try:
            # Recarrega as variáveis de ambiente para garantir que as novas chaves estão disponíveis.
            from dotenv import load_dotenv
            load_dotenv(ENV_FILE_PATH)
            
            key_str = os.getenv('CONTRACT_DECRYPTION_KEY')
            if not key_str:
                raise ValueError("CONTRACT_DECRYPTION_KEY não encontrada no ambiente após ser guardada.")
            
            with open(CONTRACT_PDF_PATH, 'rb') as f_in:
                pdf_data = f_in.read()
            
            encrypted_data = ipfs_utils.encrypt_data(pdf_data, key_str.encode('utf-8'))
            
            with open(ENCRYPTED_CONTRACT_PATH, 'wb') as f_out:
                f_out.write(encrypted_data)
            print(f"    -> Ficheiro de contrato encriptado com sucesso em '{ENCRYPTED_CONTRACT_PATH}'.")
        except Exception as e:
            print(f"    -> ERRO ao encriptar o contrato modelo: {e}")
    else:
        print("\n  - AVISO: Ficheiro de contrato já encriptado ou ficheiro original não encontrado. A pular.")
    
    print("--- SETUP DE SEGURANÇA FINALIZADO ---")


def initialize_blockchain_structure():
    """
    Garante que todas as streams necessárias para a aplicação existem na blockchain.
    """
    print("\n--- PASSO 2: A VERIFICAR E CRIAR STREAMS NA BLOCKCHAIN ---")
    all_streams_ok = True
    for stream in STREAMS_TO_CREATE:
        print(f"  - A verificar stream: '{stream}'...")
        if not blockchain_utils.create_and_subscribe_stream_if_not_exists(stream):
            print(f"    -> ERRO CRÍTICO: Falha ao criar ou subscrever a stream '{stream}'.")
            all_streams_ok = False
    
    if all_streams_ok:
        print("--- VERIFICAÇÃO DE STREAMS CONCLUÍDA COM SUCESSO ---")
    else:
        print("--- VERIFICAÇÃO DE STREAMS FALHOU. VERIFIQUE OS LOGS. ---")
        sys.exit(1)

#PERMISSÕES MOVIDAS PARA START-NODE.SH NO DOCKER-COMPOSE

def initialize_blockchain_data():
    """
    Popula a blockchain com os dados iniciais necessários para a aplicação, como
    o contrato, o inventário, dados financeiros e entregas pré-existentes.
    """
    print("\n--- PASSO 4: A INICIAR POPULAÇÃO DE DADOS NA BLOCKCHAIN ---")

    # 4.1: Enviar o contrato para o IPFS e registar o hash na blockchain.
    print("\n  [4.1] A processar contrato principal...")
    try:
        with open(ENCRYPTED_CONTRACT_PATH, 'rb') as f:
            encrypted_contract_bytes = f.read()
        
        ipfs_hash = ipfs_utils.add_to_ipfs(encrypted_contract_bytes)
        if not ipfs_hash:
            raise Exception("Falha ao enviar o contrato para o IPFS.")
        
        print(f"    -> Contrato enviado para o IPFS. Hash: {ipfs_hash}")

        contract_metadata = {
            "document_type": "master_contract",
            "ipfs_hash_encrypted": ipfs_hash,
            "valid_from": "2024-08-01",
            "valid_until": "2025-02-28"
        }
        txid = blockchain_utils.publish_to_blockchain('config_stream', "contract_v1", contract_metadata)
        if not txid:
            raise Exception("Falha ao registar metadados do contrato na blockchain.")
        print(f"    -> Metadados do contrato registados na stream 'config_stream'.")
    except Exception as e:
        print(f"    -> ERRO na etapa do contrato: {e}")
        return

    # 4.2: Ler o catálogo de produtos e inicializar o inventário.
    print("\n  [4.2] A inicializar inventário de produtos...")
    try:
        with open(PRODUCT_CATALOG_PATH, 'r', encoding='utf-8') as f:
            product_catalog = json.load(f)

        for group in product_catalog:
            initial_stock = group.get("quantidade_inicial_contrato", 0)
            if group.get("variants") and len(group["variants"]) > 0:
                inventory_key = group["variants"][0]["codigo"]
                inventory_data = {
                    "product_code": inventory_key,
                    "product_group": group["product_group"],
                    "available_stock": int(initial_stock),
                    "consumed_stock": 0
                }
                blockchain_utils.publish_to_blockchain('inventory_stream', inventory_key, inventory_data)
        print("    -> Inventário inicializado com sucesso.")
    except Exception as e:
        print(f"    -> ERRO ao processar catálogo de produtos: {e}")
        return

    # 4.3: Inicializar o status financeiro (parcelas).
    print("\n  [4.3] A inicializar status financeiro...")
    try:
        installments = [
            {"id_nomus": 20748, "due_date": "2024-09-27", "value": 41632.65, "paid": True},
            {"id_nomus": 20794, "due_date": "2024-10-27", "value": 41632.65, "paid": True},
            {"id_nomus": 21785, "due_date": "2024-11-27", "value": 16653.06, "paid": False},
            {"id_nomus": 22087, "due_date": "2024-12-26", "value": 16653.06, "paid": True},
            {"id_nomus": 23510, "due_date": "2025-01-26", "value": 16653.06, "paid": False},
            {"id_nomus": 23914, "due_date": "2025-01-26", "value": 16653.06, "paid": True}
        ]
        for inst in installments:
            key = f"installment_{inst['id_nomus']}"
            blockchain_utils.publish_to_blockchain('financial_stream', key, inst)
        print("    -> Dados financeiros inicializados com sucesso.")
    except Exception as e:
        print(f"    -> ERRO ao inicializar dados financeiros: {e}")
        return

    # 4.4: Encriptar e registar PDFs de entregas iniciais.
    print("\n  [4.4] A processar PDFs de entregas iniciais...")
    try:
        key_str = os.getenv('DELIVERIES_DECRYPTION_KEY')
        if not key_str:
            raise ValueError("A chave DELIVERIES_DECRYPTION_KEY não foi encontrada no .env")
        
        delivery_files = glob.glob(os.path.join(DELIVERIES_PDF_DIR, '*.pdf'))
        if not delivery_files:
            print("    -> AVISO: Nenhum PDF de entrega encontrado em 'config/deliveries'. A pular.")
        
        for pdf_path in delivery_files:
            delivery_id = os.path.splitext(os.path.basename(pdf_path))[0]
            print(f"    - A processar entrega: {delivery_id}.pdf")
            
            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()
            
            encrypted_pdf = ipfs_utils.encrypt_data(pdf_bytes, key_str.encode('utf-8'))
            ipfs_hash = ipfs_utils.add_to_ipfs(encrypted_pdf)
            
            if ipfs_hash:
                delivery_metadata = {
                    "delivery_id": delivery_id,
                    "ipfs_hash_encrypted": ipfs_hash,
                    "status": "Confirmado", # Marca como confirmado para não aparecer como pendente.
                    "approved_by": "Sistema (Inicialização)",
                    "approved_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()
                }
                blockchain_utils.publish_to_blockchain('deliveries_stream', delivery_id, delivery_metadata)
                print(f"      -> Entrega {delivery_id} registada com sucesso.")
            else:
                print(f"      -> ERRO: Falha ao enviar {delivery_id}.pdf para o IPFS.")
    except Exception as e:
        print(f"    -> ERRO CRÍTICO ao processar PDFs de entregas: {e}")
        return
    
    print("\n--- POPULAÇÃO DE DADOS NA BLOCKCHAIN FINALIZADA ---")


# --- 5. PONTO DE ENTRADA DO SCRIPT ---
if __name__ == "__main__":
    print("==========================================================")
    print("== INICIANDO SCRIPT DE CONFIGURAÇÃO INICIAL DA APLICAÇÃO ==")
    print("==========================================================")
    
    # Carrega as variáveis de ambiente do ficheiro .env para o ambiente atual.
    from dotenv import load_dotenv
    load_dotenv(ENV_FILE_PATH)

    # Executa as funções de inicialização na ordem correta e necessária.
    initialize_security_keys()
    initialize_blockchain_structure()
    
    initialize_blockchain_data()
    
    print("\n==========================================================")
    print("=== SCRIPT DE INICIALIZAÇÃO COMPLETO ===")
    print("==========================================================")
