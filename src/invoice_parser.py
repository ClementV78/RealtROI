#!/usr/bin/env python3
import os
from utils import parse_invoice_pdf, store_invoice_data
import json
from tinydb import TinyDB, Query

def process_invoices(invoice_dir):
    """
    Traite tous les fichiers PDF dans le dossier des factures et stocke les données dans TinyDB.
    Retourne un résumé des opérations effectuées.
    """
    stats = {
        'total': 0,
        'success': 0,
        'errors': 0,
        'processed_files': [],
        'error_files': []
    }

    # S'assurer que le dossier existe
    if not os.path.exists(invoice_dir):
        print(f"Erreur: Le dossier {invoice_dir} n'existe pas")
        return stats

    # Parcourir tous les fichiers PDF
    for filename in sorted(os.listdir(invoice_dir)):
        if not filename.endswith(".pdf"):
            continue

        stats['total'] += 1
        filepath = os.path.join(invoice_dir, filename)
        print(f"\nTraitement de {filename}...")

        try:
            # Extraire et stocker les données
            invoice_data = parse_invoice_pdf(filepath)
            store_invoice_data(invoice_data)
            
            # Afficher un résumé des données extraites
            print(f"✓ Facture {invoice_data['order_info']['invoice_number']}:")
            print(f"  Date: {invoice_data['order_info']['invoice_date']}")
            print(f"  Commande: {invoice_data['order_info']['order_number']}")
            print("  Produits:")
            for product in invoice_data['products']:
                print(f"    - {product['address']}: {product['quantity']} x ${product['token_price']}")
            
            stats['success'] += 1
            stats['processed_files'].append(filename)

        except Exception as e:
            print(f"✗ Erreur lors du traitement de {filename}: {e}")
            stats['errors'] += 1
            stats['error_files'].append(filename)

    return stats

def display_summary(stats):
    """Affiche un résumé des opérations effectuées."""
    print("\n" + "="*50)
    print("RÉSUMÉ DU TRAITEMENT")
    print("="*50)
    print(f"Total des fichiers traités: {stats['total']}")
    print(f"Succès: {stats['success']}")
    print(f"Erreurs: {stats['errors']}")
    
    if stats['processed_files']:
        print("\nFichiers traités avec succès:")
        for f in stats['processed_files']:
            print(f"  ✓ {f}")
    
    if stats['error_files']:
        print("\nFichiers en erreur:")
        for f in stats['error_files']:
            print(f"  ✗ {f}")

def main():
    # Chemin vers le dossier des factures
    invoice_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'invoices')
    
    print(f"Début du traitement des factures dans {invoice_dir}")
    stats = process_invoices(invoice_dir)
    display_summary(stats)

    # Afficher le contenu de la base
    from db import get_all_invoices
    #print("\nContenu de la base de données:")
    #print(json.dumps(get_all_invoices(), indent=2))
    #afficher le nombre de factures et le nombre de tokens (produits*qty) dans la base
    invoices = get_all_invoices()
    total_tokens = sum(len(invoice['products']) for invoice in invoices)
    print(f"\nNombre total de factures: {len(invoices)}")
    #afficher le nombre de tokens (produits) dans les factures * quantité
    total_tokens = sum(product['quantity'] for invoice in invoices for product in invoice['products'])  
    print(f"Nombre total de produits (tokens) dans les factures: {total_tokens}")
if __name__ == "__main__":
    main()
