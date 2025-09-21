# ==============================================================================
# ARQUIVO: app/integration_server/routes.py
# DESCRIÇÃO: Rotas da API interna, com a lógica de status e avaliação de pedidos.
# VERSÃO: 32.0 (Correção da lógica da rota de aprovação de entregas)
# ==============================================================================


# --- 1. IMPORTAÇÕES ---
import hashlib
import os
import json
import base64
import datetime
from flask import jsonify, request, send_file
from io import BytesIO
from . import bp
from .utils import blockchain_utils, ipfs_utils, nomus_api
from .utils.pdf_generator import generate_order_pdf

# --- 2. FUNÇÕES AUXILIARES ---
def get_inventory_key(variant_code):
    try:
        catalog_path = os.path.join(os.path.dirname(__file__), 'config', 'product_catalog.json')
        with open(catalog_path, 'r', encoding='utf-8') as f:
            product_catalog = json.load(f)
        
        for group in product_catalog:
            for variant in group.get("variants", []):
                if variant.get("codigo") == variant_code:
                    return group["variants"][0]["codigo"]
        return None
    except Exception as e:
        print(f"ERRO ao ler o catálogo de produtos: {e}")
        return None

# --- 3. ROTAS DA API ---

@bp.route('/person-details', methods=['POST'])
def get_person_details():
    data = request.get_json()
    client_id = data.get('client_id')
    rep_id = data.get('rep_id')
    client_name, client_cnpj, rep_name = "N/A", "N/A", "N/A"
    success_client, client_data = nomus_api.get_nomus_pessoa(client_id)
    if success_client:
        client_name = client_data.get("nome", "N/A")
        client_cnpj = client_data.get("cnpj", "N/A")
    success_rep, rep_data = nomus_api.get_nomus_pessoa(rep_id)
    if success_rep:
        rep_name = rep_data.get("nome", "N/A")
    return jsonify({"client_name": client_name, "client_cnpj": client_cnpj, "rep_name": rep_name})

@bp.route('/contract/status', methods=['GET'])
def get_contract_status():
    contract_metadata = blockchain_utils.get_last_item_from_stream_key('config_stream', 'contract_v1')
    inventory_dict = blockchain_utils.get_latest_stream_state('inventory_stream')
    try:
        catalog_path = os.path.join(os.path.dirname(__file__), 'config', 'product_catalog.json')
        with open(catalog_path, 'r', encoding='utf-8') as f:
            product_catalog = json.load(f)
    except Exception as e:
        return jsonify({"error": f"Falha ao carregar catálogo de produtos: {e}"}), 500
    return jsonify({"contract_info": contract_metadata, "financial_status": {"is_delinquent": False}, "inventory": inventory_dict, "product_catalog": product_catalog})

@bp.route('/contract/view', methods=['GET'])
def view_contract():
    try:
        contract_metadata = blockchain_utils.get_last_item_from_stream_key('config_stream', 'contract_v1')
        if not contract_metadata or not contract_metadata.get("ipfs_hash_encrypted"):
            return jsonify({"error": "Hash do IPFS não encontrado."}), 404
        ipfs_hash = contract_metadata.get("ipfs_hash_encrypted")
        encrypted_data = ipfs_utils.get_from_ipfs(ipfs_hash)

    #teste de criptografia
        print(f"DEBUG: Bytes do IPFS: {len(encrypted_data)}")
#fim
        if not encrypted_data: return jsonify({"error": "Não foi possível obter o ficheiro do IPFS."}), 500
        decryption_key = os.getenv('CONTRACT_DECRYPTION_KEY')

        if not decryption_key: return jsonify({"error": "Chave de descriptografia não configurada."}), 500
        decrypted_pdf_data = ipfs_utils.decrypt_data(encrypted_data, decryption_key.encode('utf-8'))
#teste
        if decrypted_pdf_data:
            print(f"DEBUG: PDF decriptado com sucesso, {len(decrypted_pdf_data)} bytes")
        else:
            print("ERRO: Falha na descriptografia")
