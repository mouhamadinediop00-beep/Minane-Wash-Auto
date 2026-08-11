# -*- coding: utf-8 -*-
"""
LAVAGE MECKHE - Module services (logique métier)
Ventes, stock automatique, journal de caisse, KPI, alertes, sauvegarde.
"""

import os
import shutil
from datetime import date, datetime, timedelta

from .database import get_conn, get_parametre, DB_PATH, BASE_DIR

MODES_PAIEMENT = ["Espèces", "Wave", "Orange Money", "Carte bancaire", "Chèque", "Virement"]
FCFA = lambda n: f"{int(round(n or 0)):,}".replace(",", " ") + " F"


# ======================================================================
# NUMEROTATION AUTOMATIQUE (MODULE 5)
# ======================================================================
def prochain_numero(prefixe: str, table: str, colonne: str = "numero") -> str:
    """Ex : V-20260706-0001, FAC-2026-0001, ACH-2026-0001"""
    conn = get_conn()
    n = conn.execute(
        f"SELECT COUNT(*) FROM {table} WHERE {colonne} LIKE ?", (f"{prefixe}%",)
    ).fetchone()[0]
    conn.close()
    return f"{prefixe}{n + 1:04d}"


# ======================================================================
# MODULE 4 : CAISSE - enregistrement d'une vente
# ======================================================================
def enregistrer_vente(caissier_id, client_id, vehicule_id, lignes, remise,
                      mode_paiement, montant_paye, employes_ids=None, produits=None,
                      abonnement_id=None, site_id=1):
    """
    lignes   = [(prestation_id, prix, quantite), ...]   (prestations de lavage)
    produits = [(produit_id, prix_vente, quantite), ...] (produits revendus au client)
    abonnement_id : si fourni, les prestations sont couvertes par l'abonnement
                    (montant net = uniquement les produits éventuels), et un lavage
                    est décompté du quota.
    Retourne le dict de la vente créée.
    """
    lignes = lignes or []
    produits = produits or []
    if not lignes and not produits:
        raise ValueError("Aucune prestation ni produit sélectionné.")

    # Avec abonnement : les prestations sont "offertes" (déjà payées via l'abonnement),
    # seul le montant des produits revendus reste à payer.
    if abonnement_id:
        brut = sum(int(p) * float(q) for _, p, q in produits)
        mode_paiement = mode_paiement if produits else "Abonnement"
    else:
        brut = sum(int(p) * int(q) for _, p, q in lignes) \
             + sum(int(p) * float(q) for _, p, q in produits)
    brut = int(round(brut))
    remise = int(remise or 0)
    net = max(brut - remise, 0)
    montant_paye = int(montant_paye or net)
    monnaie = max(montant_paye - net, 0)
    numero = prochain_numero(f"V-{date.today():%Y%m%d}-", "ventes")

    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO ventes (numero, caissier_id, client_id, vehicule_id, montant_brut, "
        "remise, montant_net, mode_paiement, montant_paye, monnaie_rendue, statut, abonnement_id, site_id) "
        "VALUES (?,?,?,?,?,?,?,?,?,?, 'Payée', ?, ?)",
        (numero, caissier_id, client_id, vehicule_id, brut, remise, net,
         mode_paiement, montant_paye, monnaie, abonnement_id, int(site_id or 1)),
    )
    vente_id = cur.lastrowid

    for prestation_id, prix, quantite in lignes:
        conn.execute(
            "INSERT INTO vente_lignes (vente_id, prestation_id, prix, quantite) VALUES (?,?,?,?)",
            (vente_id, prestation_id, int(prix), int(quantite)),
        )
        # Consommation automatique de produits (MODULE 2 + 6)
        for pp in conn.execute(
            "SELECT produit_id, quantite FROM prestation_produits WHERE prestation_id=?",
            (prestation_id,),
        ).fetchall():
            conn.execute(
                "INSERT INTO mouvements_stock (produit_id, type, quantite, motif, reference, site_id) "
                "VALUES (?, 'SORTIE', ?, 'Consommation prestation', ?, ?)",
                (pp["produit_id"], pp["quantite"] * int(quantite), numero, int(site_id or 1)),
            )

    # Produits revendus au client : ligne de vente + sortie de stock
    for produit_id, prix, quantite in produits:
        conn.execute(
            "INSERT INTO vente_produits (vente_id, produit_id, prix, quantite) VALUES (?,?,?,?)",
            (vente_id, produit_id, int(prix), float(quantite)),
        )
        conn.execute(
            "INSERT INTO mouvements_stock (produit_id, type, quantite, motif, reference, site_id) "
            "VALUES (?, 'SORTIE', ?, 'Revente produit', ?, ?)",
            (produit_id, float(quantite), numero, int(site_id or 1)),
        )

    for emp_id in (employes_ids or []):
        conn.execute(
            "INSERT OR IGNORE INTO vente_employes (vente_id, employe_id) VALUES (?,?)",
            (vente_id, emp_id),
        )

    conn.commit()
    vente = dict(conn.execute("SELECT * FROM ventes WHERE id=?", (vente_id,)).fetchone())
    conn.close()
    return vente


