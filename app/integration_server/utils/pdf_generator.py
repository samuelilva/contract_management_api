# ==============================================================================
# ARQUIVO: app/integration_server/utils/pdf_generator.py
# DESCRIÇÃO: Módulo auxiliar responsável pela geração de ficheiros PDF para os
#              pedidos de produtos, incluindo cabeçalho, rodapé e assinatura.
# VERSÃO: 8.0
# ==============================================================================

# --- 1. IMPORTAÇÕES ---
import os
import tempfile
import datetime
from fpdf import FPDF
from io import BytesIO

# --- 2. CONSTANTES E CONFIGURAÇÕES DE CAMINHO ---
# Constrói o caminho absoluto para a pasta 'static'.
# Isto garante que o script consegue encontrar a imagem do logo, independentemente
# de onde o script principal (run.py) é executado.
STATIC_FOLDER_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'static'))
LOGO_PATH = os.path.join(STATIC_FOLDER_PATH, 'img', 'logo.png')

# --- 3. CLASSE PDF PERSONALIZADA ---
class PDF(FPDF):
    """
    Classe personalizada que herda de FPDF para definir um cabeçalho e um rodapé
    padrão para todos os PDFs gerados pela aplicação.
    """
    def header(self):
        """
        Define o cabeçalho do PDF, que inclui o logo da empresa e informações de contacto.
        Este método é chamado automaticamente pela biblioteca FPDF ao criar uma nova página.
        """
        # Adiciona a imagem do logo ao canto superior direito do PDF, se o ficheiro existir.
        if os.path.exists(LOGO_PATH):
            self.image(LOGO_PATH, 170, 5, 25)
        
        # Define a fonte e escreve as informações da empresa.
        self.set_font('Arial', 'B', 12)
        self.cell(0, 8, 'Maximiano Uniforme e Confecções', 0, 1, 'L')
        self.set_font('Arial', '', 8)
        self.cell(0, 4, 'CNPJ: 35.683.304/0001-85', 0, 1, 'L')
        self.cell(0, 4, 'Contato: (31) 9073-7995 | contratos@maximianoconfeccao.com.br', 0, 1, 'L')
        
        # Adiciona uma linha horizontal para separar o cabeçalho do conteúdo.
        self.ln(5)
        self.line(self.get_x(), self.get_y(), self.get_x() + 180, self.get_y())
        self.ln(10)

    def footer(self):
        """
        Define o rodapé do PDF, que inclui um aviso legal.
        Este método é chamado automaticamente pela biblioteca FPDF.
        """
        # Posiciona o cursor a 2.5 cm do fundo da página.
        self.set_y(-25)
        self.line(self.get_x(), self.get_y(), self.get_x() + 180, self.get_y())
        self.set_font('Arial', 'I', 8)
        self.ln(5)
        # Adiciona o texto do aviso, centralizado.
        self.multi_cell(0, 4, 'Este documento é uma solicitação de pedido e não representa uma confirmação de faturamento. O pedido será confirmado pelo setor comercial após análise de estoque e condições comerciais.', 0, 'C')

# --- 4. FUNÇÃO PRINCIPAL DE GERAÇÃO DE PDF ---
def generate_order_pdf(client_info, selected_items, signature_image_bytes):
    """
    Gera o PDF completo de um pedido e retorna o seu conteúdo em bytes.

    Args:
        client_info (dict): Dicionário com informações do cliente (nome, CNPJ, etc.).
        selected_items (list): Lista de produtos selecionados no pedido.
        signature_image_bytes (bytes): A imagem da assinatura do cliente em formato de bytes.

    Returns:
        bytes: O conteúdo do ficheiro PDF gerado.
    """
    # Inicializa a classe PDF personalizada.
    pdf = PDF('P', 'mm', 'A4')
    pdf.add_page()
    
    # --- Secção 4.1: Título e Informações do Cliente ---
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, 'Solicitação de Pedido', 0, 1, 'C')
    pdf.ln(5)

    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 5, f"Cliente: {client_info.get('name', 'N/A')}", 0, 1)
    pdf.cell(0, 5, f"CNPJ: {client_info.get('cnpj', 'N/A')}", 0, 1)
    pdf.cell(0, 5, f"Representante: {client_info.get('rep_name', 'N/A')}", 0, 1)
    pdf.cell(0, 5, f"Data/Hora: {datetime.datetime.now().strftime('%d/%m/%Y, %H:%M:%S')}", 0, 1)
    pdf.cell(0, 5, f"IP de Origem: {client_info.get('ip', 'N/A')}", 0, 1)
    pdf.ln(10)

    # --- Secção 4.2: Lista de Produtos Solicitados ---
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, 'Produtos Solicitados:', 0, 1)
    pdf.ln(2)

    for group in selected_items:
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(0, 6, f"- {group['groupName']}", 0, 1)
        pdf.set_font('Arial', '', 10)
        for item in group['items']:
            # Usa '*' como bullet point para garantir a compatibilidade de codificação.
            item_text = f"  * Qtd: {item['quantity']}x - Mod: {item['modelo']} - Tam: {item['size']} (Cód: {item['codigo']})"
            pdf.multi_cell(0, 5, item_text, 0, 'L')
        pdf.ln(2)

    # --- Secção 4.3: Assinatura do Requerente ---
    # Ajusta a posição da assinatura para evitar a criação de uma página em branco extra.
    sig_y_position = pdf.h - 80
    
    # Se o conteúdo já estiver a chegar perto da área da assinatura, adiciona uma nova página.
    if pdf.get_y() > sig_y_position - 10:
        pdf.add_page()

    # Utiliza um ficheiro temporário para passar a imagem da assinatura para a biblioteca FPDF.
    # Esta é a abordagem mais segura para evitar erros de formato de imagem.
    temp_file_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp:
            temp.write(signature_image_bytes)
            temp_file_path = temp.name
        
        pdf.image(temp_file_path, x=65, y=sig_y_position, w=80, h=40, type='PNG')
    
    finally:
        # Garante que o ficheiro temporário é sempre apagado, mesmo que ocorra um erro.
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

    # Desenha a linha de assinatura e o texto.
    pdf.line(50, sig_y_position + 45, 160, sig_y_position + 45)
    pdf.set_y(sig_y_position + 45)
    pdf.set_x(pdf.w / 2)
    pdf.cell(0, 5, 'Assinatura do Requerente', 0, 1, 'C')

    # --- Secção 4.4: Finalização do PDF ---
    # Retorna o conteúdo do PDF como uma string de bytes, usando a codificação 'latin-1'.
    return pdf.output(dest='S').encode('latin-1')
