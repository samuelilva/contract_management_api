# ==============================================================================
# ARQUIVO: app/integration_server/__init__.py
# DESCRIÇÃO: Inicializa o blueprint do servidor de integração.
# v1
# ==============================================================================
from flask import Blueprint

# Cria o Blueprint para o servidor de integração.
# Todas as rotas definidas neste servidor terão o prefixo '/api'.
# Isso o estabelece como o ponto de entrada para toda a lógica de back-end.
bp = Blueprint('integration', __name__, url_prefix='/api')

# Importa as rotas no final para evitar dependências circulares.
from . import routes