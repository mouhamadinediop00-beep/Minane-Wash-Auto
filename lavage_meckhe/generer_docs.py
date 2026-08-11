# -*- coding: utf-8 -*-
"""Génère les livrables documentaires PDF de MINAN WASH AUTO."""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                ListFlowable, ListItem, PageBreak)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

BLEU = colors.HexColor("#1B4F72")
AQUA = colors.HexColor("#17A2B8")
GRIS = colors.HexColor("#5D6D7E")
OUT = "/home/claude/lavage_meckhe/livrables"
os.makedirs(OUT, exist_ok=True)

st = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=st["Heading1"], textColor=BLEU, spaceBefore=16, spaceAfter=8, fontSize=17)
H2 = ParagraphStyle("H2", parent=st["Heading2"], textColor=AQUA, spaceBefore=12, spaceAfter=6, fontSize=13.5)
BODY = ParagraphStyle("B", parent=st["Normal"], fontSize=10.5, leading=15, spaceAfter=6)
TITRE = ParagraphStyle("T", parent=st["Title"], textColor=BLEU, fontSize=26, alignment=TA_CENTER)
SOUS = ParagraphStyle("S", parent=st["Normal"], textColor=GRIS, fontSize=13, alignment=TA_CENTER, spaceAfter=4)
CENTRE = ParagraphStyle("C", parent=st["Normal"], textColor=GRIS, fontSize=10, alignment=TA_CENTER)


def puces(items):
    return ListFlowable([ListItem(Paragraph(t, BODY), leftIndent=8) for t in items],
                        bulletType="bullet", bulletColor=AQUA, start="•")


def etapes(items):
    return ListFlowable([ListItem(Paragraph(t, BODY), leftIndent=8) for t in items],
                        bulletType="1", bulletColor=BLEU)


def page_titre(titre, sous_titre, doc_type):
    return [Spacer(1, 70*mm), Paragraph("MINAN WASH AUTO", TITRE),
            Spacer(1, 6*mm), Paragraph(sous_titre, SOUS),
            Spacer(1, 3*mm), Paragraph(titre, ParagraphStyle("x", parent=st["Normal"],
                                       textColor=AQUA, fontSize=16, alignment=TA_CENTER)),
            Spacer(1, 80*mm),
            Paragraph("Application de gestion pour station de lavage automobile", CENTRE),
            Paragraph("Méckhé — Région de Thiès, Sénégal", CENTRE),
            Paragraph(doc_type + " — Version 1.0", CENTRE),
            PageBreak()]


def build(nom, elems):
    chemin = os.path.join(OUT, nom)
    doc = SimpleDocTemplate(chemin, pagesize=A4, topMargin=18*mm, bottomMargin=16*mm,
                            leftMargin=20*mm, rightMargin=20*mm, title=nom)
    doc.build(elems)
    print("créé :", nom)


# ======================================================================
# 1. MANUEL UTILISATEUR
# ======================================================================
e = page_titre("Manuel d'utilisation", "Logiciel de gestion", "Manuel utilisateur")

e += [Paragraph("1. Présentation", H1),
      Paragraph("MINAN WASH AUTO est un logiciel qui gère l'ensemble de l'activité de la "
                "station : encaissements, clients, véhicules, stock, revente de produits, "
                "achats, dépenses, employés, abonnements, relation client (CRM WhatsApp), "
                "rapports et journal d'audit. Il fonctionne sur ordinateur Windows et sur "
                "tablette Android. Il est conçu pour être utilisé facilement par un caissier, "
                "sans connaissance informatique.", BODY)]

e += [Paragraph("2. Première utilisation", H1),
      Paragraph("Au tout premier lancement, l'écran d'accueil propose l'onglet "
                "« Créer mon compte ». Saisissez votre nom, un identifiant et un mot de passe : "
                "ce compte devient l'administrateur. Les comptes de démonstration sont alors "
                "désactivés automatiquement pour des raisons de sécurité.", BODY),
      Paragraph("Ensuite, à chaque démarrage, connectez-vous avec votre identifiant et votre "
                "mot de passe.", BODY)]

