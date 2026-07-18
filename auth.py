# -*- coding: utf-8 -*-
"""
LAVAGE MECKHE - Module sécurité (MODULE 14)
Connexion des utilisateurs, rôles et droits d'accès par module.
"""

import secrets
from .database import get_conn, hacher_mot_de_passe

# Droits d'accès par défaut : quel rôle voit quel module
DROITS = {
    "tableau_de_bord": ["Administrateur", "Gérant", "Caissier", "Opérateur"],
    "analyse":         ["Administrateur", "Gérant"],
    "caisse":          ["Administrateur", "Gérant", "Caissier"],
    "clients":         ["Administrateur", "Gérant", "Caissier"],
    "abonnements":     ["Administrateur", "Gérant", "Caissier"],
    "crm":             ["Administrateur", "Gérant"],
    "vehicules":       ["Administrateur", "Gérant", "Caissier", "Opérateur"],
    "prestations":     ["Administrateur", "Gérant"],
    "stock":           ["Administrateur", "Gérant", "Opérateur"],
    "achats":          ["Administrateur", "Gérant"],
    "depenses":        ["Administrateur", "Gérant"],
    "employes":        ["Administrateur", "Gérant"],
    "rapports":        ["Administrateur", "Gérant"],
    "sites":           ["Administrateur", "Gérant"],
    "audit":           ["Administrateur"],
    "parametres":      ["Administrateur"],
}

# Libellés lisibles des modules (pour l'écran de gestion des accès)
MODULES_LABELS = [
    ("tableau_de_bord", "Tableau de bord"),
    ("analyse",         "Analyse & conseils"),
    ("caisse",          "Caisse + Journal de caisse"),
    ("clients",         "Clients"),
    ("abonnements",     "Abonnements"),
    ("crm",             "CRM WhatsApp"),
    ("vehicules",       "Véhicules"),
    ("prestations",     "Prestations"),
    ("stock",           "Stock"),
    ("achats",          "Achats"),
    ("depenses",        "Dépenses"),
    ("employes",        "Employés"),
    ("rapports",        "Rapports & KPI"),
    ("sites",           "Sites & comparaison"),
    ("parametres",      "Paramètres (réservé admin)"),
]


def _table_droits():
    conn = get_conn()
    conn.execute("""CREATE TABLE IF NOT EXISTS droits_utilisateur (
        utilisateur_id INTEGER NOT NULL REFERENCES utilisateurs(id) ON DELETE CASCADE,
        module TEXT NOT NULL,
        PRIMARY KEY (utilisateur_id, module))""")
    conn.commit()
    conn.close()


def get_droits_personnalises(utilisateur_id: int):
    """Retourne la liste des modules autorisés en personnalisé, ou None si aucun (=> droits du rôle)."""
    _table_droits()
    conn = get_conn()
    rows = conn.execute(
        "SELECT module FROM droits_utilisateur WHERE utilisateur_id=?", (utilisateur_id,)
    ).fetchall()
    conn.close()
    return [r["module"] for r in rows] if rows else None


def set_droits_personnalises(utilisateur_id: int, modules: list):
    """Définit les modules autorisés pour un utilisateur. Liste vide = revenir aux droits du rôle."""
    _table_droits()
    conn = get_conn()
    conn.execute("DELETE FROM droits_utilisateur WHERE utilisateur_id=?", (utilisateur_id,))
    for m in modules:
        conn.execute("INSERT INTO droits_utilisateur (utilisateur_id, module) VALUES (?,?)",
                     (utilisateur_id, m))
    conn.commit()
    conn.close()


def verifier_connexion(identifiant: str, mot_de_passe: str):
    """Retourne le dict utilisateur si les identifiants sont corrects, sinon None."""
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM utilisateurs WHERE identifiant=? AND actif=1", (identifiant.strip(),)
    ).fetchone()
    conn.close()
    if row and hacher_mot_de_passe(mot_de_passe, row["sel"]) == row["mot_de_passe"]:
        return dict(row)
    return None


def a_le_droit(utilisateur: dict, module: str) -> bool:
    """
    Droits personnalisés (définis par l'admin) prioritaires ; sinon droits du rôle.
    Le module « parametres » reste toujours réservé aux administrateurs.
    """
    if utilisateur is None:
        return False
    if module in ("parametres", "audit"):
        return utilisateur["role"] == "Administrateur"
    perso = get_droits_personnalises(utilisateur["id"])
    if perso is not None:
        return module in perso
    return utilisateur["role"] in DROITS.get(module, [])


def creer_utilisateur(identifiant: str, nom: str, role: str, mot_de_passe: str):
    sel = secrets.token_hex(16)
    conn = get_conn()
    conn.execute(
        "INSERT INTO utilisateurs (identifiant, nom, role, sel, mot_de_passe) VALUES (?,?,?,?,?)",
        (identifiant.strip(), nom.strip(), role, sel, hacher_mot_de_passe(mot_de_passe, sel)),
    )
    conn.commit()
    conn.close()


def changer_mot_de_passe(utilisateur_id: int, nouveau: str):
    sel = secrets.token_hex(16)
    conn = get_conn()
    conn.execute(
        "UPDATE utilisateurs SET sel=?, mot_de_passe=? WHERE id=?",
        (sel, hacher_mot_de_passe(nouveau, sel), utilisateur_id),
    )
    conn.commit()
    conn.close()


def lister_utilisateurs():
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, identifiant, nom, role, actif FROM utilisateurs ORDER BY id"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def activer_desactiver(utilisateur_id: int, actif: bool):
    conn = get_conn()
    conn.execute("UPDATE utilisateurs SET actif=? WHERE id=?", (1 if actif else 0, utilisateur_id))
    conn.commit()
    conn.close()


# ----------------------------------------------------------------------
# Configuration initiale : création du compte administrateur du propriétaire
# ----------------------------------------------------------------------
IDENTIFIANTS_DEMO = ("admin", "gerant", "caissier")


def setup_requis() -> bool:
    """Vrai tant que le propriétaire n'a pas créé son propre compte administrateur."""
    from .database import get_parametre
    return get_parametre("setup_ok", "") != "oui"


def creer_compte_initial(nom: str, identifiant: str, mot_de_passe: str):
    """
    Première configuration : crée le compte administrateur du propriétaire,
    puis désactive les comptes de démonstration (admin/gerant/caissier) pour
    éviter toute confusion et tout accès avec les mots de passe par défaut.
    """
    from .database import set_parametre
    identifiant = identifiant.strip()
    if not identifiant or not nom.strip() or not mot_de_passe:
        raise ValueError("Tous les champs sont obligatoires.")
    if len(mot_de_passe) < 4:
        raise ValueError("Le mot de passe doit contenir au moins 4 caractères.")

    conn = get_conn()
    existe = conn.execute(
        "SELECT 1 FROM utilisateurs WHERE identifiant=?", (identifiant,)).fetchone()
    conn.close()
    if existe:
        raise ValueError(f"L'identifiant « {identifiant} » existe déjà. Choisissez-en un autre.")

    creer_utilisateur(identifiant, nom, "Administrateur", mot_de_passe)

    # Désactiver les comptes de démonstration s'ils ont encore leurs valeurs par défaut
    conn = get_conn()
    for demo in IDENTIFIANTS_DEMO:
        if demo != identifiant:
            conn.execute("UPDATE utilisateurs SET actif=0 WHERE identifiant=?", (demo,))
    conn.commit()
    conn.close()

    set_parametre("setup_ok", "oui")
    return verifier_connexion(identifiant, mot_de_passe)
