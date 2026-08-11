# -*- coding: utf-8 -*-
"""
LAVAGE MECKHE - Module base de données
--------------------------------------
Schéma SQLite complet, connexion, initialisation et données de départ.
Tous les montants sont en FCFA (entiers).
"""

import os
import sqlite3
import hashlib
import secrets
from datetime import date

# Répertoire de données (à côté de l'exécutable / du projet)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "donnees")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "lavage_meckhe.db")


def get_conn():
    """Retourne une connexion SQLite avec clés étrangères activées."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ----------------------------------------------------------------------
# SCHEMA
# ----------------------------------------------------------------------
SCHEMA = """
-- MODULE 14 : utilisateurs & sécurité
CREATE TABLE IF NOT EXISTS utilisateurs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    identifiant TEXT UNIQUE NOT NULL,
    nom TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('Administrateur','Gérant','Caissier','Opérateur')),
    sel TEXT NOT NULL,
    mot_de_passe TEXT NOT NULL,
    actif INTEGER NOT NULL DEFAULT 1
);

-- Paramètres de l'entreprise (facturation)
CREATE TABLE IF NOT EXISTS parametres (
    cle TEXT PRIMARY KEY,
    valeur TEXT
);

-- MODULE 2 : prestations
CREATE TABLE IF NOT EXISTS prestations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    nom TEXT NOT NULL,
    type_vehicule TEXT NOT NULL DEFAULT 'autre',   -- moto / voiture / camion / bus / autre
    type_lavage TEXT NOT NULL DEFAULT 'option',    -- exterieur / interieur / complet / option
    prix INTEGER NOT NULL,
    duree_min INTEGER NOT NULL DEFAULT 20,
    tva REAL NOT NULL DEFAULT 0,
    actif INTEGER NOT NULL DEFAULT 1
);

-- Produits consommés automatiquement par prestation
CREATE TABLE IF NOT EXISTS prestation_produits (
    prestation_id INTEGER NOT NULL REFERENCES prestations(id) ON DELETE CASCADE,
    produit_id INTEGER NOT NULL REFERENCES produits(id) ON DELETE CASCADE,
    quantite REAL NOT NULL,
    PRIMARY KEY (prestation_id, produit_id)
);

-- MODULE 3 : clients
CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    telephone TEXT,
    adresse TEXT,
    profession TEXT,
    entreprise TEXT,
    type_client TEXT NOT NULL DEFAULT 'Particulier'
        CHECK (type_client IN ('Particulier','Entreprise','Administration','VIP')),
    carte_fidelite INTEGER NOT NULL DEFAULT 0,
    date_creation TEXT NOT NULL DEFAULT (date('now'))
);

-- ABONNEMENTS : formules proposées
CREATE TABLE IF NOT EXISTS formules_abonnement (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'quota'
        CHECK (type IN ('quota','illimite','entreprise')),
    prix INTEGER NOT NULL,
    nb_lavages INTEGER NOT NULL DEFAULT 0,   -- 0 = illimité / sans quota
    duree_jours INTEGER NOT NULL DEFAULT 30, -- validité
    prioritaire INTEGER NOT NULL DEFAULT 0,
    facturation_mensuelle INTEGER NOT NULL DEFAULT 0,
    description TEXT,
    actif INTEGER NOT NULL DEFAULT 1
);

-- ABONNEMENTS : souscriptions des clients
CREATE TABLE IF NOT EXISTS abonnements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    formule_id INTEGER NOT NULL REFERENCES formules_abonnement(id),
    date_debut TEXT NOT NULL DEFAULT (date('now')),
    date_fin TEXT NOT NULL,
    lavages_inclus INTEGER NOT NULL DEFAULT 0,   -- copie du quota au moment de la souscription (0 = illimité)
    lavages_utilises INTEGER NOT NULL DEFAULT 0,
    prix_paye INTEGER NOT NULL DEFAULT 0,
    statut TEXT NOT NULL DEFAULT 'Actif'
        CHECK (statut IN ('Actif','Expiré','Suspendu')),
    date_creation TEXT NOT NULL DEFAULT (date('now'))
);
CREATE INDEX IF NOT EXISTS idx_abo_client ON abonnements(client_id);