def annuler_vente(vente_id: int):
    """Annule une vente, restitue le stock consommé et, le cas échéant, le lavage d'abonnement."""
    conn = get_conn()
    vente = conn.execute("SELECT * FROM ventes WHERE id=?", (vente_id,)).fetchone()
    if vente and vente["statut"] != "Annulée":
        conn.execute("UPDATE ventes SET statut='Annulée' WHERE id=?", (vente_id,))
        for mvt in conn.execute(
            "SELECT * FROM mouvements_stock WHERE reference=? AND type='SORTIE'",
            (vente["numero"],),
        ).fetchall():
            conn.execute(
                "INSERT INTO mouvements_stock (produit_id, type, quantite, motif, reference, site_id) "
                "VALUES (?, 'ENTREE', ?, 'Annulation vente', ?, ?)",
                (mvt["produit_id"], mvt["quantite"], vente["numero"],
                 mvt["site_id"] if "site_id" in mvt.keys() else 1),
            )
        # Restituer le lavage décompté sur l'abonnement, s'il y en avait un
        if vente["abonnement_id"]:
            conn.execute("UPDATE abonnements SET lavages_utilises = MAX(lavages_utilises - 1, 0) "
                         "WHERE id=?", (vente["abonnement_id"],))
        conn.commit()
    conn.close()


def journal_de_caisse(jour: str = None, site_id=None) -> dict:
    """Journal de fin de journée : totaux par mode de paiement, dépenses, solde.
    Si site_id est fourni, ne compte que ce site ; sinon tous les sites."""
    jour = jour or str(date.today())
    fs = " AND site_id=?" if site_id else ""
    ps = [site_id] if site_id else []
    conn = get_conn()
    totaux = {m: 0 for m in MODES_PAIEMENT}
    for r in conn.execute(
        "SELECT mode_paiement, SUM(montant_net) t FROM ventes "
        "WHERE date=? AND statut='Payée'" + fs + " GROUP BY mode_paiement", [jour] + ps
    ).fetchall():
        totaux[r["mode_paiement"]] = r["t"] or 0
    ca = sum(totaux.values())
    depenses = conn.execute(
        "SELECT COALESCE(SUM(montant),0) FROM depenses WHERE date=?" + fs, [jour] + ps
    ).fetchone()[0]
    ventes = [dict(r) for r in conn.execute(
        "SELECT v.*, c.nom AS client, u.nom AS caissier, ve.plaque "
        "FROM ventes v LEFT JOIN clients c ON c.id=v.client_id "
        "LEFT JOIN utilisateurs u ON u.id=v.caissier_id "
        "LEFT JOIN vehicules ve ON ve.id=v.vehicule_id "
        "WHERE v.date=?" + (" AND v.site_id=?" if site_id else "") +
        " ORDER BY v.heure", [jour] + ps
    ).fetchall()]
    conn.close()
    return {"date": jour, "totaux": totaux, "ca": ca,
            "depenses": depenses, "solde": ca - depenses, "ventes": ventes}


# ======================================================================
# MULTI-SITE : gestion des sites et comparaison
# ======================================================================
def lister_sites(actifs_seulement=False):
    conn = get_conn()
    q = "SELECT * FROM sites"
    if actifs_seulement:
        q += " WHERE actif=1"
    q += " ORDER BY id"
    rows = [dict(r) for r in conn.execute(q).fetchall()]
    conn.close()
    return rows


def creer_site(nom, adresse="", telephone="", responsable=""):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO sites (nom, adresse, telephone, responsable) VALUES (?,?,?,?)",
        (nom, adresse, telephone, responsable))
    conn.commit()
    sid = cur.lastrowid
    conn.close()
    return sid


