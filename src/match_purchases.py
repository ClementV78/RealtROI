#!/usr/bin/env python3
from datetime import datetime, timedelta
from db import get_all_invoices, get_all_transactions, insert_purchase
import configparser
import os
from decimal import Decimal
from utils import get_token_decimals, format_token_value, load_config

def parse_date(date_str):
    """Convertit une chaîne de date au format DD/MM/YYYY HH:MM:SS en objet datetime"""
    return datetime.strptime(date_str, '%d/%m/%Y %H:%M:%S')

def format_transaction(tx):
    """Ajoute le champ formatted_value à une transaction"""
    if 'formatted_value' not in tx:
        decimals = get_token_decimals(tx.get('tokenSymbol', ''))
        tx['formatted_value'] = format_token_value(tx.get('value'), decimals)
    return tx

def find_matching_transaction(product, invoice_date, transactions, wallet_address):
    """
    Trouve la transaction correspondant à un produit de la facture.
    Gère le cas où plusieurs transactions avec le même hash existent.
    
    Args:
        product: Le produit de la facture (adresse, quantité)
        invoice_date: La date de la facture
        transactions: Liste des transactions
        wallet_address: L'adresse du portefeuille qui reçoit les tokens
    """
    try:
        invoice_datetime = datetime.strptime(invoice_date, '%B %d, %Y')
    except ValueError as e:
        print(f"Erreur lors du parsing de la date de facture {invoice_date}: {e}")
        return None

    # Fenêtre de recherche : de la date de facture à 120h après
    end_datetime = invoice_datetime + timedelta(hours=120)
    
    # Extraire l'adresse courte du produit (sans la ville et le code postal)
    product_street = product['address'].split(',')[0].strip().lower()
    product_number = ''.join(filter(str.isdigit, product_street))
    
    # Transactions valides par hash
    valid_txs_by_hash = {}
    
    for tx in transactions:
        # Vérifier les champs requis
        if not isinstance(tx, dict) or not all(k in tx for k in ['tokenName', 'to', 'date', 'formatted_value']):
            continue
            
        # Vérifier que c'est une transaction entrante de RealT token vers notre wallet
        if tx['to'].lower() != wallet_address.lower() or not tx.get('tokenName', '').startswith('RealToken'):
            continue
            
        # Convertir la date de transaction
        try:
            tx_datetime = datetime.strptime(tx['date'], '%d/%m/%Y %H:%M:%S')
        except ValueError:
            continue
            
        # Vérifier la fenêtre temporelle
        if not (invoice_datetime <= tx_datetime <= end_datetime):
            continue
            
        # Vérifier que l'adresse du token correspond
        token_number = ''.join(filter(str.isdigit, tx['tokenName']))
        if product_number not in token_number:
            continue
            
        # Double vérification avec le nom complet du token
        if not any(part.lower() in tx['tokenName'].lower() for part in product_street.split()):
            continue
            
        # Ajouter à notre dictionnaire de transactions valides par hash
        hash_id = tx['hash']
        if hash_id not in valid_txs_by_hash:
            valid_txs_by_hash[hash_id] = []
        valid_txs_by_hash[hash_id].append(tx)
    
    # Rechercher une correspondance exacte d'abord
    for hash_id, txs in valid_txs_by_hash.items():
        total_quantity = sum(float(tx['formatted_value']) for tx in txs)
        if abs(total_quantity - product['quantity']) < 0.0001:
            return {
                'hash': hash_id,
                'tokenName': txs[0]['tokenName'],
                'tokenSymbol': txs[0]['tokenSymbol'],
                'date': txs[0]['date'],
                'formatted_value': str(product['quantity']),
                'transactions': txs,
                'total_quantity': total_quantity
            }
    
    # Si pas de correspondance exacte, chercher des correspondances partielles
    unmatched_quantity = product['quantity']
    matched_txs = []
    
    for hash_id, txs in valid_txs_by_hash.items():
        for tx in txs:
            tx_quantity = float(tx['formatted_value'])
            if abs(tx_quantity - unmatched_quantity) < 0.0001:
                # Correspondance exacte trouvée
                return {
                    'hash': tx['hash'],
                    'tokenName': tx['tokenName'],
                    'tokenSymbol': tx['tokenSymbol'],
                    'date': tx['date'],
                    'formatted_value': str(tx_quantity),
                    'transactions': [tx]
                }
            elif tx_quantity <= unmatched_quantity:
                # Correspondance partielle trouvée
                matched_txs.append(tx)
                unmatched_quantity -= tx_quantity
                if abs(unmatched_quantity) < 0.0001:
                    # Toutes les transactions nécessaires ont été trouvées
                    total_quantity = sum(float(t['formatted_value']) for t in matched_txs)
                    return {
                        'hash': matched_txs[0]['hash'],
                        'tokenName': matched_txs[0]['tokenName'],
                        'tokenSymbol': matched_txs[0]['tokenSymbol'],
                        'date': matched_txs[0]['date'],
                        'formatted_value': str(total_quantity),
                        'transactions': matched_txs,
                        'total_quantity': total_quantity
                    }
    
    return None

