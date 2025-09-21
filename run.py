# ==============================================================================
# ARQUIVO: run.py
# DESCRIÇÃO: Ponto de entrada principal da aplicação Flask.
# v1
# ==============================================================================
from app import create_app
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
# É crucial que isso seja feito antes da criação do app
load_dotenv()

# Cria a aplicação Flask usando a factory
app = create_app()

if __name__ == '__main__':
    # Inicia o servidor de desenvolvimento do Flask
    # O debug=True é útil para desenvolvimento, mas deve ser False em produção

    app.config['DEBUG'] = True
    app.config['PROPAGATE_EXCEPTIONS'] = True

    app.run(debug=True, port=5000)