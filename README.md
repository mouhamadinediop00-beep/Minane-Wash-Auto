# Lavage Méckhé — Logiciel de gestion pour station de lavage automobile

Application de gestion complète, sécurisée et évolutive pour une station de lavage
située à **Méckhé (Région de Thiès, Sénégal)**. Conçue pour un caissier sans
connaissances informatiques : interface tactile en français, base de données locale,
exports Excel/PDF automatiques.

Fonctionne d'abord sous **Windows**, et se recompile en **Android (tablette)** sans
changer le code, grâce au framework Flet (Flutter).

---

## 1. Installation rapide (Windows)

1. Installer **Python 3.10 ou plus récent** depuis <https://www.python.org/downloads/>
   (cocher « Add Python to PATH » à l'installation).
2. Double-cliquer sur **`lancer.bat`**. Les dépendances s'installent automatiquement
   au premier lancement, puis l'application s'ouvre.

Identifiants par défaut :

| Rôle           | Identifiant | Mot de passe |
|----------------|-------------|--------------|
| Administrateur | `admin`     | `admin123`   |
| Gérant         | `gerant`    | `gerant123`  |
| Caissier       | `caissier`  | `caisse123`  |

> Changez ces mots de passe dès la première utilisation (module Paramètres).

---

## 2. Générer l'exécutable (.exe) et l'APK Android

Double-cliquer sur **`compiler.bat`** et choisir la cible :

- **Windows (.exe)** : produit un installateur dans `build/windows/`.
- **Android (.apk)** : produit `build/apk/` — nécessite Flutter et l'Android SDK
  installés (voir <https://docs.flet.dev/publish>).

La commande sous-jacente est simplement :

```
flet build windows     # exécutable Windows
flet build apk         # application Android
```

Le même code source sert aux deux plateformes : aucune réécriture n'est nécessaire
pour passer de Windows à Android.

---

## 3. Architecture du projet

```
lavage_meckhe/
├── main.py              Point d'entrée : connexion + navigation par rôle
├── app/
│   ├── database.py      Schéma SQLite, données de départ, paramètres
│   ├── auth.py          Sécurité : connexion, rôles, droits (MODULE 14)
│   ├── services.py      Logique métier : ventes, stock, KPI, caisse
│   ├── exports.py       Excel lié, rapports PDF/CSV, factures + QR (MODULES 5,12,13)
│   ├── ui.py            Thème et composants réutilisables
│   └── views.py         Les 15 écrans de l'application
├── donnees/             Base de données (créée au 1er lancement)
├── exports/             Fichiers Excel / PDF / CSV générés
├── factures/            Factures, tickets, reçus, devis en PDF
├── sauvegardes/         Sauvegardes automatiques quotidiennes (30 jours)
├── requirements.txt
├── pyproject.toml       Configuration de compilation Flet
├── lancer.bat           Lancement direct
└── compiler.bat         Génération .exe / .apk
```

L'architecture est **en couches** : la base de données et la logique métier
(`database.py`, `services.py`) sont totalement séparées de l'interface (`views.py`,
`ui.py`). On peut ainsi ajouter un module, changer l'affichage ou brancher une
synchronisation cloud sans toucher au cœur métier.

---

## 4. Les modules

| # | Module | Contenu |
|---|--------|---------|
| 1 | Tableau de bord | CA jour/semaine/mois, comptages, bénéfice, alertes, graphique |
| 2 | Prestations | 16 prestations pré-remplies, prix, durée, produits consommés, TVA |
| 3 | Clients | Fiche, type, carte fidélité, historique (visites, total, dernière visite) |
| 4 | Caisse | Encaissement tactile, 6 modes de paiement, monnaie rendue, journal |
| 5 | Facturation | Facture, facture simplifiée, ticket, reçu, devis + QR code, numérotation auto |
| 6 | Stock | 13 produits, stock réel calculé, seuil critique, péremption, valeur |
| 7 | Achats | Commande → réception → stock, paiement fournisseur |
| 8 | Dépenses | 9 catégories, justificatif photo |
| 9 | Employés | Fiche, salaire, prime, absences, productivité |
| 10 | Véhicules | Historique par plaque : lavages, montant total, dernier passage |
| 11 | KPI | Commercial, exploitation, stock, finance, marketing, top 20 clients |
| 12 | Rapports | Export Excel + PDF + CSV, périodes jour/semaine/mois/année |
| 13 | Classeur Excel | Toutes les feuilles liées + tableau de bord à formules |
| 14 | Sécurité | 4 profils, droits par module, sauvegarde quotidienne |
| 15 | Technologies | Python + Flet, SQLite, Windows/Android, exports auto |

---

## 5. Sécurité et sauvegarde

- Mots de passe **hachés** (PBKDF2-SHA256, 200 000 itérations, sel unique) : jamais
  stockés en clair.
- **Droits par rôle** : le caissier ne voit ni les achats, ni les employés, ni les
  paramètres ; seul l'administrateur gère les utilisateurs.
- **Sauvegarde automatique** de la base à chaque démarrage dans `sauvegardes/`
  (30 jours conservés). Sauvegarde manuelle possible depuis Paramètres.

---

## 6. Évolutions prévues

- **Synchronisation cloud** : `database.py` isole déjà toute la persistance ; il
  suffit de remplacer SQLite par PostgreSQL (chaîne de connexion) pour centraliser
  plusieurs stations.
- **Lecteur de code-barres / QR** sur les tickets.
- **Impression thermique** directe des tickets.

---

*Développé pour la station de lavage de Méckhé — Région de Thiès, Sénégal.*
