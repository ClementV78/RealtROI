import json
import os
import configparser
from datetime import datetime
import os
import json
import configparser

def get_project_root():
    """Retourne le chemin absolu vers la racine du projet"""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

def load_config():
    """
    Charge la configuration et retourne l'adresse du portefeuille
    """
    from utils import load_config as utils_load_config
    config = utils_load_config()
    return config['DEFAULT']['gnosis_address']

def load_json_file(relative_path):
    """
    Charge un fichier JSON en utilisant un chemin relatif à la racine du projet
    
    Args:
        relative_path: Chemin relatif depuis la racine du projet (ex: 'data/purchases.json')
    """
    filepath = os.path.join(get_project_root(), relative_path)
    with open(filepath, 'r') as f:
        data = json.load(f)
        if filepath.endswith('purchases.json'):
            return data.get('_default', {})
        return data

def save_json_file(relative_path, data):
    """
    Sauvegarde des données dans un fichier JSON en utilisant un chemin relatif à la racine du projet
    
    Args:
        relative_path: Chemin relatif depuis la racine du projet (ex: 'data/sales.json')
    """
    filepath = os.path.join(get_project_root(), relative_path)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)

def find_sale_pairs(transactions, user_address):
    """
    Trouve les paires de transactions qui constituent une vente:
    - Une transaction sortante de token RealT
    - Une transaction entrante de USDC/WXDAI avec le même hash (même transaction de swap)
    """
    print("\nDebug: Looking for sales...")
    print(f"Debug: User address: {user_address}")
    
    # Organiser les transactions par hash
    tx_by_hash = {}
    realt_out_count = 0
    usdc_in_count = 0
    
    # Normaliser l'adresse utilisateur
    user_address = user_address.lower()
    
    for tx in transactions:
        # Vérifier que nous avons toutes les données nécessaires
        if not all(key in tx for key in ['hash', 'from', 'to', 'tokenSymbol', 'formatted_value']):
            continue
            
        # Normaliser les adresses pour la comparaison
        tx['from'] = tx['from'].lower()
        tx['to'] = tx['to'].lower()
        
        # Compter les transactions intéressantes
        if tx['from'].lower() == user_address.lower() and tx['tokenSymbol'].startswith('REALTOKEN-'):
            realt_out_count += 1
            #print(f"\nDebug: Found RealToken outgoing tx:")
            #print(f"Hash: {tx['hash']}")
            #print(f"Token: {tx['tokenSymbol']}")
            #print(f"Amount: {tx.get('formatted_value', 'N/A')}")
            
        if tx['to'].lower() == user_address.lower() and tx['tokenSymbol'] in ['USDC', 'WXDAI']:
            usdc_in_count += 1
            #print(f"\nDebug: Found USDC/WXDAI incoming tx:")
            #print(f"Hash: {tx['hash']}")
            #print(f"Amount: {tx.get('formatted_value', 'N/A')} {tx['tokenSymbol']}")

        hash_id = tx['hash']
        if hash_id not in tx_by_hash:
            tx_by_hash[hash_id] = []
        tx_by_hash[hash_id].append(tx)
    
    print(f"\nDebug: Found {realt_out_count} RealToken outgoing transactions")
    print(f"Debug: Found {usdc_in_count} USDC/WXDAI incoming transactions")
    
    # Trouver les paires qui constituent des ventes
    sale_pairs = {}
    for hash_id, txs in tx_by_hash.items():
        if len(txs) < 2:  # On a besoin d'au moins 2 transactions avec le même hash
            continue
            
        realt_tx = None
        payment_tx = None
        
        # Chercher la paire RealToken sortant + USDC/WXDAI entrant
        for tx in txs:
            # Transaction sortante de RealToken
            if (tx['from'].lower() == user_address.lower() and 
                tx['tokenSymbol'].startswith('REALTOKEN-')):
                realt_tx = tx
                
            # Transaction entrante de USDC/WXDAI
            elif (tx['to'].lower() == user_address.lower() and 
                  tx['tokenSymbol'] in ['USDC', 'WXDAI']):
                payment_tx = tx
        
        # Si on a trouvé une paire complète
        if realt_tx and payment_tx:
            # Valider que les montants sont cohérents
            try:
                realt_amount = float(realt_tx['formatted_value'])
                payment_amount = float(payment_tx['formatted_value'])
                
                if realt_amount > 0 and payment_amount > 0:
                    sale_pairs[hash_id] = {
                        'realt': realt_tx,
                        'payment': payment_tx,
                        'price_per_token': payment_amount / realt_amount
                    }
                    print(f"\nFound sale: {realt_tx['tokenSymbol']}")
                    print(f"Amount received: {payment_amount} {payment_tx['tokenSymbol']}")
                    print(f"Amount sold: {realt_amount} tokens")
                    print(f"Price per token: ${payment_amount / realt_amount:.2f}")
                    print(f"Date: {realt_tx['date']}")
                else:
                    print(f"\nWarning: Invalid amounts in transaction {hash_id}")
                    print(f"RealToken amount: {realt_amount}")
                    print(f"Payment amount: {payment_amount}")
            except (ValueError, ZeroDivisionError) as e:
                print(f"\nWarning: Error processing amounts in transaction {hash_id}: {str(e)}")
    
    return sale_pairs

def calculate_roi(buy_price, sell_price):
    """Calcule le ROI en pourcentage"""
    return ((sell_price - buy_price) / buy_price) * 100

