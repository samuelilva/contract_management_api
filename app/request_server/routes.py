# ==============================================================================
# ARQUIVO: app/request_server/routes.py
# DESCRICAO: Rotas para servir as paginas HTML (frontend) e atuar como um
#              proxy seguro para a API do integration_server (backend).
# VERSAO: 13.0 (Adicionadas rotas do entregador)
# ==============================================================================

# --- 1. IMPORTAÇÕES ---
import hashlib
import requests
from functools import wraps
from flask import (
    Blueprint, render_template, session, redirect, url_for, flash, abort, Response,
    request, jsonify
)
from . import bp

# --- 2. DECORATORS DE CONTROLO DE ACESSO ---

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Você precisa de estar logado para aceder a esta página.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if session.get('user_role') not in allowed_roles:
                abort(403, "Você não tem permissão para aceder a esta página.")
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --- 3. ROTAS DE PÁGINAS E REDIRECIONAMENTO ---

@bp.route('/home')
@login_required
def home():
    role = session.get('user_role')
    if role == 'cliente':
        return redirect(url_for('request.dashboard_cliente'))
    elif role == 'entregador':
        return redirect(url_for('request.dashboard_entregador'))
    elif role == 'financeiro':
        return redirect(url_for('request.dashboard_financeiro'))
    else:
        flash('Perfil de utilizador desconhecido.', 'danger')
        return redirect(url_for('auth.logout'))

# --- 3.1 Dashboards por Perfil ---

@bp.route('/dashboard/cliente')
@login_required
@role_required(['cliente'])
def dashboard_cliente():
    notifications = []
    try:
        api_url = "http://127.0.0.1:5000/api/notifications/list"
        response = requests.get(api_url, timeout=10)
        if response.ok:
            all_notes_raw = response.json()
            # --- CORREÇÃO APLICADA AQUI ---
            # A stream pode conter listas vazias. O código agora verifica se o item
            # é um dicionário antes de tentar aceder aos seus valores.
            notifications = [
                note for note in all_notes_raw 
                if isinstance(note, dict) and note.get('target_role') == 'cliente'
            ]
        else:
            flash("Não foi possível carregar as notificações do sistema.", "warning")
    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar notificações para o dashboard: {e}")
        flash("Serviço de notificações indisponível no momento.", "danger")
    
    return render_template('dashboard_cliente.html', notifications=notifications)


@bp.route('/dashboard/entregador')
@login_required
@role_required(['entregador'])
def dashboard_entregador():
    return render_template('dashboard_entregador.html')

@bp.route('/dashboard/financeiro')
@login_required
@role_required(['financeiro'])
def dashboard_financeiro():
    return render_template('dashboard_financeiro.html')

# --- 3.2 Páginas Funcionais ---

@bp.route('/orders/new')
@login_required
@role_required(['cliente'])
def new_order_page():
    return render_template('new_orders.html')

@bp.route('/orders/finished')
@login_required
@role_required(['cliente', 'financeiro'])
def finished_orders_page():
    return render_template('finished_orders.html')

@bp.route('/contract')
@login_required
@role_required(['cliente'])
def contract_info_page():
    return render_template('contract_info.html')

@bp.route('/deliveries')
@login_required
@role_required(['entregador'])
def deliveries_page():
    return render_template('deliveries.html')

@bp.route('/confirmation')
@login_required
@role_required(['financeiro'])
def confirmation_page():
    return render_template('confirmation.html')

@bp.route('/orders/requests')
@login_required
@role_required(['financeiro'])
def new_orders_requests_page():
    return render_template('new_orders_requests.html')

@bp.route('/warnings')
@login_required
@role_required(['financeiro'])
def client_warnings_page():
    return render_template('client_warnings.html')

# --- 4. ROTAS DE PROXY PARA A API INTERNA ---