e += [Paragraph("3. Encaisser une vente (Caisse)", H1),
      etapes([
          "Ouvrez l'onglet « Caisse ».",
          "Onglet « Prestations » : cliquez sur chaque lavage réalisé. Onglet « Produits à "
          "vendre » : ajoutez les produits vendus au client (parfum, shampooing…).",
          "Choisissez éventuellement le client, le véhicule et le laveur.",
          "Indiquez la remise et le mode de paiement (Espèces, Wave, Orange Money, Carte, "
          "Chèque, Virement, ou Abonnement si le client en a un).",
          "Pour un paiement en espèces, utilisez la « Calculatrice de monnaie » : un pavé "
          "numérique et des raccourcis (500, 1000, 2000, 5000, 10000 F) calculent la monnaie "
          "à rendre.",
          "Cliquez sur « Encaisser », puis imprimez ou envoyez le ticket, le reçu ou la facture.",
      ])]

e += [Paragraph("4. Abonnements (fidélisation)", H1),
      Paragraph("L'onglet « Abonnements » gère trois formules :", BODY),
      puces([
          "<b>Mensuel</b> : 8 lavages pour 25 000 FCFA, valable 30 jours.",
          "<b>Premium</b> : lavages illimités et passage prioritaire.",
          "<b>Entreprise</b> : flotte de véhicules, facturation mensuelle sur relevé.",
      ]),
      Paragraph("Souscrivez un abonnement pour un client, puis à la caisse, si ce client est "
                "sélectionné, l'application propose d'utiliser son abonnement : le quota se "
                "décompte automatiquement, l'illimité ne décompte rien, et l'entreprise "
                "accumule les passages pour la facture mensuelle.", BODY)]

e += [Paragraph("5. CRM WhatsApp et e-mail", H1),
      Paragraph("L'onglet « CRM WhatsApp » permet de communiquer avec les clients selon les "
                "habitudes du Sénégal :", BODY),
      puces([
          "Envoyer un <b>message de remerciement</b> après un lavage.",
          "<b>Relancer</b> les clients qui ne sont pas revenus depuis 30 jours.",
          "Diffuser des <b>promotions</b> pour la Korité, la Tabaski, le Magal, le Ramadan, "
          "le Gamou ou les fêtes de fin d'année.",
          "Notifier les clients <b>proches d'un lavage offert</b> (carte de fidélité).",
      ]),
      Paragraph("L'application prépare le message et ouvre WhatsApp avec le texte déjà écrit "
                "vers le numéro du client : vous n'avez plus qu'à appuyer sur Envoyer. La "
                "facture peut aussi être envoyée par e-mail.", BODY)]

e += [Paragraph("6. Les autres onglets", H1),
      puces([
          "<b>Tableau de bord</b> : chiffre d'affaires du jour, de la semaine et du mois, "
          "nombre de véhicules, bénéfice, alertes de stock.",
          "<b>Clients</b> et <b>Véhicules</b> : fiches et historique.",
          "<b>Prestations</b> : tarifs des lavages (réservé aux responsables).",
          "<b>Stock</b> : produits, entrées/sorties, seuils critiques, produits revendables.",
          "<b>Achats</b> : commandes, réceptions, paiements fournisseurs.",
          "<b>Dépenses</b> : charges de la station.",
          "<b>Employés</b> : personnel, salaires, absences, productivité.",
          "<b>Rapports & KPI</b> : indicateurs et exports Excel / PDF / CSV.",
          "<b>Journal d'audit</b> : historique de toutes les actions (réservé administrateur).",
          "<b>Paramètres</b> : informations de l'entreprise (dont deux numéros de téléphone), "
          "logo, utilisateurs et sauvegarde.",
      ])]

e += [Paragraph("7. Sécurité", H1),
      puces([
          "Chaque utilisateur a des droits par onglet, réglables par l'administrateur.",
          "Les mots de passe sont chiffrés.",
          "Le journal d'audit trace qui fait quoi et quand.",
          "Une sauvegarde automatique est créée à chaque démarrage (30 jours conservés).",
      ])]
build("Manuel_utilisateur.pdf", e)


