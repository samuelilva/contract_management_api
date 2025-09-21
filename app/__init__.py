# ==============================================================================
# ARQUIVO: app/__init__.py
# DESCRIÇÃO: Factory da aplicação Flask, registra os blueprints dos servidores.
# v2 (Corrigido)
# ==============================================================================
from flask import Flask
import os

def create_app():
    """
    Cria e configura a instância da aplicação Flask.
    Esta função é conhecida como 'Application Factory'.
    """
    app = Flask(__name__, instance_relative_config=True, static_folder='../static')

    # Configurações da aplicação
    # A SECRET_KEY é usada pelo Flask para manter as sessões seguras.
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev_secret_key_change_this'),
    )

    # Garante que a pasta 'instance' exista
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # --- Registro dos Blueprints dos Servidores ---
    # CORREÇÃO: Importamos o módulo inteiro e depois registramos seu blueprint 'bp'.
    # Isso evita erros de importação e é uma prática padrão no Flask.
    
    # Servidor de Autenticação
    from . import auth_server
    app.register_blueprint(auth_server.bp)

    # Servidor de Requisições (Interface do Usuário)
    from . import request_server
    app.register_blueprint(request_server.bp)
    
    # Servidor de Integração (Lógica de Negócio e APIs)
    from . import integration_server
    app.register_blueprint(integration_server.bp)


    @app.route('/')
    def index():
        # Redireciona a rota raiz para a página de login
        from flask import redirect, url_for
        return redirect(url_for('auth.login'))

    return app