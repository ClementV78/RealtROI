import configparser
import os
from api_client import ApiClient
from utils import parse_token_transactions, format_transactions, load_config
from db import insert_transactions

def update_transactions():
    """Récupère et met à jour les transactions depuis la blockchain"""
    # Load configuration
    config = load_config()
    api_key = config['DEFAULT']['api_key']
    user_address = config['DEFAULT']['gnosis_address']
    contract_address = config['DEFAULT'].get('contract_address', None)

    # Initialize API client
    api_client = ApiClient(api_key)

    # Fetch token transactions (contract_address is optional)
    response = api_client.fetch_token_transactions(user_address, contract_address)
    transactions = parse_token_transactions(response)

    # Enregistre les transactions dans TinyDB
    insert_transactions(transactions)

    # Affiche les transactions fraîchement récupérées
    print('--- Transactions récupérées ---')
    print(format_transactions(transactions))

if __name__ == "__main__":
    update_transactions()