def find_p2p_purchases(transactions, wallet_address, matched_tx_hashes):
    """
    Trouve les achats P2P dans les transactions:
    - Une transaction entrante de token RealT
    - Une transaction sortante de USDC/WXDAI avec le même hash
    
    Args:
        transactions: Liste des transactions
        wallet_address: Adresse du portefeuille
        matched_tx_hashes: Set des hash de transactions déjà associées à des factures
    
    Returns:
        Liste des achats P2P trouvés
    """
    print("\nRecherche des achats P2P...")
    
    # Normaliser l'adresse du portefeuille
    wallet_address = wallet_address.lower()
    
    # Organiser les transactions par hash
    tx_by_hash = {}
    for tx in transactions:
        # Ignorer les transactions déjà matchées avec une facture
        if tx['hash'] in matched_tx_hashes:
            continue
            
        if not all(key in tx for key in ['hash', 'from', 'to', 'tokenSymbol', 'formatted_value']):
            continue
        
        # Normaliser les adresses
        tx['from'] = tx['from'].lower()
        tx['to'] = tx['to'].lower()
        
        hash_id = tx['hash']
        if hash_id not in tx_by_hash:
            tx_by_hash[hash_id] = []
        tx_by_hash[hash_id].append(tx)
    
    p2p_purchases = []
    
    for hash_id, txs in tx_by_hash.items():
        if len(txs) < 2:  # On a besoin d'au moins 2 transactions
            continue
        
        realt_tx = None
        payment_tx = None
        
        # Chercher la paire RealToken entrant + USDC/WXDAI sortant
        for tx in txs:
            tx = format_transaction(tx)
            
            # Transaction entrante de RealToken
            if (tx['to'] == wallet_address and 
                tx['tokenSymbol'].startswith('REALTOKEN-')):
                realt_tx = tx
            
            # Transaction sortante de USDC/WXDAI
            elif (tx['from'] == wallet_address and 
                  tx['tokenSymbol'] in ['USDC', 'WXDAI']):
                payment_tx = tx
        
        # Si
        if realt_tx and payment_tx:
            try:
                realt_amount = float(realt_tx['formatted_value'])
                payment_amount = float(payment_tx['formatted_value'])
                
                if realt_amount > 0 and payment_amount > 0:
                    purchase = {
                        'token_symbol': realt_tx['tokenSymbol'],
                        'token_name': realt_tx['tokenName'],
                        'product_address': realt_tx['tokenName'].replace('RealToken S ', ''),
                        'quantity': realt_amount,
                        'token_price_usd': payment_amount / realt_amount,
                        'transaction_hash': hash_id,
                        'blockchain_date': realt_tx['date'],
                        'source': 'p2p'
                    }
                    p2p_purchases.append(purchase)
                    
                    print(f"\nTrouvé achat P2P: {realt_tx['tokenSymbol']}")
                    print(f"Montant payé: {payment_amount} {payment_tx['tokenSymbol']}")
                    print(f"Tokens reçus: {realt_amount}")
                    print(f"Prix par token: ${payment_amount / realt_amount:.2f}")
                    print(f"Date: {realt_tx['date']}")
            except (ValueError, ZeroDivisionError) as e:
                print(f"\nAttention: Erreur lors du traitement des montants dans la transaction {hash_id}: {str(e)}")
    
    return p2p_purchases

