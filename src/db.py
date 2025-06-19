from tinydb import TinyDB, Query
import os

def get_transactions_db():
    db_path = os.path.join(os.path.dirname(__file__), '../data/transactions.json')
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return TinyDB(db_path)

def get_invoices_db():
    db_path = os.path.join(os.path.dirname(__file__), '../data/invoices.json')
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return TinyDB(db_path)

def get_purchases_db():
    """Base de données pour les achats (lien entre factures et transactions)"""
    db_path = os.path.join(os.path.dirname(__file__), '../data/purchases.json')
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return TinyDB(db_path)

def get_sales_db():
    """Base de données pour les ventes"""
    db_path = os.path.join(os.path.dirname(__file__), '../data/sales.json')
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return TinyDB(db_path)

def insert_transactions(transactions):
    db = get_transactions_db()
    db.insert_multiple(transactions)

def get_all_transactions():
    db = get_transactions_db()
    return db.all()

def insert_invoice(invoice_data):
    db = get_invoices_db()
    Invoice = Query()
    existing = db.get(
        Invoice.order_info.invoice_number == invoice_data['order_info']['invoice_number']
    )
    
    if existing:
        db.update(
            invoice_data,
            Invoice.order_info.invoice_number == invoice_data['order_info']['invoice_number']
        )
    else:
        db.insert(invoice_data)

def get_all_invoices():
    db = get_invoices_db()
    return db.all()

def insert_purchase(purchase_data):
    """Insère ou met à jour un achat dans la base de données"""
    db = get_purchases_db()
    Purchase = Query()
    
    # Pour les achats P2P qui n'ont pas de numéro de facture
    if 'invoice_number' not in purchase_data:
        existing = db.get(Purchase.transaction_hash == purchase_data['transaction_hash'])
        if existing:
            db.update(purchase_data, Purchase.transaction_hash == purchase_data['transaction_hash'])
        else:
            db.insert(purchase_data)
        return
    
    # Pour les achats avec facture, on utilise le hash ET le numéro de facture
    existing = db.get(
        (Purchase.transaction_hash == purchase_data['transaction_hash']) &
        (Purchase.invoice_number == purchase_data['invoice_number'])
    )
    
    if existing:
        db.update(purchase_data, 
                 (Purchase.transaction_hash == purchase_data['transaction_hash']) &
                 (Purchase.invoice_number == purchase_data['invoice_number']))
    else:
        db.insert(purchase_data)

def get_all_purchases():
    """Récupère tous les achats"""
    db = get_purchases_db()
    return db.all()

def insert_sale(sale_data):
    """Insère ou met à jour une vente dans la base de données"""
    db = get_sales_db()
    Sale = Query()
    
    # On utilise le hash de la transaction comme identifiant unique
    existing = db.get(Sale.sale_hash == sale_data['sale_hash'])
    
    if existing:
        db.update(sale_data, Sale.sale_hash == sale_data['sale_hash'])
    else:
        db.insert(sale_data)

def get_all_sales():
    """Récupère toutes les ventes"""
    db = get_sales_db()
    return db.all()
