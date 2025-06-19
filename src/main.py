#!/usr/bin/env python3
import argparse
import sys
import os
from blockchain_parser import update_transactions
from match_purchases import match_purchases
from match_sales import main as match_sales
from utils import load_config  # Import centralisé de la configuration

# Import conditionnel pour éviter de charger Selenium si pas nécessaire
def get_scrape_invoices():
    from realt_scraper import scrape_invoices
    return scrape_invoices

def print_step(step_name):
    """Affiche une étape de manière visible"""
    print("\n" + "="*50)
    print(f" {step_name}")
    print("="*50 + "\n")

def run_pipeline(start_step=None, only_step=None, skip_invoices=False):
    """
    Exécute le pipeline complet de traitement des données RealT
    
    Args:
        start_step: À partir de quelle étape commencer (None = début)
        only_step: Exécuter uniquement cette étape (None = toutes les étapes)
        skip_invoices: Ignorer l'étape de téléchargement des factures
    """
    steps = {
        'invoices': {
            'name': 'Téléchargement et analyse des factures',
            'func': lambda: get_scrape_invoices()()
        },
        'blockchain': {
            'name': 'Récupération des transactions blockchain',
            'func': update_transactions
        },
        'purchases': {
            'name': 'Association des achats',
            'func': match_purchases
        },
        'sales': {
            'name': 'Détection et analyse des ventes',
            'func': match_sales
        }
    }

    # Déterminer les étapes à exécuter
    steps_to_run = []
    if only_step:
        if only_step not in steps:
            print(f"Erreur: Étape '{only_step}' inconnue")
            return
        steps_to_run = [only_step]
    else:
        found_start = False
        for step in steps.keys():
            if not start_step or found_start or step == start_step:
                found_start = True
                steps_to_run.append(step)
        
        if start_step and not found_start:
            print(f"Erreur: Étape de départ '{start_step}' inconnue")
            return

    # Exécuter les étapes sélectionnées
    for step in steps_to_run:
        if skip_invoices and step == 'invoices':
            print(f"\nÉtape '{step}' ignorée (--skip-invoices)")
            continue
            
        print_step(steps[step]['name'])
        try:
            steps[step]['func']()
        except Exception as e:
            print(f"\nErreur lors de l'étape '{step}': {str(e)}")
            if not only_step:  # Si on exécute plusieurs étapes, on arrête en cas d'erreur
                sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description='Pipeline de traitement des données RealT pour le suivi des investissements',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation:
  %(prog)s                            # Exécute tout le pipeline dans l'ordre
  %(prog)s --skip-invoices            # Exécute le pipeline en sautant l'étape des factures
  %(prog)s --start-step blockchain    # Commence à partir de l'étape blockchain
  %(prog)s --only-step purchases      # Exécute uniquement l'étape de matching des achats

Ordre d'exécution des étapes:
  1. invoices   : Téléchargement et analyse des factures RealT
  2. blockchain : Récupération des transactions depuis la blockchain
  3. purchases  : Association des factures avec les transactions
  4. sales      : Détection et analyse des ventes
""")
    
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--start-step', choices=['invoices', 'blockchain', 'purchases', 'sales'],
                      help='Commencer le traitement à partir de cette étape')
    group.add_argument('--only-step', choices=['invoices', 'blockchain', 'purchases', 'sales'],
                      help='Exécuter uniquement cette étape')
    
    parser.add_argument('--skip-invoices', action='store_true',
                      help='Ignorer l\'étape de téléchargement des factures')
    
    args = parser.parse_args()
    
    try:
        if args.skip_invoices and args.start_step == 'invoices':
            print("Attention: --skip-invoices est ignoré car --start-step=invoices est spécifié")
            args.skip_invoices = False
            
        run_pipeline(start_step=args.start_step, only_step=args.only_step, skip_invoices=args.skip_invoices)
    except KeyboardInterrupt:
        print("\nInterruption par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        print(f"\nErreur inattendue: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