def find_transfer_invoice(tx, invoices, matched_transactions):
    """
    Recherche une facture correspondant à un transfert
    
    Args:
        tx: La transaction de transfert
        invoices: Liste des factures
        matched_transactions: Liste des transactions déjà associées à des factures
    """
    transfer_date = parse_date(tx['date'])
    quantity = float(tx['formatted_value'])
    
    for invoice in invoices:
        invoice_date = datetime.strptime(invoice['order_info']['invoice_date'], '%B %d, %Y')
        
        # La facture doit être antérieure au transfert
        if invoice_date >= transfer_date:
            continue
            
        for product in invoice['products']:
            # Vérifier la quantité
            if abs(float(product['quantity']) - quantity) >= 0.0001:
                continue
                
            # Vérifier si le token correspond (via l'adresse dans le nom)
            token_address = tx['tokenName'].replace('RealToken S ', '')
            if not any(part.strip() in token_address for part in product['address'].split(',')):
                continue
                
            # Vérifier que cette facture n'est pas déjà associée à une autre transaction
            if any(t['hash'] in matched_transactions for t in invoice.get('transactions', [])):
                continue
                
            return product, invoice
    
    return None, None

def find_transfers(transactions, wallet_address, old_wallet_address):
    """
    Trouve les transferts de tokens RealT depuis l'ancienne adresse vers la nouvelle
    et recherche les factures associées
    
    Args:
        transactions: Liste des transactions
        wallet_address: L'adresse du portefeuille actuel
        old_wallet_address: L'ancienne adresse du portefeuille
    """
    print("\nRecherche des transferts de tokens...")
    
    # Normaliser les adresses
    wallet_address = wallet_address.lower()
    old_wallet_address = old_wallet_address.lower()
    
    # Obtenir les factures et les transactions déjà matchées
    invoices = get_all_invoices()
    matched_transactions = set()
    for invoice in invoices:
        for tx in invoice.get('transactions', []):
            if tx.get('hash'):
                matched_transactions.add(tx['hash'])
    
    transfers = []
    for tx in transactions:
        # Formater la transaction si nécessaire
        tx = format_transaction(tx)
        
        # Vérifier les critères de transfert
        if (tx.get('from', '').lower() == old_wallet_address and
            tx.get('to', '').lower() == wallet_address and
            tx.get('tokenSymbol', '').startswith('REALTOKEN-')):
            
            # Rechercher une facture correspondante
            product, invoice = find_transfer_invoice(tx, invoices, matched_transactions)
            
            transfer = {
                'token_symbol': tx['tokenSymbol'],
                'token_name': tx['tokenName'],
                'product_address': tx['tokenName'].replace('RealToken S ', ''),
                'quantity': float(tx['formatted_value']),
                'transaction_hash': tx['hash'],
                'blockchain_date': tx['date'],
                'source': 'transfer',
                'token_price_usd': product['token_price'] if product else None,
                'invoice_number': invoice['order_info']['invoice_number'] if invoice else None,
                'invoice_date': invoice['order_info']['invoice_date'] if invoice else None
            }
            transfers.append(transfer)
            
            price_info = f" (prix facture: ${product['token_price']:.2f})" if product else " (facture non trouvée)"
            print(f"\nTransfert trouvé: {tx['tokenSymbol']}")
            print(f"Quantité: {tx['formatted_value']} tokens{price_info}")
            print(f"Date transfert: {tx['date']}")
            if invoice:
                print(f"Date facture: {invoice['order_info']['invoice_date']}")
    
    return transfers

def find_p2p_transactions(transactions, wallet_address):
    """Identifie les transactions P2P (achat direct auprès d'autres utilisateurs)"""
    p2p_transactions = []
    
    for tx in transactions:
        # Une transaction P2P est une transaction où les tokens sont reçus d'une adresse
        # autre que l'adresse du contrat RealT
        if (tx['to'].lower() == wallet_address.lower() and
            not tx['from'].lower().startswith('0x7e6c2522ff2b3c680c936c05187b99ca1daca151')):
            
            p2p_data = {
                'token_symbol': tx['tokenSymbol'],
                'token_name': tx['tokenName'],
                'product_address': tx['tokenName'].replace('RealToken S ', ''),
                'quantity': float(tx['formatted_value']),
                'transaction_hash': tx['hash'],
                'blockchain_date': tx['date'],
                'source': 'p2p',
                'token_price_usd': None,  # Prix inconnu pour les transactions P2P
                'invoice_number': None,
                'invoice_date': None
            }
            p2p_transactions.append(p2p_data)
    
    return p2p_transactions

