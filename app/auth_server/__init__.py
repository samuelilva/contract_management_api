# ==============================================================================
# ARQUIVO: app/auth_server/__init__.py
# DESCRIÇÃO: Inicializa o blueprint do servidor de autenticação.
# v1
# ==============================================================================
from flask import Blueprint

# Cria uma instância do Blueprint.
# O primeiro argumento é o nome do blueprint.
# O segundo é o nome do módulo/pacote, para que o Flask saiba onde encontrar templates.
# url_prefix adiciona '/auth' ao início de todas as rotas deste blueprint.
bp = Blueprint('auth', __name__, url_prefix='/auth', template_folder='templates')

# Importa as rotas no final para evitar dependências circulares.
from . import routes