def modifier_site(site_id, nom, adresse="", telephone="", responsable="", actif=1):
    conn = get_conn()
    conn.execute("UPDATE sites SET nom=?, adresse=?, telephone=?, responsable=?, actif=? WHERE id=?",
                 (nom, adresse, telephone, responsable, 1 if actif else 0, site_id))
    conn.commit()
    conn.close()


def comparaison_sites(debut: str, fin: str):
    """Compare l'activité de chaque site sur une période : CA, ventes, véhicules,
    dépenses, bénéfice (CA - dépenses), panier moyen."""
    conn = get_conn()
    resultats = []
    for s in conn.execute("SELECT * FROM sites ORDER BY id").fetchall():
        sid = s["id"]
        ca = conn.execute(
            "SELECT COALESCE(SUM(montant_net),0) FROM ventes "
            "WHERE statut='Payée' AND site_id=? AND date BETWEEN ? AND ?",
            (sid, debut, fin)).fetchone()[0]
        nb_ventes = conn.execute(
            "SELECT COUNT(*) FROM ventes WHERE statut='Payée' AND site_id=? AND date BETWEEN ? AND ?",
            (sid, debut, fin)).fetchone()[0]
        nb_veh = conn.execute(
            "SELECT COUNT(DISTINCT v.id) FROM ventes v JOIN vente_lignes l ON l.vente_id=v.id "
            "WHERE v.statut='Payée' AND v.site_id=? AND v.date BETWEEN ? AND ?",
            (sid, debut, fin)).fetchone()[0]
        depenses = conn.execute(
            "SELECT COALESCE(SUM(montant),0) FROM depenses WHERE site_id=? AND date BETWEEN ? AND ?",
            (sid, debut, fin)).fetchone()[0]
        resultats.append({
            "site_id": sid, "nom": s["nom"], "actif": s["actif"],
            "ca": ca, "nb_ventes": nb_ventes, "nb_vehicules": nb_veh,
            "depenses": depenses, "benefice": ca - depenses,
            "panier_moyen": round(ca / nb_ventes) if nb_ventes else 0,
        })
    conn.close()
    return resultats


# ======================================================================
# MODULE 6 : STOCK
# ======================================================================
def stock_reel(conn=None, site_id=None):
    """Liste des produits avec stock réel calculé.
    site_id fourni → stock de ce site uniquement ; None → tous sites cumulés.
    Le stock est entièrement basé sur les mouvements (par site)."""
    ferme = conn is None
    conn = conn or get_conn()
    fe = " AND m.site_id=?" if site_id else ""
    params = [site_id, site_id, site_id, site_id] if site_id else []
    rows = conn.execute(f"""
        SELECT p.*, f.nom AS fournisseur,
               COALESCE((SELECT SUM(quantite) FROM mouvements_stock m
                         WHERE m.produit_id=p.id AND m.type='ENTREE'{fe}),0)
               - COALESCE((SELECT SUM(quantite) FROM mouvements_stock m
                           WHERE m.produit_id=p.id AND m.type='SORTIE'{fe}),0) AS stock_reel,
               COALESCE((SELECT SUM(quantite) FROM mouvements_stock m
                         WHERE m.produit_id=p.id AND m.type='ENTREE'{fe}),0) AS entrees,
               COALESCE((SELECT SUM(quantite) FROM mouvements_stock m
                         WHERE m.produit_id=p.id AND m.type='SORTIE'{fe}),0) AS sorties
        FROM produits p LEFT JOIN fournisseurs f ON f.id=p.fournisseur_id
        WHERE p.actif=1 ORDER BY p.nom
    """, params).fetchall()
    produits = []
    for r in rows:
        d = dict(r)
        d["valeur_stock"] = round(d["stock_reel"] * d["prix_achat"])
        d["critique"] = d["stock_reel"] <= d["stock_min"]
        produits.append(d)
    if ferme:
        conn.close()
    return produits


def produits_revendables(site_id=None):
    """Produits « revendable » avec leur stock réel (du site donné) et prix de vente."""
    return [p for p in stock_reel(site_id=site_id) if p.get("revendable")]


# ======================================================================
# ABONNEMENTS : fidélisation
# ======================================================================
def lister_formules(actives_seulement=True):
    conn = get_conn()
    q = "SELECT * FROM formules_abonnement"
    if actives_seulement:
        q += " WHERE actif=1"
    q += " ORDER BY prix"
    rows = [dict(r) for r in conn.execute(q).fetchall()]
    conn.close()
    return rows