def print_summary(invoices, matched_tx_hashes, p2p_purchases):
    """
    Affiche un récapitulatif détaillé des achats trouvés et non trouvés
    """
    # Statistiques globales
    total_products = sum(len(invoice.get('products', [])) for invoice in invoices)
    
    # Collecter les détails des produits non trouvés et compter les matchés
    unmatched_details = []
    matched_count = 0

    # Les hash des transactions qui ont été utilisés
    used_hashes = set()
    
    for invoice in invoices:
        invoice_number = invoice.get('order_info', {}).get('invoice_number', 'N/A')
        invoice_date = invoice.get('order_info', {}).get('invoice_date', 'N/A')
        
        for product in invoice.get('products', []):
            # On considère qu'un produit est matché si une de ses transactions est dans matched_tx_hashes
            # et que cette transaction n'a pas déjà été utilisée pour un autre produit
            is_matched = False
            for tx_hash in matched_tx_hashes:
                if tx_hash not in used_hashes:
                    matched_count += 1
                    used_hashes.add(tx_hash)
                    is_matched = True
                    break
            
            if not is_matched:
                unmatched_details.append({
                    'invoice': invoice_number,
                    'date': invoice_date,
                    'address': product['address'],
                    'quantity': product['quantity']
                })

    # Afficher le récapitulatif
    print("\n" + "="*80)
    print("RÉCAPITULATIF DES ACHATS")
    print("="*80)
    
    print("\nSTATISTIQUES GLOBALES:")
    print(f"Total des produits dans les factures: {total_products}")
    print(f"Produits matchés avec des transactions: {matched_count}")
    print(f"Transactions P2P identifiées: {len(p2p_purchases)}")
    print(f"Produits non matchés: {len(unmatched_details)}")
    
    if unmatched_details:
        print("\nDÉTAIL DES PRODUITS NON MATCHÉS:")
        for detail in unmatched_details:
            print(f"\nFacture {detail['invoice']} ({detail['date']}):")
            print(f"  Adresse: {detail['address']}")
            print(f"  Quantité: {detail['quantity']} tokens")
    
    print("\n" + "="*80)

def match_purchases():
    """Fait correspondre les factures avec les transactions blockchain et identifie les achats P2P et transferts"""
    # Charger la configuration pour obtenir les adresses des portefeuilles
    config = load_config()
    wallet_address = config['DEFAULT']['gnosis_address']
    old_wallet_address = config['DEFAULT'].get('old_gnosis_address')
    
    # Récupérer toutes les factures et transactions
    invoices = get_all_invoices()
    transactions = get_all_transactions()
    
    # Compteurs pour les statistiques
    matched_count = 0
    unmatched_count = 0
    p2p_count = 0
    transfer_count = 0
    
    # Set pour suivre les transactions déjà matchées avec une facture
    matched_tx_hashes = set()
    
    # Set pour suivre les numéros de factures associés aux transferts
    transfer_invoice_numbers = set()
    
    # Rechercher les transferts si une ancienne adresse est configurée
    transfers = []
    if old_wallet_address:
        transfers = find_transfers(transactions, wallet_address, old_wallet_address)
        # Collecter les numéros de factures associés aux transferts
        for transfer in transfers:
            if transfer.get('invoice_number'):
                transfer_invoice_numbers.add(transfer['invoice_number'])
    
    print("\nTraitement des factures...")
    # Traiter les factures
    for invoice in invoices:
        # Vérifier que nous avons toutes les informations nécessaires
        if not all(k in invoice['order_info'] for k in ['invoice_number', 'invoice_date']):
            print(f"Facture invalide, informations manquantes: {invoice['order_info']}")
            unmatched_count += 1
            continue
            
        invoice_number = invoice['order_info']['invoice_number']
        invoice_date = invoice['order_info']['invoice_date']
        
        print(f"\nTraitement de la facture {invoice_number} du {invoice_date}")
        
        # Traiter chaque produit de la facture
        for product in invoice.get('products', []):
            tx = find_matching_transaction(product, invoice_date, transactions, wallet_address)
            
            if tx:
                # Ajouter le hash de la transaction à l'ensemble des transactions matchées
                matched_tx_hashes.add(tx['hash'])
                
                # Créer l'entrée dans la base de données des achats
                purchase_data = {
                    'invoice_number': invoice_number,
                    'invoice_date': invoice_date,
                    'product_address': product['address'],
                    'token_price_usd': float(product['token_price']),
                    'quantity': float(tx.get('total_quantity', tx['formatted_value'])),  # Utiliser la quantité totale si disponible
                    'transaction_hash': tx['hash'],
                    'token_symbol': tx['tokenSymbol'],
                    'token_name': tx['tokenName'],
                    'blockchain_date': tx['date'],
                    'source': 'invoice',
                    'matched_at': datetime.now().isoformat()
                }
                
                # Stocker les sous-transactions si présentes
                if 'sub_transactions' in tx:
                    purchase_data['sub_transactions'] = [
                        {
                            'hash': sub_tx['hash'],
                            'quantity': float(sub_tx['formatted_value']),
                            'date': sub_tx['date']
                        }
                        for sub_tx in tx['sub_transactions']
                    ]
                
                insert_purchase(purchase_data)
                matched_count += 1
                print(f"✓ Purchase enregistré: {purchase_data['quantity']} tokens pour {purchase_data['token_price_usd']}$")
            else:
                unmatched_count += 1
                print(f"\n✗ Facture sans correspondance :")
                print(f"  Numéro de facture : {invoice_number}")
                print(f"  Date de facture : {invoice_date}")
                print(f"  Adresse : {product['address']}")
                print(f"  Quantité : {product['quantity']} tokens")
                print(f"  Prix : ${product['token_price']}")
    
    # Identifier les transactions P2P
    print("\nRecherche des achats P2P...")
    p2p_purchases = find_p2p_purchases(transactions, wallet_address, matched_tx_hashes)
    
    # Enregistrer les transactions P2P dans la base de données
    for p2p in p2p_purchases:
        insert_purchase(p2p)
    
    # Enregistrer les transferts dans la base de données
    for transfer in transfers:
        insert_purchase(transfer)
    
    # Statistiques finales
    p2p_count = len(p2p_purchases)
    transfer_count = len(transfers)
    transfer_with_invoice = sum(1 for t in transfers if t.get('invoice_number'))
    
    print(f"\nRésultat de la correspondance :")
    print(f"  Achats avec facture trouvés : {matched_count}")
    print(f"  Achats P2P trouvés : {p2p_count}")
    print(f"  Transferts trouvés : {transfer_count}")
    print(f"    dont {transfer_with_invoice} avec facture")
    print(f"  Factures sans correspondance : {unmatched_count}")