#fim
        if not decrypted_pdf_data: return jsonify({"error": "Falha ao descriptografar o contrato."}), 500
        return send_file(BytesIO(decrypted_pdf_data), mimetype='application/pdf', as_attachment=False)
    except Exception as e:
        return jsonify({"error": f"Erro interno: {e}"}), 500

@bp.route('/order/submit', methods=['POST'])
def submit_order():
    print("RAW DATA:", request.data)  # bytes crus
    print("HEADERS:", request.headers)
    data = request.get_json()
    print(f"DEBUG: Dados recebidos na rota /order/submit: {data}")
    
    if not data: return jsonify({"success": False, "message": "Dados do pedido não recebidos."}), 400
    order_items, signature_image_b64, client_info = data.get('order_items'), data.get('signature_image'), data.get('client_info')
    if not all([order_items, signature_image_b64, client_info]):
        return jsonify({"success": False, "message": "Dados do pedido incompletos."}), 400
    try:
        for group in order_items:
            for item in group.get('items', []):
                inventory_key = get_inventory_key(item.get('codigo'))
                if not inventory_key: continue
                current_inventory = blockchain_utils.get_last_item_from_stream_key('inventory_stream', inventory_key)
                if not current_inventory: continue
                new_consumed_stock = int(current_inventory.get('consumed_stock', 0)) + int(item.get('quantity', 0))
                updated_inventory_data = { **current_inventory, "consumed_stock": new_consumed_stock }
                blockchain_utils.publish_to_blockchain('inventory_stream', inventory_key, updated_inventory_data)
        
        signature_image_bytes = base64.b64decode(signature_image_b64.split(',')[1])
        pdf_bytes = generate_order_pdf(client_info, order_items, signature_image_bytes)
        decryption_key = os.getenv('CONTRACT_DECRYPTION_KEY').encode('utf-8')
        encrypted_pdf_bytes = ipfs_utils.encrypt_data(pdf_bytes, decryption_key)
        ipfs_hash = ipfs_utils.add_to_ipfs(encrypted_pdf_bytes)
        if not ipfs_hash: raise ConnectionError("Falha ao enviar o PDF do pedido para o IPFS.")
        
        order_timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        simplified_items = [{"codigo": item['codigo'], "modelo": item['modelo'], "tamanho": item['size'], "quantidade": item['quantity']} for group in order_items for item in group['items']]
        order_json_data = {
            "cliente": client_info.get('name'), 
            "cnpj": client_info.get('cnpj'), 
            "representante": client_info.get('rep_name'), 
            "data_hora_utc": order_timestamp, 
            "ip_origem": client_info.get('ip'), 
            "produtos_solicitados": simplified_items, 
            "hash_pedido_ipfs": ipfs_hash, 
            "status": "Aguardando avaliação"
        }
        
        # Publica o pedido uma única vez, usando uma chave consistente
        order_key = f"order_{client_info.get('id', 'unknown')}_{order_timestamp}"
        txid = blockchain_utils.publish_to_blockchain('orders_stream', order_key, order_json_data)
        if not txid: raise ConnectionError("Falha ao publicar o pedido na blockchain.")

        # Adiciona o txid à carga de dados para facilitar a busca no frontend
        # e publica novamente com a mesma chave original.
        order_json_data["order_txid"] = txid
        blockchain_utils.publish_to_blockchain('orders_stream', order_key, order_json_data)
        
        return send_file(BytesIO(pdf_bytes), mimetype='application/pdf', as_attachment=True, download_name=f"pedido.pdf")
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@bp.route('/orders/list', methods=['GET'])
def list_orders():
    print("\n--- DEBUG [LIST ORDERS]: INICIANDO A BUSCA DE PEDIDOS ---")
    
    # ALTERAÇÃO: get_all_items_from_stream agora retorna a lista de pedidos
    # com a chave já inserida no objeto. Não precisamos mais iterar e
    # agrupar, pois a função já retorna o estado mais recente de cada um.
    orders = blockchain_utils.get_all_items_from_stream('orders_stream')
    
    print(f"--- DEBUG [LIST ORDERS]: Recebido da blockchain: {len(orders)} itens decodificados e agrupados por chave.")

    # Removemos a lógica de `latest_orders` e processamos a lista diretamente.
    valid_orders = [order for order in orders if isinstance(order, dict)]
    
    # Ordena a lista de pedidos por data, do mais recente para o mais antigo.
    sorted_orders = sorted(valid_orders, key=lambda x: x.get('data_hora_utc', ''), reverse=True)
    
    print("\n--- DEBUG [LIST ORDERS]: DADOS FINAIS PARA O FRONTEND ---")
    if not sorted_orders:
        print("  - Nenhum pedido encontrado.")
    for order in sorted_orders:
        # ALTERAÇÃO: O objeto 'order' já contém todos os dados e a chave.
        print(f"  - Pedido TXID: {order.get('order_txid')}, Status: '{order.get('status')}', Chave da Stream: '{order.get('key')}'")
    print("------------------------------------------------------------------\n")

    return jsonify(sorted_orders)