# ======================================================================
# 2. DOCUMENTATION TECHNIQUE
# ======================================================================
e = page_titre("Documentation technique", "Logiciel de gestion", "Documentation technique")

e += [Paragraph("1. Technologies", H1),
      puces([
          "Langage : <b>Python 3.10+</b>.",
          "Interface : <b>Flet</b> (moteur Flutter) — même code pour Windows et Android.",
          "Base de données : <b>SQLite</b> (fichier local, aucune installation de serveur).",
          "Documents : <b>ReportLab</b> (PDF), <b>OpenPyXL</b> (Excel), <b>qrcode</b> (QR), "
          "<b>svglib/Pillow</b> (logo).",
      ])]

e += [Paragraph("2. Architecture", H1),
      Paragraph("L'application suit une architecture en couches : la base de données et la "
                "logique métier sont séparées de l'interface, ce qui la rend évolutive.", BODY)]
arch = [["Fichier", "Rôle"],
        ["main.py", "Point d'entrée : connexion, navigation par rôle, écran d'accueil"],
        ["app/database.py", "Schéma SQLite, migrations, données de départ, paramètres"],
        ["app/auth.py", "Sécurité : connexion, rôles, droits par module"],
        ["app/services.py", "Logique métier : ventes, stock, abonnements, KPI"],
        ["app/exports.py", "Factures/tickets/devis PDF, rapports Excel/PDF/CSV, classeur"],
        ["app/crm.py", "Messages et liens WhatsApp / e-mail"],
        ["app/audit.py", "Journal d'audit"],
        ["app/ui.py", "Thème et composants d'interface réutilisables"],
        ["app/views.py", "Contenu de chaque onglet à l'écran"]]
t = Table(arch, colWidths=[45*mm, 110*mm])
t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), BLEU), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                       ("FONTSIZE", (0, 0), (-1, -1), 9), ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                       ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#EAF2F8")]),
                       ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 6)]))
e += [t, Spacer(1, 4*mm)]

e += [Paragraph("3. Principales tables de la base", H1),
      puces([
          "<b>utilisateurs</b>, <b>droits_utilisateur</b> : comptes et permissions.",
          "<b>prestations</b>, <b>prestation_produits</b> : lavages et consommables associés.",
          "<b>clients</b>, <b>vehicules</b> : fichier client et parc.",
          "<b>ventes</b>, <b>vente_lignes</b>, <b>vente_produits</b> : encaissements.",
          "<b>produits</b>, <b>mouvements_stock</b> : stock (achat, vente, consommation).",
          "<b>fournisseurs</b>, <b>achats</b>, <b>achat_lignes</b>, <b>paiements_fournisseurs</b>.",
          "<b>depenses</b>, <b>employes</b>, <b>absences</b>.",
          "<b>formules_abonnement</b>, <b>abonnements</b> : fidélisation.",
          "<b>documents</b> : factures/tickets/devis émis. <b>audit</b> : traçabilité.",
      ])]

e += [Paragraph("4. Données et sauvegarde", H1),
      puces([
          "La base est le fichier <b>donnees/lavage_meckhe.db</b>.",
          "Sauvegarde automatique quotidienne dans <b>sauvegardes/</b> (30 jours conservés).",
          "Factures dans <b>factures/AAAA-MM/</b>, exports dans <b>exports/AAAA-MM/</b> "
          "(classement mensuel).",
          "Le logo est lu depuis <b>assets/logo.png</b> (et logo_badge.png pour le menu).",
      ])]

e += [Paragraph("5. Évolutivité", H1),
      puces([
          "Passage multi-postes : remplacer SQLite par PostgreSQL (la persistance est isolée "
          "dans database.py) pour centraliser plusieurs stations.",
          "Mode réseau fourni (serveur_reseau.py) : suivi à distance sur le même Wi-Fi.",
          "WhatsApp : l'envoi assisté par lien wa.me peut évoluer vers l'API WhatsApp Business.",
      ])]

e += [Paragraph("6. Sécurité", H1),
      puces([
          "Mots de passe hachés avec PBKDF2-SHA256 (200 000 itérations, sel unique).",
          "Contrôle d'accès par rôle et par module ; « Paramètres » et « Journal d'audit » "
          "réservés à l'administrateur.",
          "Journal d'audit horodaté de toutes les actions sensibles.",
      ])]