def main():
    """Trouve et enregistre tous les achats de tokens RealT"""
    print("\nDébut du matching des achats...")
    
    # Charger les données
    invoices = get_all_invoices()
    transactions = get_all_transactions()
    
    # Charger l'adresse du wallet depuis la config
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'config.ini')
    config.read(config_path)
    wallet_address = config['DEFAULT']['gnosis_address']
    
    print(f"\nTraitement de {len(invoices)} factures...")
    print(f"Nombre total de transactions: {len(transactions)}")
    
    # Set pour suivre les transactions déjà matchées
    matched_tx_hashes = set()
    
    # Parcourir chaque facture
    for invoice in invoices:
        order_info = invoice.get('order_info', {})
        if not order_info:
            continue
        
        print(f"\nTraitement de la facture {order_info.get('invoice_number', 'N/A')}")
        invoice_date = order_info.get('invoice_date')
        
        # Parcourir chaque produit de la facture
        for product in invoice.get('products', []):
            tx = find_matching_transaction(product, invoice_date, transactions, wallet_address)
            
            if tx:
                # Créer l'entrée d'achat
                purchase = {
                    'invoice_number': order_info['invoice_number'],
                    'invoice_date': invoice_date,
                    'product_address': product['address'],
                    'token_price_usd': product['token_price'],
                    'quantity': product['quantity'],
                    'transaction_hash': tx['hash'],
                    'token_symbol': tx['tokenSymbol'],
                    'token_name': tx['tokenName'],
                    'blockchain_date': tx['date'],
                    'source': 'invoice',
                    'matched_at': datetime.now().isoformat()
                }
                
                # Insérer l'achat
                insert_purchase(purchase)
                print(f"✓ Achat enregistré: {product['quantity']} {tx['tokenSymbol']} à ${product['token_price']}/token")
                
                # Marquer toutes les transactions associées comme matchées
                if 'transactions' in tx:
                    for sub_tx in tx['transactions']:
                        matched_tx_hashes.add(sub_tx['hash'])
                else:
                    matched_tx_hashes.add(tx['hash'])
            else:
                print(f"✗ Pas de transaction trouvée pour l'achat de {product['quantity']} tokens à {product['address']}")
    
    # Chercher les achats P2P
    p2p_purchases = find_p2p_purchases(transactions, wallet_address, matched_tx_hashes)
    
    # Insérer les achats P2P
    for purchase in p2p_purchases:
        insert_purchase(purchase)
        print(f"✓ Achat P2P enregistré: {purchase['quantity']} {purchase['token_symbol']} à ${purchase['token_price_usd']}/token")
        
    # Afficher le récapitulatif
    print_summary(invoices, matched_tx_hashes, p2p_purchases)

if __name__ == "__main__":
    main()
