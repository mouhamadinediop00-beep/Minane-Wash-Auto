# -*- coding: utf-8 -*-
"""
LAVAGE MECKHE - Mode réseau (accès à distance)
------------------------------------------------
Lance l'application comme un serveur web accessible depuis un autre appareil
(téléphone, tablette, ordinateur) connecté au MÊME réseau Wi-Fi que ce PC.

Le PC de la station reste la « centrale » : c'est lui qui détient la base de
données. Les autres appareils s'y connectent via un navigateur. Le suivi de la
caisse est donc en temps réel (même base partagée).

Utilisation :
    python serveur_reseau.py
puis, sur le téléphone, ouvrir dans le navigateur :  http://ADRESSE_IP_DU_PC:8550
L'adresse IP est affichée au démarrage.
"""

import socket
import flet as ft
from main import main

PORT = 8550


def adresse_ip_locale() -> str:
    """Trouve l'adresse IP de ce PC sur le réseau local."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


if __name__ == "__main__":
    ip = adresse_ip_locale()
    print("=" * 60)
    print("  LAVAGE MECKHE - Mode reseau (acces a distance)")
    print("=" * 60)
    print()
    print("  Sur ce PC (la station), l'application est accessible ici :")
    print(f"      http://localhost:{PORT}")
    print()
    print("  Depuis un telephone/tablette sur le MEME Wi-Fi, ouvrez :")
    print(f"      http://{ip}:{PORT}")
    print()
    print("  Laissez cette fenetre ouverte tant que vous utilisez l'appli.")
    print("  Fermez-la pour arreter le serveur.")
    print("=" * 60)
    ft.run(main, view=ft.AppView.WEB_BROWSER, host="0.0.0.0", port=PORT)
