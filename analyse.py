# -*- coding: utf-8 -*-
"""
LAVAGE MECKHE - Analyse & conseils (moteur local, sans Internet)
Examine les données réelles (ventes, stock, clients, sites, finances) et
produit des observations classées par priorité :
  - "alerte"  : problème à traiter rapidement (rouge)
  - "atten"   : point de vigilance (orange)
  - "info"    : information / opportunité (bleu)
  - "ok"      : tout va bien (vert)
Chaque conseil : {niveau, titre, message, action}
"""

from datetime import date, timedelta

from .database import get_conn, get_parametre
from . import services


def _jours_stock_restants(conn, produit_id, site_id, stock_actuel, depuis_jours=30):
    """Estime en combien de jours le stock sera épuisé, au rythme de conso récent."""
    debut = (date.today() - timedelta(days=depuis_jours)).isoformat()
    fs = " AND site_id=?" if site_id else ""
    p = [produit_id, debut] + ([site_id] if site_id else [])
    sortie = conn.execute(
        "SELECT COALESCE(SUM(quantite),0) FROM mouvements_stock "
        "WHERE produit_id=? AND type='SORTIE' AND date>=?" + fs, p).fetchone()[0]
    conso_jour = sortie / depuis_jours if sortie else 0
    if conso_jour <= 0:
        return None  # pas de consommation → pas d'estimation
    return stock_actuel / conso_jour