def souscrire_abonnement(client_id, formule_id, prix_paye=None):
    """Souscrit un client à une formule. Retourne l'abonnement créé."""
    from datetime import timedelta
    conn = get_conn()
    f = conn.execute("SELECT * FROM formules_abonnement WHERE id=?", (formule_id,)).fetchone()
    if not f:
        conn.close()
        raise ValueError("Formule introuvable.")
    debut = date.today()
    fin = debut + timedelta(days=int(f["duree_jours"]))
    prix = int(prix_paye if prix_paye is not None else f["prix"])
    cur = conn.execute(
        "INSERT INTO abonnements (client_id, formule_id, date_debut, date_fin, "
        "lavages_inclus, prix_paye, statut) VALUES (?,?,?,?,?,?, 'Actif')",
        (client_id, formule_id, str(debut), str(fin), int(f["nb_lavages"]), prix),
    )
    abo_id = cur.lastrowid
    conn.commit()
    abo = dict(conn.execute("SELECT * FROM abonnements WHERE id=?", (abo_id,)).fetchone())
    conn.close()
    return abo


def _maj_statuts_expires(conn):
    conn.execute("UPDATE abonnements SET statut='Expiré' "
                 "WHERE statut='Actif' AND date_fin < date('now')")


def abonnement_actif(client_id):
    """
    Retourne l'abonnement actif et valide d'un client (dict enrichi de la formule),
    ou None. Un abonnement à quota épuisé n'est plus considéré comme utilisable.
    """
    if not client_id:
        return None
    conn = get_conn()
    _maj_statuts_expires(conn)
    conn.commit()
    row = conn.execute("""
        SELECT a.*, f.nom AS formule, f.type AS type_formule, f.prioritaire, f.nom AS formule_nom
        FROM abonnements a JOIN formules_abonnement f ON f.id=a.formule_id
        WHERE a.client_id=? AND a.statut='Actif' AND a.date_fin >= date('now')
        ORDER BY a.date_fin DESC LIMIT 1
    """, (client_id,)).fetchone()
    conn.close()
    if not row:
        return None
    a = dict(row)
    a["illimite"] = (a["lavages_inclus"] == 0)
    a["lavages_restants"] = (None if a["illimite"]
                             else max(a["lavages_inclus"] - a["lavages_utilises"], 0))
    a["utilisable"] = a["illimite"] or a["lavages_restants"] > 0
    return a


def consommer_lavage_abonnement(abonnement_id):
    """Incrémente le compteur de lavages utilisés d'un abonnement à quota."""
    conn = get_conn()
    conn.execute("UPDATE abonnements SET lavages_utilises = lavages_utilises + 1 WHERE id=?",
                 (abonnement_id,))
    conn.commit()
    conn.close()


def historique_abonnements(client_id=None):
    conn = get_conn()
    _maj_statuts_expires(conn)
    conn.commit()
    q = """SELECT a.*, c.nom AS client, c.telephone, f.nom AS formule, f.type AS type_formule
           FROM abonnements a JOIN clients c ON c.id=a.client_id
           JOIN formules_abonnement f ON f.id=a.formule_id"""
    p = []
    if client_id:
        q += " WHERE a.client_id=?"
        p.append(client_id)
    q += " ORDER BY a.date_creation DESC"
    rows = [dict(r) for r in conn.execute(q, p).fetchall()]
    conn.close()
    for a in rows:
        a["illimite"] = (a["lavages_inclus"] == 0)
        a["lavages_restants"] = (None if a["illimite"]
                                 else max(a["lavages_inclus"] - a["lavages_utilises"], 0))
    return rows


def mouvement_stock(produit_id, type_mvt, quantite, motif="", reference="", site_id=1):
    conn = get_conn()
    conn.execute(
        "INSERT INTO mouvements_stock (produit_id, type, quantite, motif, reference, site_id) "
        "VALUES (?,?,?,?,?,?)",
        (produit_id, type_mvt, float(quantite), motif, reference, int(site_id or 1)),
    )
    conn.commit()
    conn.close()


# ======================================================================
# MODULE 7 : ACHATS
# ======================================================================
def creer_achat(fournisseur_id, lignes, site_id=1):
    """lignes = [(produit_id, quantite, prix_unitaire), ...] -> crée la commande pour un site."""
    numero = prochain_numero(f"ACH-{date.today():%Y}-", "achats")
    total = sum(int(round(q * pu)) for _, q, pu in lignes)
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO achats (numero, fournisseur_id, total, site_id) VALUES (?,?,?,?)",
        (numero, fournisseur_id, total, int(site_id or 1)),
    )
    achat_id = cur.lastrowid
    for produit_id, q, pu in lignes:
        conn.execute(
            "INSERT INTO achat_lignes (achat_id, produit_id, quantite, prix_unitaire) "
            "VALUES (?,?,?,?)", (achat_id, produit_id, float(q), int(pu)),
        )
    conn.commit()
    conn.close()
    return numero


