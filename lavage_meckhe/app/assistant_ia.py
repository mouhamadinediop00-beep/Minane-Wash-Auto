# -*- coding: utf-8 -*-
"""
LAVAGE MECKHE - Assistant IA optionnel (Claude via l'API Anthropic).

IMPORTANT — à lire :
  * Cette fonctionnalité est OPTIONNELLE et DÉSACTIVÉE par défaut.
  * Elle nécessite INTERNET et une CLÉ API Anthropic (payante à l'usage).
  * Quand elle est utilisée, un RÉSUMÉ CHIFFRÉ de l'activité (pas les noms des
    clients, pas de données personnelles) est envoyé aux serveurs d'Anthropic
    pour obtenir une réponse en langage naturel.
  * Sans clé API, l'application fonctionne à 100 % en local (onglet
    « Analyse & conseils »), sans rien envoyer sur Internet.

La clé API se règle dans Paramètres (jamais stockée en dur ici).
"""

import json
import urllib.request
import urllib.error

from .database import get_parametre
from . import services, analyse

API_URL = "https://api.anthropic.com/v1/messages"
MODELE = "claude-sonnet-4-20250514"   # modèle par défaut (modifiable en paramètre)


def cle_configuree() -> bool:
    return bool(get_parametre("anthropic_api_key", "").strip())


def _resume_activite(site_id=None) -> str:
    """
    Construit un résumé CHIFFRÉ et ANONYME de l'activité, à envoyer à l'IA
    comme contexte. Aucune donnée nominative (ni client, ni employé) n'est incluse.
    """
    d = services.donnees_tableau_de_bord(site_id=site_id)
    res = analyse.analyser(site_id=site_id)
    lignes = [
        "Résumé chiffré de la station de lavage (montants en FCFA) :",
        f"- CA du jour : {d.get('ca_jour', 0)}",
        f"- CA de la semaine : {d.get('ca_semaine', 0)}",
        f"- CA du mois : {d.get('ca_mois', 0)}",
        f"- Bénéfice estimé du jour : {d.get('benefice_jour', 0)}",
        f"- Véhicules lavés aujourd'hui : {d.get('nb_vehicules', 0)}",
        f"- Dépenses du jour : {d.get('depenses_jour', 0)}",
        f"- Produits en stock critique : {d.get('nb_stock_critique', 0)}",
        "",
        "Observations détectées par l'analyse locale :",
    ]
    for c in res["conseils"]:
        lignes.append(f"- [{c['niveau']}] {c['titre']} — {c['message']}")
    return "\n".join(lignes)


def demander(question: str, site_id=None, historique=None):
    """
    Envoie la question + le résumé d'activité à Claude et renvoie (ok, texte).
    Ne lève jamais d'exception : retourne toujours (bool, message).
    """
    cle = get_parametre("anthropic_api_key", "").strip()
    if not cle:
        return False, ("L'assistant Claude n'est pas activé. Renseignez une clé API "
                       "Anthropic dans Paramètres pour l'utiliser (nécessite Internet).")
    modele = get_parametre("anthropic_modele", "").strip() or MODELE

    systeme = (
        "Tu es l'assistant de gestion d'une station de lavage automobile au Sénégal "
        "(MINAN WASH AUTO). Tu aides le gérant à comprendre ses chiffres et à prendre "
        "de bonnes décisions. Réponds en français, de façon simple, concrète et brève. "
        "Base-toi uniquement sur le résumé chiffré fourni ; si une information manque, "
        "dis-le et propose comment l'obtenir. Donne des conseils pratiques et chiffrés."
    )
    contexte = _resume_activite(site_id=site_id)
    messages = list(historique or [])
    messages.append({"role": "user",
                     "content": f"{contexte}\n\n---\nQuestion du gérant : {question}"})

    corps = json.dumps({
        "model": modele,
        "max_tokens": 700,
        "system": systeme,
        "messages": messages,
    }).encode("utf-8")

    req = urllib.request.Request(API_URL, data=corps, method="POST")
    req.add_header("content-type", "application/json")
    req.add_header("x-api-key", cle)
    req.add_header("anthropic-version", "2023-06-01")

    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            data = json.loads(r.read().decode("utf-8"))
        blocs = data.get("content", [])
        texte = "\n".join(b.get("text", "") for b in blocs if b.get("type") == "text").strip()
        return True, (texte or "Réponse vide reçue de l'assistant.")
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = json.loads(e.read().decode("utf-8")).get("error", {}).get("message", "")
        except Exception:
            pass
        if e.code == 401:
            return False, "Clé API refusée (401). Vérifiez votre clé Anthropic dans Paramètres."
        if e.code == 429:
            return False, "Limite d'utilisation atteinte (429). Réessayez plus tard."
        return False, f"Erreur de l'API ({e.code}). {detail}"
    except urllib.error.URLError:
        return False, ("Impossible de joindre le service. Vérifiez votre connexion Internet "
                       "(l'assistant Claude nécessite Internet).")
    except Exception as ex:
        return False, f"Erreur inattendue : {ex}"
