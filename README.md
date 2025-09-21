Sistema de Gestão e Autenticação de Contratos com Blockchain
Este projeto é um sistema desenvolvido para a gestão e autenticação de transações digitais em um ambiente B2B (Business-to-Business). A solução utiliza uma blockchain permissionada e privada para registrar acordos, garantir a imutabilidade das transações e permitir auditorias detalhadas, aumentando a segurança e a transparência nos processos de negócio.

A aplicação foi criada como parte do meu Trabalho de Conclusão de Curso em Ciência da Computação, com foco na aplicabilidade prática de tecnologias distribuídas em cenários corporativos, integrando-se a sistemas de gestão (ERP) existentes.

Tecnologias Utilizadas
Backend: Python, Flask

Blockchain: MultiChain

Armazenamento Descentralizado: IPFS (InterPlanetary File System)

Integração: API REST do ERP Nomus

Containerização: Docker

Frontend: HTML, CSS, JavaScript

Arquitetura
O sistema é modularizado em uma arquitetura de microsserviços para garantir escalabilidade e manutenção:

Servidor de Autenticação: Gerencia o acesso, perfis de usuário (Cliente, Financeiro, Entregador) e a emissão de tokens de sessão.

Servidor de Requisições: Apresenta a interface do usuário (frontend) e atua como um proxy seguro para as operações.

Servidor de Integração: Centraliza a lógica de negócio, incluindo a comunicação com a API do ERP, e as interações com a blockchain (MultiChain) e o armazenamento de arquivos (IPFS).

Como Executar
Para executar este projeto localmente, siga os passos abaixo:

Clone o repositório:

git clone [https://github.com/seu-usuario/seu-repositorio.git]
cd seu-repositorio

Crie e ative um ambiente virtual:

python -m venv venv
# Windows
.\venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

Instale as dependências:

pip install -r requirements.txt

Configure as variáveis de ambiente:

Renomeie o arquivo .env.example para .env.

Preencha as variáveis com suas próprias chaves e credenciais para a API Nomus e o MultiChain.

Inicie os serviços com Docker:

Certifique-se de ter o Docker e o Docker Compose instalados.

Execute o comando abaixo para iniciar os contêineres da blockchain e do IPFS:

docker-compose up -d

Execute a aplicação Flask:

flask run

A aplicação estará disponível em http://127.0.0.1:5000.

Contato
Samuel da Silva

LinkedIn: [https://l1nk.dev/BGbg7]

GitHub: [https://github.com/samuelilva/]

Email: [samuelilva@msn.com]