@bp.route('/api-proxy/contract/status')
@login_required
def proxy_contract_status():
    api_url = "http://127.0.0.1:5000/api/contract/status"
    try:
        response = requests.get(api_url, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Não foi possível obter os dados do contrato."}), 502

@bp.route('/api-proxy/secure/contract/view', methods=['POST'])
@login_required
@role_required(['cliente'])
def proxy_secure_view_contract():
    data = request.get_json()
    password = data.get('password')
    if not password:
        return jsonify({"success": False, "message": "Senha não fornecida."}), 400

    correct_hash = session.get('senha_contract_hash')
    if not correct_hash:
        return jsonify({"success": False, "message": "Utilizador não tem permissão para ver o contrato."}), 403

    provided_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    if provided_hash != correct_hash:
        return jsonify({"success": False, "message": "Senha incorreta."}), 401

    api_url = "http://127.0.0.1:5000/api/contract/view"
    try:
        response = requests.get(api_url, stream=True, timeout=20)
        response.raise_for_status()
        return Response(response.iter_content(chunk_size=1024), content_type=response.headers['Content-Type'])
    except requests.exceptions.RequestException as e:
        abort(502)

@bp.route('/api-proxy/order/submit', methods=['POST'])
@login_required
@role_required(['cliente'])
def proxy_submit_order():
    api_url = "http://127.0.0.1:5000/api/order/submit"


    #DEBUG PRINTS
    print("=== PROXY DEBUG - INÍCIO ===")
    print("HEADERS RECEBIDOS NO PROXY:")
    for k, v in request.headers.items():
        print(f"  {k}: {v}")
    print("RAW DATA RECEBIDA (request.data):")
    print(request.data[:500])  # limitar a 500 bytes para não poluir o log
    try:
        # Aqui já força o Flask a tentar parsear JSON
        data = request.get_json(force=True, silent=False)
        print("JSON PARSEADO COM SUCESSO NO PROXY:")
        print(data)
    except Exception as e:
        print(" ERRO AO PARSEAR JSON NO PROXY:", e)
        data = None

    print("=== PROXY DEBUG - FIM ===")
    #FIM DEBUG PRINTS

    try:
       #TESTE DE DEBUG LINHA ORIGINAL ABAIXO
       # response = requests.post(api_url, json=request.get_json(), timeout=30, stream=True)
        response = requests.post(api_url, json=request.get_json(), timeout=30, stream=True,  headers={"Content-Type": "application/json"})
        response.raise_for_status()
        final_headers = {k: v for k, v in response.headers.items() if k.lower() in ['content-type', 'content-disposition']}
        final_headers['Access-Control-Expose-Headers'] = 'Content-Disposition'
        return Response(response.iter_content(chunk_size=1024), headers=final_headers)
    except requests.exceptions.RequestException as e:
        error_message = f"Erro no proxy de submissão: {e}"
        try:
            error_message = e.response.json().get("message", error_message)
        except (ValueError, AttributeError): pass
        return jsonify({"success": False, "message": error_message}), 502
    
@bp.route('/api-proxy/deliveries/list')
@login_required
@role_required(['cliente', 'financeiro'])
def proxy_list_deliveries():
    api_url = "http://127.0.0.1:5000/api/deliveries/list"
    try:
        response = requests.get(api_url, timeout=20)
        response.raise_for_status()
        return response.json(), response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"success": False, "message": "Não foi possível obter a lista de entregas."}), 502

@bp.route('/api-proxy/deliveries/view/<ipfs_hash>')
@login_required
@role_required(['cliente', 'financeiro'])
def proxy_view_delivery_pdf(ipfs_hash):
    api_url = f"http://127.0.0.1:5000/api/deliveries/view/{ipfs_hash}"
    try:
        response = requests.get(api_url, stream=True, timeout=20)
        response.raise_for_status()
        return Response(response.iter_content(chunk_size=1024), content_type=response.headers['Content-Type'])
    except requests.exceptions.RequestException as e:
        abort(502)

@bp.route('/api-proxy/orders/view/<ipfs_hash>')
@login_required
@role_required(['financeiro'])
def proxy_view_order_pdf(ipfs_hash):
    api_url = f"http://127.0.0.1:5000/api/orders/view/{ipfs_hash}"
    try:
        response = requests.get(api_url, stream=True, timeout=20)
        response.raise_for_status()
        return Response(response.iter_content(chunk_size=1024), content_type=response.headers.get('Content-Type'))
    except requests.exceptions.RequestException as e:
        abort(502)

