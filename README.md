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

git clone [https://github.com/samuelilva/contract_management_api]
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

Blockchain Contract Management and Authentication System
This project is a system designed for managing and authenticating digital transactions in a B2B (Business-to-Business) environment. The solution uses a private, permissioned blockchain to record agreements, ensure the immutability of transactions, and allow for detailed audits, thereby increasing security and transparency in business processes.

This application was developed as part of my Final Year Project for a Computer Science degree, focusing on the practical application of distributed technologies in corporate settings by integrating with existing Enterprise Resource Planning (ERP) systems.

Technologies Used
Backend: Python, Flask

Blockchain: MultiChain

Decentralized Storage: IPFS (InterPlanetary File System)

Integration: Nomus ERP REST API

Containerization: Docker

Frontend: HTML, CSS, JavaScript

Architecture
The system is built on a microservices architecture to ensure scalability and maintainability:

Authentication Server: Manages access, user profiles (Client, Finance, Deliverer), and the issuance of session tokens.

Request Server: Serves the user interface (frontend) and acts as a secure proxy for operations.

Integration Server: Centralizes the business logic, including communication with the ERP's API, and interactions with the blockchain (MultiChain) and file storage (IPFS).

How to Run
To run this project locally, follow the steps below:

Clone the repository:

git clone [https://github.com/samuelilva/contract_management_api]
cd your-repository

Create and activate a virtual environment:

python -m venv venv
# Windows
.\venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

Install the dependencies:

pip install -r requirements.txt

Configure environment variables:

Rename the .env.example file to .env.

Fill in the variables with your own keys and credentials for the Nomus API and MultiChain.

Start the services with Docker:

Make sure you have Docker and Docker Compose installed.

Run the command below to start the blockchain and IPFS containers:

docker-compose up -d

Run the Flask application:

flask run

The application will be available at http://127.0.0.1:5000.

Contact
Samuel da Silva

LinkedIn: [your-linkedin]

GitHub: [your-github]

Email: [your-email]

LinkedIn: [https://l1nk.dev/BGbg7]

GitHub: [https://github.com/samuelilva/]

Email: [samuelilva@msn.com]