def analyser(site_id=None, periode_jours=30):
    """Retourne la liste des conseils, plus des compteurs par niveau."""
    conseils = []
    conn = get_conn()
    auj = date.today()
    debut = (auj - timedelta(days=periode_jours)).isoformat()
    fin = auj.isoformat()
    seuil_fid = int(get_parametre("seuil_fidelite", "5") or 5)

    def ajout(niveau, titre, message, action=""):
        conseils.append({"niveau": niveau, "titre": titre, "message": message, "action": action})

    # ---------------------------------------------------------------
    # 1. STOCK : ruptures, seuils, prévisions d'épuisement
    # ---------------------------------------------------------------
    produits = services.stock_reel(conn=conn, site_id=site_id)
    ruptures = [p for p in produits if p["stock_reel"] <= 0]
    critiques = [p for p in produits if 0 < p["stock_reel"] <= p["stock_min"]]
    if ruptures:
        noms = ", ".join(p["nom"] for p in ruptures[:5])
        ajout("alerte", f"{len(ruptures)} produit(s) en rupture de stock",
              f"En rupture : {noms}." + (" …" if len(ruptures) > 5 else ""),
              "Passez commande à un fournisseur dès que possible (module Achats).")
    if critiques:
        noms = ", ".join(f"{p['nom']} ({p['stock_reel']:g})" for p in critiques[:5])
        ajout("atten", f"{len(critiques)} produit(s) sous le seuil minimum",
              f"Stock bas : {noms}." + (" …" if len(critiques) > 5 else ""),
              "Prévoyez un réapprovisionnement pour éviter la rupture.")
    # Prévision d'épuisement sur les produits sains
    bientot = []
    for p in produits:
        if p["stock_reel"] > p["stock_min"]:
            j = _jours_stock_restants(conn, p["id"], site_id, p["stock_reel"])
            if j is not None and j <= 10:
                bientot.append((p["nom"], j))
    if bientot:
        bientot.sort(key=lambda x: x[1])
        txt = ", ".join(f"{n} (~{int(j)} j)" for n, j in bientot[:4])
        ajout("atten", "Produits bientôt épuisés (au rythme actuel)",
              f"À ce rythme de consommation : {txt}.",
              "Anticipez la commande avant la rupture.")

    # ---------------------------------------------------------------
    # 2. VENTES : activité récente, tendance, jour le plus fort
    # ---------------------------------------------------------------
    fs = " AND site_id=?" if site_id else ""
    ps = [site_id] if site_id else []

    ca_semaine = conn.execute(
        "SELECT COALESCE(SUM(montant_net),0) FROM ventes WHERE statut='Payée' AND date>=?" + fs,
        [(auj - timedelta(days=7)).isoformat()] + ps).fetchone()[0]
    ca_semaine_prec = conn.execute(
        "SELECT COALESCE(SUM(montant_net),0) FROM ventes WHERE statut='Payée' "
        "AND date>=? AND date<?" + fs,
        [(auj - timedelta(days=14)).isoformat(), (auj - timedelta(days=7)).isoformat()] + ps
    ).fetchone()[0]
    if ca_semaine_prec > 0:
        var = round(100 * (ca_semaine - ca_semaine_prec) / ca_semaine_prec)
        if var <= -20:
            ajout("alerte", f"Chiffre d'affaires en baisse ({var} % sur 7 jours)",
                  f"Cette semaine : {services.FCFA(ca_semaine)} contre "
                  f"{services.FCFA(ca_semaine_prec)} la semaine précédente.",
                  "Vérifiez la fréquentation, lancez une promotion ou relancez vos clients.")
        elif var >= 20:
            ajout("info", f"Chiffre d'affaires en hausse (+{var} % sur 7 jours)",
                  f"Belle progression : {services.FCFA(ca_semaine)} cette semaine.",
                  "Assurez-vous d'avoir assez de stock et de personnel pour suivre.")

    # Jour de la semaine le plus fort (30 derniers jours)
    jours_fr = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    par_jour = {i: 0 for i in range(7)}
    for r in conn.execute(
        "SELECT date, SUM(montant_net) t FROM ventes WHERE statut='Payée' AND date>=?" + fs +
        " GROUP BY date", [debut] + ps).fetchall():
        try:
            jj = date.fromisoformat(r["date"]).weekday()
            par_jour[jj] += r["t"] or 0
        except Exception:
            pass
    if sum(par_jour.values()) > 0:
        meilleur = max(par_jour, key=par_jour.get)
        pire = min(par_jour, key=par_jour.get)
        if par_jour[meilleur] > 0 and par_jour[meilleur] >= 1.5 * (par_jour[pire] or 1):
            ajout("info", f"Journée la plus rentable : {jours_fr[meilleur]}",
                  f"Sur 30 jours, le {jours_fr[meilleur].lower()} rapporte le plus, "
                  f"le {jours_fr[pire].lower()} le moins.",
                  f"Renforcez le personnel le {jours_fr[meilleur].lower()}, "
                  "et proposez une offre les jours creux.")

    # ---------------------------------------------------------------
    # 3. CLIENTS : relances, fidélité
    # ---------------------------------------------------------------
    try:
        from . import crm
        a_relancer = crm.clients_a_relancer(30)
        if a_relancer:
            ajout("atten", f"{len(a_relancer)} client(s) à relancer",
                  "Ces clients ne sont pas revenus depuis plus de 30 jours.",
                  "Onglet CRM WhatsApp → Relances : envoyez-leur un message.")
        proches = crm.clients_proches_fidelite() if hasattr(crm, "clients_proches_fidelite") else []
        if proches:
            ajout("info", f"{len(proches)} client(s) proche(s) d'un lavage offert",
                  "Ils approchent du seuil de fidélité.",
                  "Notifiez-les (CRM → Fidélité) pour les faire revenir.")
    except Exception:
        pass

    # ---------------------------------------------------------------
    # 4. RENTABILITÉ PRODUITS : prix de vente sous le coût d'achat
    # ---------------------------------------------------------------
    perte = [p for p in produits
             if p.get("revendable") and p.get("prix_vente") and p["prix_vente"] < p["prix_achat"]]
    if perte:
        noms = ", ".join(f"{p['nom']}" for p in perte[:4])
        ajout("alerte", "Produit(s) vendu(s) à perte",
              f"Le prix de vente est inférieur au prix d'achat pour : {noms}.",
              "Corrigez le prix de vente dans le module Stock.")

    # ---------------------------------------------------------------
    # 5. FINANCES : bénéfice, part des dépenses
    # ---------------------------------------------------------------
    ca = conn.execute(
        "SELECT COALESCE(SUM(montant_net),0) FROM ventes WHERE statut='Payée' AND date>=?" + fs,
        [debut] + ps).fetchone()[0]
    depenses = conn.execute(
        "SELECT COALESCE(SUM(montant),0) FROM depenses WHERE date>=?" + fs,
        [debut] + ps).fetchone()[0]
    if ca > 0:
        ratio = round(100 * depenses / ca)
        if depenses > ca:
            ajout("alerte", "Dépenses supérieures au chiffre d'affaires",
                  f"Sur 30 jours : {services.FCFA(depenses)} de dépenses pour "
                  f"{services.FCFA(ca)} de CA.",
                  "Analysez vos charges (module Dépenses) : certaines sont-elles évitables ?")
        elif ratio >= 70:
            ajout("atten", f"Les dépenses pèsent lourd ({ratio} % du CA)",
                  f"{services.FCFA(depenses)} de dépenses pour {services.FCFA(ca)} de CA.",
                  "Cherchez à réduire les charges ou à augmenter le volume de ventes.")

    # Ventes annulées (possible source de fraude ou d'erreurs)
    nb_annul = conn.execute(
        "SELECT COUNT(*) FROM ventes WHERE statut='Annulée' AND date>=?" + fs,
        [debut] + ps).fetchone()[0]
    nb_total = conn.execute(
        "SELECT COUNT(*) FROM ventes WHERE date>=?" + fs, [debut] + ps).fetchone()[0]
    if nb_total > 0 and nb_annul >= 3 and nb_annul >= 0.1 * nb_total:
        ajout("atten", f"{nb_annul} vente(s) annulée(s) sur 30 jours",
              f"Cela représente {round(100*nb_annul/nb_total)} % des ventes.",
              "Vérifiez le journal d'audit : erreurs de caisse ou annulations à surveiller ?")

    # ---------------------------------------------------------------
    # 6. PERSONNEL : laveur le plus / le moins productif
    # ---------------------------------------------------------------
    laveurs = conn.execute(
        "SELECT e.nom, COUNT(DISTINCT ve.vente_id) nb, COALESCE(SUM(v.montant_net),0) ca "
        "FROM vente_employes ve "
        "JOIN ventes v ON v.id=ve.vente_id "
        "JOIN employes e ON e.id=ve.employe_id "
        "WHERE v.statut='Payée' AND v.date>=?" + (" AND v.site_id=?" if site_id else "") +
        " GROUP BY e.id ORDER BY nb DESC", [debut] + ps).fetchall()
    laveurs = [dict(r) for r in laveurs]
    if len(laveurs) >= 2:
        top = laveurs[0]
        bas = laveurs[-1]
        ajout("info", f"Laveur le plus actif : {top['nom']}",
              f"Sur 30 jours, {top['nom']} a traité {top['nb']} lavages "
              f"({services.FCFA(top['ca'])}), contre {bas['nb']} pour {bas['nom']}.",
              "Valorisez les plus performants (prime) et accompagnez ceux qui décrochent.")
    elif len(laveurs) == 1 and laveurs[0]["nb"] > 0:
        ajout("info", f"Activité de {laveurs[0]['nom']}",
              f"{laveurs[0]['nom']} a traité {laveurs[0]['nb']} lavages sur 30 jours "
              f"({services.FCFA(laveurs[0]['ca'])}).",
              "Affectez les lavages aux employés pour suivre la productivité de chacun.")

    # ---------------------------------------------------------------
    # 7. PRESTATIONS les plus demandées
    # ---------------------------------------------------------------
    top_prest = conn.execute(
        "SELECT p.nom, SUM(l.quantite) q, SUM(l.prix*l.quantite) ca "
        "FROM vente_lignes l JOIN ventes v ON v.id=l.vente_id "
        "JOIN prestations p ON p.id=l.prestation_id "
        "WHERE v.statut='Payée' AND v.date>=?" + (" AND v.site_id=?" if site_id else "") +
        " GROUP BY p.id ORDER BY q DESC LIMIT 3", [debut] + ps).fetchall()
    top_prest = [dict(r) for r in top_prest]
    if top_prest and top_prest[0]["q"]:
        liste = ", ".join(f"{r['nom']} ({int(r['q'])}×)" for r in top_prest)
        ajout("info", "Prestations les plus demandées",
              f"Top sur 30 jours : {liste}.",
              "Mettez en avant ces prestations et assurez-vous d'avoir le stock consommé.")

    # ---------------------------------------------------------------
    # 8. PRODUITS DE REVENTE les plus vendus
    # ---------------------------------------------------------------
    top_prod = conn.execute(
        "SELECT p.nom, SUM(vp.quantite) q, SUM(vp.prix*vp.quantite) ca "
        "FROM vente_produits vp JOIN ventes v ON v.id=vp.vente_id "
        "JOIN produits p ON p.id=vp.produit_id "
        "WHERE v.statut='Payée' AND v.date>=?" + (" AND v.site_id=?" if site_id else "") +
        " GROUP BY p.id ORDER BY q DESC LIMIT 3", [debut] + ps).fetchall()
    top_prod = [dict(r) for r in top_prod]
    if top_prod and top_prod[0]["q"]:
        liste = ", ".join(f"{r['nom']} ({r['q']:g})" for r in top_prod)
        ajout("info", "Produits les plus vendus au client",
              f"Meilleures ventes sur 30 jours : {liste}.",
              "Gardez ces produits toujours en stock et mettez-les en avant à la caisse.")

    # ---------------------------------------------------------------
    # 9. CONSOMMABLE le plus utilisé (sorties de stock par prestation)
    # ---------------------------------------------------------------
    top_conso = conn.execute(
        "SELECT p.nom, SUM(m.quantite) q FROM mouvements_stock m "
        "JOIN produits p ON p.id=m.produit_id "
        "WHERE m.type='SORTIE' AND m.motif='Consommation prestation' AND m.date>=?" +
        (" AND m.site_id=?" if site_id else "") +
        " GROUP BY p.id ORDER BY q DESC LIMIT 1", [debut] + ps).fetchone()
    if top_conso and top_conso["q"]:
        ajout("info", f"Consommable le plus utilisé : {top_conso['nom']}",
              f"{top_conso['nom']} est le produit le plus consommé par les lavages "
              f"({top_conso['q']:g} sur 30 jours).",
              "Surveillez son stock de près et négociez son prix d'achat (gros volume).")

    # ---------------------------------------------------------------
    # 10. MULTI-SITE : comparaison de performance
    # ---------------------------------------------------------------
    sites = services.lister_sites(actifs_seulement=True)
    if len(sites) > 1:
        comp = services.comparaison_sites(debut, fin)
        actifs = [c for c in comp if c["ca"] > 0]
        if len(actifs) > 1:
            meilleur = max(actifs, key=lambda c: c["ca"])
            faible = min(actifs, key=lambda c: c["ca"])
            if faible["ca"] > 0 and meilleur["ca"] >= 1.4 * faible["ca"]:
                ajout("info", "Écart de performance entre les sites",
                      f"« {meilleur['nom']} » réalise {services.FCFA(meilleur['ca'])} contre "
                      f"{services.FCFA(faible['ca'])} pour « {faible['nom']} » sur 30 jours.",
                      "Analysez ce qui marche sur le meilleur site pour le reproduire ailleurs.")

    conn.close()

    # ---------------------------------------------------------------
    # Rien à signaler ?
    # ---------------------------------------------------------------
    if not conseils:
        ajout("ok", "Tout est en ordre",
              "Aucun problème détecté sur les 30 derniers jours : stock sain, "
              "ventes stables, finances équilibrées.",
              "Continuez ainsi ! Revenez consulter cet écran régulièrement.")

    ordre = {"alerte": 0, "atten": 1, "info": 2, "ok": 3}
    conseils.sort(key=lambda c: ordre.get(c["niveau"], 9))
    compteurs = {n: sum(1 for c in conseils if c["niveau"] == n)
                 for n in ("alerte", "atten", "info", "ok")}
    return {"conseils": conseils, "compteurs": compteurs}