-- MODULE 10 : véhicules
CREATE TABLE IF NOT EXISTS vehicules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plaque TEXT UNIQUE NOT NULL,
    marque TEXT,
    modele TEXT,
    couleur TEXT,
    categorie TEXT NOT NULL DEFAULT 'voiture',  -- moto / voiture / camion / bus
    client_id INTEGER REFERENCES clients(id) ON DELETE SET NULL
);

-- MODULE 6 : fournisseurs et stock
CREATE TABLE IF NOT EXISTS fournisseurs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    telephone TEXT,
    adresse TEXT
);

CREATE TABLE IF NOT EXISTS produits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    nom TEXT NOT NULL,
    categorie TEXT NOT NULL DEFAULT 'Consommable',
    unite TEXT NOT NULL DEFAULT 'unité',
    stock_initial REAL NOT NULL DEFAULT 0,
    stock_min REAL NOT NULL DEFAULT 0,
    prix_achat INTEGER NOT NULL DEFAULT 0,
    date_peremption TEXT,
    fournisseur_id INTEGER REFERENCES fournisseurs(id) ON DELETE SET NULL,
    actif INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS mouvements_stock (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    produit_id INTEGER NOT NULL REFERENCES produits(id) ON DELETE CASCADE,
    date TEXT NOT NULL DEFAULT (date('now')),
    type TEXT NOT NULL CHECK (type IN ('ENTREE','SORTIE')),
    quantite REAL NOT NULL,
    motif TEXT,
    reference TEXT
);

-- MODULE 4 : caisse / ventes
CREATE TABLE IF NOT EXISTS ventes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT UNIQUE NOT NULL,
    date TEXT NOT NULL DEFAULT (date('now')),
    heure TEXT NOT NULL DEFAULT (time('now','localtime')),
    caissier_id INTEGER REFERENCES utilisateurs(id),
    client_id INTEGER REFERENCES clients(id),
    vehicule_id INTEGER REFERENCES vehicules(id),
    montant_brut INTEGER NOT NULL,
    remise INTEGER NOT NULL DEFAULT 0,
    montant_net INTEGER NOT NULL,
    mode_paiement TEXT NOT NULL DEFAULT 'Espèces',
    montant_paye INTEGER NOT NULL DEFAULT 0,
    monnaie_rendue INTEGER NOT NULL DEFAULT 0,
    statut TEXT NOT NULL DEFAULT 'Payée'
        CHECK (statut IN ('Payée','En attente','Annulée'))
);

CREATE TABLE IF NOT EXISTS vente_lignes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vente_id INTEGER NOT NULL REFERENCES ventes(id) ON DELETE CASCADE,
    prestation_id INTEGER NOT NULL REFERENCES prestations(id),
    prix INTEGER NOT NULL,
    quantite INTEGER NOT NULL DEFAULT 1
);

-- Revente de produits (produits de lavage / entretien vendus au client)
CREATE TABLE IF NOT EXISTS vente_produits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vente_id INTEGER NOT NULL REFERENCES ventes(id) ON DELETE CASCADE,
    produit_id INTEGER NOT NULL REFERENCES produits(id),
    prix INTEGER NOT NULL,
    quantite REAL NOT NULL DEFAULT 1
);

-- MODULE 5 : documents (factures, devis, tickets, reçus)
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT UNIQUE NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('Facture','Facture simplifiée','Ticket','Reçu','Devis')),
    vente_id INTEGER REFERENCES ventes(id) ON DELETE CASCADE,
    date TEXT NOT NULL DEFAULT (date('now')),
    fichier TEXT
);

-- MODULE 7 : achats
CREATE TABLE IF NOT EXISTS achats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT UNIQUE NOT NULL,
    date TEXT NOT NULL DEFAULT (date('now')),
    fournisseur_id INTEGER REFERENCES fournisseurs(id),
    statut TEXT NOT NULL DEFAULT 'Commande'
        CHECK (statut IN ('Commande','Livrée','Facturée','Payée')),
    total INTEGER NOT NULL DEFAULT 0,
    montant_paye INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS achat_lignes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    achat_id INTEGER NOT NULL REFERENCES achats(id) ON DELETE CASCADE,
    produit_id INTEGER NOT NULL REFERENCES produits(id),
    quantite REAL NOT NULL,
    prix_unitaire INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS paiements_fournisseurs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    achat_id INTEGER NOT NULL REFERENCES achats(id) ON DELETE CASCADE,
    date TEXT NOT NULL DEFAULT (date('now')),
    montant INTEGER NOT NULL,
    mode TEXT NOT NULL DEFAULT 'Espèces'
);

