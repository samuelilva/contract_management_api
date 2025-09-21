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

LinkedIn: [https://l1nk.dev/BGbg7]

GitHub: [https://github.com/samuelilva/]

Email: [samuelilva@msn.com]
