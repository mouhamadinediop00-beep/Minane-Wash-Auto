# -*- coding: utf-8 -*-
import time
import ssl
import pg8000
from app.database import get_conn

# =====================================================================
# CONFIGURATION SUPABASE
# =====================================================================
SUPABASE_HOST = "aws-0-eu-west-1.pooler.supabase.com"
SUPABASE_PORT = 6543                                    
SUPABASE_DB   = "postgres"
SUPABASE_USER = "postgres.dzljopqaowewmyxtzfnl"  
SUPABASE_PASSWORD = "Mdiop74KfVphprootpostgresql"

def initialiser_base_locale():
    """Crée la table sync_queue en local si elle n'existe pas encore."""
    try:
        db_local = get_conn()
        db_local.execute("""
            CREATE TABLE IF NOT EXISTS sync_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom_table TEXT NOT NULL,
                enregistrement_id TEXT NOT NULL,
                action TEXT NOT NULL,
                statut TEXT DEFAULT 'en_attente',
                tentatives INTEGER DEFAULT 0,
                dernier_erreur TEXT,
                cree_le TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        db_local.commit()
        db_local.close()
        print("[SYNC] Table locale 'sync_queue' vérifiée et prête.")
    except Exception as e:
        print(f"[SYNC] Erreur lors de l'initialisation de la table locale : {e}")

def connecter_serveur_supabase():
    """Tente de se connecter à Supabase via pg8000 en désactivant la stricte vérification SSL."""
    try:
        contexte_ssl = ssl.create_default_context()
        contexte_ssl.check_hostname = False
        contexte_ssl.verify_mode = ssl.CERT_NONE

        conn = pg8000.connect(
            host=SUPABASE_HOST,
            port=SUPABASE_PORT,
            database=SUPABASE_DB,
            user=SUPABASE_USER,
            password=SUPABASE_PASSWORD,
            ssl_context=contexte_ssl
        )
        return conn
    except Exception as e:
        print(f"[SYNC] ❌ Impossible de joindre Supabase : {e}")
        return None

def démarrer_synchronisation_background():
    """Boucle de fond qui vide la file SQLite locale vers Supabase."""
    print("[SYNC] Worker de synchronisation Local-First (via PG8000) démarré.")
    
    initialiser_base_locale()
    
    while True:
        try:
            db_local = get_conn()
            tickets = db_local.execute(
                "SELECT id, nom_table, enregistrement_id, action FROM sync_queue WHERE statut='en_attente' ORDER BY id ASC LIMIT 20"
            ).fetchall()
            
            if not tickets:
                db_local.close()
                time.sleep(5)  
                continue
                
            # --- MODIFICATION ICI : On signale qu'on a trouvé du travail ! ---
            print(f"[SYNC] 📦 {len(tickets)} opération(s) détectée(s) dans la file locale. Connexion à Supabase...")
            
            db_supabase = connecter_serveur_supabase()
            
            if db_supabase is None:
                db_local.close()
                time.sleep(10)
                continue
                
            cursor_supabase = db_supabase.cursor()
            
            for t in tickets:
                id_ticket = t["id"]
                table = t["nom_table"]
                id_rec = t["enregistrement_id"]
                action = t["action"]
                
                try:
                    ligne = db_local.execute(f"SELECT * FROM {table} WHERE id=?", (id_rec,)).fetchone()
                    
                    if ligne is None and action != 'DELETE':
                        db_local.execute("UPDATE sync_queue SET statut='succes' WHERE id=?", (id_ticket,))
                        db_local.commit()
                        print(f"[SYNC] ⚠️ Enregistrement {id_rec} introuvable dans {table} (déjà supprimé localement). Passé au statut 'succes'.")
                        continue
                    
                    donnees_dict = dict(ligne) if ligne else {}
                    
                    if action == 'INSERT' or action == 'UPDATE':
                        colonnes = list(donnees_dict.keys())
                        placeholders = ", ".join(["%s"] * len(colonnes))
                        updates = ", ".join([f"{col}=EXCLUDED.{col}" for col in colonnes if col != 'id'])
                        
                        if updates:
                            sql = f"""
                                INSERT INTO {table} ({', '.join(colonnes)}) 
                                VALUES ({placeholders}) 
                                ON CONFLICT (id) 
                                DO UPDATE SET {updates}
                            """
                        else:
                            sql = f"INSERT INTO {table} ({', '.join(colonnes)}) VALUES ({placeholders}) ON CONFLICT (id) DO NOTHING"
                        
                        cursor_supabase.execute(sql, list(donnees_dict.values()))
                        
                    elif action == 'DELETE':
                        sql = f"DELETE FROM {table} WHERE id = %s"
                        cursor_supabase.execute(sql, (id_rec,))
                        
                    db_supabase.commit()
                    db_local.execute("UPDATE sync_queue SET statut='succes' WHERE id=?", (id_ticket,))
                    db_local.commit()
                    
                    # --- MODIFICATION ICI : Log de succès clair et net ! ---
                    print(f"[SYNC] ✅ Synchro réussie : [{action}] sur la table '{table}' (ID Local: {id_rec})")
                    
                except Exception as err:
                    db_supabase.rollback()
                    db_local.execute(
                        "UPDATE sync_queue SET tentatives=tentatives+1, dernier_erreur=? WHERE id=?",
                        (str(err), id_ticket)
                    )
                    db_local.commit()
                    print(f"[SYNC] ❌ Erreur sur le ticket {id_ticket} (Table {table}) : {err}")
                    
            cursor_supabase.close()
            db_supabase.close()
            db_local.close()
            print("[SYNC] 😴 File d'attente traitée. Retour en veille.")
            
        except Exception as e:
            print(f"[SYNC] Erreur générale dans le Worker : {e}")
            
        time.sleep(5)

if __name__ == "__main__":
    démarrer_synchronisation_background()