-- MODULE 8 : dépenses
CREATE TABLE IF NOT EXISTS depenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL DEFAULT (date('now')),
    categorie TEXT NOT NULL DEFAULT 'Divers'
        CHECK (categorie IN ('Electricité','Eau','Salaires','Maintenance','Produits',
                             'Carburant','Internet','Téléphone','Divers')),
    libelle TEXT NOT NULL,
    montant INTEGER NOT NULL,
    mode_paiement TEXT NOT NULL DEFAULT 'Espèces',
    photo TEXT
);

-- MODULE 9 : employés
CREATE TABLE IF NOT EXISTS employes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    telephone TEXT,
    fonction TEXT,
    salaire INTEGER NOT NULL DEFAULT 0,
    prime INTEGER NOT NULL DEFAULT 0,
    horaires TEXT DEFAULT '08h00 - 20h00',
    actif INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS absences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employe_id INTEGER NOT NULL REFERENCES employes(id) ON DELETE CASCADE,
    date TEXT NOT NULL DEFAULT (date('now')),
    type TEXT NOT NULL DEFAULT 'Absence' CHECK (type IN ('Absence','Congé','Retard','Maladie')),
    motif TEXT
);

-- Lien vente -> employé (productivité / CA par employé)
CREATE TABLE IF NOT EXISTS vente_employes (
    vente_id INTEGER NOT NULL REFERENCES ventes(id) ON DELETE CASCADE,
    employe_id INTEGER NOT NULL REFERENCES employes(id) ON DELETE CASCADE,
    PRIMARY KEY (vente_id, employe_id)
);

CREATE INDEX IF NOT EXISTS idx_ventes_date ON ventes(date);
CREATE INDEX IF NOT EXISTS idx_mvt_produit ON mouvements_stock(produit_id);
CREATE INDEX IF NOT EXISTS idx_depenses_date ON depenses(date);

-- Journal d'audit : traçabilité des actions
CREATE TABLE IF NOT EXISTS audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL DEFAULT (date('now')),
    heure TEXT NOT NULL DEFAULT (time('now','localtime')),
    utilisateur_id INTEGER,
    utilisateur TEXT,
    action TEXT NOT NULL,
    details TEXT
);
CREATE INDEX IF NOT EXISTS idx_audit_date ON audit(date);

-- Sites / agences de lavage (multi-site)
CREATE TABLE IF NOT EXISTS sites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    adresse TEXT,
    telephone TEXT,
    responsable TEXT,
    actif INTEGER NOT NULL DEFAULT 1
);

-- =====================================================================
-- NOUVEAU MODULE : LOCAL-FIRST SYNCHRONISATION
-- =====================================================================
CREATE TABLE IF NOT EXISTS sync_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom_table TEXT NOT NULL,
    enregistrement_id INTEGER NOT NULL,
    action TEXT NOT NULL,                   -- 'INSERT', 'UPDATE', 'DELETE'
    statut TEXT NOT NULL DEFAULT 'en_attente', -- 'en_attente', 'succes', 'erreur'
    tentatives INTEGER NOT NULL DEFAULT 0,
    dernier_erreur TEXT,
    cree_le TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- TRIGGERS AUTOMATIQUES : Capture les écritures en temps réel sans toucher au code Python
CREATE TRIGGER IF NOT EXISTS trg_ventes_ins AFTER INSERT ON ventes BEGIN INSERT INTO sync_queue (nom_table, enregistrement_id, action) VALUES ('ventes', NEW.id, 'INSERT'); END;
CREATE TRIGGER IF NOT EXISTS trg_ventes_upd AFTER UPDATE ON ventes BEGIN INSERT INTO sync_queue (nom_table, enregistrement_id, action) VALUES ('ventes', NEW.id, 'UPDATE'); END;
CREATE TRIGGER IF NOT EXISTS trg_ventes_del AFTER DELETE ON ventes BEGIN INSERT INTO sync_queue (nom_table, enregistrement_id, action) VALUES ('ventes', OLD.id, 'DELETE'); END;

