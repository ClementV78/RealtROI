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

Pour configurer le projet :
1. Copiez `config.ini.example` vers `config.ini.local`
2. Modifiez `config.ini.local` avec vos paramètres sensibles
3. Les autres paramètres peuvent rester dans `config.ini`

### Format de configuration
```ini
[DEFAULT]
# Votre adresse de portefeuille Gnosis actuelle
gnosis_address = 0x...

# Optionnel : Votre ancienne adresse si vous avez migré
old_gnosis_address = 0x...

# Optionnel : Configuration personnalisée
pdf_invoice_folder = invoices
data_folder = data
```

## 📁 Structure du Projet

```
RealtROI/
├── src/
│   ├── main.py              # Point d'entrée de l'application
│   ├── api_client.py        # Client API pour Gnosis
│   ├── match_purchases.py   # Logique de réconciliation factures/transactions
│   ├── match_sales.py       # Analyse des ventes de tokens
│   ├── invoice_parser.py    # Parser pour les factures RealT
│   ├── blockchain_parser.py # Parser pour les données blockchain
│   ├── db.py               # Gestion de la base de données locale
│   └── utils.py            # Fonctions utilitaires
├── config/
│   └── config.ini          # Configuration (adresses wallet, etc.)
├── data/
│   ├── invoices.json       # Cache des factures RealT
│   ├── transactions.json   # Cache des transactions blockchain
│   ├── purchases.json      # Base de données des achats
│   └── sales.json         # Base de données des ventes
└── invoices/              # Dossier contenant les factures PDF
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

### Import des factures

1. Placez vos factures RealT (format PDF) dans le dossier `invoices/`
2. Exécutez l'analyseur de factures :
   ```bash
   python src/invoice_parser.py
   ```

### Réconciliation des transactions

Pour associer les factures avec les transactions blockchain :
```bash
python src/match_purchases.py
```

Pour analyser les ventes :
```bash
python src/match_sales.py
```

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