# --- ROTAS DE PROXY PARA GESTÃO DE PEDIDOS PELO FINANCEIRO ---

@bp.route('/api-proxy/orders/list')
@login_required
@role_required(['financeiro'])
def proxy_list_orders():
    api_url = "http://127.0.0.1:5000/api/orders/list"
    try:
        response = requests.get(api_url, timeout=20)
        response.raise_for_status()
        return response.json(), response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"success": False, "message": "Não foi possível obter a lista de pedidos."}), 502

# ==============================================================================
# --- ROTA DE PROXY COM DEBUG PRINTS ---
# ==============================================================================
@bp.route('/api-proxy/order/review', methods=['POST'])
@login_required
@role_required(['financeiro'])
def proxy_review_order():
    print("\n--- DEBUG [PROXY]: Rota /api-proxy/order/review ACIONADA ---")
    
    api_url = "http://127.0.0.1:5000/api/order/review"
    payload = request.get_json()
    
    # Adiciona o nome do revisor da sessão ao payload
    reviewer = session.get('representative_name')
    print(f"DEBUG [PROXY]: Nome do representante na sessão: '{reviewer}'")
    
    # Lógica de segurança: Garante que há um nome de revisor.
    if not reviewer or reviewer == 'N/A':
        print("DEBUG [PROXY]: ERRO - Nome do representante não encontrado ou inválido na sessão.")
        # Define um nome padrão para evitar que a validação `all()` falhe,
        # mas idealmente o login deveria garantir este dado.
        payload['reviewer_name'] = 'Financeiro (Sessão Inválida)'
    else:
        payload['reviewer_name'] = reviewer
    
    print(f"DEBUG [PROXY]: A enviar para o Integration Server o seguinte payload: {payload}")
    
    try:
        response = requests.post(api_url, json=payload, timeout=20)
        print(f"DEBUG [PROXY]: Resposta recebida do Integration Server com status: {response.status_code}")
        response.raise_for_status()
        return response.json(), response.status_code
    except requests.exceptions.RequestException as e:
        print(f"DEBUG [PROXY]: ERRO na comunicação com o Integration Server: {e}")
        error_message = f"Erro de comunicação com o servidor de integração."
        try:
            error_json = e.response.json()
            error_message = error_json.get("message", error_message)
            print(f"DEBUG [PROXY]: Mensagem de erro do backend: {error_message}")
        except (ValueError, AttributeError, Exception):
             pass
        return jsonify({"success": False, "message": error_message}), 502
