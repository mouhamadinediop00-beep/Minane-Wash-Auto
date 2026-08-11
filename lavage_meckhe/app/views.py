# -*- coding: utf-8 -*-
"""
LAVAGE MECKHE - Vues (contenu de chaque module à l'écran)
Chaque fonction construit et renvoie un contrôle Flet pour la zone principale.
"""

import os
import flet as ft
from datetime import date, timedelta

from . import services, exports
from . import audit
from .database import get_conn, get_parametre, set_parametre
from . import auth
from .ui import (BLEU_PROFOND, AQUA, VERT, ORANGE, ROUGE, GRIS, BLANC, FCFA,
                 carte_kpi, graphique_barres, tableau, titre_page, Formulaire,
                 notifier, confirmer, bouton_principal, dropdown, etat_vide, pastille)


def _ouvrir_fichier(page, chemin):
    """Ouvre un fichier généré de façon fiable (Windows/macOS/Linux, ou web)."""
    import sys
    import subprocess
    chemin = os.path.abspath(chemin)
    try:
        if getattr(page, "web", False):
            page.launch_url(f"file://{chemin}")
        elif os.name == "nt":
            os.startfile(chemin)  # Windows
        elif sys.platform == "darwin":
            subprocess.Popen(["open", chemin])
        else:
            subprocess.Popen(["xdg-open", chemin])
    except Exception:
        try:
            page.launch_url(f"file://{chemin}")
        except Exception:
            pass
    notifier(page, f"Fichier créé : {os.path.basename(chemin)}")


def _ouvrir_url(page, url):
    """
    Ouvre une URL (WhatsApp wa.me, e-mail mailto, http) de façon fiable :
    - en application bureau : via le navigateur système (module webbrowser) ;
    - en accès navigateur (mode réseau) : via un nouvel onglet.
    Renvoie True si l'ouverture a pu être déclenchée.
    """
    try:
        if getattr(page, "web", False):
            page.launch_url(url)
            return True
        import webbrowser
        if webbrowser.open(url, new=2):
            return True
        page.launch_url(url)
        return True
    except Exception:
        try:
            page.launch_url(url)
            return True
        except Exception:
            return False


def dialog_message_pret(page, titre, message, lien, ouvert, relancer):
    """
    Affiche le message prêt à envoyer, avec une zone copiable et un bouton pour
    (r)ouvrir WhatsApp/e-mail. Garantit que l'utilisateur peut toujours envoyer,
    même si l'ouverture automatique est bloquée.
    """
    zone = ft.TextField(value=message, multiline=True, min_lines=4, max_lines=10,
                        read_only=True, text_size=13, width=460)
    info = (ft.Text("WhatsApp devrait s'ouvrir dans votre navigateur. Sinon, copiez le "
                    "message ci-dessous (sélectionnez tout puis Ctrl+C) et envoyez-le "
                    "manuellement.", size=12, color=GRIS)
            if ouvert else
            ft.Text("L'ouverture automatique n'a pas abouti. Cliquez sur « Ouvrir » ci-dessous, "
                    "ou copiez le message et envoyez-le manuellement.", size=12, color=ORANGE))
    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text(titre, color=BLEU_PROFOND, weight=ft.FontWeight.BOLD),
        content=ft.Container(ft.Column([info, zone], tight=True, spacing=10), width=480),
        actions=[
            ft.TextButton("Fermer", on_click=lambda e: page.pop_dialog()),
            ft.FilledButton("Ouvrir", icon=ft.Icons.OPEN_IN_NEW, bgcolor="#25D366", color="white",
                            on_click=lambda e: relancer()),
        ],
    )
    page.show_dialog(dlg)


# ======================================================================
# MODULE 1 : TABLEAU DE BORD
# ======================================================================
def vue_tableau_de_bord(page, session, rafraichir):
    sites = services.lister_sites()
    portee = session.get("tdb_portee", "site")
    site_courant = session.get("site_id", 1)
    site_id = None if (portee == "tous" or len(sites) <= 1) else site_courant
    d = services.donnees_tableau_de_bord(site_id=site_id)
    nom_site = next((s["nom"] for s in sites if s["id"] == site_courant), "")

    def set_portee(p):
        session["tdb_portee"] = p
        rafraichir()

    if len(sites) > 1:
        bascule = ft.Row([
            ft.Text("Affichage :", size=13, color=GRIS),
            ft.Container(ft.Text(f"Ce site ({nom_site})", size=12,
                                 color="white" if portee == "site" else BLEU_PROFOND,
                                 weight=ft.FontWeight.BOLD),
                         bgcolor=BLEU_PROFOND if portee == "site" else "#ECF0F1",
                         border_radius=8, padding=ft.padding.symmetric(vertical=8, horizontal=14),
                         ink=True, on_click=lambda e: set_portee("site")),
            ft.Container(ft.Text("Tous les sites", size=12,
                                 color="white" if portee == "tous" else BLEU_PROFOND,
                                 weight=ft.FontWeight.BOLD),
                         bgcolor=BLEU_PROFOND if portee == "tous" else "#ECF0F1",
                         border_radius=8, padding=ft.padding.symmetric(vertical=8, horizontal=14),
                         ink=True, on_click=lambda e: set_portee("tous")),
        ], spacing=8)
    else:
        bascule = ft.Container()

    cartes_haut = ft.ResponsiveRow([
        ft.Container(carte_kpi("CA du jour", FCFA(d["ca_jour"]), ft.Icons.TODAY, VERT), col={"xs": 12, "sm": 6, "md": 3}),
        ft.Container(carte_kpi("CA de la semaine", FCFA(d["ca_semaine"]), ft.Icons.DATE_RANGE, AQUA), col={"xs": 12, "sm": 6, "md": 3}),
        ft.Container(carte_kpi("CA du mois", FCFA(d["ca_mois"]), ft.Icons.CALENDAR_MONTH, BLEU_PROFOND), col={"xs": 12, "sm": 6, "md": 3}),
        ft.Container(carte_kpi("Bénéfice estimé", FCFA(d["benefice_jour"]), ft.Icons.TRENDING_UP,
                               VERT if d["benefice_jour"] >= 0 else ROUGE,
                               "CA − dépenses − consommables"), col={"xs": 12, "sm": 6, "md": 3}),
    ], run_spacing=12, spacing=12)

    cartes_milieu = ft.ResponsiveRow([
        ft.Container(carte_kpi("Véhicules lavés", str(d["nb_vehicules"]), ft.Icons.DIRECTIONS_CAR, BLEU_PROFOND), col={"xs": 6, "md": 2}),
        ft.Container(carte_kpi("Motos", str(int(d["nb_motos"])), ft.Icons.TWO_WHEELER, AQUA), col={"xs": 6, "md": 2}),
        ft.Container(carte_kpi("Camions", str(int(d["nb_camions"])), ft.Icons.LOCAL_SHIPPING, GRIS), col={"xs": 6, "md": 2}),
        ft.Container(carte_kpi("Lavages intérieurs", str(int(d["nb_interieurs"])), ft.Icons.CLEANING_SERVICES, AQUA), col={"xs": 6, "md": 2}),
        ft.Container(carte_kpi("Lavages complets", str(int(d["nb_complets"])), ft.Icons.AUTO_AWESOME, VERT), col={"xs": 6, "md": 2}),
        ft.Container(carte_kpi("Clients fidélisés", str(d["clients_fideles"]), ft.Icons.LOYALTY, ORANGE), col={"xs": 6, "md": 2}),
    ], run_spacing=12, spacing=12)

    cartes_bas = ft.ResponsiveRow([
        ft.Container(carte_kpi("Dépenses du jour", FCFA(d["depenses_jour"]), ft.Icons.MONEY_OFF, ROUGE), col={"xs": 12, "sm": 6, "md": 4}),
        ft.Container(carte_kpi("Consommables du jour", FCFA(d["cout_conso_jour"]), ft.Icons.INVENTORY, ORANGE), col={"xs": 12, "sm": 6, "md": 4}),
        ft.Container(carte_kpi("Produits en stock critique", str(len(d["stock_critique"])), ft.Icons.WARNING_AMBER,
                               ROUGE if d["stock_critique"] else VERT), col={"xs": 12, "sm": 6, "md": 4}),
    ], run_spacing=12, spacing=12)

    # Panneau d'alertes
    if d["alertes"]:
        alertes = ft.Container(
            ft.Column([
                ft.Row([ft.Icon(ft.Icons.NOTIFICATIONS_ACTIVE, color=ROUGE),
                        ft.Text("Alertes", weight=ft.FontWeight.BOLD, color=ROUGE)]),
                *[ft.Row([ft.Icon(ft.Icons.CHEVRON_RIGHT, size=16, color=ORANGE),
                          ft.Text(a, size=13)]) for a in d["alertes"]],
            ], spacing=6),
            bgcolor="#FDEDEC", border_radius=12, padding=14,
            border=ft.border.all(1, ROUGE),
        )
    else:
        alertes = ft.Container(
            ft.Row([ft.Icon(ft.Icons.CHECK_CIRCLE, color=VERT),
                    ft.Text("Aucune alerte — tout est en ordre.", color=VERT)]),
            bgcolor="#EAFAF1", border_radius=12, padding=14,
        )

    return ft.Column([
        titre_page("Tableau de bord", ft.Icons.DASHBOARD),
        bascule,
        ft.Text("Chiffre d'affaires des 7 derniers jours", size=13, color=GRIS),
        graphique_barres(d["ca_7_jours"]),
        cartes_haut, cartes_milieu, cartes_bas, alertes,
    ], spacing=16, scroll=ft.ScrollMode.AUTO, expand=True)


