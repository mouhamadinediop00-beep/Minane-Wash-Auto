# -*- coding: utf-8 -*-
"""
LAVAGE MECKHE - CRM / WhatsApp
--------------------------------
Génère des messages et des liens pour communiquer avec les clients via WhatsApp
(wa.me) et e-mail (mailto), adaptés aux habitudes du Sénégal.

Remarque : l'envoi 100 % automatique sans intervention nécessite l'API WhatsApp
Business (payante, sur approbation). Ici, l'application prépare le message et
ouvre WhatsApp / la messagerie avec le texte pré-rempli vers le bon numéro :
l'utilisateur n'a plus qu'à valider l'envoi (« en un clic »).
"""

import urllib.parse
from datetime import date, timedelta

from .database import get_conn, get_parametre

# Fêtes / occasions courantes au Sénégal pour les promotions ciblées
OCCASIONS = ["Korité", "Tabaski", "Magal de Touba", "Ramadan",
             "Gamou / Maouloud", "Fêtes de fin d'année", "Nouvel An"]


def _tel_e164(telephone: str) -> str:
    """
    Normalise un numéro sénégalais au format international sans '+', pour wa.me.
    Ex : '77 123 45 67' -> '221771234567'. Si déjà en 221..., on garde.
    """
    if not telephone:
        return ""
    n = "".join(c for c in telephone if c.isdigit())
    if n.startswith("00"):
        n = n[2:]
    if n.startswith("221"):
        return n
    # numéro local sénégalais (9 chiffres commençant par 7)
    if len(n) == 9 and n.startswith("7"):
        return "221" + n
    return n


def lien_whatsapp(telephone: str, message: str) -> str:
    """Construit un lien wa.me qui ouvre WhatsApp avec le message pré-rempli."""
    num = _tel_e164(telephone)
    texte = urllib.parse.quote(message)
    return f"https://wa.me/{num}?text={texte}" if num else f"https://wa.me/?text={texte}"


def lien_email(email: str, sujet: str, corps: str) -> str:
    """Construit un lien mailto: qui ouvre la messagerie avec le message pré-rempli."""
    params = urllib.parse.urlencode({"subject": sujet, "body": corps}, quote_via=urllib.parse.quote)
    return f"mailto:{email or ''}?{params}"


# ----------------------------------------------------------------------
# Modèles de messages
# ----------------------------------------------------------------------
def _entreprise():
    return get_parametre("entreprise_nom", "MINAN WASH AUTO")


def _signature():
    nom = _entreprise()
    tel1 = get_parametre("entreprise_telephone", "")
    tel2 = get_parametre("entreprise_telephone2", "")
    tels = " / ".join(t for t in (tel1, tel2) if t)
    return f"{nom}" + (f"\n{tels}" if tels else "")


def msg_remerciement(client_nom: str, montant_txt: str = "", plaque: str = "") -> str:
    nom = client_nom or "cher client"
    veh = f" (véhicule {plaque})" if plaque else ""
    return (f"Bonjour {nom}, merci d'avoir choisi {_entreprise()} pour le lavage de votre "
            f"véhicule{veh} aujourd'hui. Nous espérons vous revoir bientôt !\n\n{_signature()}")


def msg_rappel(client_nom: str, jours: int = 30) -> str:
    nom = client_nom or "cher client"
    return (f"Bonjour {nom}, cela fait environ {jours} jours depuis votre dernier lavage chez "
            f"{_entreprise()}. Votre véhicule mérite un bon nettoyage — nous vous attendons !\n\n"
            f"{_signature()}")


def msg_promo(client_nom: str, occasion: str, detail: str = "") -> str:
    nom = client_nom or "cher client"
    intro = {
        "Korité": "À l'occasion de la Korité",
        "Tabaski": "À l'occasion de la Tabaski",
        "Magal de Touba": "À l'occasion du Magal de Touba",
        "Ramadan": "En ce mois béni de Ramadan",
        "Gamou / Maouloud": "À l'occasion du Gamou",
        "Fêtes de fin d'année": "Pour les fêtes de fin d'année",
        "Nouvel An": "Pour le Nouvel An",
    }.get(occasion, f"À l'occasion de {occasion}")
    offre = detail or "profitez de nos offres spéciales sur le lavage de votre véhicule"
    return (f"Bonjour {nom}, {intro}, {_entreprise()} vous gâte : {offre}. "
            f"Passez nous voir !\n\n{_signature()}")


def msg_fidelite(client_nom: str, visites: int, seuil: int) -> str:
    nom = client_nom or "cher client"
    restants = max(seuil - visites, 0)
    if restants <= 0:
        return (f"Bonjour {nom}, félicitations ! Vous avez atteint {visites} lavages chez "
                f"{_entreprise()} : votre prochain lavage est OFFERT. À très vite !\n\n{_signature()}")
    return (f"Bonjour {nom}, vous avez déjà effectué {visites} lavages chez {_entreprise()}. "
            f"Plus que {restants} avant votre lavage OFFERT ! Merci de votre fidélité.\n\n"
            f"{_signature()}")


def msg_facture(client_nom: str, numero: str, montant_txt: str) -> str:
    nom = client_nom or "cher client"
    return (f"Bonjour {nom}, voici le récapitulatif de votre facture {numero} d'un montant de "
            f"{montant_txt} chez {_entreprise()}. Merci de votre visite !\n\n{_signature()}")


# ----------------------------------------------------------------------
# Ciblage : listes de clients pour les campagnes
# ----------------------------------------------------------------------
def clients_a_relancer(jours=30):
    """Clients dont le dernier lavage remonte à plus de `jours` jours."""
    limite = str(date.today() - timedelta(days=jours))
    conn = get_conn()
    rows = conn.execute("""
        SELECT c.id, c.nom, c.telephone,
               MAX(v.date) AS derniere, COUNT(v.id) AS visites
        FROM clients c JOIN ventes v ON v.client_id=c.id AND v.statut='Payée'
        WHERE c.telephone IS NOT NULL AND c.telephone <> ''
        GROUP BY c.id
        HAVING MAX(v.date) <= ?
        ORDER BY derniere ASC
    """, (limite,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def clients_proches_fidelite(seuil=5, marge=1):
    """Clients à `marge` lavage(s) d'un lavage offert (ou l'ayant atteint)."""
    conn = get_conn()
    rows = conn.execute("""
        SELECT c.id, c.nom, c.telephone, COUNT(v.id) AS visites
        FROM clients c JOIN ventes v ON v.client_id=c.id AND v.statut='Payée'
        WHERE c.telephone IS NOT NULL AND c.telephone <> ''
        GROUP BY c.id
        HAVING COUNT(v.id) >= ?
        ORDER BY visites DESC
    """, (max(seuil - marge, 1),)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def tous_clients_avec_tel():
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, nom, telephone, email FROM clients "
        "WHERE telephone IS NOT NULL AND telephone <> '' ORDER BY nom"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
