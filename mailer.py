# -*- coding: utf-8 -*-
"""
LAVAGE MECKHE - Envoi d'e-mails (SMTP) avec pièce jointe.
Permet d'envoyer réellement la facture PDF par e-mail au client, en utilisant
les identifiants de messagerie de la station (configurés dans Paramètres).
"""

import os
import smtplib
from email.message import EmailMessage

from .database import get_parametre


def config_smtp_ok() -> bool:
    """Vrai si la messagerie est configurée (serveur, expéditeur, mot de passe)."""
    return all([
        get_parametre("email_expediteur", "").strip(),
        get_parametre("email_mot_de_passe", "").strip(),
        get_parametre("email_smtp_serveur", "").strip(),
    ])


def _port() -> int:
    try:
        return int(get_parametre("email_smtp_port", "587") or 587)
    except ValueError:
        return 587


def envoyer_email(destinataire: str, sujet: str, corps: str, pieces_jointes=None):
    """
    Envoie un e-mail avec d'éventuelles pièces jointes.
    Retourne (True, "Envoyé") en cas de succès, sinon (False, message d'erreur).
    Ne lève pas d'exception : renvoie toujours un couple (ok, message).
    """
    destinataire = (destinataire or "").strip()
    if not destinataire:
        return False, "Le client n'a pas d'adresse e-mail."
    if not config_smtp_ok():
        return False, ("La messagerie n'est pas configurée. Renseignez l'expéditeur, "
                       "le serveur SMTP et le mot de passe dans Paramètres.")

    expediteur = get_parametre("email_expediteur").strip()
    mdp = get_parametre("email_mot_de_passe").strip()
    serveur = get_parametre("email_smtp_serveur").strip()
    port = _port()
    nom_entreprise = get_parametre("entreprise_nom", "MINAN WASH AUTO")

    msg = EmailMessage()
    msg["From"] = f"{nom_entreprise} <{expediteur}>"
    msg["To"] = destinataire
    msg["Subject"] = sujet
    msg.set_content(corps)

    for chemin in (pieces_jointes or []):
        try:
            with open(chemin, "rb") as f:
                donnees = f.read()
            nom = os.path.basename(chemin)
            msg.add_attachment(donnees, maintype="application", subtype="pdf", filename=nom)
        except Exception as ex:
            return False, f"Pièce jointe illisible ({os.path.basename(chemin)}) : {ex}"

    try:
        if port == 465:
            with smtplib.SMTP_SSL(serveur, port, timeout=25) as s:
                s.login(expediteur, mdp)
                s.send_message(msg)
        else:
            with smtplib.SMTP(serveur, port, timeout=25) as s:
                s.ehlo()
                s.starttls()
                s.login(expediteur, mdp)
                s.send_message(msg)
        return True, "E-mail envoyé avec succès."
    except smtplib.SMTPAuthenticationError:
        return False, ("Échec d'authentification. Pour Gmail, utilisez un « mot de passe "
                       "d'application » (et non votre mot de passe habituel).")
    except Exception as ex:
        return False, f"Échec de l'envoi : {ex}"


# Réglages courants pour aider l'utilisateur
SERVEURS_COURANTS = {
    "Gmail": ("smtp.gmail.com", 587),
    "Outlook / Hotmail": ("smtp-mail.outlook.com", 587),
    "Yahoo": ("smtp.mail.yahoo.com", 587),
    "Orange": ("smtp.orange.fr", 587),
}
