# ==============================================================================
# ARQUIVO: app/request_server/__init__.py
# DESCRIÇÃO: Inicializa o blueprint do servidor de requisições (front-end).
# v1
# ==============================================================================
from flask import Blueprint

# Cria o Blueprint para o servidor de requisições.
# Este blueprint não tem um prefixo de URL, pois ele servirá as rotas principais
# como /home, /dashboard, /orders, etc.
bp = Blueprint('request', __name__, template_folder='templates')

# Importa as rotas no final para evitar dependências circulares.
from . import routes