CREATE TRIGGER IF NOT EXISTS trg_vente_lignes_ins AFTER INSERT ON vente_lignes BEGIN INSERT INTO sync_queue (nom_table, enregistrement_id, action) VALUES ('vente_lignes', NEW.id, 'INSERT'); END;
CREATE TRIGGER IF NOT EXISTS trg_vente_lignes_upd AFTER UPDATE ON vente_lignes BEGIN INSERT INTO sync_queue (nom_table, enregistrement_id, action) VALUES ('vente_lignes', NEW.id, 'UPDATE'); END;
CREATE TRIGGER IF NOT EXISTS trg_vente_lignes_del AFTER DELETE ON vente_lignes BEGIN INSERT INTO sync_queue (nom_table, enregistrement_id, action) VALUES ('vente_lignes', OLD.id, 'DELETE'); END;

CREATE TRIGGER IF NOT EXISTS trg_vente_produits_ins AFTER INSERT ON vente_produits BEGIN INSERT INTO sync_queue (nom_table, enregistrement_id, action) VALUES ('vente_produits', NEW.id, 'INSERT'); END;
CREATE TRIGGER IF NOT EXISTS trg_vente_produits_upd AFTER UPDATE ON vente_produits BEGIN INSERT INTO sync_queue (nom_table, enregistrement_id, action) VALUES ('vente_produits', NEW.id, 'UPDATE'); END;
CREATE TRIGGER IF NOT EXISTS trg_vente_produits_del AFTER DELETE ON vente_produits BEGIN INSERT INTO sync_queue (nom_table, enregistrement_id, action) VALUES ('vente_produits', OLD.id, 'DELETE'); END;

CREATE TRIGGER IF NOT EXISTS trg_depenses_ins AFTER INSERT ON depenses BEGIN INSERT INTO sync_queue (nom_table, enregistrement_id, action) VALUES ('depenses', NEW.id, 'INSERT'); END;
CREATE TRIGGER IF NOT EXISTS trg_depenses_upd AFTER UPDATE ON depenses BEGIN INSERT INTO sync_queue (nom_table, enregistrement_id, action) VALUES ('depenses', NEW.id, 'UPDATE'); END;
CREATE TRIGGER IF NOT EXISTS trg_depenses_del AFTER DELETE ON depenses BEGIN INSERT INTO sync_queue (nom_table, enregistrement_id, action) VALUES ('depenses', OLD.id, 'DELETE'); END;

CREATE TRIGGER IF NOT EXISTS trg_clients_ins AFTER INSERT ON clients BEGIN INSERT INTO sync_queue (nom_table, enregistrement_id, action) VALUES ('clients', NEW.id, 'INSERT'); END;
CREATE TRIGGER IF NOT EXISTS trg_clients_upd AFTER UPDATE ON clients BEGIN INSERT INTO sync_queue (nom_table, enregistrement_id, action) VALUES ('clients', NEW.id, 'UPDATE'); END;
CREATE TRIGGER IF NOT EXISTS trg_clients_del AFTER DELETE ON clients BEGIN INSERT INTO sync_queue (nom_table, enregistrement_id, action) VALUES ('clients', OLD.id, 'DELETE'); END;

CREATE TRIGGER IF NOT EXISTS trg_vehicules_ins AFTER INSERT ON vehicules BEGIN INSERT INTO sync_queue (nom_table, enregistrement_id, action) VALUES ('vehicules', NEW.id, 'INSERT'); END;
CREATE TRIGGER IF NOT EXISTS trg_vehicules_upd AFTER UPDATE ON vehicules BEGIN INSERT INTO sync_queue (nom_table, enregistrement_id, action) VALUES ('vehicules', NEW.id, 'UPDATE'); END;
CREATE TRIGGER IF NOT EXISTS trg_vehicules_del AFTER DELETE ON vehicules BEGIN INSERT INTO sync_queue (nom_table, enregistrement_id, action) VALUES ('vehicules', OLD.id, 'DELETE'); END;