def receptionner_achat(achat_id):
    """Bon de livraison : passe l'achat en 'Livrée' et crée les entrées de stock sur son site."""
    conn = get_conn()
    achat = conn.execute("SELECT * FROM achats WHERE id=?", (achat_id,)).fetchone()
    if achat and achat["statut"] == "Commande":
        site = achat["site_id"] if "site_id" in achat.keys() else 1
        for l in conn.execute(
            "SELECT * FROM achat_lignes WHERE achat_id=?", (achat_id,)
        ).fetchall():
            conn.execute(
                "INSERT INTO mouvements_stock (produit_id, type, quantite, motif, reference, site_id) "
                "VALUES (?, 'ENTREE', ?, 'Réception achat', ?, ?)",
                (l["produit_id"], l["quantite"], achat["numero"], site),
            )
            conn.execute(  # met à jour le dernier prix d'achat
                "UPDATE produits SET prix_achat=? WHERE id=?",
                (l["prix_unitaire"], l["produit_id"]),
            )
        conn.execute("UPDATE achats SET statut='Livrée' WHERE id=?", (achat_id,))
        conn.commit()
    conn.close()


def payer_fournisseur(achat_id, montant, mode="Espèces"):
    conn = get_conn()
    conn.execute(
        "INSERT INTO paiements_fournisseurs (achat_id, montant, mode) VALUES (?,?,?)",
        (achat_id, int(montant), mode),
    )
    conn.execute(
        "UPDATE achats SET montant_paye = montant_paye + ?, "
        "statut = CASE WHEN montant_paye + ? >= total THEN 'Payée' ELSE statut END "
        "WHERE id=?", (int(montant), int(montant), achat_id),
    )
    conn.commit()
    conn.close()


# ======================================================================
# MODULE 1 + 11 : TABLEAU DE BORD & KPI
# ======================================================================
def _ca_entre(conn, debut, fin, site_id=None):
    fs = " AND site_id=?" if site_id else ""
    ps = [site_id] if site_id else []
    return conn.execute(
        "SELECT COALESCE(SUM(montant_net),0) FROM ventes "
        "WHERE date BETWEEN ? AND ? AND statut='Payée'" + fs, [str(debut), str(fin)] + ps,
    ).fetchone()[0]


def _compte_lavages(conn, debut, fin, champ, valeur, site_id=None):
    fs = " AND v.site_id=?" if site_id else ""
    ps = [site_id] if site_id else []
    return conn.execute(
        f"SELECT COALESCE(SUM(l.quantite),0) FROM vente_lignes l "
        f"JOIN ventes v ON v.id=l.vente_id JOIN prestations p ON p.id=l.prestation_id "
        f"WHERE v.date BETWEEN ? AND ? AND v.statut='Payée' AND p.{champ}=?" + fs,
        [str(debut), str(fin), valeur] + ps,
    ).fetchone()[0]


def cout_consommables(conn, debut, fin, site_id=None):
    """Valorisation des sorties de stock (consommation) au prix d'achat."""
    fs = " AND m.site_id=?" if site_id else ""
    ps = [site_id] if site_id else []
    return conn.execute(
        "SELECT COALESCE(SUM(m.quantite * p.prix_achat),0) FROM mouvements_stock m "
        "JOIN produits p ON p.id=m.produit_id "
        "WHERE m.type='SORTIE' AND m.date BETWEEN ? AND ?" + fs, [str(debut), str(fin)] + ps,
    ).fetchone()[0]


