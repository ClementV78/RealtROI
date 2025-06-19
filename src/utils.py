from datetime import datetime
from tinydb import Query
import re
import pdfplumber
from decimal import Decimal
import configparser
import os

# Dictionnaire des décimales connues par symbole de token
TOKEN_DECIMALS = {
    'USDC': 6,
    'USDT': 6,
    'DAI': 18,
    'WXDAI': 18,
}

def get_token_decimals(token_symbol):
    """Retourne le nombre de décimales pour un token."""
    if token_symbol.startswith('REALTOKEN-'):
        return 18  # Tous les RealTokens utilisent 18 décimales
    return TOKEN_DECIMALS.get(token_symbol, 18)  # Par défaut 18 décimales

def format_token_value(value, decimals):
    """Convertit une valeur brute en valeur lisible selon le nombre de décimales."""
    if not value:
        return "0"
    
    # Conversion en Decimal pour éviter les erreurs de précision des floats
    raw_value = Decimal(value)
    divisor = Decimal(10 ** decimals)
    return str(raw_value / divisor)

def parse_token_transactions(response):
    """Parse the token transactions from the API response."""
    transactions = response.get('result', [])
    parsed_transactions = []
    
    for tx in transactions:
        if 'value' in tx and 'tokenSymbol' in tx:
            # Obtenir le nombre de décimales pour ce token
            decimals = get_token_decimals(tx.get('tokenSymbol', ''))
            # Formater la valeur
            formatted_value = format_token_value(tx.get('value'), decimals)
            
            parsed_transactions.append({
                'blockNumber': tx.get('blockNumber'),
                'timeStamp': tx.get('timeStamp'),
                'from': tx.get('from'),
                'to': tx.get('to'),
                'value': tx.get('value'),
                'formatted_value': formatted_value,
                'tokenName': tx.get('tokenName'),
                'tokenSymbol': tx.get('tokenSymbol'),
                'hash': tx.get('hash'),
                'date': datetime.fromtimestamp(int(tx.get('timeStamp'))).strftime('%d/%m/%Y %H:%M:%S') if tx.get('timeStamp') else ''
            })
    
    return parsed_transactions

def format_transactions(transactions):
    """Format the list of transactions for display."""
    formatted = []
    for idx, tx in enumerate(transactions, 1):
        formatted.append(f"{idx}. Date: {tx['date']} | Token: {tx['tokenName']} ({tx['tokenSymbol']}) - Value: {tx['formatted_value']} ({tx['value']}) - From: {tx['from']} - To: {tx['to']} - Hash: {tx['hash']}")
    return "\n".join(formatted)

def parse_invoice_pdf(pdf_path):
    """Parse une facture PDF RealT et extrait les informations pertinentes."""
    products = []
    
    with pdfplumber.open(pdf_path) as pdf:
        # Extraction du texte pour les informations d'en-tête
        text = pdf.pages[0].extract_text()
        
        # Extraction des informations de commande
        invoice_number = re.search(r'Invoice Number:\s*(\d+)', text)
        invoice_date = re.search(r'Invoice Date:\s*([^\n]+)', text)
        order_number = re.search(r'Order Number:\s*(\d+)', text)
        payment_method = re.search(r'Payment Method:\s*([^\n]+)', text)
        
        # Extraction du tableau
        table = pdf.pages[0].extract_table()
        
        if table:
            # Trouver la ligne qui contient le produit (celle après PRODUCT)
            product_found = False
            for row in table:
                if not row[0]:
                    continue
                    
                if 'PRODUCT' in row[0]:
                    product_found = True
                    continue
                
                if product_found and 'SUBTOTAL' not in row[0]:
                    # Le format est : "adresse $prix quantité $total"
                    text = row[0]
                    
                    # Mise à jour du regex pour supporter les quantités décimales
                    match = re.match(r'(.*?)\s+\$(\d+\.\d+)\s+(\d*\.?\d+)\s+\$', text)
                    if match:
                        address = match.group(1).strip()
                        price = float(match.group(2))
                        qty = float(match.group(3))  # Changé de int à float
                        
                        product = {
                            'address': address,
                            'token_price': price,
                            'quantity': qty
                        }
                        products.append(product)
                        print(f"\nProduit extrait: {product}")
                
                if 'SUBTOTAL' in row[0]:
                    break
    
    # Construction du document final
    invoice_data = {
        'order_info': {
            'invoice_number': invoice_number.group(1) if invoice_number else None,
            'invoice_date': invoice_date.group(1) if invoice_date else None,
            'order_number': order_number.group(1) if order_number else None,
            'payment_method': payment_method.group(1) if payment_method else None,
        },
        'products': products,
        'processed_at': datetime.now().isoformat()
    }
    
    return invoice_data

def store_invoice_data(invoice_data):
    """Stocke les données de facture dans TinyDB."""
    from db import insert_invoice
    insert_invoice(invoice_data)

def load_config():
    """
    Charge la configuration depuis les fichiers config.ini
    Cherche d'abord un fichier config.ini.local, puis utilise config.ini comme fallback
    
    Returns:
        configparser.ConfigParser: L'objet de configuration chargé
    """
    config = configparser.ConfigParser()
    
    # Chemin vers les fichiers de configuration
    config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config')
    local_config = os.path.join(config_dir, 'config.ini.local')
    default_config = os.path.join(config_dir, 'config.ini')
    example_config = os.path.join(config_dir, 'config.ini.example')
    
    # Charger d'abord la configuration locale si elle existe
    if os.path.exists(local_config):
        config.read(local_config)
        print("Configuration chargée depuis config.ini.local")
    # Sinon charger la configuration par défaut
    elif os.path.exists(default_config):
        config.read(default_config)
        print("Configuration chargée depuis config.ini")
    # En dernier recours, utiliser l'exemple
    elif os.path.exists(example_config):
        config.read(example_config)
        print("Configuration chargée depuis config.ini.example")
    else:
        raise FileNotFoundError("Aucun fichier de configuration trouvé")
        
    return config