CREATE TRIGGER IF NOT EXISTS trg_mouvements_stock_ins AFTER INSERT ON mouvements_stock BEGIN INSERT INTO sync_queue (nom_table, enregistrement_id, action) VALUES ('mouvements_stock', NEW.id, 'INSERT'); END;
CREATE TRIGGER IF NOT EXISTS trg_mouvements_stock_upd AFTER UPDATE ON mouvements_stock BEGIN INSERT INTO sync_queue (nom_table, enregistrement_id, action) VALUES ('mouvements_stock', NEW.id, 'UPDATE'); END;
CREATE TRIGGER IF NOT EXISTS trg_mouvements_stock_del AFTER DELETE ON mouvements_stock BEGIN INSERT INTO sync_queue (nom_table, enregistrement_id, action) VALUES ('mouvements_stock', OLD.id, 'DELETE'); END;

CREATE TRIGGER IF NOT EXISTS trg_abonnements_ins AFTER INSERT ON abonnements BEGIN INSERT INTO sync_queue (nom_table, enregistrement_id, action) VALUES ('abonnements', NEW.id, 'INSERT'); END;
CREATE TRIGGER IF NOT EXISTS trg_abonnements_upd AFTER UPDATE ON abonnements BEGIN INSERT INTO sync_queue (nom_table, enregistrement_id, action) VALUES ('abonnements', NEW.id, 'UPDATE'); END;
CREATE TRIGGER IF NOT EXISTS trg_abonnements_del AFTER DELETE ON abonnements BEGIN INSERT INTO sync_queue (nom_table, enregistrement_id, action) VALUES ('abonnements', OLD.id, 'DELETE'); END;
"""


def hacher_mot_de_passe(mot_de_passe: str, sel: str) -> str:
    """Hachage SHA-256 salé (200 000 itérations PBKDF2)."""
    return hashlib.pbkdf2_hmac(
        "sha256", mot_de_passe.encode("utf-8"), sel.encode("utf-8"), 200_000
    ).hex()


# ----------------------------------------------------------------------
# DONNEES DE DEPART
# ----------------------------------------------------------------------
PRESTATIONS_DEFAUT = [
    ("LAV-MOT", "Lavage moto",             "moto",    "exterieur", 1000, 15, 0),
    ("LAV-CIT", "Lavage voiture citadine", "voiture", "exterieur", 2000, 25, 0),
    ("LAV-SUV", "Lavage SUV / 4x4",        "voiture", "exterieur", 3000, 30, 0),
    ("LAV-PIC", "Lavage Pick-up",          "voiture", "exterieur", 3500, 35, 0),
    ("LAV-CAM", "Lavage camion",           "camion",  "exterieur", 7500, 60, 0),
    ("LAV-BUS", "Lavage bus",              "bus",     "exterieur", 6000, 50, 0),
    ("LAV-INT", "Lavage intérieur",        "autre",   "interieur", 2000, 30, 0),
    ("LAV-CPL", "Lavage complet",          "voiture", "complet",   4500, 60, 0),
    ("LAV-MOT2","Lavage moteur",           "autre",   "option",    2500, 25, 0),
    ("POLISH",  "Polish carrosserie",      "autre",   "option",    10000, 90, 0),
    ("LUSTR",   "Lustrage",                "autre",   "option",    7500, 60, 0),
    ("ASPIR",   "Aspiration",              "autre",   "option",    1000, 15, 0),
    ("DESINF",  "Désinfection habitacle",  "autre",   "option",    3000, 25, 0),
    ("CUIR",    "Traitement cuir",         "autre",   "option",    5000, 40, 0),
    ("PLAST",   "Traitement plastiques",   "autre",   "option",    3000, 30, 0),
    ("CIRE",    "Cire de protection",      "autre",   "option",    4000, 30, 0),
]

PRODUITS_DEFAUT = [
    ("SHP", "Shampooing auto",     "Produit lavage", "litre",  50, 10, 1500),
    ("DET", "Détergent",           "Produit lavage", "litre",  40, 10, 1000),
    ("CIR", "Cire",                "Produit finition","litre", 10, 2,  5000),
    ("PAR", "Parfum habitacle",    "Produit finition","unité", 30, 5,  1000),
    ("NJT", "Nettoyant jantes",    "Produit lavage", "litre",  15, 3,  2500),
    ("NMT", "Nettoyant moteur",    "Produit lavage", "litre",  15, 3,  3000),
    ("MCF", "Microfibres",         "Matériel",       "unité",  40, 10, 500),
    ("GNT", "Gants",               "Matériel",       "paire",  20, 5,  750),
    ("EPG", "Éponges",             "Matériel",       "unité",  30, 10, 300),
    ("SAC", "Sacs poubelles",      "Matériel",       "rouleau",10, 3,  1000),
    ("GAS", "Gasoil",              "Carburant",      "litre",  60, 20, 755),
    ("ESS", "Essence",             "Carburant",      "litre",  40, 15, 990),
    ("HCP", "Huile compresseur",   "Maintenance",    "litre",  8,  2,  4500),
]

CONSOMMATIONS_DEFAUT = [
    ("LAV-MOT", "SHP", 0.05), ("LAV-MOT", "DET", 0.05),
    ("LAV-CIT", "SHP", 0.10), ("LAV-CIT", "DET", 0.10),
    ("LAV-SUV", "SHP", 0.15), ("LAV-SUV", "DET", 0.15),
    ("LAV-PIC", "SHP", 0.15), ("LAV-PIC", "DET", 0.15),
    ("LAV-CAM", "SHP", 0.40), ("LAV-CAM", "DET", 0.40),
    ("LAV-BUS", "SHP", 0.35), ("LAV-BUS", "DET", 0.35),
    ("LAV-INT", "PAR", 0.50), ("LAV-INT", "DET", 0.05),
    ("LAV-CPL", "SHP", 0.15), ("LAV-CPL", "DET", 0.15), ("LAV-CPL", "PAR", 0.50),
    ("LAV-MOT2","NMT", 0.20),
    ("POLISH",  "CIR", 0.20), ("LUSTR", "CIR", 0.10),
    ("DESINF",  "DET", 0.10), ("CIRE",  "CIR", 0.15),
    ("CUIR",    "MCF", 1.0),  ("PLAST", "MCF", 1.0),
]

PRODUITS_REVENTE_DEFAUT = [
    ("RV-PARF", "Parfum voiture (sapin)",     "Revente", "unité",     40, 10,  800, 1500),
    ("RV-SHMP", "Shampooing auto 1L",         "Revente", "bouteille", 25,  5, 2500, 4000),
    ("RV-CIRE", "Cire lustrante 500ml",       "Revente", "bouteille", 15,  3, 3500, 6000),
    ("RV-MICR", "Chiffon microfibre",         "Revente", "unité",     50, 10,  500, 1000),
    ("RV-EPNG", "Éponge de lavage",           "Revente", "unité",     40, 10,  300,  700),
    ("RV-JANT", "Nettoyant jantes 500ml",     "Revente", "bouteille", 12,  3, 2500, 4500),
    ("RV-TBRD", "Rénovateur tableau de bord", "Revente", "bouteille", 15,  3, 2000, 3500),
    ("RV-GANT", "Gant de lavage microfibre",  "Revente", "unité",     20,  5, 1000, 2000),
]

FORMULES_ABONNEMENT_DEFAUT = [
    ("Mensuel", "quota", 25000, 8, 30, 0, 0,
     "8 lavages par mois — idéal pour un usage régulier."),
    ("Premium", "illimite", 45000, 0, 30, 1, 0,
     "Lavages illimités + passage prioritaire (file d'attente réduite)."),
    ("Entreprise", "entreprise", 0, 0, 30, 1, 1,
     "Lavages illimités pour une flotte, facturation mensuelle sur relevé."),
]

PARAMETRES_DEFAUT = {
    "entreprise_nom": "MINAN WASH AUTO",
    "entreprise_slogan": "Votre véhicule mérite le meilleur",
    "entreprise_ninea": "A DEFINIR",
    "entreprise_rccm": "A DEFINIR",
    "entreprise_adresse": "Méckhé, Région de Thiès, Sénégal",
    "entreprise_telephone": "+221 77 781 16 46",
    "entreprise_telephone2": "+221 76 000 00 00",
    "entreprise_email": "contact@minanwashauto.sn",
    "email_expediteur": "",
    "email_mot_de_passe": "",
    "email_smtp_serveur": "smtp.gmail.com",
    "email_smtp_port": "587",
    "auto_refresh_intervalle": "20",
    "anthropic_api_key": "",
    "anthropic_modele": "",
    "entreprise_logo": "",
    "seuil_fidelite": "5",
}


def initialiser_base():
    """Crée les tables, les triggers et insère les données de départ si la base est vide."""
    conn = get_conn()
    conn.executescript(SCHEMA)

    # --- Migrations ---
    colonnes_produits = [r["name"] for r in conn.execute("PRAGMA table_info(produits)").fetchall()]
    if "prix_vente" not in colonnes_produits:
        conn.execute("ALTER TABLE produits ADD COLUMN prix_vente INTEGER NOT NULL DEFAULT 0")
    if "revendable" not in colonnes_produits:
        conn.execute("ALTER TABLE produits ADD COLUMN revendable INTEGER NOT NULL DEFAULT 0")
    colonnes_ventes = [r["name"] for r in conn.execute("PRAGMA table_info(ventes)").fetchall()]
    if "abonnement_id" not in colonnes_ventes:
        conn.execute("ALTER TABLE ventes ADD COLUMN abonnement_id INTEGER")
    colonnes_clients = [r["name"] for r in conn.execute("PRAGMA table_info(clients)").fetchall()]
    if "email" not in colonnes_clients:
        conn.execute("ALTER TABLE clients ADD COLUMN email TEXT")
    conn.commit()

    # Reconstruction ventes (migration mode_paiement)
    sql_ventes = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='ventes'").fetchone()
    if sql_ventes and "CHECK (mode_paiement" in (sql_ventes["sql"] or ""):
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.executescript("""
            CREATE TABLE ventes_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero TEXT UNIQUE NOT NULL,
                date TEXT NOT NULL DEFAULT (date('now')),
                heure TEXT NOT NULL DEFAULT (time('now','localtime')),
                caissier_id INTEGER,
                client_id INTEGER,
                vehicule_id INTEGER,
                montant_brut INTEGER NOT NULL,
                remise INTEGER NOT NULL DEFAULT 0,
                montant_net INTEGER NOT NULL,
                mode_paiement TEXT NOT NULL DEFAULT 'Espèces',
                montant_paye INTEGER NOT NULL DEFAULT 0,
                monnaie_rendue INTEGER NOT NULL DEFAULT 0,
                statut TEXT NOT NULL DEFAULT 'Payée',
                abonnement_id INTEGER
            );
            INSERT INTO ventes_new (id, numero, date, heure, caissier_id, client_id, vehicule_id,
                montant_brut, remise, montant_net, mode_paiement, montant_paye, monnaie_rendue,
                statut, abonnement_id)
            SELECT id, numero, date, heure, caissier_id, client_id, vehicule_id,
                montant_brut, remise, montant_net, mode_paiement, montant_paye, monnaie_rendue,
                statut, abonnement_id FROM ventes;
            DROP TABLE ventes;
            ALTER TABLE ventes_new RENAME TO ventes;
            CREATE INDEX IF NOT EXISTS idx_ventes_date ON ventes(date);
        """)
        conn.execute("PRAGMA foreign_keys=ON")
        conn.commit()

    # Multi-site
    cols_ventes2 = [r["name"] for r in conn.execute("PRAGMA table_info(ventes)").fetchall()]
    if "site_id" not in cols_ventes2:
        conn.execute("ALTER TABLE ventes ADD COLUMN site_id INTEGER NOT NULL DEFAULT 1")
    cols_dep = [r["name"] for r in conn.execute("PRAGMA table_info(depenses)").fetchall()]
    if "site_id" not in cols_dep:
        conn.execute("ALTER TABLE depenses ADD COLUMN site_id INTEGER NOT NULL DEFAULT 1")
    cols_mvt = [r["name"] for r in conn.execute("PRAGMA table_info(mouvements_stock)").fetchall()]
    if "site_id" not in cols_mvt:
        conn.execute("ALTER TABLE mouvements_stock ADD COLUMN site_id INTEGER NOT NULL DEFAULT 1")
    cols_ach = [r["name"] for r in conn.execute("PRAGMA table_info(achats)").fetchall()]
    if "site_id" not in cols_ach:
        conn.execute("ALTER TABLE achats ADD COLUMN site_id INTEGER NOT NULL DEFAULT 1")
    conn.commit()

    if conn.execute("SELECT COUNT(*) FROM sites").fetchone()[0] == 0:
        conn.execute(
            "INSERT INTO sites (id, nom, adresse, telephone, responsable) VALUES (1,?,?,?,?)",
            (
                get_parametre("entreprise_nom", "MINAN WASH AUTO") + " — Méckhé",
                get_parametre("entreprise_adresse", "Méckhé, Thiès, Sénégal"),
                get_parametre("entreprise_telephone", ""),
                ""
            )
        )
        conn.commit()

    # Utilisateur admin par défaut
    if conn.execute("SELECT COUNT(*) FROM utilisateurs").fetchone()[0] == 0:
        for identifiant, nom, role, mdp in [
            ("moustapha",    "Administrateur", "Administrateur", "root.min@ne.w@sh")
        ]:
            sel = secrets.token_hex(16)
            conn.execute(
                "INSERT INTO utilisateurs (identifiant, nom, role, sel, mot_de_passe) VALUES (?,?,?,?,?)",
                (identifiant, nom, role, sel, hacher_mot_de_passe(mdp, sel)),
            )

    if conn.execute("SELECT COUNT(*) FROM parametres").fetchone()[0] == 0:
        conn.executemany("INSERT INTO parametres (cle, valeur) VALUES (?,?)", PARAMETRES_DEFAUT.items())

    if conn.execute("SELECT COUNT(*) FROM prestations").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO prestations (code, nom, type_vehicule, type_lavage, prix, duree_min, tva) VALUES (?,?,?,?,?,?,?)",
            PRESTATIONS_DEFAUT,
        )

    if conn.execute("SELECT COUNT(*) FROM produits").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO produits (code, nom, categorie, unite, stock_initial, stock_min, prix_achat) VALUES (?,?,?,?,?,?,?)",
            PRODUITS_DEFAUT,
        )
        for cp, cprod, q in CONSOMMATIONS_DEFAUT:
            conn.execute(
                "INSERT INTO prestation_produits (prestation_id, produit_id, quantite) "
                "SELECT p.id, pr.id, ? FROM prestations p, produits pr WHERE p.code=? AND pr.code=?",
                (q, cp, cprod),
            )
        for code, nom, cat, unite, stock, mini, achat, vente in PRODUITS_REVENTE_DEFAUT:
            conn.execute(
                "INSERT INTO produits (code, nom, categorie, unite, stock_initial, stock_min, prix_achat, prix_vente, revendable) VALUES (?,?,?,?,?,?,?,?,1)",
                (code, nom, cat, unite, stock, mini, achat, vente),
            )

    if conn.execute("SELECT COUNT(*) FROM formules_abonnement").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO formules_abonnement (nom, type, prix, nb_lavages, duree_jours, prioritaire, facturation_mensuelle, description) VALUES (?,?,?,?,?,?,?,?)",
            FORMULES_ABONNEMENT_DEFAUT,
        )

    conn.commit()

    if conn.execute("SELECT valeur FROM parametres WHERE cle='stock_migre_sites'").fetchone() is None:
        for p in conn.execute("SELECT id, stock_initial FROM produits WHERE stock_initial > 0").fetchall():
            conn.execute(
                "INSERT INTO mouvements_stock (produit_id, type, quantite, motif, site_id) VALUES (?, 'ENTREE', ?, 'Stock initial', 1)",
                (p["id"], p["stock_initial"]))
        conn.execute("UPDATE produits SET stock_initial = 0")
        conn.execute("INSERT INTO parametres (cle, valeur) VALUES ('stock_migre_sites','oui')")
        conn.commit()

    conn.close()


def get_parametre(cle: str, defaut: str = "") -> str:
    conn = get_conn()
    row = conn.execute("SELECT valeur FROM parametres WHERE cle=?", (cle,)).fetchone()
    conn.close()
    return row["valeur"] if row else defaut


def set_parametre(cle: str, valeur: str):
    conn = get_conn()
    conn.execute(
        "INSERT INTO parametres (cle, valeur) VALUES (?,?) ON CONFLICT(cle) DO UPDATE SET valeur=excluded.valeur",
        (cle, valeur),
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    initialiser_base()
    print("Base initialisée avec Triggers Local-First :", DB_PATH)