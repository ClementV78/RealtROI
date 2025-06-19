# RealtROI

RealtROI est un outil Python conçu pour suivre et analyser vos investissements RealT sur la blockchain Gnosis. Il permet de réconcilier automatiquement les factures RealT avec les transactions blockchain et d'identifier les transactions P2P.

## 🚀 Fonctionnalités

- 📊 Réconciliation automatique des factures RealT avec les transactions blockchain
- 🤝 Détection des transactions P2P (achats directs auprès d'autres utilisateurs)
- 🔄 Suivi des transferts entre portefeuilles
- 📈 Calcul des prix moyens d'achat par propriété

## ⚙️ Configuration

Le projet utilise un système de configuration en couches pour une gestion sécurisée des paramètres :

1. `config/config.ini.local` : Configuration locale (non versionnée, prioritaire)
   - Utilisé pour les secrets (API keys, mots de passe)
   - Spécifique à votre machine
   - Non inclus dans Git

2. `config/config.ini` : Configuration principale
   - Paramètres généraux du projet
   - Peut être versionné si ne contient pas de secrets

3. `config/config.ini.example` : Template de configuration
   - Exemple de configuration avec des valeurs factices
   - Toujours versionné
   - Sert de référence pour créer votre configuration

```

## 📁 Structure du Projet

```
RealtROI/
├── src/                     # Code source
│   ├── main.py             # Point d'entrée de l'application
│   ├── api_client.py       # Client API pour Gnosis
│   ├── match_purchases.py  # Réconciliation factures/transactions
│   ├── match_sales.py      # Analyse des ventes de tokens
│   ├── invoice_parser.py   # Parser pour les factures RealT
│   ├── blockchain_parser.py# Parser pour les données blockchain
│   ├── db.py              # Gestion de la base de données locale
│   ├── utils.py           # Fonctions utilitaires
│   ├── realt_scraper.py   # Scraping des factures RealT
│   └── viewer.py          # Interface de visualisation
│
├── config/                 # Configuration
│   ├── config.ini         # Configuration principale
│   ├── config.ini.local   # Configuration locale (secrets)
│   └── config.ini.example # Template de configuration
│
├── data/                  # Données générées
│   ├── invoices.json     # Cache des factures RealT
│   ├── transactions.json # Cache des transactions blockchain
│   ├── purchases.json    # Base de données des achats
│   └── sales.json       # Base de données des ventes
│
└── invoices/             # Factures PDF RealT
```

## 🛠 Installation

1. Clonez le dépôt :
   ```bash
   git clone https://github.com/ClementV78/RealtROI.git
   cd RealtROI
   ```

2. Installez les dépendances :
   ```bash
   pip install -r requirements.txt
   ```

3. Configurez votre environnement :
   - Copiez `config/config.ini.example` vers `config/config.ini`
   - Ajoutez votre adresse de portefeuille Gnosis
   - (Optionnel) Ajoutez votre ancienne adresse de portefeuille si vous avez migré

## 📋 Utilisation

### Pipeline Complet avec `main.py`

Le script `main.py` est le point d'entrée principal qui permet d'exécuter l'ensemble du pipeline d'analyse :

```bash
python src/main.py [options]
```

#### Étapes du Pipeline
1. **invoices** : Téléchargement et analyse des factures RealT
2. **blockchain** : Récupération des transactions depuis Gnosis
3. **purchases** : Association des factures avec les transactions
4. **sales** : Détection et analyse des ventes

#### Options Disponibles

| Option | Description |
|--------|-------------|
| `--start-step ÉTAPE` | Commence l'exécution à partir d'une étape spécifique |
| `--only-step ÉTAPE` | Exécute uniquement l'étape spécifiée |
| `--skip-invoices` | Ignore l'étape de téléchargement des factures |

Les valeurs possibles pour ÉTAPE sont : `invoices`, `blockchain`, `purchases`, `sales`

#### Exemples d'Utilisation

```bash
# Exécute le pipeline complet
python src/main.py

# Ignore le téléchargement des factures
python src/main.py --skip-invoices

# Commence à partir de l'analyse blockchain
python src/main.py --start-step blockchain

# Exécute uniquement l'association des achats
python src/main.py --only-step purchases
```

### Utilisation Individuelle des Scripts

Si vous préférez exécuter les scripts individuellement :

#### Import des factures

1. Placez vos factures RealT (format PDF) dans le dossier `invoices/`
2. Exécutez l'analyseur de factures :
   ```bash
   python src/invoice_parser.py
   ```

#### Réconciliation des transactions

Pour associer les factures avec les transactions blockchain :
```bash
python src/match_purchases.py
```

Pour analyser les ventes :
```bash
python src/match_sales.py
```

### Cas d'Utilisation Courants

1. **Première utilisation**
   ```bash
   python src/main.py
   ```
   Exécute le pipeline complet pour initialiser votre base de données.

2. **Mise à jour périodique**
   ```bash
   python src/main.py --skip-invoices
   ```
   Met à jour uniquement les transactions blockchain et les analyses, sans re-télécharger les factures.

3. **Après ajout de nouvelles factures**
   ```bash
   python src/main.py --start-step invoices
   ```
   Analyse les nouvelles factures et met à jour les analyses.

4. **Vérification des ventes**
   ```bash
   python src/main.py --only-step sales
   ```
   Analyse uniquement les transactions de vente.

### Gestion des Erreurs

- En cas d'interruption, vous pouvez reprendre le traitement à n'importe quelle étape avec `--start-step`
- Si une étape échoue, corrigez l'erreur puis relancez avec `--start-step` à l'étape qui a échoué
- Pour le débogage, utilisez `--only-step` pour isoler une étape spécifique

## 📊 Exemple de sortie

```
RÉCAPITULATIF DES ACHATS
================================================================================

STATISTIQUES GLOBALES:
Total des produits dans les factures: 81
Produits matchés avec des transactions: 70
Transactions P2P identifiées: 8
Produits non matchés: 11
```

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à :
- Ouvrir une issue pour signaler un bug ou proposer une amélioration
- Soumettre une pull request
- Partager vos idées d'amélioration

## 📝 Licence

Ce projet est sous licence MIT. Voir le fichier LICENSE pour plus de détails.

---
Dernière mise à jour : 19 juin 2025