def donnees_tableau_de_bord(site_id=None) -> dict:
    """Toutes les données du MODULE 1. site_id → ce site ; None → tous les sites."""
    auj = date.today()
    lundi = auj - timedelta(days=auj.weekday())
    premier_mois = auj.replace(day=1)
    seuil_fid = int(get_parametre("seuil_fidelite", "5") or 5)
    fsv = " AND v.site_id=?" if site_id else ""
    fs = " AND site_id=?" if site_id else ""
    psv = [site_id] if site_id else []

    conn = get_conn()
    d = {
        "site_id": site_id,
        "ca_jour": _ca_entre(conn, auj, auj, site_id),
        "ca_semaine": _ca_entre(conn, lundi, auj, site_id),
        "ca_mois": _ca_entre(conn, premier_mois, auj, site_id),
        "nb_vehicules": conn.execute(
            "SELECT COUNT(DISTINCT v.id) FROM ventes v "
            "JOIN vente_lignes l ON l.vente_id=v.id "
            "WHERE v.date=? AND v.statut='Payée'" + fsv, [str(auj)] + psv
        ).fetchone()[0],
        "nb_motos": _compte_lavages(conn, auj, auj, "type_vehicule", "moto", site_id),
        "nb_camions": _compte_lavages(conn, auj, auj, "type_vehicule", "camion", site_id),
        "nb_interieurs": _compte_lavages(conn, auj, auj, "type_lavage", "interieur", site_id),
        "nb_complets": _compte_lavages(conn, auj, auj, "type_lavage", "complet", site_id),
        "depenses_jour": conn.execute(
            "SELECT COALESCE(SUM(montant),0) FROM depenses WHERE date=?" + fs, [str(auj)] + psv
        ).fetchone()[0],
        "clients_fideles": conn.execute(
            "SELECT COUNT(*) FROM (SELECT client_id FROM ventes WHERE client_id IS NOT NULL "
            "AND statut='Payée' GROUP BY client_id HAVING COUNT(*) >= ?)", (seuil_fid,)
        ).fetchone()[0],
    }
    d["cout_conso_jour"] = round(cout_consommables(conn, auj, auj, site_id))
    d["benefice_jour"] = d["ca_jour"] - d["depenses_jour"] - d["cout_conso_jour"]

    # Stock critique + alertes péremption (du site concerné)
    produits = stock_reel(conn, site_id=site_id)
    d["stock_critique"] = [p for p in produits if p["critique"]]
    d["alertes"] = [f"Stock critique : {p['nom']} ({p['stock_reel']:g} {p['unite']})"
                    for p in d["stock_critique"]]
    limite = str(auj + timedelta(days=30))
    for p in produits:
        if p["date_peremption"] and p["date_peremption"] <= limite:
            d["alertes"].append(f"Péremption proche : {p['nom']} ({p['date_peremption']})")

    # CA des 7 derniers jours pour le graphique
    d["ca_7_jours"] = []
    jours_fr = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
    for i in range(6, -1, -1):
        j = auj - timedelta(days=i)
        libelle = f"{jours_fr[j.weekday()]} {j.day:02d}"
        d["ca_7_jours"].append((libelle, _ca_entre(conn, j, j, site_id)))

    conn.close()
    return d