def match_sales_with_purchases(purchases, sale_pairs):
    """
    Associe les ventes avec les achats correspondants et calcule le ROI.
    Gère les ventes partielles en gardant une trace des quantités restantes.
    """
    print("\nDebug: Matching sales with purchases...")
    sales = []
    total_invested = 0
    total_received = 0
    
    # Copier les achats pour garder une trace des quantités restantes
    remaining_purchases = {}
    for pid, purchase in purchases.items():
        if purchase.get('quantity') is not None:
            remaining_purchases[pid] = {
                **purchase,
                'remaining_quantity': float(purchase['quantity'])
            }
    
    for hash_id, pair in sale_pairs.items():
        realt_tx = pair['realt']
        payment_tx = pair['payment']
        token_symbol = realt_tx['tokenSymbol']
        sale_quantity = float(realt_tx['formatted_value'])
        
        print(f"\nProcessing sale transaction: {hash_id}")
        print(f"Token: {token_symbol}")
        print(f"Sale quantity: {sale_quantity}")
        
        # Chercher l'achat correspondant avec une quantité suffisante
        matching_purchase = None
        for purchase_id, purchase in remaining_purchases.items():
            if not purchase.get('token_symbol') or purchase.get('remaining_quantity', 0) <= 0:
                continue
                
            if (purchase.get('token_symbol') == token_symbol and
                purchase.get('remaining_quantity', 0) >= sale_quantity):
                matching_purchase = purchase
                purchase_id_matched = purchase_id
                break
        
        if matching_purchase:
            print(f"Found matching purchase from {matching_purchase.get('blockchain_date', 'unknown date')}")
            print(f"Remaining quantity before sale: {matching_purchase['remaining_quantity']}")
            
            # Vérifier que toutes les valeurs nécessaires sont présentes
            if not all(key in matching_purchase for key in ['token_price_usd', 'product_address']):
                print(f"Warning: Purchase is missing required data: {matching_purchase}")
                continue
                
            try:
                # Convertir les valeurs en nombres décimaux
                sell_amount = float(payment_tx['formatted_value'])
                sell_price = sell_amount / sale_quantity
                
                # Pour les achats P2P, on n'a pas le prix d'achat
                if matching_purchase['source'] == 'p2p' and matching_purchase.get('token_price_usd') is None:
                    print(f"P2P purchase without price information - skipping ROI calculation")
                    continue
                    
                buy_price = float(matching_purchase['token_price_usd'])
                
                # Mettre à jour la quantité restante
                remaining_purchases[purchase_id_matched]['remaining_quantity'] -= sale_quantity
                print(f"Updated remaining quantity: {remaining_purchases[purchase_id_matched]['remaining_quantity']}")
                
                sale = {
                    'token_symbol': token_symbol,
                    'token_name': realt_tx['tokenName'],
                    'product_address': matching_purchase['product_address'],
                    'sale_hash': hash_id,
                    'purchase_date': matching_purchase['blockchain_date'],
                    'sale_date': realt_tx['date'],
                    'buy_price': buy_price,
                    'sell_price': sell_price,
                    'quantity': sale_quantity,
                    'total_received': sell_amount,
                    'payment_currency': payment_tx['tokenSymbol'],
                    'roi_percent': calculate_roi(buy_price, sell_price),
                    'is_partial_sale': sale_quantity < float(matching_purchase['quantity'])
                }
                sales.append(sale)
                
                print(f"Successfully processed sale:")
                print(f"Buy price: ${buy_price:.2f}")
                print(f"Sell price: ${sell_price:.2f}")
                print(f"ROI: {sale['roi_percent']:.2f}%")
            except (TypeError, ValueError) as e:
                print(f"Error processing sale {hash_id}: {str(e)}")
                print(f"RealT tx: {realt_tx}")
                print(f"Payment tx: {payment_tx}")
                print(f"Matching purchase: {matching_purchase}")
        else:
            print(f"No matching purchase found for {token_symbol} (quantity: {sale_quantity})")
            # Liste les achats disponibles pour ce token pour debug
            available_purchases = [p for p in remaining_purchases.values() 
                                if p.get('token_symbol') == token_symbol and p.get('remaining_quantity', 0) > 0]
            if available_purchases:
                print("Available purchases for this token:")
                for p in available_purchases:
                    print(f"- Quantity: {p.get('remaining_quantity')} from {p.get('blockchain_date', 'unknown')}")
    
    return sales

def main():
    # Charger l'adresse de l'utilisateur
    user_address = load_config()
    print(f"Using wallet address: {user_address}")
    
    # Charger les données
    purchases = load_json_file('data/purchases.json')
    print(f"\nLoaded {len(purchases)} purchases")
    
    transactions_data = load_json_file('data/transactions.json')['_default']
    transactions = []
    for tx_id, tx in transactions_data.items():
        if not isinstance(tx, dict):
            continue
        if 'date' in tx and len(tx) == 1:
            continue
        transactions.append(tx)
    
    print(f"\nProcessing {len(transactions)} transactions")
    
    # Trouver les paires de transactions de vente
    sale_pairs = find_sale_pairs(transactions, user_address)
    print(f"\nFound {len(sale_pairs)} sale pairs")
    
    # Faire correspondre les ventes avec les achats et calculer le ROI
    sales = match_sales_with_purchases(purchases, sale_pairs)
    
    # Sauvegarder les résultats
    save_json_file('data/sales.json', sales)
    
    # Afficher un résumé global
    if sales:
        total_invested = sum(sale['buy_price'] * sale['quantity'] for sale in sales)
        total_received = sum(sale['total_received'] for sale in sales)
        total_roi = ((total_received - total_invested) / total_invested) * 100
        
        print(f"\nSummary of {len(sales)} sales:")
        print(f"Total invested: ${total_invested:.2f}")
        print(f"Total received: ${total_received:.2f}")
        print(f"Overall ROI: {total_roi:.2f}%")
    else:
        print("\nNo sales found")

if __name__ == "__main__":
    main()
