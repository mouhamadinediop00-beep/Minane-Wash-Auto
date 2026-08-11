# -*- coding: utf-8 -*-
"""
LAVAGE MECKHE - Application principale
Point d'entrée : connexion sécurisée + navigation par rôle.
Lancement :   python main.py       (fenêtre bureau Windows)
              flet run main.py     (mode développement)
"""
import flet.fastapi
import sys
import traceback

# Rediriger toutes les erreurs vers un fichier log.txt au démarrage
sys.stdout = open("log.txt", "w", encoding="utf-8")
sys.stderr = sys.stdout
import flet as ft

from app.database import initialiser_base, get_parametre
from app import auth, services
from app import audit
from app.ui import (BLEU_PROFOND, AQUA, VERT, FOND, BLANC, GRIS, notifier, logo_image)
from app import views


# Modules : (clé de droit, libellé, icône, fonction de vue)
MODULES = [
    ("tableau_de_bord", "Tableau de bord", ft.Icons.DASHBOARD,      views.vue_tableau_de_bord),
    ("analyse",         "Analyse & conseils", ft.Icons.INSIGHTS,     views.vue_analyse),
    ("caisse",          "Caisse",          ft.Icons.POINT_OF_SALE,   views.vue_caisse),
    ("caisse",          "Journal de caisse", ft.Icons.RECEIPT_LONG,  views.vue_journal),
    ("clients",         "Clients",          ft.Icons.PEOPLE,          views.vue_clients),
    ("abonnements",     "Abonnements",      ft.Icons.CARD_MEMBERSHIP, views.vue_abonnements),
    ("crm",             "CRM WhatsApp",     ft.Icons.CAMPAIGN,        views.vue_crm),
    ("vehicules",       "Véhicules",       ft.Icons.DIRECTIONS_CAR,  views.vue_vehicules),
    ("prestations",     "Prestations",     ft.Icons.LOCAL_CAR_WASH,  views.vue_prestations),
    ("stock",           "Stock",           ft.Icons.INVENTORY_2,     views.vue_stock),
    ("achats",          "Achats",          ft.Icons.SHOPPING_CART,   views.vue_achats),
    ("depenses",        "Dépenses",        ft.Icons.MONEY_OFF,       views.vue_depenses),
    ("employes",        "Employés",        ft.Icons.BADGE,           views.vue_employes),
    ("rapports",        "Rapports & KPI",  ft.Icons.ANALYTICS,       views.vue_rapports),
    ("sites",           "Sites & comparaison", ft.Icons.STORE,       views.vue_sites),
    ("audit",           "Journal d'audit", ft.Icons.FACT_CHECK,      views.vue_audit),
    ("parametres",      "Paramètres",      ft.Icons.SETTINGS,        views.vue_parametres),
]