def calculer_kpi(debut: str, fin: str) -> dict:
    """MODULE 11 : KPI commercial / exploitation / stock / finance / marketing."""
    conn = get_conn()
    kpi = {}

    # --- Commercial ---
    ca = _ca_entre(conn, debut, fin)
    nb_ventes = conn.execute(
        "SELECT COUNT(*) FROM ventes WHERE date BETWEEN ? AND ? AND statut='Payée'",
        (debut, fin)).fetchone()[0]
    nb_clients = conn.execute(
        "SELECT COUNT(DISTINCT client_id) FROM ventes "
        "WHERE date BETWEEN ? AND ? AND statut='Payée' AND client_id IS NOT NULL",
        (debut, fin)).fetchone()[0]
    nb_prestations = conn.execute(
        "SELECT COALESCE(SUM(l.quantite),0) FROM vente_lignes l JOIN ventes v ON v.id=l.vente_id "
        "WHERE v.date BETWEEN ? AND ? AND v.statut='Payée'", (debut, fin)).fetchone()[0]
    ca_produits = conn.execute(
        "SELECT COALESCE(SUM(vp.prix*vp.quantite),0) FROM vente_produits vp "
        "JOIN ventes v ON v.id=vp.vente_id "
        "WHERE v.date BETWEEN ? AND ? AND v.statut='Payée'", (debut, fin)).fetchone()[0]
    # Marge de revente = prix de vente encaissé - coût d'achat des produits vendus
    marge_produits = conn.execute(
        "SELECT COALESCE(SUM((vp.prix - p.prix_achat) * vp.quantite),0) "
        "FROM vente_produits vp JOIN ventes v ON v.id=vp.vente_id "
        "JOIN produits p ON p.id=vp.produit_id "
        "WHERE v.date BETWEEN ? AND ? AND v.statut='Payée'", (debut, fin)).fetchone()[0]
    kpi["commercial"] = {
        "CA de la période": ca,
        "dont CA revente produits": round(ca_produits),
        "Marge sur revente produits": round(marge_produits),
        "Taux de marge revente (%)": round(100 * marge_produits / ca_produits, 1) if ca_produits else 0,
        "Nombre de ventes": nb_ventes,
        "Nombre de clients": nb_clients,
        "Panier moyen": round(ca / nb_ventes) if nb_ventes else 0,
        "Nombre de prestations": nb_prestations,
    }
    kpi["ca_par_produit"] = [dict(r) for r in conn.execute(
        "SELECT p.nom, SUM(vp.prix*vp.quantite) ca, SUM(vp.quantite) nb, "
        "SUM((vp.prix - p.prix_achat) * vp.quantite) marge "
        "FROM vente_produits vp JOIN ventes v ON v.id=vp.vente_id "
        "JOIN produits p ON p.id=vp.produit_id "
        "WHERE v.date BETWEEN ? AND ? AND v.statut='Payée' "
        "GROUP BY p.id ORDER BY ca DESC", (debut, fin)).fetchall()]
    kpi["ca_par_prestation"] = [dict(r) for r in conn.execute(
        "SELECT p.nom, SUM(l.prix*l.quantite) ca, SUM(l.quantite) nb "
        "FROM vente_lignes l JOIN ventes v ON v.id=l.vente_id "
        "JOIN prestations p ON p.id=l.prestation_id "
        "WHERE v.date BETWEEN ? AND ? AND v.statut='Payée' "
        "GROUP BY p.id ORDER BY ca DESC", (debut, fin)).fetchall()]
    kpi["ca_par_employe"] = [dict(r) for r in conn.execute(
        "SELECT e.nom, SUM(v.montant_net) ca, COUNT(*) nb "
        "FROM vente_employes ve JOIN ventes v ON v.id=ve.vente_id "
        "JOIN employes e ON e.id=ve.employe_id "
        "WHERE v.date BETWEEN ? AND ? AND v.statut='Payée' "
        "GROUP BY e.id ORDER BY ca DESC", (debut, fin)).fetchall()]

    # --- Exploitation ---
    duree = conn.execute(
        "SELECT COALESCE(SUM(p.duree_min*l.quantite),0) FROM vente_lignes l "
        "JOIN ventes v ON v.id=l.vente_id JOIN prestations p ON p.id=l.prestation_id "
        "WHERE v.date BETWEEN ? AND ? AND v.statut='Payée'", (debut, fin)).fetchone()[0]
    nb_jours = max((datetime.fromisoformat(fin) - datetime.fromisoformat(debut)).days + 1, 1)
    heures_ouvre = nb_jours * 12  # 08h-20h
    kpi["exploitation"] = {
        "Véhicules lavés": nb_ventes,
        "Temps moyen de lavage (min)": round(duree / nb_ventes) if nb_ventes else 0,
        "Véhicules par heure": round(nb_ventes / heures_ouvre, 2),
        "Taux d'occupation (%)": round(100 * (duree / 60) / heures_ouvre, 1),
        "CA par heure": round(ca / heures_ouvre) if heures_ouvre else 0,
    }

    # --- Stock ---
    produits = stock_reel(conn)
    valeur = sum(p["valeur_stock"] for p in produits)
    conso = cout_consommables(conn, debut, fin)
    kpi["stock"] = {
        "Valeur du stock": round(valeur),
        "Produits critiques": len([p for p in produits if p["critique"]]),
        "Consommation de la période": round(conso),
        "Consommation journalière moyenne": round(conso / nb_jours),
        "Rotation du stock (%)": round(100 * conso / valeur, 1) if valeur else 0,
        "Ruptures (stock à zéro)": len([p for p in produits if p["stock_reel"] <= 0]),
    }

    # --- Finance ---
    depenses = conn.execute(
        "SELECT COALESCE(SUM(montant),0) FROM depenses WHERE date BETWEEN ? AND ?",
        (debut, fin)).fetchone()[0]
    charges_fixes = conn.execute(
        "SELECT COALESCE(SUM(montant),0) FROM depenses WHERE date BETWEEN ? AND ? "
        "AND categorie IN ('Electricité','Eau','Salaires','Internet','Téléphone')",
        (debut, fin)).fetchone()[0]
    charges_variables = depenses - charges_fixes
    marge_brute = ca - conso
    benefice = ca - conso - depenses
    kpi["finance"] = {
        "Chiffre d'affaires": ca,
        "Coût des consommables": round(conso),
        "Marge brute": round(marge_brute),
        "Charges fixes": charges_fixes,
        "Charges variables": charges_variables,
        "Bénéfice net": round(benefice),
        "Coût moyen par lavage": round((conso + depenses) / nb_ventes) if nb_ventes else 0,
        "Rentabilité (%)": round(100 * benefice / ca, 1) if ca else 0,
        "Seuil de rentabilité": round(charges_fixes / (marge_brute / ca), 0) if ca and marge_brute > 0 else 0,
    }

    # --- Marketing ---
    seuil_fid = int(get_parametre("seuil_fidelite", "5") or 5)
    nouveaux = conn.execute(
        "SELECT COUNT(*) FROM clients WHERE date_creation BETWEEN ? AND ?",
        (debut, fin)).fetchone()[0]
    fideles = conn.execute(
        "SELECT COUNT(*) FROM (SELECT client_id FROM ventes WHERE client_id IS NOT NULL "
        "AND statut='Payée' GROUP BY client_id HAVING COUNT(*) >= ?)", (seuil_fid,)
    ).fetchone()[0]
    retour = conn.execute(
        "SELECT COUNT(*) FROM (SELECT client_id FROM ventes WHERE client_id IS NOT NULL "
        "AND statut='Payée' AND date BETWEEN ? AND ? GROUP BY client_id HAVING COUNT(*) > 1)",
        (debut, fin)).fetchone()[0]
    kpi["marketing"] = {
        "Nouveaux clients": nouveaux,
        "Clients fidèles": fideles,
        "Taux de retour (%)": round(100 * retour / nb_clients, 1) if nb_clients else 0,
        "Fréquence moyenne (visites/client)": round(nb_ventes / nb_clients, 1) if nb_clients else 0,
    }
    kpi["top_clients"] = [dict(r) for r in conn.execute(
        "SELECT c.nom, c.telephone, COUNT(*) visites, SUM(v.montant_net) total "
        "FROM ventes v JOIN clients c ON c.id=v.client_id "
        "WHERE v.statut='Payée' GROUP BY c.id ORDER BY total DESC LIMIT 20").fetchall()]

    conn.close()
    return kpi