build("Documentation_technique.pdf", e)


# ======================================================================
# 3. GUIDE D'INSTALLATION
# ======================================================================
e = page_titre("Guide d'installation", "Logiciel de gestion", "Guide d'installation")

e += [Paragraph("1. Installation sur Windows (utilisation directe)", H1),
      etapes([
          "Installer <b>Python 3.10 ou plus récent</b> depuis python.org/downloads en cochant "
          "impérativement « Add Python to PATH » au début de l'installation.",
          "Extraire le dossier de l'application (clic droit sur le .zip → Extraire tout).",
          "Double-cliquer sur <b>DEMARRER.bat</b> : les composants s'installent automatiquement "
          "au premier lancement, puis l'application s'ouvre.",
          "Créer votre compte administrateur au premier écran.",
      ]),
      Paragraph("Version conseillée : Python 3.12 (la plus stable). Si un blocage survient à "
                "l'installation des composants avec une version très récente, installez "
                "Python 3.12.", BODY)]

e += [Paragraph("2. Accès à distance (même Wi-Fi)", H1),
      etapes([
          "Sur le PC de la station, double-cliquer sur <b>DEMARRER_RESEAU.bat</b>.",
          "L'adresse à ouvrir s'affiche (ex. http://192.168.1.10:8550).",
          "Depuis un téléphone ou une tablette connecté au même Wi-Fi, ouvrir cette adresse "
          "dans le navigateur et se connecter avec son compte.",
      ]),
      Paragraph("Pour un accès depuis l'extérieur (4G), il faut exposer le PC via un tunnel "
                "(Cloudflare Tunnel, ngrok) ou héberger la base dans le cloud — étape "
                "optionnelle décrite dans la documentation technique.", BODY)]

e += [Paragraph("3. Générer l'exécutable Windows (.exe)", H1),
      etapes([
          "Installer Python 3.10+ (comme ci-dessus).",
          "Double-cliquer sur <b>compiler.bat</b> et choisir l'option Windows.",
          "L'exécutable est généré dans le dossier <b>build/windows/</b>.",
      ]),
      Paragraph("La commande sous-jacente est : <font face='Courier'>flet build windows</font>.", BODY)]

e += [Paragraph("4. Générer l'application Android (.apk)", H1),
      etapes([
          "Installer <b>Flutter</b> et l'<b>Android SDK</b> "
          "(voir docs.flet.dev/publish pour la procédure détaillée).",
          "Double-cliquer sur <b>compiler.bat</b> et choisir l'option Android.",
          "L'APK est généré dans le dossier <b>build/apk/</b>.",
          "Transférer l'APK sur la tablette et l'installer (autoriser les sources inconnues).",
      ]),
      Paragraph("La commande sous-jacente est : <font face='Courier'>flet build apk</font>. "
                "Le même code source sert à Windows et à Android.", BODY)]

e += [Paragraph("5. Contenu de la livraison", H1),
      puces([
          "Le code source complet de l'application (dossier lavage_meckhe).",
          "Les lanceurs : DEMARRER.bat, DEMARRER_RESEAU.bat, compiler.bat.",
          "Le logo MINAN WASH AUTO (dossier assets).",
          "Les modèles de facture, ticket, reçu et devis (générés par l'application).",
          "Les modèles Excel automatisés (générés par l'application : classeur de gestion, "
          "rapports, journal d'audit).",
          "Le manuel utilisateur, la documentation technique et ce guide (PDF).",
      ])]

e += [Paragraph("6. Sauvegarde et transfert", H1),
      puces([
          "Toutes les données sont dans le dossier <b>donnees</b> : pour changer de PC, "
          "copiez ce dossier.",
          "Lors d'une mise à jour, remplacez le dossier de l'application en conservant votre "
          "dossier <b>donnees</b> : les nouvelles colonnes sont ajoutées automatiquement sans "
          "perte de données.",
      ])]
build("Guide_installation.pdf", e)

print("\nTous les documents PDF ont été générés dans", OUT)