def main(page: ft.Page):
    initialiser_base()
    services.sauvegarde_quotidienne()

    page.title = "Lavage Méckhé — Gestion"
    page.bgcolor = FOND
    page.theme = ft.Theme(
        color_scheme_seed=BLEU_PROFOND,
        color_scheme=ft.ColorScheme(primary=BLEU_PROFOND, secondary=AQUA, tertiary=AQUA,
                                    surface_tint=BLEU_PROFOND),
        scrollbar_theme=ft.ScrollbarTheme(thumb_color="#C3CFDB", thickness=8),
        font_family="Roboto",
    )
    page.window.width = 1200
    page.window.height = 780
    page.window.min_width = 900
    page.window.min_height = 600
    page.padding = 0

    session = {"utilisateur": None}

    # ------------------------------------------------------------------
    # ECRAN D'ACCUEIL : Connexion uniquement (Sécurisé)
    # ------------------------------------------------------------------
    def ecran_connexion():
        contenu = ft.Container()

        # --- Formulaire de CONNEXION ---
        def form_connexion():
            tf_id = ft.TextField(label="Identifiant", width=320, autofocus=True,
                                 prefix_icon=ft.Icons.PERSON)
            tf_mdp = ft.TextField(label="Mot de passe", width=320, password=True,
                                  can_reveal_password=True, prefix_icon=ft.Icons.LOCK,
                                  on_submit=lambda e: tenter())

            def tenter(e=None):
                u = auth.verifier_connexion(tf_id.value, tf_mdp.value)
                if u:
                    session["utilisateur"] = u
                    audit.journaliser(u, "Connexion", "Connexion réussie")
                    construire_app()
                else:
                    audit.journaliser(tf_id.value or "?", "Connexion échouée",
                                      "Identifiant ou mot de passe incorrect")
                    notifier(page, "Identifiant ou mot de passe incorrect.", erreur=True)

            elements = [
                tf_id, tf_mdp,
                ft.Divider(height=6, color="transparent"),
                ft.FilledButton("Se connecter", icon=ft.Icons.LOGIN, width=320,
                                bgcolor=BLEU_PROFOND, color="white", on_click=tenter,
                                style=ft.ButtonStyle(padding=16)),
            ]
            return ft.Column(elements, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=12)

        def afficher():
            contenu.content = form_connexion()
            page.controls.clear()
            page.add(ft.Container(
                ft.Column([
                    ft.Container(
                        ft.Column([
                            (logo_image(width=180) or
                             ft.Icon(ft.Icons.LOCAL_CAR_WASH, size=60, color=AQUA)),
                            ft.Text(get_parametre("entreprise_nom", "MINAN WASH AUTO"),
                                    size=23, weight=ft.FontWeight.BOLD, color=BLEU_PROFOND,
                                    text_align=ft.TextAlign.CENTER),
                            ft.Text(get_parametre("entreprise_slogan", ""), size=13, color=GRIS,
                                    text_align=ft.TextAlign.CENTER),
                            ft.Divider(height=14, color="transparent"),
                            contenu,
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                        bgcolor=BLANC, border_radius=20, padding=36,
                        shadow=ft.BoxShadow(blur_radius=20, color="#33000000"),
                        width=440,
                    ),
                ], alignment=ft.MainAxisAlignment.CENTER,
                   horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                   scroll=ft.ScrollMode.AUTO),
                expand=True, alignment=ft.Alignment.CENTER,
                gradient=ft.LinearGradient(begin=ft.Alignment.TOP_CENTER, end=ft.Alignment.BOTTOM_CENTER,
                                           colors=["#D6EAF8", FOND]),
            ))
            page.update()

        afficher()

    # ------------------------------------------------------------------
    # APPLICATION PRINCIPALE (après connexion)
    # ------------------------------------------------------------------
    def construire_app():
        import threading
        import time as _time
        from datetime import datetime as _dt
        u = session["utilisateur"]
        modules_autorises = [m for m in MODULES if auth.a_le_droit(u, m[0])]
        etat = {"index": 0, "auto": False}
        zone = ft.Container(expand=True, padding=20)
        # Écrans de suivi rafraîchissables automatiquement (jamais les écrans de saisie)
        ECRANS_SUIVI = ("tableau_de_bord", "journal", "rapports", "audit", "stock", "abonnements", "sites")

        # Site courant (multi-site)
        sites = services.lister_sites(actifs_seulement=True) or services.lister_sites()
        if not session.get("site_id") or session["site_id"] not in [s["id"] for s in sites]:
            session["site_id"] = sites[0]["id"] if sites else 1

        maj_label = ft.Text("", size=11, color="#BFD7EA")

        def _intervalle():
            try:
                return max(5, int(get_parametre("auto_refresh_intervalle", "20") or 20))
            except ValueError:
                return 20

        def afficher(index):
            etat["index"] = index
            _, _, _, fn_vue = modules_autorises[index]
            zone.content = fn_vue(page, session, lambda: afficher(etat["index"]))
            cle = modules_autorises[index][0]
            if cle in ECRANS_SUIVI:
                maj_label.value = f"Dernière actualisation à {_dt.now():%H:%M:%S}"
            else:
                maj_label.value = ""
            construire_menu()
            page.update()

        def rafraichir_maintenant(e=None):
            afficher(etat["index"])
            notifier(page, "Données actualisées.")

        def boucle_auto():
            while etat["auto"] and session.get("utilisateur"):
                _time.sleep(_intervalle())
                if not (etat["auto"] and session.get("utilisateur")):
                    break
                cle = modules_autorises[etat["index"]][0]
                # ne rafraîchir que les écrans de suivi (pas la caisse/saisie)
                if cle in ECRANS_SUIVI:
                    try:
                        afficher(etat["index"])
                    except Exception:
                        pass

        def basculer_auto(e):
            etat["auto"] = e.control.value
            if etat["auto"]:
                threading.Thread(target=boucle_auto, daemon=True).start()
                notifier(page, f"Actualisation automatique activée (toutes les {_intervalle()}s, "
                               "écrans de suivi).")
            else:
                notifier(page, "Actualisation automatique désactivée.")

        # Bandeau du menu : logo si disponible, sinon icône + nom de l'entreprise
        logo_menu = logo_image(width=120, badge=True)
        if logo_menu is not None:
            entete_rail = ft.Container(logo_menu, padding=ft.padding.symmetric(vertical=14))
        else:
            nom = get_parametre("entreprise_nom", "MINAN WASH AUTO")
            entete_rail = ft.Container(
                ft.Column([
                    ft.Icon(ft.Icons.LOCAL_CAR_WASH, size=34, color=AQUA),
                    ft.Text(nom, size=12, weight=ft.FontWeight.BOLD, color=BLEU_PROFOND,
                            text_align=ft.TextAlign.CENTER),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4),
                padding=ft.padding.symmetric(vertical=16),
            )

        # Menu de navigation déroulant (défile si l'écran est petit → tous les onglets accessibles)
        menu_col = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=2)

        def construire_menu():
            items = []
            for idx, m in enumerate(modules_autorises):
                sel = (idx == etat["index"])
                items.append(ft.Container(
                    ft.Row([ft.Icon(m[2], color=BLEU_PROFOND if sel else "#7A8896", size=22),
                            ft.Text(m[1], size=13,
                                    color=BLEU_PROFOND if sel else "#34495E",
                                    weight=ft.FontWeight.BOLD if sel else ft.FontWeight.W_500)],
                           spacing=12),
                    bgcolor="#EAF2F8" if sel else None,
                    border=ft.Border.only(left=ft.BorderSide(3, AQUA)) if sel else None,
                    border_radius=8, ink=True,
                    padding=ft.padding.symmetric(vertical=11, horizontal=14),
                    on_click=lambda e, i=idx: afficher(i),
                ))
            menu_col.controls = items

        panneau_menu = ft.Container(
            ft.Column([
                entete_rail,
                ft.Divider(height=1, color="#E5ECF3"),
                ft.Container(menu_col, expand=True,
                             padding=ft.padding.only(left=8, right=8, top=6, bottom=6)),
            ], expand=True, spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            width=218, bgcolor=BLANC,
        )
        construire_menu()

        def deconnexion(e):
            etat["auto"] = False
            audit.journaliser(session["utilisateur"], "Déconnexion", "")
            session["utilisateur"] = None
            ecran_connexion()

        def changer_site(e):
            try:
                session["site_id"] = int(e.control.value)
            except (TypeError, ValueError):
                pass
            afficher(etat["index"])

        selecteur_site = None
        if len(sites) > 1:
            selecteur_site = ft.Dropdown(
                value=str(session["site_id"]), width=210, dense=True,
                label="Site", bgcolor="white",
                options=[ft.dropdown.Option(str(s["id"]), s["nom"]) for s in sites],
                on_change=changer_site)
        elif sites:
            selecteur_site = ft.Text(sites[0]["nom"], color="white", size=12,
                                     weight=ft.FontWeight.BOLD)

        entete = ft.Container(
            ft.Row([
                ft.Row([
                    ft.Text(get_parametre("entreprise_nom"), size=18, weight=ft.FontWeight.BOLD,
                            color="white"),
                    ft.Container(width=8),
                    selecteur_site or ft.Container(),
                ]),
                ft.Row([
                    maj_label,
                    ft.Container(width=6),
                    ft.IconButton(ft.Icons.REFRESH, icon_color="white", tooltip="Actualiser les données",
                                  on_click=rafraichir_maintenant),
                    ft.Row([
                        ft.Switch(value=False, on_change=basculer_auto,
                                  active_color="white", tooltip="Actualisation automatique (écrans de suivi)"),
                        ft.Text("Auto", color="white", size=12),
                    ], spacing=2),
                    ft.Container(width=10),
                    ft.Icon(ft.Icons.ACCOUNT_CIRCLE, color="white"),
                    ft.Text(f"{u['nom']} ({u['role']})", color="white", size=13),
                    ft.IconButton(ft.Icons.LOGOUT, icon_color="white", tooltip="Déconnexion",
                                  on_click=deconnexion),
                ], spacing=8),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            bgcolor=BLEU_PROFOND, padding=ft.padding.symmetric(horizontal=20, vertical=12),
        )

        page.controls.clear()
        page.add(ft.Column([
            entete,
            ft.Row([panneau_menu, ft.VerticalDivider(width=1), zone], expand=True, spacing=0),
        ], expand=True, spacing=0))
        afficher(0)

    ecran_connexion()


# if __name__ == "__main__":
#     ft.app(target=main)
# Vercel va détecter cette variable "app"
app = flet.fastapi.app(main)