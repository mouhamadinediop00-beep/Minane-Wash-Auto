# -*- coding: utf-8 -*-
"""
LAVAGE MECKHE - Composants d'interface réutilisables (Flet)
Thème, cartes KPI, graphique en barres, tableaux et formulaires génériques.
"""

import flet as ft
import os
import base64
from datetime import date

# --- Compat Flet 0.85 : les helpers ft.border.all / ft.padding.* / ft.border_radius.*
# ne sont plus des fonctions de module mais des méthodes de classe. On rétablit les
# raccourcis attendus par le reste du code.
if not hasattr(ft.border, "all"):
    ft.border.all = ft.Border.all
if not hasattr(ft.padding, "all"):
    ft.padding.all = ft.Padding.all
    ft.padding.symmetric = ft.Padding.symmetric
    ft.padding.only = ft.Padding.only if hasattr(ft.Padding, "only") else ft.Padding
if not hasattr(ft.border_radius, "all"):
    ft.border_radius.all = ft.BorderRadius.all
    if hasattr(ft.BorderRadius, "only"):
        ft.border_radius.only = ft.BorderRadius.only
# Les constantes d'alignement sont désormais des attributs MAJUSCULES de la classe
# ft.Alignment (CENTER, TOP_CENTER…) et non plus ft.alignment.center en minuscules.
if not hasattr(ft.alignment, "center"):
    for _nom in ("center", "top_center", "bottom_center", "top_left", "top_right",
                 "bottom_left", "bottom_right", "center_left", "center_right"):
        _const = getattr(ft.Alignment, _nom.upper(), None)
        if _const is not None:
            setattr(ft.alignment, _nom, _const)

# --- Thème : eau & propreté ------------------------------------------
BLEU_PROFOND = "#1B4F72"   # confiance / professionnel
AQUA = "#17A2B8"           # eau
VERT = "#1E8449"           # encaissement / bénéfice
ORANGE = "#CA6F1E"         # alertes
ROUGE = "#B03A2E"          # critique
FOND = "#F4F8FB"
BLANC = "#FFFFFF"
GRIS = "#5D6D7E"

FCFA = lambda n: f"{int(round(n or 0)):,}".replace(",", " ") + " F"

# Dossier des ressources graphiques (logo)
_ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")


def logo_image(width=None, height=None, badge=False):
    """
    Renvoie un ft.Image du logo (PNG/JPG) encodé en base64, ou None si aucun logo
    raster n'est disponible. Cherche dans assets : logo_badge.png (si badge), puis
    logo.png / logo.jpg / logo.jpeg. Le SVG n'est pas affichable ici (utilisé sur
    les factures uniquement) — pour l'app, fournir un PNG.
    """
    noms = (["logo_badge.png"] if badge else []) + [
        "logo.png", "logo.jpg", "logo.jpeg", "logo.PNG", "logo.JPG"]
    for nom in noms:
        chemin = os.path.join(_ASSETS, nom)
        if os.path.exists(chemin):
            try:
                with open(chemin, "rb") as f:
                    donnees = f.read()
                # Flet 0.85 : src accepte une chaîne base64 brute (ou des octets)
                b64 = base64.b64encode(donnees).decode("ascii")
                return ft.Image(
                    src=b64, width=width, height=height, fit=ft.BoxFit.CONTAIN,
                    error_content=ft.Icon(ft.Icons.LOCAL_CAR_WASH, size=48, color=AQUA),
                )
            except Exception:
                return None
    return None


def dropdown(on_change=None, **kwargs):
    """Dropdown compatible Flet 0.85 : on_change n'est plus accepté au constructeur."""
    dd = ft.Dropdown(**kwargs)
    if on_change is not None:
        dd.on_change = on_change
    return dd


def notifier(page: ft.Page, message: str, erreur: bool = False):
    page.show_dialog(ft.SnackBar(
        ft.Text(message, color="white"),
        bgcolor=ROUGE if erreur else VERT,
    ))


def titre_page(texte: str, icone=None):
    return ft.Row([
        ft.Icon(icone, color=BLEU_PROFOND, size=30) if icone else ft.Container(),
        ft.Text(texte, size=24, weight=ft.FontWeight.BOLD, color=BLEU_PROFOND),
    ], spacing=10)