@bp.route('/order/review', methods=['POST'])
def review_order():
    data = request.get_json()
    order_txid, decision, reviewer_name, rejection_reason = data.get('order_txid'), data.get('decision'), data.get('reviewer_name'), data.get('rejection_reason', None)
    if not all([order_txid, decision, reviewer_name]) or decision not in ["approved", "rejected"]:
        return jsonify({"success": False, "message": "Dados inválidos."}), 400

    print("\n--- DEBUG [REVIEW ORDER]: INICIANDO BUSCA POR CHAVE ORIGINAL ---")
    print(f"--- DEBUG [REVIEW ORDER]: order_txid recebido do frontend: '{order_txid}'")

    all_items_raw = blockchain_utils.get_all_items_from_stream('orders_stream')

    original_key = None
    for item in all_items_raw:
        # CORREÇÃO: Comparar o order_txid recebido com o 'order_txid' dentro do item,
        # e usar a 'key' do item para a atualização.
        if isinstance(item, dict) and item.get('order_txid') == order_txid:
            original_key = item.get('key')
            print(f"--- DEBUG [REVIEW ORDER]: Chave original encontrada: '{original_key}'")
            break
# ALTERANDO PARA TESTAR
    # original_key = None
    # for item in all_items_raw:
    #     # A nova estrutura de `item` já é o objeto de dados decodificado, com a `key` adicionada.
    #     # Procuramos o item cujo `order_txid` corresponda ao que foi enviado do frontend.
    #     if isinstance(item, dict) and item.get('order_txid') == order_txid:
    #         original_key = item.get('key')
    #         print(f"--- DEBUG [REVIEW ORDER]: Chave original encontrada: '{original_key}'")
    #         break
    
    if not original_key:
        print(f"--- DEBUG [REVIEW ORDER]: ERRO: Chave original do pedido com txid '{order_txid}' não encontrada. ---")
        return jsonify({"success": False, "message": "Registo original do pedido não encontrado."}), 404

    status_update_data = {"status": "Aprovado" if decision == "approved" else "Recusado", "reviewed_by": reviewer_name, "reviewed_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    if decision == "rejected" and rejection_reason:
        status_update_data['rejection_reason'] = rejection_reason
    
    print(f"--- DEBUG [REVIEW ORDER]: Publicando atualização para a chave: '{original_key}'")
    update_txid = blockchain_utils.publish_to_blockchain('orders_stream', original_key, status_update_data)
    if not update_txid:
        print("--- DEBUG [REVIEW ORDER]: Falha ao publicar atualização. ---")
        return jsonify({"success": False, "message": "Falha ao registar a decisão na blockchain."}), 500

    status_text = "aprovado" if decision == "approved" else "recusado"
    notification_text = f"O seu pedido (ID: ...{order_txid[-8:]}) foi {status_text}."
    notification_data = {"Tipo da notificação": f"Pedido {status_text.capitalize()}", "Texto": notification_text, "target_role": "cliente"}
    blockchain_utils.publish_to_blockchain('notes_stream', f"note_review_{order_txid}", notification_data)
    print(f"--- DEBUG [REVIEW ORDER]: Publicação de notificação e retorno de sucesso. ---")
    return jsonify({"success": True, "message": f"Pedido {status_text} com sucesso."})

@bp.route('/orders/view/<ipfs_hash>', methods=['GET'])
def view_order_pdf(ipfs_hash):
    try:
        encrypted_data = ipfs_utils.get_from_ipfs(ipfs_hash)
        if not encrypted_data: return jsonify({"error": "Ficheiro não encontrado no IPFS."}), 404
        decryption_key_str = os.getenv('CONTRACT_DECRYPTION_KEY')
        if not decryption_key_str: return jsonify({"error": "Chave de descriptografia não configurada."}), 500
        decrypted_pdf_data = ipfs_utils.decrypt_data(encrypted_data, decryption_key_str.encode('utf-8'))
        if not decrypted_pdf_data: return jsonify({"error": "Falha ao descriptografar o PDF do pedido."}), 500
        return send_file(BytesIO(decrypted_pdf_data), mimetype='application/pdf', as_attachment=False)
    except Exception as e:
        return jsonify({"error": f"Erro interno: {e}"}), 500

@bp.route('/deliveries/list', methods=['GET'])
def list_deliveries():
    try:
        nomus_ok, nomus_data = nomus_api.get_nomus_deliveries(sales_order_id=3523)
        nomus_deliveries_processed = []
        if nomus_ok:
            for entrega in nomus_data:
                total_pecas = sum(int(item.get('qtde', 0)) for item in entrega.get('itensDocumentoEstoque', []))
                nomus_deliveries_processed.append({'dataEmissao': entrega.get('dataEmissao', 'N/A'), 'id': entrega.get('id', 'N/A'), 'totalPecas': total_pecas})
        
        blockchain_deliveries_list = blockchain_utils.get_all_items_from_stream('deliveries_stream')
        blockchain_map = {}
        for item in blockchain_deliveries_list:
            if isinstance(item, dict) and 'delivery_id' in item:
                 blockchain_map[str(item['delivery_id'])] = item

        merged_list = []
        for nomus_delivery in nomus_deliveries_processed:
            delivery_id = str(nomus_delivery.get('id'))
            blockchain_record = blockchain_map.get(delivery_id)
            nomus_delivery['has_blockchain_record'] = bool(blockchain_record)
            nomus_delivery['ipfs_hash_encrypted'] = blockchain_record.get('ipfs_hash_encrypted') if blockchain_record else None
            merged_list.append(nomus_delivery)

        def get_sort_key(e):
            try: return int(e.get('id', 0))
            except (ValueError, TypeError): return float('inf')
        sorted_list = sorted(merged_list, key=get_sort_key)
        
        return jsonify(sorted_list)
    except Exception as e:
        return jsonify({"success": False, "message": "Erro ao obter a lista de entregas."}), 500

@bp.route('/deliveries/view/<ipfs_hash>', methods=['GET'])
def view_delivery_pdf(ipfs_hash):
    try:
        encrypted_data = ipfs_utils.get_from_ipfs(ipfs_hash)
        if not encrypted_data: return jsonify({"error": "Ficheiro não encontrado no IPFS."}), 404
        decryption_key_str = os.getenv('DELIVERIES_DECRYPTION_KEY')
        if not decryption_key_str: return jsonify({"error": "Chave de desencriptação de entregas não configurada."}), 500
        decrypted_pdf_data = ipfs_utils.decrypt_data(encrypted_data, decryption_key_str.encode('utf-8'))
        if not decrypted_pdf_data: return jsonify({"error": "Falha ao descriptografar o PDF."}), 500
        return send_file(BytesIO(decrypted_pdf_data), mimetype='application/pdf', as_attachment=False)
    except Exception as e:
        return jsonify({"error": f"Erro interno: {e}"}), 500
    
@bp.route('/notifications/list', methods=['GET'])
def list_notifications():
    try:
        all_notes = blockchain_utils.get_all_items_from_stream('notes_stream')
        valid_notes = [note.get('data') for note in all_notes if isinstance(note.get('data'), dict)]
        return jsonify(valid_notes)
    except Exception as e:
        return jsonify({"success": False, "message": "Erro ao obter notificações."}), 500
    
    # ==============================================================================
# --- ROTA CONSOLIDADA DE NOTAS ---
# ==============================================================================
@bp.route('/notifications/consolidated', methods=['GET'])
def get_consolidated_notes():
    """
    Rota que consolida todos os alertas do sistema (pedidos, entregas, financeiro)
    em uma unica lista para a pagina de alertas do financeiro.
    """
    print("\n--- DEBUG [ALERTS]: Iniciando consolidacao de alertas ---")
    consolidated_alerts = []
    
    # 1. Obter alertas da notes_stream (aprovacoes/recusas de pedidos)
    try:
        notes = blockchain_utils.get_all_items_from_stream('notes_stream')
        for note in notes:
            note_data = note.get('data', {})
            if note_data.get('Tipo da notificacao') in ["Pedido Aprovado", "Pedido Recusado"]:
                alert = {
                    "tipo": note_data.get('Tipo da notificacao'),
                    "data_hora": note_data.get('reviewed_at_utc'),
                    "informacoes": note_data.get('Texto')
                }
                consolidated_alerts.append(alert)
        print(f"--- DEBUG [ALERTS]: {len(notes)} alertas da notes_stream processados.")
    except Exception as e:
        return jsonify({"success": False, "message": f"Erro ao buscar notificacoes da stream: {e}"}), 500

    # 2. Obter status de entregas da API Nomus e da blockchain
    try:
        deliveries_list_response = list_deliveries()
        if isinstance(deliveries_list_response, tuple):
            if deliveries_list_response[1] != 200:
                raise Exception("Erro ao buscar a lista de entregas.")
            deliveries_list = deliveries_list_response[0].json
        else:
            deliveries_list = deliveries_list_response.json
        
        for delivery in deliveries_list:
            if not delivery.get('has_blockchain_record'):
                alert = {
                    "tipo": "Novo Romaneio encontrado",
                    "data_hora": delivery.get('dataEmissao'),
                    "informacoes": f"O romaneio {delivery.get('id')} foi encontrado na Nomus e aguarda confirmacao."
                }
                consolidated_alerts.append(alert)
        print(f"--- DEBUG [ALERTS]: {len(deliveries_list)} romaneios processados.")
    except Exception as e:
        return jsonify({"success": False, "message": f"Erro ao buscar entregas da Nomus: {e}"}), 500
    
    # 3. Obter status financeiro (inadimplencia)
    print(f"--- DEBUG [ALERTS]: Verificando status financeiro...")
    try:
        financial_installments_stream = blockchain_utils.get_all_items_from_stream('financial_stream')
        
        for inst in financial_installments_stream:
            if isinstance(inst, dict) and not inst.get('paid'):
                success, nomus_data = nomus_api.get_nomus_contas_receber(inst.get('id_nomus'))
                
                if success and nomus_data:
                    if nomus_data.get('status'):
                        update_data = {"paid": True}
                        blockchain_utils.publish_to_blockchain('financial_stream', inst.get('key'), update_data)
                        print(f"--- DEBUG [ALERTS]: Parcela {inst.get('id_nomus')} atualizada na blockchain (paga).")
                    else:
                        due_date_str = inst.get('due_date')
                        if due_date_str:
                            due_date = datetime.datetime.strptime(nomus_data.get('dataVencimento'), "%d/%m/%Y").date()
                            if due_date < datetime.date.today():
                                alert = {
                                    "tipo": "Parcela inadimplente",
                                    "data_hora": due_date.isoformat(),
                                    "informacoes": f"A parcela {inst.get('id_nomus')} esta em atraso desde {nomus_data.get('dataVencimento')}."
                                }
                                consolidated_alerts.append(alert)
                else:
                    print(f"--- DEBUG [ALERTS]: Falha ao consultar a API Nomus para a parcela {inst.get('id_nomus')}.")

        print(f"--- DEBUG [ALERTS]: {len(financial_installments_stream)} parcelas financeiras processadas.")
    except Exception as e:
        return jsonify({"success": False, "message": f"Erro ao buscar dados financeiros da stream: {e}"}), 500

    sorted_alerts = sorted(
        consolidated_alerts,
        key=lambda x: x.get('data_hora') or '0000-01-01', 
        reverse=True
    )

    print(f"--- DEBUG [ALERTS]: Consolidacao finalizada com {len(sorted_alerts)} alertas.")
    return jsonify(sorted_alerts)
# ==============================================================================
# --- ROTAS DE GESTAO DE ENTREGAS ---
# ==============================================================================



@bp.route('/deliveries/pending-approval', methods=['GET'])
def list_pending_deliveries():
    """
    Busca todas as entregas que foram confirmadas pelo entregador (tem registo na
    blockchain), mas que ainda nao foram aprovadas pelo financeiro.
    """
    print("\n--- DEBUG [DELIVERIES]: Rota /api/deliveries/pending-approval acionada ---")
    try:
        # 1. Buscar todos os romaneios da Nomus
        nomus_ok, nomus_data = nomus_api.get_nomus_deliveries(sales_order_id=3523)
        if not nomus_ok:
            raise Exception("Falha ao buscar entregas na Nomus.")
        
        print(f"--- DEBUG [DELIVERIES]: Recebido da Nomus: {len(nomus_data)} itens.")
        
        # 2. Buscar o estado mais recente de todos os romaneios da blockchain
        blockchain_deliveries_list = blockchain_utils.get_all_items_from_stream('deliveries_stream')
        blockchain_map = {item.get('delivery_id'): item for item in blockchain_deliveries_list if isinstance(item, dict)}
        
     
        if nomus_data:
            print(f"--- DEBUG [DELIVERIES]: Tipo de ID da Nomus: {type(nomus_data[0]['id']) if 'id' in nomus_data[0] else 'N/A'}")
        if blockchain_map:
            print(f"--- DEBUG [DELIVERIES]: Tipo de ID da Blockchain: {type(list(blockchain_map.keys())[0]) if blockchain_map else 'N/A'}")
       

        pending_deliveries = []
        # 3. Iterar sobre os dados da Nomus e unificar/filtrar
        for nomus_delivery in nomus_data:
            delivery_id = nomus_delivery.get('id')
            # CORRECAO: Converter o ID do romaneio da Nomus para string antes de usar como chave.
            blockchain_record = blockchain_map.get(str(delivery_id))
            
            print(f"--- DEBUG [DELIVERIES]: Processando romaneio Nomus {delivery_id}. Registro na blockchain? {'Sim' if blockchain_record else 'Nao'}")
            
            if blockchain_record:
                status_blockchain = blockchain_record.get('status')
                print(f"--- DEBUG [DELIVERIES]: Status do romaneio {delivery_id} na blockchain: '{status_blockchain}'")
                
                if status_blockchain == 'Confirmado':
                    # Romaneio ja confirmado, deve ser ignorado na lista de pendentes
                    continue
                elif status_blockchain == 'Aguardando aprovacao':
                    # Romaneio que ja tem prova de entrega, mas nao foi aprovado
                    nomus_delivery.update(blockchain_record)
                    pending_deliveries.append(nomus_delivery)
            else:
                # Romaneio que so existe na Nomus, sem prova de entrega
                print(f"--- DEBUG [DELIVERIES]: Romaneio {delivery_id} na Nomus nao encontrado na blockchain. Status: 'Aguardando envio'")
                nomus_delivery['status'] = 'Aguardando envio'
                nomus_delivery['key'] = str(delivery_id) 
                pending_deliveries.append(nomus_delivery)

        # DEBUG: Adicionando a logica de validacao solicitada
        if len(blockchain_deliveries_list) > 0 and len(pending_deliveries) == len(nomus_data):
            print("--- ERRO CRITICO: A logica de filtragem falhou. O numero de pendentes nao deve ser igual ao numero total da Nomus se a stream nao estiver vazia. ---")

        # DEBUG: Adicionando print para mostrar a lista final
        print(f"--- DEBUG [DELIVERIES]: {len(pending_deliveries)} entregas pendentes de aprovacao encontradas. Lista final: {pending_deliveries}")

        # 4. Retornar a lista filtrada para o frontend
        return jsonify(pending_deliveries), 200
        
    except Exception as e:
        print(f"--- DEBUG [DELIVERIES]: ERRO ao listar entregas pendentes: {e}")
        return jsonify({"success": False, "message": "Erro ao obter a lista de entregas pendentes."}), 500

@bp.route('/delivery/approve', methods=['POST'])
def approve_delivery():
    """
    Recebe a decisao do financeiro sobre uma entrega e atualiza o seu status
    na blockchain para 'Confirmado'.
    """
    print("\n--- DEBUG [DELIVERIES]: Rota /api/delivery/approve acionada ---")
    data = request.get_json()
    delivery_key = data.get('delivery_key') 
    reviewer_name = data.get('reviewer_name')

    if not all([delivery_key, reviewer_name]):
        print(f"--- DEBUG [DELIVERIES]: ERRO - Dados incompletos: {data}")
        return jsonify({"success": False, "message": "Dados incompletos para aprovacao."}), 400

    try:
        update_data = {
            "status": "Confirmado",
            "approved_by": reviewer_name,
            "approved_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        
        print(f"--- DEBUG [DELIVERIES]: A publicar atualizacao para a chave '{delivery_key}' com os dados: {update_data}")
        txid = blockchain_utils.publish_to_blockchain('deliveries_stream', delivery_key, update_data)

        if not txid:
            print(f"--- DEBUG [DELIVERIES]: ERRO - Falha ao publicar na blockchain.")
            raise Exception("Falha ao registar a aprovacao na blockchain.")

        print(f"--- DEBUG [DELIVERIES]: Entrega aprovada com sucesso. TXID da atualizacao: {txid}")
        return jsonify({"success": True, "message": "Entrega confirmada com sucesso!"}), 200

    except Exception as e:
        print(f"--- DEBUG [DELIVERIES]: ERRO no processo de aprovacao: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
    


# ==============================================================================
# --- ROTAS DE GESTAO DE ENTREGAS ---
# ==============================================================================
@bp.route('/deliveries/entregador', methods=['GET'])
def list_deliveries_entregador():
    """
    Busca romaneios que aguardam envio (existem na Nomus mas nao na blockchain)
    e os retorna para o entregador.
    """
    print("\n--- DEBUG [DELIVERIES]: Rota /api/deliveries/entregador acionada ---")
    try:
        # 1. Buscar todos os romaneios da Nomus
        nomus_ok, nomus_data = nomus_api.get_nomus_deliveries(sales_order_id=3523)
        if not nomus_ok:
            raise Exception("Falha ao buscar entregas na Nomus.")
        
        # 2. Buscar o estado mais recente de todos os romaneios da blockchain
        blockchain_deliveries_list = blockchain_utils.get_all_items_from_stream('deliveries_stream')
        blockchain_map = {item.get('key'): item for item in blockchain_deliveries_list if isinstance(item, dict)}

        pending_deliveries = []
        for nomus_delivery in nomus_data:
            delivery_id = nomus_delivery.get('id')
            blockchain_record = blockchain_map.get(str(delivery_id))

            # Filtra os romaneios que o entregador precisa ver:
            # Apenas os que não existem na blockchain (status: "Aguardando envio").
            if not blockchain_record:
                nomus_delivery['status'] = 'Aguardando envio'
                nomus_delivery['key'] = str(delivery_id)
                pending_deliveries.append(nomus_delivery)
        
        print(f"--- DEBUG [DELIVERIES]: {len(pending_deliveries)} entregas para o entregador encontradas.")
        return jsonify(pending_deliveries), 200

    except Exception as e:
        print(f"--- DEBUG [DELIVERIES]: ERRO ao listar entregas para o entregador: {e}")
        return jsonify({"success": False, "message": "Erro ao obter a lista de entregas para o entregador."}), 500

@bp.route('/delivery/submit', methods=['POST'])
def submit_delivery_proof():
    """
    Recebe a prova de entrega (PDF ou imagem com assinatura) e a submete a blockchain.
    """
    print("\n--- DEBUG [DELIVERIES]: Rota /api/delivery/submit acionada ---")
    delivery_key = request.form.get('delivery_key')
    proof_file = request.files.get('proof_file')
    signature_image_b64 = request.form.get('signature_image')
    
    if not all([delivery_key, proof_file]):
        return jsonify({"success": False, "message": "Dados incompletos para a submissao da prova de entrega."}), 400

    try:
        # A logica de processamento do arquivo e da assinatura sera implementada aqui
        # Por enquanto, apenas um placeholder para o fluxo

        # Simula o upload para o IPFS e obtém um hash
        ipfs_hash = "QmSimulatedIpfsHash" 

        update_data = {
            "status": "Aguardando aprovacao",
            "confirmed_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "ipfs_hash_encrypted": ipfs_hash,
        }
        
        print(f"--- DEBUG [DELIVERIES]: A publicar prova de entrega para a chave '{delivery_key}' com os dados: {update_data}")
        txid = blockchain_utils.publish_to_blockchain('deliveries_stream', delivery_key, update_data)

        if not txid:
            print(f"--- DEBUG [DELIVERIES]: ERRO - Falha ao publicar na blockchain.")
            raise Exception("Falha ao registar a aprovacao na blockchain.")

        print(f"--- DEBUG [DELIVERIES]: Prova de entrega submetida com sucesso. TXID: {txid}")
        return jsonify({"success": True, "message": "Prova de entrega submetida com sucesso!", "txid": txid}), 200

        if not delivery_key or delivery_key.lower() == "null":
            return jsonify({"success": False, "message": "Chave de entrega inválida."}), 400

    except Exception as e:
        print(f"--- DEBUG [DELIVERIES]: ERRO no processo de submissao da prova: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


# ==============================================================================
# NOVA ROTA: SUBMISSAO DE PEDIDO PARA POSTGRESQL
# ==============================================================================
@bp.route('/order/submit-postgres', methods=['POST'])
def submit_order_postgres():
    """
    Processa um pedido e insere os dados em um banco de dados PostgreSQL.
    Esta rota serve como baseline para o benchmark de desempenho.
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Dados do pedido não recebidos."}), 400
    
    order_items, signature_image_b64, client_info = data.get('order_items'), data.get('signature_image'), data.get('client_info')
    
    if not all([order_items, signature_image_b64, client_info]):
        return jsonify({"success": False, "message": "Dados do pedido incompletos."}), 400

    try:
       
        signature_image_bytes = base64.b64decode(signature_image_b64.split(',')[1])
        pdf_bytes = generate_order_pdf(client_info, order_items, signature_image_bytes)
        decryption_key = os.getenv('CONTRACT_DECRYPTION_KEY')
        if not decryption_key:
            raise Exception("Chave de descriptografia do contrato não configurada.")
        
       
        encrypted_pdf_bytes = ipfs_utils.encrypt_data(pdf_bytes, decryption_key.encode('utf-8'))

       
        order_hash = hashlib.sha256(encrypted_pdf_bytes).hexdigest()
        
        # Insercao no PostgreSQL
        from .utils.database_utils import insert_order
        success = insert_order(client_info, order_hash, encrypted_pdf_bytes, order_items)
        if not success:
           raise Exception("Falha ao inserir o pedido no PostgreSQL.")
        
        return jsonify({
            "success": True,
            "message": "Pedido submetido com sucesso ao PostgreSQL!",
            "order_hash": order_hash
        }), 200

    except Exception as e:
        print(f"ERRO: Falha ao submeter pedido ao PostgreSQL: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