# ==============================================================================
# --- ROTA DE PROXY PARA ALERTAS CONSOLIDADOS ---
# ==============================================================================
@bp.route('/api-proxy/notifications/consolidated')
@login_required
@role_required(['financeiro'])
def proxy_get_consolidated_notifications():
    api_url = "http://127.0.0.1:5000/api/notifications/consolidated"
    try:
        response = requests.get(api_url, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return jsonify({"success": False, "message": "Não foi possível obter os alertas consolidados."}), 502
# ==============================================================================
# --- NOVAS ROTAS DE PROXY PARA APROVAÇÃO DE ENTREGAS (FASE 2) ---
# ==============================================================================

@bp.route('/api-proxy/deliveries/pending-approval')
@login_required
@role_required(['financeiro'])
def proxy_list_pending_deliveries():
    """Proxy para buscar entregas que aguardam aprovação do financeiro."""
    api_url = "http://127.0.0.1:5000/api/deliveries/pending-approval"
    print(f"\n--- DEBUG [PROXY]: Rota /api-proxy/deliveries/pending-approval acionada ---")
    try:
        response = requests.get(api_url, timeout=20)
        response.raise_for_status()
        print(f"--- DEBUG [PROXY]: Resposta do Integration Server: {response.status_code} ---")
        return response.json(), response.status_code
    except requests.exceptions.RequestException as e:
        print(f"--- DEBUG [PROXY]: ERRO na comunicação: {e} ---")
        return jsonify({"success": False, "message": "Não foi possível obter a lista de entregas pendentes."}), 502

@bp.route('/api-proxy/delivery/approve', methods=['POST'])
@login_required
@role_required(['financeiro'])
def proxy_approve_delivery():
    """Proxy para o financeiro aprovar uma entrega."""
    api_url = "http://127.0.0.1:5000/api/delivery/approve"
    payload = request.get_json()
    
    # Adiciona o nome do revisor da sessão por segurança
    payload['reviewer_name'] = session.get('representative_name', 'Financeiro Desconhecido')
    
    print(f"\n--- DEBUG [PROXY]: Rota /api-proxy/delivery/approve acionada com payload: {payload} ---")
    
    try:
        response = requests.post(api_url, json=payload, timeout=20)
        print(f"--- DEBUG [PROXY]: Resposta do Integration Server: {response.status_code} ---")
        response.raise_for_status()
        return response.json(), response.status_code
    except requests.exceptions.RequestException as e:
        print(f"--- DEBUG [PROXY]: ERRO na comunicação: {e} ---")
        error_message = "Erro de comunicação com o servidor de integração."
        try:
            error_message = e.response.json().get("message", error_message)
        except (ValueError, AttributeError, Exception):
             pass
        return jsonify({"success": False, "message": error_message}), 502

# ==============================================================================
# --- ROTAS DE PROXY PARA O ENTREGADOR ---
# ==============================================================================

@bp.route('/api-proxy/deliveries/entregador')
@login_required
@role_required(['entregador'])
def proxy_deliveries_entregador():
    api_url = "http://127.0.0.1:5000/api/deliveries/entregador"
    print(f"\n--- DEBUG [PROXY]: Rota /api-proxy/deliveries/entregador acionada ---")
    try:
        response = requests.get(api_url, timeout=20)
        response.raise_for_status()
        print(f"--- DEBUG [PROXY]: Resposta do Integration Server: {response.status_code} ---")
        return response.json(), response.status_code
    except requests.exceptions.RequestException as e:
        print(f"--- DEBUG [PROXY]: ERRO na comunicacao: {e} ---")
        return jsonify({"success": False, "message": "Nao foi possivel obter a lista de entregas para o entregador."}), 502

@bp.route('/api-proxy/delivery/submit', methods=['POST'])
@login_required
@role_required(['entregador'])
def proxy_submit_delivery_proof():
    api_url = "http://127.0.0.1:5000/api/delivery/submit"
    print(f"\n--- DEBUG [PROXY]: Rota /api-proxy/delivery/submit acionada ---")
    
    try:
        # A requisição de proxy precisa ser feita com o corpo completo da requisição original
        # A biblioteca 'requests' lida com 'multipart/form-data' de forma transparente
        files = request.files.to_dict()
        data = request.form.to_dict()

        response = requests.post(api_url, files=files, data=data, timeout=30)
        response.raise_for_status()
        print(f"--- DEBUG [PROXY]: Resposta do Integration Server: {response.status_code} ---")
        return response.json(), response.status_code
    except requests.exceptions.RequestException as e:
        print(f"--- DEBUG [PROXY]: ERRO na comunicacao: {e} ---")
        error_message = "Erro de comunicacao com o servidor de integracao."
        try:
            error_json = e.response.json()
            error_message = error_json.get("message", error_message)
            print(f"DEBUG [PROXY]: Mensagem de erro do backend: {error_message}")
        except (ValueError, AttributeError):
             pass
        return jsonify({"success": False, "message": error_message}), 502

@bp.route('/api-proxy/order/submit-postgres', methods=['POST'])
@login_required
@role_required(['cliente'])
def proxy_submit_order_postgres():
    api_url = "http://127.0.0.1:5000/api/order/submit-postgres"
    try:
        response = requests.post(api_url, json=request.get_json(), timeout=30, stream=True)
        response.raise_for_status()
        final_headers = {k: v for k, v in response.headers.items() if k.lower() in ['content-type', 'content-disposition']}
        final_headers['Access-Control-Expose-Headers'] = 'Content-Disposition'
        return Response(response.iter_content(chunk_size=1024), headers=final_headers)
    except requests.exceptions.RequestException as e:
        error_message = f"Erro no proxy de submissao: {e}"
        try:
            error_message = e.response.json().get("message", error_message)
        except (ValueError, AttributeError):
             pass
        return jsonify({"success": False, "message": error_message}), 502