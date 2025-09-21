# ==============================================================================
# ARQUIVO: app/auth_server/routes.py
# DESCRIÇÃO: Rotas para autenticação, com lógica de sessão corrigida
#              e debug prints para análise de falhas de login.
# VERSÃO: 5.1 (Debug)
# ==============================================================================

# --- 1. IMPORTAÇÕES ---
import json
import hashlib
import datetime
import requests
import os 
from flask import render_template, request, session, redirect, url_for, flash
from . import bp

# --- 2. FUNÇÕES AUXILIARES ---
def load_users():
    """
    Carrega os dados dos utilizadores a partir do ficheiro users.json.
    """
    try:
        # É uma boa prática usar um caminho absoluto para garantir que o ficheiro é sempre encontrado
        # Assumindo que users.json está na raiz do projeto, um nível acima de 'app'
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        users_path = os.path.join(base_dir, 'users.json')
        with open(users_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

# --- 3. ROTAS DA APLICAÇÃO ---
@bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Lida com o processo de login do utilizador, validando credenciais e
    populando a sessão com os dados corretos para cada perfil.
    """
    if request.method == 'POST':
        login = request.form.get('login')
        representante = request.form.get('representante')
        senha = request.form.get('senha')
        client_ip = request.remote_addr

        users = load_users()
    
        senha_hash_digitada = hashlib.sha256(senha.encode('utf-8')).hexdigest()
        
        # Primeiro, tenta encontrar o utilizador pelo login e representante
        user_data = next((user for user in users if user['login'] == login and user['representante'] == representante), None)

        # Verifica se o utilizador não foi encontrado ou se a senha está incorreta
        if not user_data or user_data['senha_hash'] != senha_hash_digitada:
            # --- INÍCIO DO DEBUG PRINT ---
            print("\n--- FALHA NO LOGIN ---")
            print("DADOS DIGITADOS:")
            print(f"  - Login: '{login}'")
            print(f"  - Representante: '{representante}'")
            print(f"  - Senha: '{senha}'")
            print(f"  - Hash Gerado: {senha_hash_digitada}")
            print("-" * 20)
            if user_data:
                # O utilizador foi encontrado, mas a senha estava errada
                print("DADOS ESPERADOS (Utilizador Encontrado):")
                print(f"  - Login: '{user_data['login']}'")
                print(f"  - Representante: '{user_data['representante']}'")
                print(f"  - Hash no Ficheiro: {user_data['senha_hash']}")
            else:
                # O utilizador nem sequer foi encontrado com a combinação login/representante
                print("DADOS ESPERADOS: Nenhum utilizador encontrado com o login e representante fornecidos.")
            print("----------------------\n")
            # --- FIM DO DEBUG ---
            
            flash('Login, identificador ou senha inválidos.', 'danger')
            return redirect(url_for('auth.login'))

        # Se chegou até aqui, o login foi bem-sucedido
        details = {}
        try:
            payload = {'client_id': user_data.get('nomus_client_id')}
            
            if user_data['role'] == 'cliente':
                payload['rep_id'] = user_data.get('nomus_rep_id')
            
            api_response = requests.post("http://127.0.0.1:5000/api/person-details", json=payload, timeout=10)
            api_response.raise_for_status()
            details = api_response.json()

            if user_data['role'] != 'cliente':
                details['rep_name'] = user_data.get('representante')

        except requests.exceptions.RequestException as e:
            print(f"ERRO ao chamar a API de integração: {e}")
            details = {"client_name": "N/A", "client_cnpj": "N/A", "rep_name": "N/A"}
            flash("Aviso: Não foi possível carregar os detalhes do cliente/representante.", "warning")

        session.clear()
        session['user_id'] = user_data['login']
        session['user_role'] = user_data['role']
        session['user_ip'] = client_ip
        session['cliente_nome'] = details.get('client_name', 'Nome não encontrado')
        session['cliente_cnpj'] = details.get('client_cnpj', 'CNPJ não encontrado')
        session['representative_name'] = details.get('rep_name', 'N/A')
        session['senha_contract_hash'] = user_data.get('senha_contract_hash')
        session['login_time'] = datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        
        flash('Login realizado com sucesso!', 'success')
        return redirect(url_for('request.home'))

    return render_template('login.html')

@bp.route('/logout')
def logout():
    """Limpa a sessão do utilizador."""
    session.clear()
    flash('Você saiu da sua conta.', 'info')
    return redirect(url_for('auth.login'))