# ======================================================================
# MODULE 4 : CAISSE (nouvelle vente)
# ======================================================================
def vue_caisse(page, session, rafraichir):
    conn = get_conn()
    prestations = [dict(r) for r in conn.execute(
        "SELECT * FROM prestations WHERE actif=1 ORDER BY type_vehicule, nom").fetchall()]
    clients = [dict(r) for r in conn.execute("SELECT id, nom FROM clients ORDER BY nom").fetchall()]
    vehicules = [dict(r) for r in conn.execute("SELECT id, plaque FROM vehicules ORDER BY plaque").fetchall()]
    employes = [dict(r) for r in conn.execute("SELECT id, nom FROM employes WHERE actif=1").fetchall()]
    conn.close()
    produits = services.produits_revendables(site_id=session.get("site_id"))   # stock du site courant
    pmap = {p["id"]: p for p in prestations}
    prodmap = {p["id"]: p for p in produits}

    panier = {}        # prestation_id -> quantité
    panier_prod = {}   # produit_id -> quantité
    etat = {"client": None, "vehicule": None, "remise": 0, "mode": "Espèces", "paye": 0,
            "employe": None, "onglet": "prestations"}

    total_txt = ft.Text("0 F", size=30, weight=ft.FontWeight.BOLD, color=VERT)
    monnaie_txt = ft.Text("Net : 0 F", size=13, color=GRIS)
    liste_panier = ft.Column(spacing=4)
    zone_boutons = ft.Container(expand=True)

    def calc_total():
        return sum(pmap[pid]["prix"] * q for pid, q in panier.items()) \
             + sum(int(prodmap[pid]["prix_vente"]) * q for pid, q in panier_prod.items())

    def maj_panier():
        liste_panier.controls.clear()
        nb = len(panier) + len(panier_prod)
        if nb == 0:
            liste_panier.controls.append(ft.Container(
                ft.Column([
                    ft.Icon(ft.Icons.SHOPPING_CART_OUTLINED, size=40, color="#B7C4D0"),
                    ft.Text("Panier vide", size=13, color=GRIS, weight=ft.FontWeight.BOLD),
                    ft.Text("Cliquez sur une prestation ou un produit pour l'ajouter.",
                            size=11, color="#9AA7B4", text_align=ft.TextAlign.CENTER),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
                alignment=ft.Alignment.CENTER, padding=16))
        else:
            def ligne_panier(nom, sous_total, on_moins, on_plus, couleur):
                return ft.Container(ft.Row([
                    ft.Column([ft.Text(nom, size=13, weight=ft.FontWeight.W_500,
                                       color=BLEU_PROFOND, max_lines=1),
                               ft.Text(FCFA(sous_total), size=12, color=couleur,
                                       weight=ft.FontWeight.BOLD)], spacing=0, expand=True),
                    ft.IconButton(ft.Icons.REMOVE_CIRCLE_OUTLINE, icon_color=ROUGE, icon_size=20,
                                  on_click=on_moins, tooltip="Retirer 1"),
                    ft.IconButton(ft.Icons.ADD_CIRCLE_OUTLINE, icon_color=VERT, icon_size=20,
                                  on_click=on_plus, tooltip="Ajouter 1"),
                ], spacing=2), bgcolor="#F8FBFD", border_radius=8,
                    padding=ft.padding.symmetric(vertical=4, horizontal=8))
            for pid, q in panier.items():
                p = pmap[pid]
                liste_panier.controls.append(ligne_panier(
                    f"{p['nom']}  ×{q}", p["prix"] * q,
                    lambda e, i=pid: retirer(i), lambda e, i=pid: ajouter(i), BLEU_PROFOND))
            for pid, q in panier_prod.items():
                p = prodmap[pid]
                liste_panier.controls.append(ligne_panier(
                    f"{p['nom']}  ×{q}", int(p["prix_vente"]) * q,
                    lambda e, i=pid: retirer_prod(i), lambda e, i=pid: ajouter_prod(i), AQUA))
        brut = calc_total()
        net = max(brut - int(etat["remise"] or 0), 0)
        total_txt.value = FCFA(net)
        rendu = max(int(etat["paye"] or 0) - net, 0)
        monnaie_txt.value = f"Net : {FCFA(net)}   |   Monnaie rendue : {FCFA(rendu)}"
        page.update()

    def ajouter(pid):
        panier[pid] = panier.get(pid, 0) + 1
        maj_panier()

    def retirer(pid):
        if pid in panier:
            panier[pid] -= 1
            if panier[pid] <= 0:
                del panier[pid]
        maj_panier()

    def ajouter_prod(pid):
        stock = prodmap[pid]["stock_reel"]
        if panier_prod.get(pid, 0) + 1 > stock:
            notifier(page, f"Stock insuffisant pour {prodmap[pid]['nom']} (reste {stock:g}).", erreur=True)
            return
        panier_prod[pid] = panier_prod.get(pid, 0) + 1
        maj_panier()

    def retirer_prod(pid):
        if pid in panier_prod:
            panier_prod[pid] -= 1
            if panier_prod[pid] <= 0:
                del panier_prod[pid]
        maj_panier()

    def grille_prestations():
        return ft.ResponsiveRow([
            ft.Container(ft.Container(
                ft.Column([
                    ft.Text(p["nom"], size=13, weight=ft.FontWeight.BOLD, color=BLEU_PROFOND,
                            text_align=ft.TextAlign.CENTER),
                    ft.Text(FCFA(p["prix"]), size=13, color=VERT),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
                bgcolor=BLANC, border_radius=12, padding=12, ink=True,
                on_click=lambda e, i=p["id"]: ajouter(i),
                border=ft.border.all(1, "#D5DBDB")),
                col={"xs": 6, "sm": 4, "md": 3}) for p in prestations
        ], run_spacing=10, spacing=10)

    def grille_produits():
        if not produits:
            return ft.Container(ft.Text("Aucun produit en revente. Ajoutez-en dans le module Stock "
                                        "en cochant « Revendable ».", color=GRIS, size=13), padding=10)
        cartes = []
        for p in produits:
            rupture = p["stock_reel"] <= 0
            cartes.append(ft.Container(ft.Container(
                ft.Column([
                    ft.Text(p["nom"], size=13, weight=ft.FontWeight.BOLD,
                            color=GRIS if rupture else BLEU_PROFOND, text_align=ft.TextAlign.CENTER),
                    ft.Text(FCFA(p["prix_vente"]), size=13, color=VERT),
                    ft.Text(f"stock : {p['stock_reel']:g}", size=10,
                            color=ROUGE if rupture else GRIS),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
                bgcolor="#F2F4F4" if rupture else BLANC, border_radius=12, padding=12,
                ink=not rupture,
                on_click=(None if rupture else (lambda e, i=p["id"]: ajouter_prod(i))),
                border=ft.border.all(1, "#D5DBDB")),
                col={"xs": 6, "sm": 4, "md": 3}))
        return ft.ResponsiveRow(cartes, run_spacing=10, spacing=10)

    def maj_onglet():
        est_prest = etat["onglet"] == "prestations"
        zone_boutons.content = ft.Column([
            ft.Row([
                _onglet_caisse("Prestations", est_prest, lambda e: changer_onglet("prestations")),
                _onglet_caisse("Produits à vendre", not est_prest, lambda e: changer_onglet("produits")),
            ], spacing=8),
            ft.Container(height=8),
            grille_prestations() if est_prest else grille_produits(),
        ], scroll=ft.ScrollMode.AUTO)
        page.update()

    def changer_onglet(o):
        etat["onglet"] = o
        maj_onglet()

    def set_val(cle):
        def _(e):
            etat[cle] = e.control.value
            maj_panier()
        return _

    dd_client = dropdown(label="Client (optionnel)", width=250,
                            options=[ft.dropdown.Option("", "Client de passage")] +
                                    [ft.dropdown.Option(str(c["id"]), c["nom"]) for c in clients],
                            on_change=set_val("client"))
    dd_vehicule = dropdown(label="Véhicule / plaque (optionnel)", width=250,
                              options=[ft.dropdown.Option("", "—")] +
                                      [ft.dropdown.Option(str(v["id"]), v["plaque"]) for v in vehicules],
                              on_change=set_val("vehicule"))
    dd_employe = dropdown(label="Laveur (optionnel)", width=250,
                             options=[ft.dropdown.Option("", "—")] +
                                     [ft.dropdown.Option(str(v["id"]), v["nom"]) for v in employes],
                             on_change=set_val("employe"))
    tf_remise = ft.TextField(label="Remise (F)", width=120, value="0",
                             keyboard_type=ft.KeyboardType.NUMBER, on_change=set_val("remise"))
    dd_mode = dropdown(label="Mode de paiement", width=180, value="Espèces",
                          options=[ft.dropdown.Option(m) for m in services.MODES_PAIEMENT],
                          on_change=set_val("mode"))
    tf_paye = ft.TextField(label="Montant payé (F)", width=150, value="0",
                           keyboard_type=ft.KeyboardType.NUMBER, on_change=set_val("paye"))

    def encaisser(e):
        if not panier and not panier_prod:
            notifier(page, "Le panier est vide.", erreur=True)
            return
        lignes = [(pid, pmap[pid]["prix"], q) for pid, q in panier.items()]
        prods = [(pid, int(prodmap[pid]["prix_vente"]), q) for pid, q in panier_prod.items()]
        net = max(calc_total() - int(etat["remise"] or 0), 0)
        paye = int(etat["paye"] or 0) or net
        try:
            vente = services.enregistrer_vente(
                caissier_id=session["utilisateur"]["id"],
                client_id=int(etat["client"]) if etat["client"] else None,
                vehicule_id=int(etat["vehicule"]) if etat["vehicule"] else None,
                lignes=lignes, remise=int(etat["remise"] or 0),
                mode_paiement=etat["mode"], montant_paye=paye,
                employes_ids=[int(etat["employe"])] if etat["employe"] else None,
                produits=prods,
                site_id=session.get("site_id", 1),
            )
        except Exception as ex:
            notifier(page, f"Erreur : {ex}", erreur=True)
            return

        def imprimer(type_doc):
            conn = get_conn()
            vid = conn.execute("SELECT id FROM ventes WHERE numero=?", (vente["numero"],)).fetchone()[0]
            conn.close()
            chemin = exports.generer_document(vid, type_doc)
            _ouvrir_fichier(page, chemin)

        dlg = ft.AlertDialog(
            title=ft.Text("Encaissement réussi", color=VERT),
            content=ft.Column([
                ft.Text(f"Vente {vente['numero']}"),
                ft.Text(f"Net : {FCFA(vente['montant_net'])}"),
                ft.Text(f"Monnaie à rendre : {FCFA(vente['monnaie_rendue'])}",
                        weight=ft.FontWeight.BOLD, size=16, color=BLEU_PROFOND),
            ], tight=True),
            actions=[
                ft.TextButton("Ticket", on_click=lambda e: imprimer("Ticket")),
                ft.TextButton("Reçu", on_click=lambda e: imprimer("Reçu")),
                ft.TextButton("Facture", on_click=lambda e: imprimer("Facture")),
                ft.FilledButton("Nouvelle vente", bgcolor=VERT, color="white",
                                on_click=lambda e: (page.pop_dialog(), rafraichir())),
            ],
        )
        page.show_dialog(dlg)

    def ouvrir_calculatrice(e=None):
        net = max(calc_total() - int(etat["remise"] or 0), 0)
        recu = {"v": int(etat["paye"] or 0) or 0}

        aff_net = ft.Text(FCFA(net), size=20, weight=ft.FontWeight.BOLD, color=BLEU_PROFOND)
        aff_recu = ft.Text(FCFA(recu["v"]), size=24, weight=ft.FontWeight.BOLD, color=AQUA)
        aff_rendu = ft.Text("0 F", size=30, weight=ft.FontWeight.BOLD, color=VERT)

        def maj():
            aff_recu.value = FCFA(recu["v"])
            r = recu["v"] - net
            if r >= 0:
                aff_rendu.value = FCFA(r)
                aff_rendu.color = VERT
            else:
                aff_rendu.value = f"Manque {FCFA(-r)}"
                aff_rendu.color = ROUGE
            page.update()

        def taper(d):
            recu["v"] = recu["v"] * 10 + d
            maj()

        def deux_zeros():
            recu["v"] = recu["v"] * 100
            maj()

        def effacer():
            recu["v"] = 0
            maj()

        def retour():
            recu["v"] = recu["v"] // 10
            maj()

        def ajouter_billet(m):
            recu["v"] += m
            maj()

        def montant_juste():
            recu["v"] = net
            maj()

        def touche(txt, on_click, couleur=BLANC, txtcol=BLEU_PROFOND):
            return ft.Container(
                ft.Text(txt, size=22, weight=ft.FontWeight.BOLD, color=txtcol,
                        text_align=ft.TextAlign.CENTER),
                bgcolor=couleur, border_radius=12, height=58, ink=True,
                on_click=lambda e: on_click(), alignment=ft.Alignment.CENTER,
                border=ft.border.all(1, "#D5DBDB"), expand=True)

        clavier = ft.Column([
            ft.Row([touche("7", lambda: taper(7)), touche("8", lambda: taper(8)),
                    touche("9", lambda: taper(9))], spacing=8),
            ft.Row([touche("4", lambda: taper(4)), touche("5", lambda: taper(5)),
                    touche("6", lambda: taper(6))], spacing=8),
            ft.Row([touche("1", lambda: taper(1)), touche("2", lambda: taper(2)),
                    touche("3", lambda: taper(3))], spacing=8),
            ft.Row([touche("0", lambda: taper(0)), touche("00", deux_zeros),
                    touche("⌫", retour, "#FDEDEC", ROUGE)], spacing=8),
        ], spacing=8)

        billets = ft.Row([
            touche("+500", lambda: ajouter_billet(500), "#EAF2F8"),
            touche("+1000", lambda: ajouter_billet(1000), "#EAF2F8"),
            touche("+2000", lambda: ajouter_billet(2000), "#EAF2F8"),
        ], spacing=8)
        billets2 = ft.Row([
            touche("+5000", lambda: ajouter_billet(5000), "#EAF2F8"),
            touche("+10000", lambda: ajouter_billet(10000), "#EAF2F8"),
            touche("Appoint", montant_juste, "#EAFAF1", VERT),
        ], spacing=8)

        def valider():
            etat["paye"] = recu["v"]
            tf_paye.value = str(recu["v"])
            page.pop_dialog()
            maj_panier()
            notifier(page, f"Montant reçu : {FCFA(recu['v'])} — Monnaie : "
                           f"{FCFA(max(recu['v'] - net, 0))}")

        maj()
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([ft.Icon(ft.Icons.CALCULATE, color=BLEU_PROFOND),
                          ft.Text("Calculatrice de monnaie", color=BLEU_PROFOND,
                                  weight=ft.FontWeight.BOLD)]),
            content=ft.Container(ft.Column([
                ft.Row([ft.Text("À payer :", size=14, color=GRIS), aff_net],
                       alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Row([ft.Text("Reçu :", size=14, color=GRIS), aff_recu],
                       alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(),
                ft.Row([ft.Text("MONNAIE À RENDRE", size=14, weight=ft.FontWeight.BOLD,
                                color=BLEU_PROFOND), aff_rendu],
                       alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Container(height=6),
                billets, billets2,
                ft.Container(height=6),
                clavier,
            ], spacing=10, tight=True), width=340),
            actions=[
                ft.TextButton("Effacer", on_click=lambda e: effacer()),
                ft.TextButton("Annuler", on_click=lambda e: page.pop_dialog()),
                ft.FilledButton("Valider", bgcolor=VERT, color="white",
                                on_click=lambda e: valider()),
            ],
        )
        page.show_dialog(dlg)

    panneau_paiement = ft.Container(
        ft.Column([
            ft.Text("Encaissement", weight=ft.FontWeight.BOLD, color=BLEU_PROFOND, size=16),
            liste_panier,
            ft.Divider(),
            total_txt, monnaie_txt,
            ft.Row([dd_client, dd_vehicule], wrap=True, spacing=8),
            ft.Row([dd_employe, tf_remise], wrap=True, spacing=8),
            ft.Row([dd_mode, tf_paye], wrap=True, spacing=8),
            ft.OutlinedButton("Calculatrice de monnaie", icon=ft.Icons.CALCULATE,
                              on_click=ouvrir_calculatrice),
            bouton_principal("Encaisser", ft.Icons.POINT_OF_SALE, encaisser, VERT),
        ], spacing=10, scroll=ft.ScrollMode.AUTO),
        bgcolor=BLANC, border_radius=14, padding=16, width=340,
        shadow=ft.BoxShadow(blur_radius=6, color="#22000000"),
    )

    maj_onglet()
    maj_panier()
    return ft.Column([
        titre_page("Caisse — Nouvelle vente", ft.Icons.POINT_OF_SALE),
        ft.Row([
            ft.Container(zone_boutons, expand=True),
            panneau_paiement,
        ], vertical_alignment=ft.CrossAxisAlignment.START, expand=True),
    ], spacing=14, expand=True)


def _onglet_caisse(libelle, actif, on_click):
    return ft.Container(
        ft.Text(libelle, weight=ft.FontWeight.BOLD, color="white" if actif else GRIS, size=13),
        bgcolor=BLEU_PROFOND if actif else "#ECF0F1",
        border_radius=10, padding=ft.padding.symmetric(vertical=10, horizontal=16),
        ink=True, on_click=on_click,
    )


# ======================================================================
# MODULE : JOURNAL DE CAISSE
# ======================================================================
def vue_journal(page, session, rafraichir):
    j = services.journal_de_caisse(site_id=session.get("site_id"))
    peut_annuler = auth.a_le_droit(session["utilisateur"], "rapports") or \
        session["utilisateur"]["role"] in ("Administrateur", "Gérant")

    def imprimer(vente_id, type_doc):
        chemin = exports.generer_document(vente_id, type_doc)
        conn = get_conn()
        num = conn.execute("SELECT numero FROM ventes WHERE id=?", (vente_id,)).fetchone()
        conn.close()
        audit.journaliser(session["utilisateur"], f"Édition {type_doc.lower()}",
                          f"Vente {num['numero'] if num else vente_id}")
        _ouvrir_fichier(page, chemin)

    def _infos_vente(vente_id):
        conn = get_conn()
        r = conn.execute(
            "SELECT v.numero, v.montant_net, cl.nom AS client, cl.telephone, cl.email "
            "FROM ventes v LEFT JOIN clients cl ON cl.id=v.client_id WHERE v.id=?",
            (vente_id,)).fetchone()
        conn.close()
        return dict(r) if r else None

    def envoyer_email_facture(v):
        from . import mailer, crm
        info = _infos_vente(v["id"])
        if not info or not (info.get("email") or "").strip():
            notifier(page, "Ce client n'a pas d'adresse e-mail enregistrée (fiche client).", erreur=True)
            return
        chemin = exports.generer_document(v["id"], "Facture")
        sujet = f"Votre facture {info['numero']} — {get_parametre('entreprise_nom','MINAN WASH AUTO')}"
        corps = crm.msg_facture(info.get("client") or "cher client", info["numero"],
                                FCFA(info["montant_net"]))
        ok, message = mailer.envoyer_email(info["email"], sujet, corps, pieces_jointes=[chemin])
        if ok:
            audit.journaliser(session["utilisateur"], "Envoi facture e-mail",
                              f"{info['numero']} → {info['email']}")
            notifier(page, f"Facture envoyée par e-mail à {info['email']}.")
        else:
            notifier(page, message, erreur=True)

    def envoyer_whatsapp_facture(v):
        from . import crm
        info = _infos_vente(v["id"])
        if not info or not crm._tel_e164(info.get("telephone") or ""):
            notifier(page, "Ce client n'a pas de numéro WhatsApp valide (fiche client).", erreur=True)
            return
        chemin = exports.generer_document(v["id"], "Facture")
        msg = crm.msg_facture(info.get("client") or "cher client", info["numero"],
                              FCFA(info["montant_net"]))
        lien = crm.lien_whatsapp(info["telephone"], msg)
        ouvert = _ouvrir_url(page, lien)
        audit.journaliser(session["utilisateur"], "Envoi facture WhatsApp",
                          f"{info['numero']} → {info['telephone']}")
        note = (msg + "\n\n———\nLe PDF de la facture a été enregistré ici :\n" + chemin +
                "\nDans WhatsApp, touchez le trombone (📎) pour joindre ce fichier si besoin.")
        dialog_message_pret(page, "Facture par WhatsApp", note, lien, ouvert,
                            relancer=lambda: _ouvrir_url(page, lien))

    def menu_impression(v):
        dlg = ft.AlertDialog(
            title=ft.Text(f"Document — {v['numero']}", color=BLEU_PROFOND, weight=ft.FontWeight.BOLD),
            content=ft.Container(ft.Column([
                ft.Text("Imprimer / ouvrir le document :", size=12, color=GRIS),
                ft.Row([
                    ft.OutlinedButton("Ticket", icon=ft.Icons.RECEIPT,
                                      on_click=lambda e: (page.pop_dialog(), imprimer(v["id"], "Ticket"))),
                    ft.OutlinedButton("Reçu", icon=ft.Icons.DESCRIPTION,
                                      on_click=lambda e: (page.pop_dialog(), imprimer(v["id"], "Reçu"))),
                    ft.FilledButton("Facture", icon=ft.Icons.PICTURE_AS_PDF, bgcolor=BLEU_PROFOND,
                                    color="white",
                                    on_click=lambda e: (page.pop_dialog(), imprimer(v["id"], "Facture"))),
                ], wrap=True, spacing=8),
                ft.Divider(),
                ft.Text("Envoyer la facture au client :", size=12, color=GRIS),
                ft.Row([
                    ft.FilledButton("Par e-mail (PDF joint)", icon=ft.Icons.EMAIL,
                                    bgcolor=AQUA, color="white",
                                    on_click=lambda e: (page.pop_dialog(), envoyer_email_facture(v))),
                    ft.FilledButton("Par WhatsApp", icon=ft.Icons.CHAT, bgcolor="#25D366",
                                    color="white",
                                    on_click=lambda e: (page.pop_dialog(), envoyer_whatsapp_facture(v))),
                ], wrap=True, spacing=8),
            ], tight=True, spacing=10), width=420),
            actions=[ft.TextButton("Fermer", on_click=lambda e: page.pop_dialog())],
        )
        page.show_dialog(dlg)

    def annuler(v):
        def faire():
            services.annuler_vente(v["id"])
            audit.journaliser(session["utilisateur"], "Annulation vente",
                              f"{v['numero']} — {FCFA(v['montant_net'])}")
            notifier(page, f"Vente {v['numero']} annulée (stock restitué).")
            rafraichir()
        confirmer(page, f"Annuler définitivement la vente {v['numero']} "
                        f"({FCFA(v['montant_net'])}) ? Le stock consommé sera restitué.", faire)

    # Couleurs et icônes par mode de paiement (différenciation visuelle)
    STYLE_PAIEMENT = {
        "Espèces":      (VERT,          "#EAFAF1", ft.Icons.PAYMENTS),
        "Wave":         ("#1DA1F2",     "#E8F6FE", ft.Icons.PHONE_ANDROID),
        "Orange Money": (ORANGE,        "#FEF5E7", ft.Icons.PHONE_IPHONE),
        "Carte bancaire": (BLEU_PROFOND, "#EAF2F8", ft.Icons.CREDIT_CARD),
        "Chèque":       ("#8E44AD",     "#F4ECF7", ft.Icons.RECEIPT_LONG),
        "Virement":     ("#16A085",     "#E8F8F5", ft.Icons.ACCOUNT_BALANCE),
        "Abonnement":   ("#CA6F1E",     "#FEF5E7", ft.Icons.CARD_MEMBERSHIP),
    }

    def pastille_paiement(mode):
        coul, fond, _ = STYLE_PAIEMENT.get(mode, (GRIS, "#EEEEEE", ft.Icons.PAYMENTS))
        return pastille(mode, coul, fond)

    lignes = []
    for v in j["ventes"]:
        statut_c = (pastille("Annulée", ROUGE, "#FDEDEC") if v["statut"] == "Annulée"
                    else pastille("Payée", VERT, "#EAFAF1"))
        actions = ft.Row([
            ft.IconButton(ft.Icons.PRINT, icon_color=BLEU_PROFOND, icon_size=20,
                          tooltip="Imprimer / envoyer",
                          on_click=lambda e, ve=v: menu_impression(ve)),
            ft.IconButton(ft.Icons.CANCEL, icon_color=ROUGE, icon_size=20, tooltip="Annuler la vente",
                          on_click=lambda e, ve=v: annuler(ve))
            if (peut_annuler and v["statut"] != "Annulée") else ft.Container(),
        ], spacing=0)
        lignes.append((v["id"], [v["numero"], v["heure"][:5], v["caissier"] or "—",
                                 v["client"] or "Passage", v["plaque"] or "—",
                                 ft.Text(FCFA(v["montant_net"]), weight=ft.FontWeight.BOLD,
                                         size=12.5),
                                 pastille_paiement(v["mode_paiement"]), statut_c, actions]))

    # Pastilles de mode de paiement : couleur/icône propre, estompées si à zéro
    cartes_paiement = []
    for m, montant in j["totaux"].items():
        coul, fond, icone = STYLE_PAIEMENT.get(m, (AQUA, "#EAF2F8", ft.Icons.PAYMENTS))
        actif = montant > 0
        cartes_paiement.append(ft.Container(
            ft.Row([
                ft.Container(ft.Icon(icone, color="white", size=20),
                             bgcolor=coul if actif else "#B7C4D0", border_radius=10, padding=8),
                ft.Column([
                    ft.Text(m, size=11, color=GRIS),
                    ft.Text(FCFA(montant), size=15, weight=ft.FontWeight.BOLD,
                            color=coul if actif else GRIS),
                ], spacing=0),
            ], spacing=8),
            bgcolor=BLANC, border_radius=12, padding=12, col={"xs": 6, "md": 2},
            opacity=1 if actif else 0.55,
            shadow=ft.BoxShadow(blur_radius=6, color="#14000000")))
    cartes = ft.ResponsiveRow(cartes_paiement, run_spacing=10, spacing=10)

    resume = ft.ResponsiveRow([
        ft.Container(carte_kpi("Total encaissé", FCFA(j["ca"]), ft.Icons.ACCOUNT_BALANCE_WALLET, VERT), col={"xs": 12, "md": 4}),
        ft.Container(carte_kpi("Total dépenses", FCFA(j["depenses"]), ft.Icons.MONEY_OFF, ROUGE), col={"xs": 12, "md": 4}),
        ft.Container(carte_kpi("Solde de caisse", FCFA(j["solde"]), ft.Icons.SAVINGS,
                               VERT if j["solde"] >= 0 else ROUGE), col={"xs": 12, "md": 4}),
    ], run_spacing=10, spacing=10)

    def exporter_pdf(e):
        _ouvrir_fichier(page, exports.exporter_journal_caisse_pdf())

    if lignes:
        bloc_tableau = ft.Container(
            tableau(["N°", "Heure", "Caissier", "Client", "Plaque", "Montant", "Paiement", "Statut", "Actions"],
                    lignes,
                    alignements=["left", "center", "left", "left", "left", "right", "center", "center", "center"]),
            bgcolor=BLANC, border_radius=12, padding=10)
    else:
        bloc_tableau = ft.Container(
            etat_vide("Aucune vente enregistrée aujourd'hui", ft.Icons.RECEIPT_LONG,
                      "Les ventes encaissées à la caisse apparaîtront ici."),
            bgcolor=BLANC, border_radius=12, padding=10, height=220)

    return ft.Column([
        ft.Row([titre_page(f"Journal de caisse — {j['date']}", ft.Icons.RECEIPT_LONG),
                ft.Row([
                    ft.IconButton(ft.Icons.REFRESH, icon_color=BLEU_PROFOND, tooltip="Actualiser",
                                  on_click=lambda e: rafraichir()),
                    bouton_principal("Exporter le journal (PDF)", ft.Icons.PICTURE_AS_PDF, exporter_pdf),
                ])], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        cartes, resume,
        bloc_tableau,
    ], spacing=16, scroll=ft.ScrollMode.AUTO, expand=True)


# ======================================================================
# MODULE 3 : CLIENTS
# ======================================================================
def vue_clients(page, session, rafraichir):
    clients = services.historique_clients()

    def enregistrer(vals, cid=None):
        conn = get_conn()
        if cid:
            conn.execute("UPDATE clients SET nom=?, telephone=?, email=?, adresse=?, profession=?, "
                         "entreprise=?, type_client=?, carte_fidelite=? WHERE id=?",
                         (vals["nom"], vals["telephone"], vals.get("email"), vals["adresse"],
                          vals["profession"], vals["entreprise"], vals["type_client"],
                          1 if vals["carte"] == "Oui" else 0, cid))
        else:
            conn.execute("INSERT INTO clients (nom, telephone, email, adresse, profession, entreprise, "
                         "type_client, carte_fidelite) VALUES (?,?,?,?,?,?,?,?)",
                         (vals["nom"], vals["telephone"], vals.get("email"), vals["adresse"],
                          vals["profession"], vals["entreprise"], vals["type_client"],
                          1 if vals["carte"] == "Oui" else 0))
        conn.commit(); conn.close()
        notifier(page, "Client enregistré.")
        rafraichir()

    def form(client=None):
        champs = [
            {"cle": "nom", "label": "Nom", "obligatoire": True, "valeur": client and client["nom"]},
            {"cle": "telephone", "label": "Téléphone (WhatsApp)", "valeur": client and client["telephone"]},
            {"cle": "email", "label": "Email", "valeur": client and (client["email"] if "email" in client.keys() else "")},
            {"cle": "adresse", "label": "Adresse", "valeur": client and client["adresse"]},
            {"cle": "profession", "label": "Profession", "valeur": client and client["profession"]},
            {"cle": "entreprise", "label": "Entreprise", "valeur": client and client["entreprise"]},
            {"cle": "type_client", "label": "Type de client", "type": "liste",
             "options": [(t, t) for t in ("Particulier", "Entreprise", "Administration", "VIP")],
             "valeur": (client and client["type_client"]) or "Particulier"},
            {"cle": "carte", "label": "Carte fidélité", "type": "liste",
             "options": [("Non", "Non"), ("Oui", "Oui")],
             "valeur": "Oui" if client and client["carte_fidelite"] else "Non"},
        ]
        Formulaire(page, "Fiche client", champs,
                   lambda v: enregistrer(v, client["id"] if client else None)).ouvrir()

    etat = {"q": ""}
    zone = ft.Container()

    def construire():
        q = etat["q"].strip().lower()
        vus = [c for c in clients if not q or q in (c["nom"] or "").lower()
               or q in (c["telephone"] or "").lower()]
        if not vus:
            zone.content = etat_vide(
                "Aucun client trouvé" if q else "Aucun client enregistré",
                ft.Icons.PEOPLE,
                "Essayez un autre nom ou numéro." if q
                else "Cliquez sur « Nouveau client » pour en ajouter un.")
            page.update(); return
        lignes = []
        for c in vus:
            fid = pastille("★ Fidèle", ORANGE, "#FEF5E7") if c["carte_fidelite"] else ft.Text("—", size=12)
            lignes.append((c["id"], [c["nom"], c["telephone"] or "—", c["type_client"], fid,
                                     str(c["visites"]),
                                     ft.Text(FCFA(c["total"]), weight=ft.FontWeight.BOLD, size=12.5),
                                     c["derniere"] or "—"]))
        zone.content = tableau(
            ["Nom", "Téléphone", "Type", "Fidélité", "Visites", "Total dépensé", "Dernière visite"],
            lignes, sur_selection=lambda i: form(next(c for c in clients if c["id"] == i)),
            alignements=["left", "left", "left", "center", "center", "right", "left"])
        page.update()

    def sur_recherche(e):
        etat["q"] = e.control.value
        construire()

    champ = ft.TextField(hint_text="Rechercher un client (nom ou téléphone)…",
                         prefix_icon=ft.Icons.SEARCH, width=360, height=46,
                         on_change=sur_recherche, content_padding=10)
    construire()
    return ft.Column([
        ft.Row([titre_page("Clients", ft.Icons.PEOPLE),
                bouton_principal("Nouveau client", ft.Icons.PERSON_ADD, lambda e: form())],
               alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        champ,
        ft.Container(zone, bgcolor=BLANC, border_radius=12, padding=10),
        ft.Text("Astuce : cliquez sur une ligne pour modifier la fiche.", size=12, color=GRIS),
    ], spacing=16, scroll=ft.ScrollMode.AUTO, expand=True)


# ======================================================================
# MODULE 10 : VEHICULES
# ======================================================================
def vue_vehicules(page, session, rafraichir):
    vehicules = services.historique_vehicules()
    conn = get_conn()
    clients = [dict(r) for r in conn.execute("SELECT id, nom FROM clients ORDER BY nom").fetchall()]
    conn.close()

    def enregistrer(vals, vid=None):
        conn = get_conn()
        try:
            if vid:
                conn.execute("UPDATE vehicules SET plaque=?, marque=?, modele=?, couleur=?, "
                             "categorie=?, client_id=? WHERE id=?",
                             (vals["plaque"], vals["marque"], vals["modele"], vals["couleur"],
                              vals["categorie"], int(vals["client"]) if vals["client"] else None, vid))
            else:
                conn.execute("INSERT INTO vehicules (plaque, marque, modele, couleur, categorie, client_id) "
                             "VALUES (?,?,?,?,?,?)",
                             (vals["plaque"], vals["marque"], vals["modele"], vals["couleur"],
                              vals["categorie"], int(vals["client"]) if vals["client"] else None))
            conn.commit()
            notifier(page, "Véhicule enregistré.")
        except Exception as ex:
            notifier(page, f"Erreur : {ex}", erreur=True)
        finally:
            conn.close()
        rafraichir()

    def form(v=None):
        champs = [
            {"cle": "plaque", "label": "Plaque", "obligatoire": True, "valeur": v and v["plaque"]},
            {"cle": "marque", "label": "Marque", "valeur": v and v["marque"]},
            {"cle": "modele", "label": "Modèle", "valeur": v and v["modele"]},
            {"cle": "couleur", "label": "Couleur", "valeur": v and v["couleur"]},
            {"cle": "categorie", "label": "Catégorie", "type": "liste",
             "options": [(c, c) for c in ("moto", "voiture", "camion", "bus")],
             "valeur": (v and v["categorie"]) or "voiture"},
            {"cle": "client", "label": "Propriétaire", "type": "liste",
             "options": [("", "—")] + [(str(c["id"]), c["nom"]) for c in clients],
             "valeur": v and v["client_id"]},
        ]
        Formulaire(page, "Fiche véhicule", champs,
                   lambda val: enregistrer(val, v["id"] if v else None)).ouvrir()

    lignes = [(v["id"], [v["plaque"], v["marque"] or "—", v["modele"] or "—", v["categorie"],
                         v["client"] or "—", str(v["nb_lavages"]), FCFA(v["total"]), v["dernier"] or "—"])
              for v in vehicules]

    return ft.Column([
        ft.Row([titre_page("Véhicules", ft.Icons.DIRECTIONS_CAR),
                bouton_principal("Nouveau véhicule", ft.Icons.ADD, lambda e: form())],
               alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.Container(tableau(["Plaque", "Marque", "Modèle", "Catégorie", "Propriétaire", "Nb lavages", "Total", "Dernier"],
                             lignes, sur_selection=lambda i: form(next(v for v in vehicules if v["id"] == i))),
                     bgcolor=BLANC, border_radius=12, padding=10),
    ], spacing=16, scroll=ft.ScrollMode.AUTO, expand=True)


# ======================================================================
# MODULE 2 : PRESTATIONS
# ======================================================================
def vue_prestations(page, session, rafraichir):
    conn = get_conn()
    prestations = [dict(r) for r in conn.execute("SELECT * FROM prestations ORDER BY code").fetchall()]
    conn.close()

    def vue_prestations_moi():
        return session["utilisateur"]

    def enregistrer(vals, pid=None, ancien=None):
        conn = get_conn()
        try:
            if pid:
                conn.execute("UPDATE prestations SET nom=?, type_vehicule=?, type_lavage=?, prix=?, "
                             "duree_min=?, tva=? WHERE id=?",
                             (vals["nom"], vals["type_vehicule"], vals["type_lavage"], vals["prix"],
                              vals["duree_min"], vals["tva"], pid))
                # Audit : modification de prix
                if ancien is not None and int(ancien["prix"]) != int(vals["prix"]):
                    audit.journaliser(session["utilisateur"], "Modification prix prestation",
                                      f"{ancien['nom']} : {ancien['prix']} F → {vals['prix']} F")
                else:
                    audit.journaliser(session["utilisateur"], "Modification prestation",
                                      f"{vals['nom']}")
            else:
                conn.execute("INSERT INTO prestations (code, nom, type_vehicule, type_lavage, prix, duree_min, tva) "
                             "VALUES (?,?,?,?,?,?,?)",
                             (vals["code"], vals["nom"], vals["type_vehicule"], vals["type_lavage"],
                              vals["prix"], vals["duree_min"], vals["tva"]))
                audit.journaliser(session["utilisateur"], "Création prestation",
                                  f"{vals['code']} - {vals['nom']} ({vals['prix']} F)")
            conn.commit()
            notifier(page, "Prestation enregistrée.")
        except Exception as ex:
            notifier(page, f"Erreur : {ex}", erreur=True)
        finally:
            conn.close()
        rafraichir()

    def form(p=None):
        champs = [
            {"cle": "code", "label": "Code", "obligatoire": True, "valeur": p and p["code"]} if not p else
            {"cle": "code", "label": "Code (non modifiable)", "valeur": p["code"]},
            {"cle": "nom", "label": "Nom", "obligatoire": True, "valeur": p and p["nom"]},
            {"cle": "type_vehicule", "label": "Type véhicule", "type": "liste",
             "options": [(c, c) for c in ("moto", "voiture", "camion", "bus", "autre")],
             "valeur": (p and p["type_vehicule"]) or "voiture"},
            {"cle": "type_lavage", "label": "Type lavage", "type": "liste",
             "options": [(c, c) for c in ("exterieur", "interieur", "complet", "option")],
             "valeur": (p and p["type_lavage"]) or "exterieur"},
            {"cle": "prix", "label": "Prix (F)", "type": "entier", "obligatoire": True, "valeur": p and p["prix"]},
            {"cle": "duree_min", "label": "Durée (min)", "type": "entier", "valeur": (p and p["duree_min"]) or 20},
            {"cle": "tva", "label": "TVA (%)", "type": "reel", "valeur": (p and p["tva"]) or 0},
        ]
        # Retire "code" de la validation si modification
        if p:
            champs[0] = {"cle": "_ignore", "label": "Code (non modifiable)", "valeur": p["code"]}
        Formulaire(page, "Fiche prestation", champs,
                   lambda v: enregistrer(v, p["id"] if p else None, ancien=p)).ouvrir()

    lignes = [(p["id"], [p["code"], p["nom"], p["type_vehicule"], p["type_lavage"],
                         FCFA(p["prix"]), f"{p['duree_min']} min", f"{p['tva']:g} %"])
              for p in prestations]

    return ft.Column([
        ft.Row([titre_page("Prestations", ft.Icons.LOCAL_CAR_WASH),
                bouton_principal("Nouvelle prestation", ft.Icons.ADD, lambda e: form())],
               alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.Container(tableau(["Code", "Nom", "Véhicule", "Lavage", "Prix", "Durée", "TVA"],
                             lignes, sur_selection=lambda i: form(next(p for p in prestations if p["id"] == i))),
                     bgcolor=BLANC, border_radius=12, padding=10),
    ], spacing=16, scroll=ft.ScrollMode.AUTO, expand=True)


# ======================================================================
# MODULE 6 : STOCK
# ======================================================================
def vue_stock(page, session, rafraichir):
    produits = services.stock_reel(site_id=session.get("site_id"))
    conn = get_conn()
    fournisseurs = [dict(r) for r in conn.execute("SELECT id, nom FROM fournisseurs ORDER BY nom").fetchall()]
    conn.close()

    def enregistrer(vals, pid=None, ancien=None):
        conn = get_conn()
        try:
            revendable = 1 if vals.get("revendable") == "Oui" else 0
            if pid:
                conn.execute("UPDATE produits SET nom=?, categorie=?, unite=?, stock_min=?, "
                             "prix_achat=?, prix_vente=?, revendable=?, date_peremption=?, "
                             "fournisseur_id=? WHERE id=?",
                             (vals["nom"], vals["categorie"], vals["unite"], vals["stock_min"],
                              vals["prix_achat"], vals["prix_vente"], revendable, vals["peremption"],
                              int(vals["fournisseur"]) if vals["fournisseur"] else None, pid))
                # Audit : changement de prix d'achat ou de vente
                if ancien is not None:
                    chgs = []
                    if int(ancien["prix_achat"]) != int(vals["prix_achat"]):
                        chgs.append(f"achat {ancien['prix_achat']}→{vals['prix_achat']} F")
                    if int(ancien.get("prix_vente") or 0) != int(vals["prix_vente"]):
                        chgs.append(f"vente {ancien.get('prix_vente') or 0}→{vals['prix_vente']} F")
                    if chgs:
                        audit.journaliser(session["utilisateur"], "Modification prix produit",
                                          f"{ancien['nom']} : " + ", ".join(chgs))
            else:
                cur = conn.execute(
                    "INSERT INTO produits (code, nom, categorie, unite, stock_initial, "
                    "stock_min, prix_achat, prix_vente, revendable, date_peremption, fournisseur_id) "
                    "VALUES (?,?,?,?,0,?,?,?,?,?,?)",
                    (vals["code"], vals["nom"], vals["categorie"], vals["unite"],
                     vals["stock_min"], vals["prix_achat"],
                     vals["prix_vente"], revendable, vals["peremption"],
                     int(vals["fournisseur"]) if vals["fournisseur"] else None))
                pid_new = cur.lastrowid
                # Stock initial → entrée sur le SITE COURANT (stock par site)
                qte_init = float(vals.get("stock_initial") or 0)
                if qte_init > 0:
                    conn.execute(
                        "INSERT INTO mouvements_stock (produit_id, type, quantite, motif, site_id) "
                        "VALUES (?, 'ENTREE', ?, 'Stock initial', ?)",
                        (pid_new, qte_init, session.get("site_id", 1)))
                audit.journaliser(session["utilisateur"], "Création produit",
                                  f"{vals['code']} - {vals['nom']}")
            conn.commit()
            notifier(page, "Produit enregistré.")
        except Exception as ex:
            notifier(page, f"Erreur : {ex}", erreur=True)
        finally:
            conn.close()
        rafraichir()

    def form(p=None):
        champs = ([{"cle": "code", "label": "Code", "obligatoire": True}] if not p else []) + [
            {"cle": "nom", "label": "Nom", "obligatoire": True, "valeur": p and p["nom"]},
            {"cle": "categorie", "label": "Catégorie", "valeur": (p and p["categorie"]) or "Consommable"},
            {"cle": "unite", "label": "Unité", "valeur": (p and p["unite"]) or "unité"},
        ] + ([{"cle": "stock_initial", "label": "Stock initial", "type": "reel", "valeur": 0}] if not p else []) + [
            {"cle": "stock_min", "label": "Stock minimum", "type": "reel", "valeur": (p and p["stock_min"]) or 0},
            {"cle": "prix_achat", "label": "Prix d'achat (F)", "type": "entier", "valeur": (p and p["prix_achat"]) or 0},
            {"cle": "revendable", "label": "Revendable au client ?", "type": "liste",
             "options": [("Non", "Non"), ("Oui", "Oui")],
             "valeur": "Oui" if (p and p.get("revendable")) else "Non"},
            {"cle": "prix_vente", "label": "Prix de vente (F) — si revendable", "type": "entier",
             "valeur": (p and p.get("prix_vente")) or 0},
            {"cle": "peremption", "label": "Date de péremption", "type": "date", "valeur": p and p["date_peremption"]},
            {"cle": "fournisseur", "label": "Fournisseur", "type": "liste",
             "options": [("", "—")] + [(str(f["id"]), f["nom"]) for f in fournisseurs],
             "valeur": p and p.get("fournisseur_id")},
        ]
        Formulaire(page, "Fiche produit", champs,
                   lambda v: enregistrer(v, p["id"] if p else None, ancien=p)).ouvrir()

    def mouvement(p, type_mvt):
        Formulaire(page, f"{'Entrée' if type_mvt == 'ENTREE' else 'Sortie'} — {p['nom']}",
                   [{"cle": "q", "label": f"Quantité ({p['unite']})", "type": "reel", "obligatoire": True},
                    {"cle": "motif", "label": "Motif", "valeur": ""}],
                   lambda v: (services.mouvement_stock(p["id"], type_mvt, v["q"], v["motif"] or "",
                                                       site_id=session.get("site_id", 1)),
                              audit.journaliser(session["utilisateur"],
                                                "Entrée stock" if type_mvt == "ENTREE" else "Sortie stock",
                                                f"{p['nom']} : {v['q']} {p['unite']}"),
                              notifier(page, "Mouvement enregistré."), rafraichir())).ouvrir()

    total_valeur = sum(p["valeur_stock"] for p in produits)
    categories = sorted({p["categorie"] or "—" for p in produits})
    nb_critiques = sum(1 for p in produits if p["critique"])
    etat = {"q": "", "cat": ""}
    zone_tableau = ft.Container()

    def badge_stock(p):
        if p["stock_reel"] <= 0:
            coul, fond = ROUGE, "#FDEDEC"
        elif p["critique"]:
            coul, fond = ORANGE, "#FEF5E7"
        else:
            coul, fond = VERT, "#EAFAF1"
        return ft.Container(
            ft.Text(f"{p['stock_reel']:g}", color=coul, size=12.5, weight=ft.FontWeight.BOLD),
            bgcolor=fond, border_radius=20, alignment=ft.Alignment.CENTER,
            padding=ft.padding.symmetric(vertical=4, horizontal=12))

    def construire_lignes():
        q = etat["q"].strip().lower()
        cat = etat["cat"]
        lignes = []
        for p in produits:
            if q and q not in (p["nom"] or "").lower() and q not in (p["categorie"] or "").lower():
                continue
            if cat and (p["categorie"] or "—") != cat:
                continue
            actions = ft.Row([
                ft.IconButton(ft.Icons.ADD_CIRCLE, icon_color=VERT, icon_size=20, tooltip="Entrée",
                              on_click=lambda e, prod=p: mouvement(prod, "ENTREE")),
                ft.IconButton(ft.Icons.REMOVE_CIRCLE, icon_color=ORANGE, icon_size=20, tooltip="Sortie",
                              on_click=lambda e, prod=p: mouvement(prod, "SORTIE")),
                ft.IconButton(ft.Icons.EDIT, icon_color=BLEU_PROFOND, icon_size=20, tooltip="Modifier",
                              on_click=lambda e, prod=p: form(prod)),
            ], spacing=0)
            cat_p = pastille(p["categorie"] or "—", BLEU_PROFOND, "#EAF2F8")
            lignes.append((p["id"], [p["nom"], cat_p, badge_stock(p),
                                     f"{p['stock_min']:g} {p['unite']}",
                                     FCFA(p["prix_achat"]), FCFA(p["valeur_stock"]), actions]))
        if not lignes:
            zone_tableau.content = etat_vide(
                "Aucun produit trouvé" if (q or cat) else "Aucun produit en stock",
                ft.Icons.INVENTORY_2,
                "Essayez un autre mot-clé ou catégorie." if (q or cat)
                else "Cliquez sur « Nouveau produit » pour commencer.")
        else:
            zone_tableau.content = ft.Column([tableau(
                ["Produit", "Catégorie", "Stock", "Stock min", "Prix achat", "Valeur", "Actions"],
                lignes, alignements=["left", "center", "center", "left", "right", "right", "center"])])
        page.update()

    def sur_recherche(e):
        etat["q"] = e.control.value
        construire_lignes()

    def sur_cat(e):
        etat["cat"] = e.control.value or ""
        construire_lignes()

    champ_recherche = ft.TextField(
        hint_text="Rechercher un produit…", prefix_icon=ft.Icons.SEARCH, width=320,
        height=46, on_change=sur_recherche, content_padding=10)
    filtre_cat = dropdown(on_change=sur_cat, label="Catégorie", width=200, value="",
                          options=[ft.dropdown.Option("", "Toutes")] +
                                  [ft.dropdown.Option(c, c) for c in categories])

    sites = services.lister_sites()
    nom_site = next((s["nom"] for s in sites if s["id"] == session.get("site_id", 1)), "")
    sous_titre = (ft.Container(
        ft.Row([ft.Icon(ft.Icons.STORE, size=16, color=AQUA),
                ft.Text(f"Stock du site : {nom_site}", size=13, color=BLEU_PROFOND,
                        weight=ft.FontWeight.BOLD)]),
        bgcolor="#EAF2F8", border_radius=8, padding=ft.padding.symmetric(vertical=6, horizontal=12))
        if len(sites) > 1 else ft.Container())

    cartes_haut = ft.ResponsiveRow([
        ft.Container(carte_kpi("Valeur totale du stock", FCFA(total_valeur),
                               ft.Icons.WAREHOUSE, BLEU_PROFOND), col={"xs": 12, "md": 6}),
        ft.Container(carte_kpi("Produits en alerte", str(nb_critiques), ft.Icons.WARNING_AMBER,
                               ROUGE if nb_critiques else VERT,
                               "sous le seuil minimum"), col={"xs": 12, "md": 6}),
    ], run_spacing=12, spacing=12)

    construire_lignes()
    return ft.Column([
        ft.Row([titre_page("Stock", ft.Icons.INVENTORY_2),
                bouton_principal("Nouveau produit", ft.Icons.ADD, lambda e: form())],
               alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        sous_titre,
        cartes_haut,
        ft.Row([champ_recherche, filtre_cat], spacing=12, wrap=True),
        zone_tableau,
    ], spacing=16, scroll=ft.ScrollMode.AUTO, expand=True)


# ======================================================================
# MODULE 7 : ACHATS
# ======================================================================
def vue_achats(page, session, rafraichir):
    conn = get_conn()
    achats = [dict(r) for r in conn.execute(
        "SELECT a.*, f.nom fournisseur FROM achats a LEFT JOIN fournisseurs f ON f.id=a.fournisseur_id "
        "ORDER BY a.date DESC").fetchall()]
    fournisseurs = [dict(r) for r in conn.execute("SELECT id, nom FROM fournisseurs ORDER BY nom").fetchall()]
    produits = [dict(r) for r in conn.execute("SELECT id, nom, prix_achat FROM produits WHERE actif=1").fetchall()]
    conn.close()

    def nouveau_fournisseur():
        Formulaire(page, "Nouveau fournisseur",
                   [{"cle": "nom", "label": "Nom", "obligatoire": True},
                    {"cle": "telephone", "label": "Téléphone"},
                    {"cle": "adresse", "label": "Adresse"}],
                   lambda v: (_ajout_fournisseur(v), rafraichir())).ouvrir()

    def _ajout_fournisseur(v):
        conn = get_conn()
        conn.execute("INSERT INTO fournisseurs (nom, telephone, adresse) VALUES (?,?,?)",
                     (v["nom"], v["telephone"], v["adresse"]))
        conn.commit(); conn.close()
        audit.journaliser(session["utilisateur"], "Ajout fournisseur", v["nom"])
        notifier(page, "Fournisseur ajouté.")

    def nouvelle_commande():
        if not produits:
            notifier(page, "Ajoutez d'abord des produits au stock.", erreur=True)
            return
        Formulaire(page, "Nouvelle commande (1 produit)",
                   [{"cle": "fournisseur", "label": "Fournisseur", "type": "liste", "obligatoire": True,
                     "options": [(str(f["id"]), f["nom"]) for f in fournisseurs]},
                    {"cle": "produit", "label": "Produit", "type": "liste", "obligatoire": True,
                     "options": [(str(p["id"]), p["nom"]) for p in produits]},
                    {"cle": "quantite", "label": "Quantité", "type": "reel", "obligatoire": True},
                    {"cle": "prix", "label": "Prix unitaire (F)", "type": "entier", "obligatoire": True}],
                   lambda v: (_creer_commande(v), rafraichir())).ouvrir()

    def _creer_commande(v):
        num = services.creer_achat(int(v["fournisseur"]),
                                   [(int(v["produit"]), v["quantite"], v["prix"])],
                                   site_id=session.get("site_id", 1))
        f_nom = next((f["nom"] for f in fournisseurs if str(f["id"]) == str(v["fournisseur"])), "?")
        p_nom = next((p["nom"] for p in produits if str(p["id"]) == str(v["produit"])), "?")
        audit.journaliser(session["utilisateur"], "Création commande achat",
                          f"{num} — {f_nom} : {p_nom} x{v['quantite']:g} à {FCFA(v['prix'])}")
        notifier(page, f"Commande {num} créée.")

    def receptionner(aid):
        a = next((x for x in achats if x["id"] == aid), None)
        services.receptionner_achat(aid)
        if a:
            audit.journaliser(session["utilisateur"], "Réception achat",
                              f"{a['numero']} — {a['fournisseur'] or 'fournisseur ?'} "
                              f"(stock mis à jour, {FCFA(a['total'])})")
        notifier(page, "Commande réceptionnée, stock mis à jour.")
        rafraichir()

    def payer(a):
        reste = a["total"] - a["montant_paye"]
        def _payer(v):
            services.payer_fournisseur(a["id"], v["montant"], v["mode"] or "Espèces")
            audit.journaliser(session["utilisateur"], "Paiement fournisseur",
                              f"{a['numero']} — {a['fournisseur'] or 'fournisseur ?'} : "
                              f"{FCFA(v['montant'])} ({v['mode'] or 'Espèces'})")
            notifier(page, "Paiement enregistré.")
            rafraichir()
        Formulaire(page, f"Paiement fournisseur — {a['numero']}",
                   [{"cle": "montant", "label": f"Montant (reste {FCFA(reste)})", "type": "entier",
                     "obligatoire": True, "valeur": reste},
                    {"cle": "mode", "label": "Mode", "type": "liste",
                     "options": [(m, m) for m in services.MODES_PAIEMENT]}],
                   _payer).ouvrir()

    lignes = []
    for a in achats:
        actions = ft.Row([
            ft.IconButton(ft.Icons.LOCAL_SHIPPING, icon_color=VERT, icon_size=20, tooltip="Réceptionner",
                          on_click=lambda e, i=a["id"]: receptionner(i)) if a["statut"] == "Commande" else ft.Container(),
            ft.IconButton(ft.Icons.PAYMENTS, icon_color=BLEU_PROFOND, icon_size=20, tooltip="Payer",
                          on_click=lambda e, ac=a: payer(ac)) if a["montant_paye"] < a["total"] else ft.Container(),
        ], spacing=0)
        lignes.append((a["id"], [a["numero"], a["date"], a["fournisseur"] or "—", a["statut"],
                                 FCFA(a["total"]), FCFA(a["montant_paye"]), actions]))

    return ft.Column([
        ft.Row([titre_page("Achats", ft.Icons.SHOPPING_CART),
                ft.Row([bouton_principal("Nouveau fournisseur", ft.Icons.STORE, lambda e: nouveau_fournisseur(), GRIS),
                        bouton_principal("Nouvelle commande", ft.Icons.ADD, lambda e: nouvelle_commande())])],
               alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.Container(tableau(["Numéro", "Date", "Fournisseur", "Statut", "Total", "Payé", "Actions"], lignes),
                     bgcolor=BLANC, border_radius=12, padding=10),
    ], spacing=16, scroll=ft.ScrollMode.AUTO, expand=True)


# ======================================================================
# MODULE 8 : DEPENSES
# ======================================================================
def vue_depenses(page, session, rafraichir):
    conn = get_conn()
    depenses = [dict(r) for r in conn.execute("SELECT * FROM depenses ORDER BY date DESC, id DESC LIMIT 200").fetchall()]
    conn.close()

    def ajouter():
        Formulaire(page, "Nouvelle dépense",
                   [{"cle": "categorie", "label": "Catégorie", "type": "liste", "obligatoire": True,
                     "options": [(c, c) for c in ("Electricité", "Eau", "Salaires", "Maintenance",
                                                  "Produits", "Carburant", "Internet", "Téléphone", "Divers")]},
                    {"cle": "libelle", "label": "Libellé", "obligatoire": True},
                    {"cle": "montant", "label": "Montant (F)", "type": "entier", "obligatoire": True},
                    {"cle": "mode", "label": "Mode de paiement", "type": "liste",
                     "options": [(m, m) for m in services.MODES_PAIEMENT]},
                    {"cle": "photo", "label": "Photo facture (chemin fichier)", "valeur": ""}],
                   lambda v: (_ajout(v), rafraichir())).ouvrir()

    def _ajout(v):
        conn = get_conn()
        conn.execute("INSERT INTO depenses (categorie, libelle, montant, mode_paiement, photo, site_id) "
                     "VALUES (?,?,?,?,?,?)",
                     (v["categorie"], v["libelle"], v["montant"], v["mode"] or "Espèces", v["photo"],
                      session.get("site_id", 1)))
        conn.commit(); conn.close()
        audit.journaliser(session["utilisateur"], "Ajout dépense",
                          f"{v['categorie']} - {v['libelle']} ({FCFA(v['montant'])})")
        notifier(page, "Dépense enregistrée.")

    lignes = [(d["id"], [d["date"], d["categorie"], d["libelle"], FCFA(d["montant"]),
                         d["mode_paiement"], "📎" if d["photo"] else ""]) for d in depenses]
    total = sum(d["montant"] for d in depenses)

    return ft.Column([
        ft.Row([titre_page("Dépenses", ft.Icons.MONEY_OFF),
                bouton_principal("Nouvelle dépense", ft.Icons.ADD, lambda e: ajouter(), ROUGE)],
               alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        carte_kpi("Total des dépenses affichées", FCFA(total), ft.Icons.RECEIPT, ROUGE),
        ft.Container(tableau(["Date", "Catégorie", "Libellé", "Montant", "Mode", "Justif."], lignes),
                     bgcolor=BLANC, border_radius=12, padding=10),
    ], spacing=16, scroll=ft.ScrollMode.AUTO, expand=True)


# ======================================================================
# MODULE 9 : EMPLOYES
# ======================================================================
def vue_employes(page, session, rafraichir):
    conn = get_conn()
    employes = [dict(r) for r in conn.execute("""
        SELECT e.*,
               (SELECT COUNT(*) FROM vente_employes ve JOIN ventes v ON v.id=ve.vente_id
                WHERE ve.employe_id=e.id AND v.statut='Payée') productivite,
               (SELECT COUNT(*) FROM absences a WHERE a.employe_id=e.id) nb_absences
        FROM employes e ORDER BY e.nom""").fetchall()]
    conn.close()

    def enregistrer(vals, eid=None):
        conn = get_conn()
        if eid:
            conn.execute("UPDATE employes SET nom=?, telephone=?, fonction=?, salaire=?, prime=?, horaires=? WHERE id=?",
                         (vals["nom"], vals["telephone"], vals["fonction"], vals["salaire"],
                          vals["prime"], vals["horaires"], eid))
        else:
            conn.execute("INSERT INTO employes (nom, telephone, fonction, salaire, prime, horaires) VALUES (?,?,?,?,?,?)",
                         (vals["nom"], vals["telephone"], vals["fonction"], vals["salaire"],
                          vals["prime"], vals["horaires"]))
        conn.commit(); conn.close()
        notifier(page, "Employé enregistré.")
        rafraichir()

    def form(e=None):
        champs = [
            {"cle": "nom", "label": "Nom", "obligatoire": True, "valeur": e and e["nom"]},
            {"cle": "telephone", "label": "Téléphone", "valeur": e and e["telephone"]},
            {"cle": "fonction", "label": "Fonction", "valeur": e and e["fonction"]},
            {"cle": "salaire", "label": "Salaire (F)", "type": "entier", "valeur": (e and e["salaire"]) or 0},
            {"cle": "prime", "label": "Prime (F)", "type": "entier", "valeur": (e and e["prime"]) or 0},
            {"cle": "horaires", "label": "Horaires", "valeur": (e and e["horaires"]) or "08h00 - 20h00"},
        ]
        Formulaire(page, "Fiche employé", champs,
                   lambda v: enregistrer(v, e["id"] if e else None)).ouvrir()

    def absence(emp):
        Formulaire(page, f"Absence / congé — {emp['nom']}",
                   [{"cle": "type", "label": "Type", "type": "liste",
                     "options": [(t, t) for t in ("Absence", "Congé", "Retard", "Maladie")]},
                    {"cle": "motif", "label": "Motif"}],
                   lambda v: (_ajout_absence(emp["id"], v), rafraichir())).ouvrir()

    def _ajout_absence(eid, v):
        conn = get_conn()
        conn.execute("INSERT INTO absences (employe_id, type, motif) VALUES (?,?,?)",
                     (eid, v["type"] or "Absence", v["motif"]))
        conn.commit(); conn.close()
        notifier(page, "Absence enregistrée.")

    lignes = []
    for e in employes:
        actions = ft.Row([
            ft.IconButton(ft.Icons.EDIT, icon_color=BLEU_PROFOND, icon_size=20, tooltip="Modifier",
                          on_click=lambda ev, emp=e: form(emp)),
            ft.IconButton(ft.Icons.EVENT_BUSY, icon_color=ORANGE, icon_size=20, tooltip="Absence",
                          on_click=lambda ev, emp=e: absence(emp)),
        ], spacing=0)
        lignes.append((e["id"], [e["nom"], e["fonction"] or "—", FCFA(e["salaire"]), FCFA(e["prime"]),
                                 str(e["productivite"]), str(e["nb_absences"]), actions]))

    return ft.Column([
        ft.Row([titre_page("Employés", ft.Icons.BADGE),
                bouton_principal("Nouvel employé", ft.Icons.PERSON_ADD, lambda e: form())],
               alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.Container(tableau(["Nom", "Fonction", "Salaire", "Prime", "Lavages", "Absences", "Actions"], lignes),
                     bgcolor=BLANC, border_radius=12, padding=10),
    ], spacing=16, scroll=ft.ScrollMode.AUTO, expand=True)


# ======================================================================
# MODULE 11 + 12 : RAPPORTS & KPI
# ======================================================================
# Icône propre à chaque indicateur KPI (rend l'écran Rapports plus lisible)
ICONES_KPI = {
    # Commercial
    "CA de la période": ft.Icons.PAYMENTS,
    "dont CA revente produits": ft.Icons.SHOPPING_BAG,
    "Marge sur revente produits": ft.Icons.TRENDING_UP,
    "Taux de marge revente (%)": ft.Icons.PERCENT,
    "Nombre de ventes": ft.Icons.RECEIPT_LONG,
    "Nombre de clients": ft.Icons.GROUP,
    "Panier moyen": ft.Icons.SHOPPING_CART,
    "Nombre de prestations": ft.Icons.LOCAL_CAR_WASH,
    # Exploitation
    "Véhicules lavés": ft.Icons.DIRECTIONS_CAR,
    "Temps moyen de lavage (min)": ft.Icons.TIMER,
    "Véhicules par heure": ft.Icons.SPEED,
    "Taux d'occupation (%)": ft.Icons.PIE_CHART,
    "CA par heure": ft.Icons.SCHEDULE,
    # Stock
    "Valeur du stock": ft.Icons.WAREHOUSE,
    "Produits critiques": ft.Icons.WARNING_AMBER,
    "Consommation de la période": ft.Icons.LOCAL_SHIPPING,
    "Consommation journalière moyenne": ft.Icons.CALENDAR_TODAY,
    "Rotation du stock (%)": ft.Icons.AUTORENEW,
    "Ruptures (stock à zéro)": ft.Icons.REMOVE_SHOPPING_CART,
    # Finance
    "Chiffre d'affaires": ft.Icons.PAYMENTS,
    "Coût des consommables": ft.Icons.INVENTORY,
    "Marge brute": ft.Icons.TRENDING_UP,
    "Charges fixes": ft.Icons.HOME_WORK,
    "Charges variables": ft.Icons.SHOWER,
    "Bénéfice net": ft.Icons.SAVINGS,
    "Coût moyen par lavage": ft.Icons.CALCULATE,
    "Rentabilité (%)": ft.Icons.PERCENT,
    "Seuil de rentabilité": ft.Icons.FLAG,
    # Marketing
    "Nouveaux clients": ft.Icons.PERSON_ADD,
    "Clients fidèles": ft.Icons.LOYALTY,
    "Taux de retour (%)": ft.Icons.REPLAY,
    "Fréquence moyenne (visites/client)": ft.Icons.REPEAT,
}


def vue_rapports(page, session, rafraichir):
    auj = date.today()
    debut = ft.TextField(label="Du (AAAA-MM-JJ)", value=str(auj.replace(day=1)), width=180)
    fin = ft.TextField(label="Au (AAAA-MM-JJ)", value=str(auj), width=180)
    zone_kpi = ft.Column(spacing=14)

    def periode(jours=None, mois=False, annee=False):
        def _(e):
            if mois:
                debut.value = str(auj.replace(day=1)); fin.value = str(auj)
            elif annee:
                debut.value = str(auj.replace(month=1, day=1)); fin.value = str(auj)
            elif jours is not None:
                debut.value = str(auj - timedelta(days=jours)); fin.value = str(auj)
            page.update()
            afficher(None)
        return _

    def afficher(e):
        try:
            kpi = services.calculer_kpi(debut.value.strip(), fin.value.strip())
        except Exception as ex:
            notifier(page, f"Dates invalides : {ex}", erreur=True)
            return
        zone_kpi.controls.clear()

        def bloc(titre, dico, icone, couleur):
            cartes = [ft.Container(
                carte_kpi(k, FCFA(v) if _est_montant(k) else str(v),
                          ICONES_KPI.get(k, icone), couleur),
                col={"xs": 12, "sm": 6, "md": 4}) for k, v in dico.items()]
            zone_kpi.controls.append(ft.Column([
                ft.Row([ft.Icon(icone, color=couleur, size=20),
                        ft.Text(titre, size=17, weight=ft.FontWeight.BOLD, color=couleur)], spacing=6),
                ft.ResponsiveRow(cartes, run_spacing=10, spacing=10),
            ], spacing=8))

        bloc("Commercial", kpi["commercial"], ft.Icons.SELL, BLEU_PROFOND)
        bloc("Exploitation", kpi["exploitation"], ft.Icons.SPEED, AQUA)
        bloc("Stock", kpi["stock"], ft.Icons.INVENTORY_2, ORANGE)
        bloc("Finance", kpi["finance"], ft.Icons.ACCOUNT_BALANCE, VERT)
        bloc("Marketing", kpi["marketing"], ft.Icons.CAMPAIGN, "#8E44AD")

        # CA par prestation (graphique)
        if kpi["ca_par_prestation"]:
            zone_kpi.controls.append(ft.Column([
                ft.Text("CA par prestation", size=17, weight=ft.FontWeight.BOLD, color=BLEU_PROFOND),
                graphique_barres([(r["nom"][:10], r["ca"]) for r in kpi["ca_par_prestation"][:8]]),
            ], spacing=8))

        # Revente de produits : CA et marge par produit
        if kpi["ca_par_produit"]:
            lignes = [(i, [r["nom"], f"{r['nb']:g}", FCFA(r["ca"]),
                           ft.Text(FCFA(r["marge"]), color=VERT if (r["marge"] or 0) >= 0 else ROUGE,
                                   weight=ft.FontWeight.BOLD, size=12.5)])
                      for i, r in enumerate(kpi["ca_par_produit"])]
            zone_kpi.controls.append(ft.Column([
                ft.Text("Revente de produits — CA et marge", size=17,
                        weight=ft.FontWeight.BOLD, color=BLEU_PROFOND),
                ft.Container(tableau(["Produit", "Qté vendue", "CA", "Marge (vente − achat)"], lignes),
                             bgcolor=BLANC, border_radius=12, padding=10),
            ], spacing=8))

        # Top 20 clients
        if kpi["top_clients"]:
            lignes = [(i, [r["nom"], r["telephone"] or "—", str(r["visites"]), FCFA(r["total"])])
                      for i, r in enumerate(kpi["top_clients"])]
            zone_kpi.controls.append(ft.Column([
                ft.Text("Top 20 clients", size=17, weight=ft.FontWeight.BOLD, color=BLEU_PROFOND),
                ft.Container(tableau(["Client", "Téléphone", "Visites", "Total"], lignes),
                             bgcolor=BLANC, border_radius=12, padding=10),
            ], spacing=8))
        page.update()

    def exporter(e):
        try:
            fichiers = exports.exporter_rapport_kpi(debut.value.strip(), fin.value.strip())
            _ouvrir_fichier(page, fichiers[0])
            notifier(page, f"{len(fichiers)} fichiers exportés (Excel, PDF, CSV).")
        except Exception as ex:
            notifier(page, f"Erreur : {ex}", erreur=True)

    def exporter_classeur(e):
        _ouvrir_fichier(page, exports.exporter_classeur_complet())

    afficher(None)
    return ft.Column([
        titre_page("Rapports & Indicateurs KPI", ft.Icons.ANALYTICS),
        ft.Row([debut, fin,
                bouton_principal("Afficher", ft.Icons.SEARCH, afficher)], wrap=True, spacing=10),
        ft.Row([
            ft.OutlinedButton("Aujourd'hui", on_click=periode(jours=0)),
            ft.OutlinedButton("7 jours", on_click=periode(jours=7)),
            ft.OutlinedButton("Ce mois", on_click=periode(mois=True)),
            ft.OutlinedButton("Cette année", on_click=periode(annee=True)),
        ], wrap=True, spacing=8),
        ft.Row([
            bouton_principal("Exporter le rapport (Excel + PDF + CSV)", ft.Icons.DOWNLOAD, exporter, VERT),
            bouton_principal("Exporter le classeur Excel complet", ft.Icons.TABLE_VIEW, exporter_classeur, AQUA),
        ], wrap=True, spacing=10),
        ft.Divider(),
        zone_kpi,
    ], spacing=16, scroll=ft.ScrollMode.AUTO, expand=True)


def _est_montant(cle):
    mots = ("CA", "FCFA", "Marge", "Bénéfice", "Valeur", "Coût", "Charges",
            "Panier", "Seuil", "Consommation", "affaires")
    return any(m in cle for m in mots)


# ======================================================================
# MODULE 14 : PARAMETRES & UTILISATEURS
# ======================================================================
def vue_parametres(page, session, rafraichir):
    cles = [("entreprise_nom", "Nom de l'entreprise"),
            ("entreprise_slogan", "Slogan"),
            ("entreprise_ninea", "NINEA"),
            ("entreprise_rccm", "RCCM"),
            ("entreprise_adresse", "Adresse"),
            ("entreprise_telephone", "Téléphone 1"),
            ("entreprise_telephone2", "Téléphone 2"),
            ("entreprise_email", "Email affiché sur les factures"),
            ("entreprise_logo", "Logo (chemin fichier)"),
            ("seuil_fidelite", "Visites pour être client fidèle")]
    champs = {cle: ft.TextField(label=label, value=get_parametre(cle), width=380)
              for cle, label in cles}
    champ_intervalle = ft.TextField(
        label="Intervalle d'actualisation automatique (secondes)",
        value=get_parametre("auto_refresh_intervalle", "20"), width=380)
    champs["auto_refresh_intervalle"] = champ_intervalle

    # Assistant Claude (IA générative optionnelle)
    champ_cle_ia = ft.TextField(label="Clé API Anthropic (optionnelle)",
                                value=get_parametre("anthropic_api_key", ""), width=380,
                                password=True, can_reveal_password=True)
    champs["anthropic_api_key"] = champ_cle_ia

    # Champs de messagerie (envoi réel des factures par e-mail)
    cles_mail = [("email_expediteur", "Adresse e-mail d'envoi (expéditeur)"),
                 ("email_mot_de_passe", "Mot de passe d'application"),
                 ("email_smtp_serveur", "Serveur SMTP"),
                 ("email_smtp_port", "Port SMTP")]
    champs_mail = {}
    for cle, label in cles_mail:
        tf = ft.TextField(label=label, value=get_parametre(cle), width=380)
        if cle == "email_mot_de_passe":
            tf.password = True
            tf.can_reveal_password = True
        champs_mail[cle] = tf

    def sauver(e):
        for cle, c in list(champs.items()) + list(champs_mail.items()):
            set_parametre(cle, c.value or "")
        audit.journaliser(session["utilisateur"], "Modification paramètres entreprise", "")
        notifier(page, "Paramètres enregistrés.")

    # Détection du logo actuel
    logo_actuel = exports.trouver_logo()
    if logo_actuel:
        import os as _os
        info_logo = ft.Row([ft.Icon(ft.Icons.CHECK_CIRCLE, color=VERT, size=18),
                             ft.Text(f"Logo détecté : {_os.path.basename(logo_actuel)}",
                                     size=13, color=VERT)])
    else:
        info_logo = ft.Row([ft.Icon(ft.Icons.INFO, color=ORANGE, size=18),
                             ft.Text("Aucun logo détecté.", size=13, color=ORANGE)])
    bloc_logo = ft.Container(ft.Column([
        ft.Text("Logo sur les factures", size=16, weight=ft.FontWeight.BOLD, color=BLEU_PROFOND),
        info_logo,
        ft.Text("Pour mettre votre logo : placez votre fichier dans le dossier « assets » "
                "de l'application, nommé « logo.png » (ou logo.svg / logo.jpg). Il apparaîtra "
                "automatiquement, centré en haut de chaque facture.", size=12, color=GRIS),
        ft.Text("Vous pouvez aussi indiquer un chemin précis dans le champ « Logo » ci-dessus.",
                size=12, color=GRIS),
    ], spacing=8), bgcolor=BLANC, border_radius=12, padding=16)

    # Bloc messagerie (SMTP) pour l'envoi réel des factures par e-mail
    from . import mailer
    smtp_ok = mailer.config_smtp_ok()
    etat_smtp = ft.Row([
        ft.Icon(ft.Icons.CHECK_CIRCLE if smtp_ok else ft.Icons.INFO,
                color=VERT if smtp_ok else ORANGE, size=18),
        ft.Text("Messagerie configurée : l'envoi d'e-mails est actif."
                if smtp_ok else "Messagerie non configurée : renseignez les champs ci-dessous.",
                size=13, color=VERT if smtp_ok else ORANGE)])
    bloc_mail = ft.Container(ft.Column([
        ft.Text("Messagerie — envoi des factures par e-mail", size=16,
                weight=ft.FontWeight.BOLD, color=BLEU_PROFOND),
        etat_smtp,
        ft.Text("Pour envoyer réellement les factures par e-mail, renseignez le compte d'envoi. "
                "Avec Gmail, activez la validation en deux étapes puis créez un « mot de passe "
                "d'application » (Compte Google → Sécurité) à coller ci-dessous — n'utilisez pas "
                "votre mot de passe habituel.", size=12, color=GRIS),
        ft.ResponsiveRow([ft.Container(champs_mail["email_expediteur"], col={"xs": 12, "md": 6}),
                          ft.Container(champs_mail["email_mot_de_passe"], col={"xs": 12, "md": 6}),
                          ft.Container(champs_mail["email_smtp_serveur"], col={"xs": 12, "md": 6}),
                          ft.Container(champs_mail["email_smtp_port"], col={"xs": 12, "md": 6})],
                         run_spacing=8),
        ft.Text("Serveurs courants — Gmail : smtp.gmail.com (587) · Outlook : smtp-mail.outlook.com "
                "(587) · Yahoo : smtp.mail.yahoo.com (587).", size=11, color=GRIS),
    ], spacing=10), bgcolor=BLANC, border_radius=12, padding=16)

    # Bloc Assistant Claude (IA optionnelle)
    ia_active = bool(get_parametre("anthropic_api_key", "").strip())
    bloc_ia = ft.Container(ft.Column([
        ft.Row([ft.Icon(ft.Icons.SMART_TOY, color=BLEU_PROFOND),
                ft.Text("Assistant Claude (IA) — optionnel", size=16,
                        weight=ft.FontWeight.BOLD, color=BLEU_PROFOND)]),
        ft.Row([ft.Icon(ft.Icons.CHECK_CIRCLE if ia_active else ft.Icons.INFO,
                        color=VERT if ia_active else ORANGE, size=18),
                ft.Text("Activé : vous pouvez poser des questions dans l'onglet Analyse."
                        if ia_active else "Désactivé : l'analyse locale fonctionne sans cette option.",
                        size=13, color=VERT if ia_active else ORANGE)]),
        ft.Text("Cette option permet de poser des questions en langage naturel (« Pourquoi mon "
                "bénéfice a baissé ? »). Elle nécessite Internet et une clé API Anthropic "
                "(payante à l'usage, quelques centimes par question). Un résumé chiffré et "
                "anonyme de l'activité est alors envoyé à Anthropic — aucun nom de client. "
                "Sans clé, l'application reste 100 % locale.", size=12, color=GRIS),
        champ_cle_ia,
        ft.Text("Obtenez une clé sur console.anthropic.com → API Keys. Laissez vide pour "
                "désactiver l'assistant.", size=11, color=GRIS),
    ], spacing=10), bgcolor=BLANC, border_radius=12, padding=16)

    # Utilisateurs
    utilisateurs = auth.lister_utilisateurs()
    moi = session["utilisateur"]

    def nouvel_utilisateur():
        Formulaire(page, "Nouvel utilisateur",
                   [{"cle": "identifiant", "label": "Identifiant", "obligatoire": True},
                    {"cle": "nom", "label": "Nom", "obligatoire": True},
                    {"cle": "role", "label": "Rôle", "type": "liste", "obligatoire": True,
                     "options": [(r, r) for r in ("Administrateur", "Gérant", "Caissier", "Opérateur")]},
                    {"cle": "mdp", "label": "Mot de passe", "obligatoire": True}],
                   lambda v: (_creer_utilisateur(v), rafraichir())).ouvrir()

    def _creer_utilisateur(v):
        try:
            auth.creer_utilisateur(v["identifiant"], v["nom"], v["role"], v["mdp"])
            audit.journaliser(moi, "Création utilisateur", f"{v['identifiant']} ({v['role']})")
            notifier(page, "Utilisateur créé.")
        except Exception as ex:
            notifier(page, f"Erreur : {ex}", erreur=True)

    def changer_mdp(u):
        Formulaire(page, f"Nouveau mot de passe — {u['identifiant']}",
                   [{"cle": "mdp", "label": "Nouveau mot de passe", "obligatoire": True},
                    {"cle": "mdp2", "label": "Confirmer le mot de passe", "obligatoire": True}],
                   lambda v: _valider_mdp(u, v)).ouvrir()

    def _valider_mdp(u, v):
        if v["mdp"] != v["mdp2"]:
            notifier(page, "Les deux mots de passe ne correspondent pas.", erreur=True)
            return
        if len(v["mdp"]) < 4:
            notifier(page, "Le mot de passe doit contenir au moins 4 caractères.", erreur=True)
            return
        auth.changer_mot_de_passe(u["id"], v["mdp"])
        audit.journaliser(moi, "Changement mot de passe", f"utilisateur : {u['identifiant']}")
        notifier(page, f"Mot de passe de « {u['identifiant']} » modifié.")
        rafraichir()

    def basculer_actif(u):
        nb_admins_actifs = sum(
            1 for x in utilisateurs if x["role"] == "Administrateur" and x["actif"])
        if u["actif"] and u["id"] == moi["id"]:
            notifier(page, "Vous ne pouvez pas désactiver votre propre compte.", erreur=True)
            return
        if u["actif"] and u["role"] == "Administrateur" and nb_admins_actifs <= 1:
            notifier(page, "Impossible : c'est le dernier administrateur actif.", erreur=True)
            return
        auth.activer_desactiver(u["id"], not u["actif"])
        audit.journaliser(moi, "Désactivation compte" if u["actif"] else "Réactivation compte",
                          f"utilisateur : {u['identifiant']}")
        notifier(page, f"Utilisateur « {u['identifiant']} » "
                       f"{'désactivé' if u['actif'] else 'réactivé'}.")
        rafraichir()

    def gerer_acces(u):
        """Ouvre une fenêtre avec une case à cocher par module."""
        perso = auth.get_droits_personnalises(u["id"])
        # état initial : droits personnalisés si définis, sinon droits du rôle
        autorises = set(perso) if perso is not None else {
            m for m, roles in auth.DROITS.items() if u["role"] in roles}
        cases = {}
        lignes = []
        for cle, label in auth.MODULES_LABELS:
            if cle == "parametres":
                continue  # toujours réservé à l'admin, non modifiable
            c = ft.Checkbox(label=label, value=(cle in autorises))
            cases[cle] = c
            lignes.append(c)

        def enregistrer(e):
            choisis = [cle for cle, c in cases.items() if c.value]
            auth.set_droits_personnalises(u["id"], choisis)
            audit.journaliser(moi, "Modification accès utilisateur",
                              f"{u['identifiant']} : {', '.join(choisis) or 'aucun'}")
            page.pop_dialog()
            notifier(page, f"Accès de « {u['identifiant']} » mis à jour.")
            rafraichir()

        def reinitialiser(e):
            auth.set_droits_personnalises(u["id"], [])  # vide => revient aux droits du rôle
            page.pop_dialog()
            notifier(page, f"Accès de « {u['identifiant']} » remis aux droits du rôle {u['role']}.")
            rafraichir()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Accès de {u['nom']} ({u['role']})", color=BLEU_PROFOND,
                          weight=ft.FontWeight.BOLD),
            content=ft.Column(
                [ft.Text("Cochez les onglets auxquels cet utilisateur a accès :",
                         size=12, color=GRIS)] + lignes,
                tight=True, scroll=ft.ScrollMode.AUTO, height=min(60 + 42 * len(lignes), 420)),
            actions=[
                ft.TextButton("Droits du rôle", on_click=reinitialiser),
                ft.TextButton("Annuler", on_click=lambda e: page.pop_dialog()),
                ft.FilledButton("Enregistrer", bgcolor=VERT, color="white", on_click=enregistrer),
            ],
        )
        page.show_dialog(dlg)

    lignes_u = []
    for u in utilisateurs:
        etat = ft.Container(
            ft.Text("Actif" if u["actif"] else "Inactif", color="white", size=11,
                    weight=ft.FontWeight.BOLD),
            bgcolor=VERT if u["actif"] else GRIS, border_radius=8,
            padding=ft.padding.symmetric(vertical=3, horizontal=8))
        actions = ft.Row([
            ft.IconButton(ft.Icons.TUNE, icon_color=AQUA, icon_size=20,
                          tooltip="Gérer les accès (onglets)",
                          on_click=lambda e, us=u: gerer_acces(us)),
            ft.IconButton(ft.Icons.KEY, icon_color=BLEU_PROFOND, icon_size=20,
                          tooltip="Changer le mot de passe",
                          on_click=lambda e, us=u: changer_mdp(us)),
            ft.IconButton(
                ft.Icons.TOGGLE_ON if u["actif"] else ft.Icons.TOGGLE_OFF,
                icon_color=VERT if u["actif"] else GRIS, icon_size=22,
                tooltip="Désactiver" if u["actif"] else "Réactiver",
                on_click=lambda e, us=u: basculer_actif(us)),
        ], spacing=0)
        nom_affiche = u["nom"] + ("  (vous)" if u["id"] == moi["id"] else "")
        lignes_u.append((u["id"], [u["identifiant"], nom_affiche, u["role"], etat, actions]))

    return ft.Column([
        titre_page("Paramètres", ft.Icons.SETTINGS),
        ft.Container(ft.Column([
            ft.Text("Informations de l'entreprise (facturation)", size=16, weight=ft.FontWeight.BOLD, color=BLEU_PROFOND),
            ft.ResponsiveRow([ft.Container(c, col={"xs": 12, "md": 6}) for c in champs.values()],
                             run_spacing=10, spacing=10),
            bouton_principal("Enregistrer les paramètres", ft.Icons.SAVE, sauver, VERT),
        ], spacing=12), bgcolor=BLANC, border_radius=12, padding=16),
        bloc_logo,
        bloc_mail,
        bloc_ia,
        ft.Container(ft.Column([
            ft.Row([ft.Text("Utilisateurs & sécurité", size=16, weight=ft.FontWeight.BOLD, color=BLEU_PROFOND),
                    bouton_principal("Nouvel utilisateur", ft.Icons.PERSON_ADD, lambda e: nouvel_utilisateur())],
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Text("Réglez (⚙) les onglets accessibles par personne, la clé pour le mot de passe, "
                    "l'interrupteur pour activer/désactiver un compte.",
                    size=12, color=GRIS),
            tableau(["Identifiant", "Nom", "Rôle", "État", "Actions"], lignes_u),
        ], spacing=12), bgcolor=BLANC, border_radius=12, padding=16),
        ft.Container(ft.Column([
            ft.Text("Sauvegarde", size=16, weight=ft.FontWeight.BOLD, color=BLEU_PROFOND),
            ft.Text("Une sauvegarde automatique est créée à chaque démarrage (dossier « sauvegardes », 30 jours conservés).",
                    size=13, color=GRIS),
            bouton_principal("Sauvegarder maintenant", ft.Icons.BACKUP,
                             lambda e: (services.sauvegarde_quotidienne(), notifier(page, "Sauvegarde effectuée."))),
        ], spacing=8), bgcolor=BLANC, border_radius=12, padding=16),
    ], spacing=16, scroll=ft.ScrollMode.AUTO, expand=True)


# ======================================================================
# JOURNAL D'AUDIT (réservé administrateur)
# ======================================================================
def vue_audit(page, session, rafraichir):
    from datetime import date as _date
    recherche = ft.TextField(label="Rechercher (utilisateur, action, détail)", width=340)
    debut = ft.TextField(label="Du (AAAA-MM-JJ)", value="", width=160)
    fin = ft.TextField(label="Au (AAAA-MM-JJ)", value="", width=160)
    zone = ft.Column(spacing=0)

    # Couleur selon le type d'action
    def couleur_action(a):
        a = a.lower()
        if "échou" in a or "annulation" in a or "désactiv" in a or "suppress" in a:
            return ROUGE
        if "connexion" in a or "déconnexion" in a:
            return GRIS
        if "prix" in a or "paramètr" in a or "accès" in a or "mot de passe" in a:
            return ORANGE
        return BLEU_PROFOND

    def charger():
        entrees = audit.lister(limite=1000, recherche=recherche.value.strip() or "",
                               debut=debut.value.strip() or None, fin=fin.value.strip() or None)
        lignes = []
        for e in entrees:
            action_c = ft.Text(e["action"], size=12.5, weight=ft.FontWeight.BOLD,
                               color=couleur_action(e["action"]))
            lignes.append((e["id"], [f"{e['date']}", e["heure"][:8], e["utilisateur"] or "—",
                                     action_c, e["details"] or ""]))
        zone.controls.clear()
        zone.controls.append(ft.Text(f"{len(entrees)} action(s) tracée(s)", size=12, color=GRIS))
        zone.controls.append(ft.Container(
            tableau(["Date", "Heure", "Utilisateur", "Action", "Détails"], lignes),
            bgcolor=BLANC, border_radius=12, padding=10))
        page.update()

    def exporter(e):
        chemin = exports.exporter_audit(recherche.value.strip() or "",
                                        debut.value.strip() or None, fin.value.strip() or None)
        _ouvrir_fichier(page, chemin)

    charger()
    return ft.Column([
        titre_page("Journal d'audit", ft.Icons.FACT_CHECK),
        ft.Text("Historique des actions sensibles : connexions, modifications de prix, "
                "annulations de ventes, éditions de factures, gestion des comptes.",
                size=13, color=GRIS),
        ft.Row([recherche, debut, fin,
                bouton_principal("Filtrer", ft.Icons.SEARCH, lambda e: charger()),
                bouton_principal("Exporter (Excel)", ft.Icons.DOWNLOAD, exporter, VERT)],
               wrap=True, spacing=10),
        zone,
    ], spacing=16, scroll=ft.ScrollMode.AUTO, expand=True)


# ======================================================================
# ABONNEMENTS (fidélisation)
# ======================================================================
def vue_abonnements(page, session, rafraichir):
    formules = services.lister_formules(actives_seulement=False)
    abos = services.historique_abonnements()
    conn = get_conn()
    clients = [dict(r) for r in conn.execute("SELECT id, nom FROM clients ORDER BY nom").fetchall()]
    conn.close()

    # Cartes des formules
    def carte_formule(f, recommande=False):
        badges = []
        if f["type"] == "illimite" or f["nb_lavages"] == 0:
            badges.append("Lavages illimités")
        else:
            badges.append(f"{f['nb_lavages']} lavages / {f['duree_jours']} j")
        if f["prioritaire"]:
            badges.append("Prioritaire")
        if f["facturation_mensuelle"]:
            badges.append("Facturation mensuelle")
        couleur = {"quota": AQUA, "illimite": VERT, "entreprise": BLEU_PROFOND}.get(f["type"], AQUA)

        entete = ft.Row([ft.Icon(ft.Icons.WORKSPACE_PREMIUM, color=couleur),
                         ft.Text(f["nom"], size=18, weight=ft.FontWeight.BOLD, color=couleur)],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        if recommande:
            entete = ft.Row([
                ft.Row([ft.Icon(ft.Icons.WORKSPACE_PREMIUM, color=couleur),
                        ft.Text(f["nom"], size=18, weight=ft.FontWeight.BOLD, color=couleur)]),
                pastille("★ Populaire", ORANGE, "#FEF5E7"),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        interieur = ft.Column([
            entete,
            ft.Text(FCFA(f["prix"]) + (" / mois" if f["prix"] else "  (sur devis)"),
                    size=24, weight=ft.FontWeight.BOLD, color=VERT),
            ft.Divider(height=8, color="#EEF2F5"),
            *[ft.Row([ft.Icon(ft.Icons.CHECK_CIRCLE, size=15, color=VERT),
                      ft.Text(b, size=12.5, color=BLEU_PROFOND)]) for b in badges],
            ft.Text(f["description"] or "", size=11, color=GRIS),
            ft.Container(expand=True),  # pousse le bouton en bas → boutons alignés
            ft.FilledButton("Souscrire", icon=ft.Icons.PERSON_ADD, bgcolor=couleur, color="white",
                            width=10000, on_click=lambda e, fo=f: souscrire(fo),
                            style=ft.ButtonStyle(padding=14)),
        ], spacing=8, expand=True)

        return ft.Container(
            interieur, bgcolor=BLANC, border_radius=16, padding=18, height=330,
            border=ft.border.all(2 if recommande else 1, couleur if recommande else "#E0E6E8"),
            shadow=ft.BoxShadow(blur_radius=16 if recommande else 8,
                                color=(couleur + "40") if recommande else "#22000000",
                                offset=ft.Offset(0, 3)))

    def souscrire(f):
        if not clients:
            notifier(page, "Créez d'abord un client (onglet Clients).", erreur=True)
            return
        Formulaire(page, f"Souscrire — {f['nom']}",
                   [{"cle": "client", "label": "Client", "type": "liste", "obligatoire": True,
                     "options": [(str(c["id"]), c["nom"]) for c in clients]},
                    {"cle": "prix", "label": "Prix payé (F)", "type": "entier", "valeur": f["prix"]}],
                   lambda v: _souscrire(f, v)).ouvrir()

    def _souscrire(f, v):
        try:
            abo = services.souscrire_abonnement(int(v["client"]), f["id"], v["prix"])
            audit.journaliser(session["utilisateur"], "Souscription abonnement",
                              f"{f['nom']} — client #{v['client']} ({FCFA(v['prix'])})")
            notifier(page, f"Abonnement {f['nom']} souscrit jusqu'au {abo['date_fin']}.")
            rafraichir()
        except Exception as ex:
            notifier(page, f"Erreur : {ex}", erreur=True)

    # Tableau des souscriptions
    lignes = []
    for a in abos:
        if a["illimite"]:
            conso = "Illimité"
        else:
            conso = f"{a['lavages_utilises']}/{a['lavages_inclus']}"
        statut_c = (pastille("Actif", VERT, "#EAFAF1") if a["statut"] == "Actif"
                    else pastille(a["statut"], GRIS, "#EEEEEE"))
        lignes.append((a["id"], [a["client"], a["formule"], a["date_debut"], a["date_fin"],
                                 conso, ft.Text(FCFA(a["prix_paye"]), weight=ft.FontWeight.BOLD,
                                                size=12.5), statut_c]))

    actifs = [a for a in abos if a["statut"] == "Actif"]
    if lignes:
        bloc_souscriptions = ft.Container(
            tableau(["Client", "Formule", "Début", "Fin", "Lavages", "Prix payé", "Statut"], lignes,
                    alignements=["left", "left", "left", "left", "center", "right", "center"]),
            bgcolor=BLANC, border_radius=12, padding=10)
    else:
        bloc_souscriptions = ft.Container(
            etat_vide("Aucune souscription pour le moment", ft.Icons.CARD_MEMBERSHIP,
                      "Cliquez sur « Souscrire » sur une formule pour abonner un client."),
            bgcolor=BLANC, border_radius=12, padding=10, height=200)
    return ft.Column([
        titre_page("Abonnements", ft.Icons.CARD_MEMBERSHIP),
        ft.Text("Fidélisez vos clients avec des formules d'abonnement. "
                "Un client abonné paie 0 F à la caisse (le lavage est décompté de sa formule).",
                size=13, color=GRIS),
        ft.ResponsiveRow(
            [ft.Container(carte_formule(f, recommande=(f["type"] == "illimite")),
                          col={"xs": 12, "sm": 6, "md": 4})
             for f in sorted([x for x in formules if x["actif"]],
                             key=lambda x: {"quota": 0, "illimite": 1, "entreprise": 2}.get(x["type"], 3))],
            run_spacing=12, spacing=12, vertical_alignment=ft.CrossAxisAlignment.STRETCH),
        ft.Row([carte_kpi("Abonnements actifs", str(len(actifs)), ft.Icons.VERIFIED, VERT)]),
        ft.Text("Souscriptions", size=17, weight=ft.FontWeight.BOLD, color=BLEU_PROFOND),
        bloc_souscriptions,
    ], spacing=16, scroll=ft.ScrollMode.AUTO, expand=True)


# ======================================================================
# CRM / WHATSAPP (fidélisation)
# ======================================================================
def vue_crm(page, session, rafraichir):
    from . import crm
    seuil_fid = int(get_parametre("seuil_fidelite", "5") or 5)

    def envoyer_whatsapp(tel, message):
        lien = crm.lien_whatsapp(tel, message)
        ouvert = _ouvrir_url(page, lien)
        dialog_message_pret(page, "Message WhatsApp", message, lien, ouvert,
                            relancer=lambda: _ouvrir_url(page, lien))

    def envoyer_email(email, sujet, corps):
        lien = crm.lien_email(email, sujet, corps)
        ouvert = _ouvrir_url(page, lien)
        dialog_message_pret(page, "Message e-mail", corps, lien, ouvert,
                            relancer=lambda: _ouvrir_url(page, lien))

    def bouton_wa(tel, message, texte="WhatsApp"):
        actif = bool(crm._tel_e164(tel))
        return ft.FilledButton(texte, icon=ft.Icons.CHAT,
                               bgcolor="#25D366" if actif else "#B2BEC3", color="white",
                               disabled=not actif, tooltip=None if actif else "Numéro manquant/incorrect",
                               on_click=lambda e: envoyer_whatsapp(tel, message))

    # --- Onglet 1 : relance des clients inactifs ---
    def bloc_relance():
        jours = 30
        clients = crm.clients_a_relancer(jours)
        lignes = []
        for c in clients:
            msg = crm.msg_rappel(c["nom"], jours)
            lignes.append((c["id"], [c["nom"], c["telephone"], c["derniere"], str(c["visites"]),
                                     bouton_wa(c["telephone"], msg)]))
        return ft.Column([
            ft.Text(f"Clients sans lavage depuis plus de {jours} jours : {len(clients)}",
                    size=14, weight=ft.FontWeight.BOLD, color=BLEU_PROFOND),
            ft.Text("Cliquez sur WhatsApp pour ouvrir la conversation avec le message de rappel pré-rempli.",
                    size=12, color=GRIS),
            ft.Container(tableau(["Client", "Téléphone", "Dernier lavage", "Visites", "Rappel"], lignes),
                         bgcolor=BLANC, border_radius=12, padding=10) if lignes else
            ft.Text("Aucun client à relancer pour le moment.", size=13, color=GRIS),
        ], spacing=10)

    # --- Onglet 2 : fidélité (proches du lavage offert) ---
    def bloc_fidelite():
        clients = crm.clients_proches_fidelite(seuil_fid, marge=1)
        lignes = []
        for c in clients:
            msg = crm.msg_fidelite(c["nom"], c["visites"], seuil_fid)
            restant = max(seuil_fid - c["visites"], 0)
            etiquette = "Offert atteint !" if restant <= 0 else f"{restant} avant offert"
            lignes.append((c["id"], [c["nom"], c["telephone"], str(c["visites"]), etiquette,
                                     bouton_wa(c["telephone"], msg)]))
        return ft.Column([
            ft.Text(f"Clients proches d'un lavage offert (seuil : {seuil_fid} lavages)",
                    size=14, weight=ft.FontWeight.BOLD, color=BLEU_PROFOND),
            ft.Container(tableau(["Client", "Téléphone", "Lavages", "Statut", "Notifier"], lignes),
                         bgcolor=BLANC, border_radius=12, padding=10) if lignes else
            ft.Text("Aucun client concerné pour le moment.", size=13, color=GRIS),
        ], spacing=10)

    # --- Onglet 3 : promotions ciblées (fêtes) ---
    occasion = ft.Dropdown(label="Occasion", width=240,
                           options=[ft.dropdown.Option(o) for o in crm.OCCASIONS],
                           value=crm.OCCASIONS[0])
    detail = ft.TextField(label="Détail de l'offre (optionnel)", width=360,
                          hint_text="ex : -20% sur le lavage complet")
    zone_promo = ft.Column(spacing=10)

    def generer_promo(e):
        clients = crm.tous_clients_avec_tel()
        occ = occasion.value or crm.OCCASIONS[0]
        det = detail.value.strip()
        lignes = []
        for c in clients:
            msg = crm.msg_promo(c["nom"], occ, det)
            lignes.append((c["id"], [c["nom"], c["telephone"], bouton_wa(c["telephone"], msg)]))
        zone_promo.controls.clear()
        zone_promo.controls.append(
            ft.Text(f"{len(clients)} client(s) avec numéro — message « {occ} » prêt.",
                    size=13, color=GRIS))
        zone_promo.controls.append(
            ft.Container(tableau(["Client", "Téléphone", "Envoyer"], lignes),
                         bgcolor=BLANC, border_radius=12, padding=10) if lignes else
            ft.Text("Aucun client avec numéro de téléphone.", size=13, color=GRIS))
        page.update()

    def bloc_promo():
        return ft.Column([
            ft.Text("Diffusez une promotion à l'occasion d'une fête", size=14,
                    weight=ft.FontWeight.BOLD, color=BLEU_PROFOND),
            ft.Row([occasion, detail,
                    bouton_principal("Préparer", ft.Icons.CAMPAIGN, generer_promo)], wrap=True, spacing=10),
            zone_promo,
        ], spacing=10)

    contenu = ft.Container(bloc_relance(), expand=True)
    etat = {"onglet": "relance"}

    def changer(o):
        etat["onglet"] = o
        contenu.content = {"relance": bloc_relance, "fidelite": bloc_fidelite,
                           "promo": bloc_promo}[o]()
        maj_onglets()
        page.update()

    barre = ft.Row(spacing=8)

    def maj_onglets():
        barre.controls = [
            _onglet_caisse("Relances (30 j)", etat["onglet"] == "relance", lambda e: changer("relance")),
            _onglet_caisse("Fidélité", etat["onglet"] == "fidelite", lambda e: changer("fidelite")),
            _onglet_caisse("Promotions (fêtes)", etat["onglet"] == "promo", lambda e: changer("promo")),
        ]

    maj_onglets()
    return ft.Column([
        titre_page("CRM — WhatsApp", ft.Icons.CAMPAIGN),
        ft.Text("Fidélisez vos clients par WhatsApp : relances, offres de fêtes, cartes de fidélité. "
                "Chaque bouton ouvre WhatsApp avec le message pré-rempli vers le bon numéro.",
                size=13, color=GRIS),
        barre,
        ft.Divider(),
        contenu,
    ], spacing=14, scroll=ft.ScrollMode.AUTO, expand=True)


# ======================================================================
# SITES & COMPARAISON (multi-site)
# ======================================================================
def vue_sites(page, session, rafraichir):
    from datetime import date as _date, timedelta as _td

    # --- Gestion des sites ---
    sites = services.lister_sites()

    def form_site(s=None):
        Formulaire(page, "Fiche site / agence", [
            {"cle": "nom", "label": "Nom du site", "obligatoire": True, "valeur": s and s["nom"]},
            {"cle": "adresse", "label": "Adresse", "valeur": s and s["adresse"]},
            {"cle": "telephone", "label": "Téléphone", "valeur": s and s["telephone"]},
            {"cle": "responsable", "label": "Responsable", "valeur": s and s["responsable"]},
        ], lambda v: _enreg_site(v, s["id"] if s else None)).ouvrir()

    def _enreg_site(v, sid):
        if sid:
            services.modifier_site(sid, v["nom"], v["adresse"], v["telephone"], v["responsable"], 1)
            audit.journaliser(session["utilisateur"], "Modification site", v["nom"])
        else:
            services.creer_site(v["nom"], v["adresse"], v["telephone"], v["responsable"])
            audit.journaliser(session["utilisateur"], "Création site", v["nom"])
        notifier(page, "Site enregistré.")
        rafraichir()

    lignes_sites = []
    for s in sites:
        actif = ft.Text("Actif" if s["actif"] else "Inactif", size=12,
                        color=VERT if s["actif"] else GRIS, weight=ft.FontWeight.BOLD)
        modifier = ft.IconButton(ft.Icons.EDIT, icon_color=BLEU_PROFOND, icon_size=20,
                                 tooltip="Modifier", on_click=lambda e, si=s: form_site(si))
        lignes_sites.append((s["id"], [s["nom"], s["adresse"] or "—", s["telephone"] or "—",
                                       s["responsable"] or "—", actif, modifier]))

    bloc_gestion = ft.Column([
        ft.Row([ft.Text(f"Sites enregistrés : {len(sites)}", size=15,
                        weight=ft.FontWeight.BOLD, color=BLEU_PROFOND),
                bouton_principal("Nouveau site", ft.Icons.ADD_BUSINESS, lambda e: form_site(), VERT)],
               alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.Container(tableau(["Nom", "Adresse", "Téléphone", "Responsable", "Statut", ""], lignes_sites),
                     bgcolor=BLANC, border_radius=12, padding=10),
    ], spacing=10)

    # --- Comparaison sur une période ---
    auj = _date.today()
    debut = ft.TextField(label="Du", value=str(auj.replace(day=1)), width=150)
    fin = ft.TextField(label="Au", value=str(auj), width=150)
    zone_comp = ft.Column(spacing=12)

    def comparer(e=None):
        data = services.comparaison_sites(debut.value.strip(), fin.value.strip())
        zone_comp.controls.clear()
        if not data:
            zone_comp.controls.append(ft.Text("Aucun site.", color=GRIS))
            page.update(); return
        # Tableau comparatif
        lignes = []
        for d in data:
            lignes.append((d["site_id"], [
                d["nom"], FCFA(d["ca"]), str(d["nb_ventes"]), str(d["nb_vehicules"]),
                FCFA(d["depenses"]),
                ft.Text(FCFA(d["benefice"]), weight=ft.FontWeight.BOLD,
                        color=VERT if d["benefice"] >= 0 else ROUGE),
                FCFA(d["panier_moyen"])]))
        # Ligne total (tous sites)
        tot_ca = sum(d["ca"] for d in data); tot_v = sum(d["nb_ventes"] for d in data)
        tot_veh = sum(d["nb_vehicules"] for d in data); tot_dep = sum(d["depenses"] for d in data)
        lignes.append(("_", [ft.Text("TOTAL", weight=ft.FontWeight.BOLD),
                             ft.Text(FCFA(tot_ca), weight=ft.FontWeight.BOLD),
                             ft.Text(str(tot_v), weight=ft.FontWeight.BOLD),
                             ft.Text(str(tot_veh), weight=ft.FontWeight.BOLD),
                             ft.Text(FCFA(tot_dep), weight=ft.FontWeight.BOLD),
                             ft.Text(FCFA(tot_ca - tot_dep), weight=ft.FontWeight.BOLD,
                                     color=VERT if tot_ca - tot_dep >= 0 else ROUGE),
                             ft.Text("—", weight=ft.FontWeight.BOLD)]))
        zone_comp.controls.append(ft.Container(
            tableau(["Site", "CA", "Ventes", "Véhicules", "Dépenses", "Bénéfice", "Panier moyen"], lignes,
                    alignements=["left", "right", "right", "right", "right", "right", "right"]),
            bgcolor=BLANC, border_radius=12, padding=10))
        # Graphique du CA par site
        if any(d["ca"] for d in data):
            zone_comp.controls.append(ft.Column([
                ft.Text("Chiffre d'affaires par site", size=15, weight=ft.FontWeight.BOLD,
                        color=BLEU_PROFOND),
                graphique_barres([(d["nom"][:12], d["ca"]) for d in data]),
            ], spacing=8))
        # Meilleur site
        meilleur = max(data, key=lambda d: d["ca"])
        if meilleur["ca"] > 0:
            zone_comp.controls.append(ft.Container(
                ft.Row([ft.Icon(ft.Icons.EMOJI_EVENTS, color=ORANGE),
                        ft.Text(f"Site le plus performant sur la période : {meilleur['nom']} "
                                f"({FCFA(meilleur['ca'])})", color=BLEU_PROFOND,
                                weight=ft.FontWeight.BOLD)]),
                bgcolor="#FEF9E7", border_radius=10, padding=12))
        page.update()

    comparer()
    return ft.Column([
        titre_page("Sites & comparaison", ft.Icons.STORE),
        ft.Text("Gérez vos différents sites de lavage et comparez leurs performances.",
                size=13, color=GRIS),
        bloc_gestion,
        ft.Divider(),
        ft.Text("Comparaison des sites", size=17, weight=ft.FontWeight.BOLD, color=BLEU_PROFOND),
        ft.Row([debut, fin, bouton_principal("Comparer", ft.Icons.COMPARE_ARROWS, comparer)],
               wrap=True, spacing=10),
        zone_comp,
    ], spacing=16, scroll=ft.ScrollMode.AUTO, expand=True)


# ======================================================================
# ANALYSE & CONSEILS (moteur local, sans Internet)
# ======================================================================
def vue_analyse(page, session, rafraichir):
    from . import analyse
    site_id = session.get("site_id") if len(services.lister_sites()) > 1 else None
    res = analyse.analyser(site_id=site_id)
    conseils = res["conseils"]
    comp = res["compteurs"]

    STYLE = {
        "alerte": (ROUGE, "#FDEDEC", ft.Icons.ERROR, "À traiter"),
        "atten":  (ORANGE, "#FEF5E7", ft.Icons.WARNING_AMBER, "Vigilance"),
        "info":   (BLEU_PROFOND, "#EAF2F8", ft.Icons.LIGHTBULB, "Conseil"),
        "ok":     (VERT, "#EAFAF1", ft.Icons.CHECK_CIRCLE, "OK"),
    }

    # Bandeau résumé
    resume = ft.ResponsiveRow([
        ft.Container(carte_kpi("À traiter", str(comp["alerte"]), ft.Icons.ERROR,
                               ROUGE if comp["alerte"] else GRIS), col={"xs": 6, "md": 3}),
        ft.Container(carte_kpi("Points de vigilance", str(comp["atten"]), ft.Icons.WARNING_AMBER,
                               ORANGE if comp["atten"] else GRIS), col={"xs": 6, "md": 3}),
        ft.Container(carte_kpi("Conseils", str(comp["info"]), ft.Icons.LIGHTBULB,
                               BLEU_PROFOND), col={"xs": 6, "md": 3}),
        ft.Container(carte_kpi("Analyses OK", str(comp["ok"]), ft.Icons.CHECK_CIRCLE,
                               VERT), col={"xs": 6, "md": 3}),
    ], run_spacing=12, spacing=12)

    # Cartes de conseils
    cartes = []
    for c in conseils:
        coul, fond, icone, label = STYLE.get(c["niveau"], STYLE["info"])
        contenu = [
            ft.Row([
                ft.Container(ft.Icon(icone, color="white", size=22),
                             bgcolor=coul, border_radius=10, padding=8),
                ft.Column([
                    ft.Row([ft.Text(c["titre"], size=15, weight=ft.FontWeight.BOLD,
                                    color=BLEU_PROFOND, expand=True),
                            pastille(label, coul, fond)]),
                    ft.Text(c["message"], size=12.5, color=GRIS),
                ], spacing=2, expand=True),
            ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.START),
        ]
        if c.get("action"):
            contenu.append(ft.Container(
                ft.Row([ft.Icon(ft.Icons.ARROW_RIGHT_ALT, size=18, color=coul),
                        ft.Text(c["action"], size=12.5, color=coul, weight=ft.FontWeight.W_500,
                                expand=True)]),
                bgcolor=fond, border_radius=8, padding=10, margin=ft.Margin.only(left=46, top=4)))
        cartes.append(ft.Container(
            ft.Column(contenu, spacing=6),
            bgcolor=BLANC, border_radius=14, padding=16,
            border=ft.Border.only(left=ft.BorderSide(4, coul)),
            shadow=ft.BoxShadow(blur_radius=8, color="#18000000", offset=ft.Offset(0, 2))))

    sites = services.lister_sites()
    nom_site = next((s["nom"] for s in sites if s["id"] == session.get("site_id", 1)), "")
    sous = (f"Analyse du site : {nom_site} — 30 derniers jours" if len(sites) > 1
            else "Analyse des 30 derniers jours")

    # --- Assistant Claude (optionnel) ---
    from . import assistant_ia
    zone_reponse = ft.Column(spacing=8)
    champ_question = ft.TextField(
        hint_text="Posez une question : « Pourquoi mon bénéfice a baissé ? »",
        expand=True, on_submit=lambda e: poser(), multiline=False)

    def poser(e=None):
        q = (champ_question.value or "").strip()
        if not q:
            return
        zone_reponse.controls.append(ft.Container(
            ft.Text(q, size=13, color=BLEU_PROFOND, weight=ft.FontWeight.BOLD),
            bgcolor="#EAF2F8", border_radius=10, padding=10))
        zone_reponse.controls.append(ft.Row([
            ft.ProgressRing(width=16, height=16, stroke_width=2),
            ft.Text("Claude réfléchit…", size=12, color=GRIS)]))
        champ_question.value = ""
        page.update()
        ok, reponse = assistant_ia.demander(q, site_id=session.get("site_id"))
        zone_reponse.controls.pop()  # retirer l'indicateur
        zone_reponse.controls.append(ft.Container(
            ft.Row([ft.Icon(ft.Icons.SMART_TOY, color=VERT if ok else ROUGE, size=20),
                    ft.Text(reponse, size=13, color=BLEU_PROFOND if ok else ROUGE,
                            selectable=True, expand=True)],
                   vertical_alignment=ft.CrossAxisAlignment.START, spacing=8),
            bgcolor="#F4F8FB", border_radius=10, padding=12))
        page.update()

    if assistant_ia.cle_configuree():
        bloc_ia = ft.Container(ft.Column([
            ft.Row([ft.Icon(ft.Icons.SMART_TOY, color=BLEU_PROFOND),
                    ft.Text("Poser une question à Claude", size=16, weight=ft.FontWeight.BOLD,
                            color=BLEU_PROFOND)]),
            ft.Text("Claude reçoit un résumé chiffré et anonyme de votre activité pour répondre. "
                    "Nécessite Internet ; facturé à l'usage.", size=11, color=GRIS),
            ft.Row([champ_question,
                    bouton_principal("Demander", ft.Icons.SEND, poser)], spacing=8),
            zone_reponse,
        ], spacing=10), bgcolor=BLANC, border_radius=14, padding=16,
            border=ft.Border.only(left=ft.BorderSide(4, BLEU_PROFOND)))
    else:
        bloc_ia = ft.Container(ft.Row([
            ft.Icon(ft.Icons.SMART_TOY, color=GRIS),
            ft.Column([
                ft.Text("Assistant Claude (optionnel, désactivé)", size=14,
                        weight=ft.FontWeight.BOLD, color=BLEU_PROFOND),
                ft.Text("Pour poser des questions en langage naturel, ajoutez une clé API "
                        "Anthropic dans Paramètres. Nécessite Internet et un coût à l'usage. "
                        "Sans cela, l'analyse locale ci-dessus reste entièrement gratuite.",
                        size=12, color=GRIS),
            ], spacing=2, expand=True),
        ], spacing=12), bgcolor="#F4F8FB", border_radius=14, padding=16)

    return ft.Column([
        ft.Row([titre_page("Analyse & conseils", ft.Icons.INSIGHTS),
                ft.IconButton(ft.Icons.REFRESH, icon_color=BLEU_PROFOND, tooltip="Relancer l'analyse",
                              on_click=lambda e: rafraichir())],
               alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.Text("Votre assistant local examine vos ventes, votre stock, vos clients et vos "
                "finances pour repérer les problèmes et suggérer des actions. "
                "Aucune donnée ne quitte votre ordinateur.", size=13, color=GRIS),
        ft.Text(sous, size=12, color=AQUA, weight=ft.FontWeight.BOLD),
        resume,
        ft.Divider(),
        ft.Column(cartes, spacing=12),
        ft.Divider(),
        bloc_ia,
    ], spacing=16, scroll=ft.ScrollMode.AUTO, expand=True)