def carte_kpi(titre: str, valeur: str, icone, couleur=BLEU_PROFOND, sous_titre: str = ""):
    return ft.Container(
        content=ft.Row([
            ft.Container(
                ft.Icon(icone, color="white", size=26),
                bgcolor=couleur, border_radius=12, padding=12,
            ),
            ft.Column([
                ft.Text(titre, size=12, color=GRIS),
                ft.Text(valeur, size=19, weight=ft.FontWeight.BOLD, color=couleur),
                ft.Text(sous_titre, size=10, color=GRIS) if sous_titre else ft.Container(),
            ], spacing=1),
        ], spacing=12),
        bgcolor=BLANC, border_radius=14, padding=14, expand=True,
        shadow=ft.BoxShadow(blur_radius=6, color="#22000000"),
    )


def graphique_barres(donnees, hauteur=170, couleur=AQUA, format_valeur=None):
    """Graphique en barres : donnees = [(libellé, valeur), ...].
    Barres avec dégradé, valeur au-dessus, ligne de base, invite si tout est à zéro."""
    fmt = format_valeur or (lambda v: FCFA(v) if v else "")
    maxi = max((v for _, v in donnees), default=0) or 1
    tout_zero = not any(v for _, v in donnees)
    barres = []
    for libelle, valeur in donnees:
        h = max(3, (hauteur - 22) * valeur / maxi) if valeur else 3
        barres.append(ft.Column([
            ft.Text(fmt(valeur), size=9, color=BLEU_PROFOND, weight=ft.FontWeight.BOLD),
            ft.Container(
                width=40, height=h,
                gradient=ft.LinearGradient(begin=ft.Alignment.TOP_CENTER,
                                           end=ft.Alignment.BOTTOM_CENTER,
                                           colors=[AQUA, BLEU_PROFOND]) if valeur else None,
                bgcolor=None if valeur else "#E5ECF3",
                border_radius=ft.BorderRadius(top_left=7, top_right=7, bottom_left=0, bottom_right=0),
                tooltip=f"{libelle} : {fmt(valeur) or '0'}",
                animate_size=ft.Animation(250, ft.AnimationCurve.EASE_OUT),
            ),
            ft.Text(libelle, size=10, color=GRIS),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
           alignment=ft.MainAxisAlignment.END, spacing=3))
    contenu = ft.Column([
        ft.Container(
            ft.Row(barres, alignment=ft.MainAxisAlignment.SPACE_EVENLY,
                   vertical_alignment=ft.CrossAxisAlignment.END),
            height=hauteur),
        ft.Container(height=1, bgcolor="#D5DBDB"),
    ], spacing=0)
    if tout_zero:
        contenu = ft.Stack([contenu, ft.Container(
            ft.Text("Aucune donnée sur la période", size=12, color=GRIS, italic=True),
            alignment=ft.Alignment.CENTER, height=hauteur)])
    return ft.Container(
        contenu, bgcolor=BLANC, border_radius=14, padding=16,
        shadow=ft.BoxShadow(blur_radius=8, color="#1A000000",
                            offset=ft.Offset(0, 2)),
    )


def etat_vide(message, icone=ft.Icons.INBOX, sous_message=""):
    """Bloc d'état vide soigné : icône + message d'invite, centré."""
    col = [ft.Icon(icone, size=52, color="#B7C4D0"),
           ft.Text(message, size=14, color=GRIS, weight=ft.FontWeight.BOLD,
                   text_align=ft.TextAlign.CENTER)]
    if sous_message:
        col.append(ft.Text(sous_message, size=12, color="#9AA7B4",
                           text_align=ft.TextAlign.CENTER))
    return ft.Container(
        ft.Column(col, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
        alignment=ft.Alignment.CENTER, padding=40, expand=True)


def pastille(texte, couleur, fond=None):
    """Petite pastille colorée (statut, catégorie…)."""
    import re as _re
    if fond is None:
        # fond très clair dérivé de la couleur
        fond = couleur + "22" if _re.match(r"^#", str(couleur)) else "#EEEEEE"
    return ft.Container(
        ft.Text(texte, size=11.5, weight=ft.FontWeight.BOLD, color=couleur),
        bgcolor=fond, border_radius=20,
        padding=ft.padding.symmetric(vertical=4, horizontal=10))


def tableau(colonnes, lignes_cellules, sur_selection=None, alignements=None):
    """DataTable zébré, pleine largeur. lignes_cellules = [(id, [val...]), ...].
    alignements : liste optionnelle 'left'/'right'/'center' par colonne."""
    aligns = alignements or ["left"] * len(colonnes)

    def cellule(c, al):
        if isinstance(c, ft.Control):
            ctrl = c
        else:
            ctrl = ft.Text(str(c if c is not None else "—"), size=12.5)
        if al == "right":
            return ft.DataCell(ft.Row([ctrl], alignment=ft.MainAxisAlignment.END))
        if al == "center":
            return ft.DataCell(ft.Row([ctrl], alignment=ft.MainAxisAlignment.CENTER))
        return ft.DataCell(ctrl)

    rows = []
    for idx, (ident, cellules) in enumerate(lignes_cellules):
        rows.append(ft.DataRow(
            cells=[cellule(c, aligns[i] if i < len(aligns) else "left")
                   for i, c in enumerate(cellules)],
            color={"": "#FFFFFF" if idx % 2 == 0 else "#F4F8FB"},
            on_select_change=(lambda e, i=ident: sur_selection(i)) if sur_selection else None,
        ))
    return ft.DataTable(
        columns=[ft.DataColumn(ft.Text(c, weight=ft.FontWeight.BOLD, size=12.5, color=BLEU_PROFOND),
                               numeric=(aligns[i] == "right" if i < len(aligns) else False))
                 for i, c in enumerate(colonnes)],
        rows=rows,
        heading_row_color="#E4EEF6",
        border_radius=12,
        column_spacing=22,
        heading_row_height=44,
        data_row_min_height=42,
        divider_thickness=0.5,
        expand=True,
    )


class Formulaire:
    """
    Formulaire générique en boîte de dialogue.
    champs = [
      {"cle","label","type": "texte|entier|reel|liste|date|multiligne",
       "options":[...], "valeur": ..., "obligatoire": bool}
    ]
    """

    def __init__(self, page, titre, champs, sur_valider, texte_bouton="Enregistrer"):
        self.page = page
        self.sur_valider = sur_valider
        self.controles = {}
        colonne = []
        for ch in champs:
            t = ch.get("type", "texte")
            val = ch.get("valeur")
            label = ch["label"] + (" *" if ch.get("obligatoire") else "")
            if t == "liste":
                c = ft.Dropdown(
                    label=label,
                    options=[ft.dropdown.Option(key=str(k), text=str(v))
                             for k, v in ch["options"]],
                    value=str(val) if val is not None else None,
                    width=380,
                )
            elif t == "date":
                c = ft.TextField(label=label + " (AAAA-MM-JJ)",
                                 value=str(val or ""), width=380)
            elif t == "multiligne":
                c = ft.TextField(label=label, value=str(val or ""),
                                 multiline=True, min_lines=2, width=380)
            else:
                c = ft.TextField(
                    label=label, value="" if val is None else str(val), width=380,
                    keyboard_type=ft.KeyboardType.NUMBER if t in ("entier", "reel") else None,
                )
            c._type = t
            c._obligatoire = ch.get("obligatoire", False)
            self.controles[ch["cle"]] = c
            colonne.append(c)

        self.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(titre, color=BLEU_PROFOND, weight=ft.FontWeight.BOLD),
            content=ft.Column(colonne, tight=True, scroll=ft.ScrollMode.AUTO, height=min(90 * len(colonne), 420)),
            actions=[
                ft.TextButton("Annuler", on_click=lambda e: page.pop_dialog()),
                ft.FilledButton(texte_bouton, bgcolor=VERT, color="white",
                                on_click=self._valider),
            ],
        )

    def ouvrir(self):
        self.page.show_dialog(self.dialog)

    def _valider(self, e):
        valeurs = {}
        for cle, c in self.controles.items():
            v = (c.value or "").strip() if isinstance(c.value, str) else c.value
            if c._obligatoire and not v:
                notifier(self.page, f"Le champ « {c.label.replace(' *','')} » est obligatoire.", erreur=True)
                return
            try:
                if c._type == "entier":
                    v = int(float(v)) if v else 0
                elif c._type == "reel":
                    v = float(v) if v else 0.0
            except ValueError:
                notifier(self.page, f"Valeur numérique invalide pour « {c.label} ».", erreur=True)
                return
            valeurs[cle] = v if v != "" else None
        self.page.pop_dialog()
        self.sur_valider(valeurs)


def confirmer(page, message, sur_oui):
    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text("Confirmation"),
        content=ft.Text(message),
        actions=[
            ft.TextButton("Non", on_click=lambda e: page.pop_dialog()),
            ft.FilledButton("Oui", bgcolor=ROUGE, color="white",
                            on_click=lambda e: (page.pop_dialog(), sur_oui())),
        ],
    )
    page.show_dialog(dlg)


def barre_actions(*boutons):
    return ft.Row(list(boutons), wrap=True, spacing=10)


def bouton_principal(texte, icone, sur_clic, couleur=BLEU_PROFOND):
    return ft.FilledButton(texte, icon=icone, bgcolor=couleur, color="white",
                           on_click=sur_clic,
                           style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10),
                                                padding=14))