# ======================================================================
# MODULE 10 : HISTORIQUE VEHICULES
# ======================================================================
def historique_vehicules():
    conn = get_conn()
    rows = conn.execute("""
        SELECT ve.*, c.nom AS client,
               (SELECT COUNT(*) FROM ventes v WHERE v.vehicule_id=ve.id AND v.statut='Payée') nb_lavages,
               (SELECT COALESCE(SUM(v.montant_net),0) FROM ventes v
                WHERE v.vehicule_id=ve.id AND v.statut='Payée') total,
               (SELECT MAX(v.date) FROM ventes v WHERE v.vehicule_id=ve.id AND v.statut='Payée') dernier
        FROM vehicules ve LEFT JOIN clients c ON c.id=ve.client_id ORDER BY ve.plaque
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def historique_clients():
    conn = get_conn()
    rows = conn.execute("""
        SELECT c.*,
               (SELECT COUNT(*) FROM ventes v WHERE v.client_id=c.id AND v.statut='Payée') visites,
               (SELECT COALESCE(SUM(v.montant_net),0) FROM ventes v
                WHERE v.client_id=c.id AND v.statut='Payée') total,
               (SELECT MAX(v.date) FROM ventes v WHERE v.client_id=c.id AND v.statut='Payée') derniere
        FROM clients c ORDER BY c.nom
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ======================================================================
# MODULE 14 : SAUVEGARDE AUTOMATIQUE
# ======================================================================
def sauvegarde_quotidienne() -> str:
    """Copie la base dans /sauvegardes une fois par jour (appelée au lancement)."""
    dossier = os.path.join(BASE_DIR, "sauvegardes")
    os.makedirs(dossier, exist_ok=True)
    cible = os.path.join(dossier, f"lavage_meckhe_{date.today():%Y-%m-%d}.db")
    if not os.path.exists(cible) and os.path.exists(DB_PATH):
        shutil.copy2(DB_PATH, cible)
    # Conserver les 30 dernières sauvegardes
    fichiers = sorted(f for f in os.listdir(dossier) if f.endswith(".db"))
    for f in fichiers[:-30]:
        os.remove(os.path.join(dossier, f))
    return cible
