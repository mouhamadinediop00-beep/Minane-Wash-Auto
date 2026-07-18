# -*- coding: utf-8 -*-
"""
LAVAGE MECKHE - Journal d'audit
Trace « qui a fait quoi et quand » : connexions, modifications de prix,
annulations de ventes, éditions de factures, gestion des utilisateurs, etc.
Réservé à la consultation par l'administrateur.
"""

from .database import get_conn


def _table():
    conn = get_conn()
    conn.execute("""CREATE TABLE IF NOT EXISTS audit (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL DEFAULT (date('now')),
        heure TEXT NOT NULL DEFAULT (time('now','localtime')),
        utilisateur_id INTEGER,
        utilisateur TEXT,
        action TEXT NOT NULL,
        details TEXT
    )""")
    conn.commit()
    conn.close()


def journaliser(utilisateur, action, details=""):
    """
    Enregistre une action dans le journal d'audit.
    `utilisateur` peut être le dict utilisateur, ou une chaîne (ex. identifiant
    saisi lors d'une tentative de connexion échouée).
    """
    _table()
    if isinstance(utilisateur, dict):
        uid = utilisateur.get("id")
        unom = utilisateur.get("nom") or utilisateur.get("identifiant") or "?"
    else:
        uid = None
        unom = str(utilisateur) if utilisateur else "?"
    conn = get_conn()
    conn.execute(
        "INSERT INTO audit (utilisateur_id, utilisateur, action, details) VALUES (?,?,?,?)",
        (uid, unom, action, details or ""),
    )
    conn.commit()
    conn.close()


def lister(limite=1000, recherche="", debut=None, fin=None):
    """Retourne les entrées d'audit, les plus récentes d'abord, avec filtres optionnels."""
    _table()
    conn = get_conn()
    q = "SELECT * FROM audit WHERE 1=1"
    p = []
    if recherche:
        q += " AND (utilisateur LIKE ? OR action LIKE ? OR details LIKE ?)"
        p += [f"%{recherche}%"] * 3
    if debut:
        q += " AND date >= ?"
        p.append(debut)
    if fin:
        q += " AND date <= ?"
        p.append(fin)
    q += " ORDER BY id DESC LIMIT ?"
    p.append(limite)
    rows = [dict(r) for r in conn.execute(q, p).fetchall()]
    conn.close()
    return rows
