# ==============================================================================
# ARQUIVO: app/integration_server/utils/database_utils.py
# DESCRICAO: Funcoes utilitarias para interagir com o banco de dados PostgreSQL.
# VERSAO: 1.0
# ==============================================================================

import os
import psycopg2
import json
import datetime

# Funcao para estabelecer a conexao com o banco de dados
def get_db_connection():
    """
    Estabelece uma conexao com o banco de dados PostgreSQL.
    As credenciais sao obtidas das variaveis de ambiente.
    """
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
        return conn
    except Exception as e:
        print(f"Erro ao conectar ao banco de dados: {e}")
        return None

# Funcao para inserir um novo pedido
def insert_order(client_info, order_hash, encrypted_pdf_bytes, order_items):
    """
    Insere um novo registro de pedido na tabela 'orders' do PostgreSQL.
    """
    conn = get_db_connection()
    if conn is None:
        return False

    try:
        with conn.cursor() as cur:
            # Dados a serem inseridos
            order_data = {
                "order_txid": order_hash,
                "cliente": client_info.get('name'),
                "cnpj": client_info.get('cnpj'),
                "representante": client_info.get('rep_name'),
                "data_hora_utc": datetime.datetime.now(datetime.timezone.utc),
                "ip_origem": client_info.get('ip'),
                "produtos_solicitados": json.dumps(order_items),
                "hash_pedido_ipfs": order_hash, # Reutiliza a hash para o exemplo
                "status": "Aguardando avaliacao"
            }
            
            # Query SQL para insercao
            query = """
                INSERT INTO orders (
                    order_txid, cliente, cnpj, representante, data_hora_utc, 
                    ip_origem, produtos_solicitados, hash_pedido_ipfs, status
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """
            
            cur.execute(query, list(order_data.values()))
            conn.commit()
            
            print(f"Pedido com hash {order_hash} inserido com sucesso no PostgreSQL.")
            return True
            
    except Exception as e:
        conn.rollback()
        print(f"Erro ao inserir pedido no banco de dados: {e}")
        return False
        
    finally:
        conn.close()
