import sys
import os
import traceback

# Ajout du chemin racine pour l'import de src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.infrastructure.database import get_supabase_client


def test_supabase_connection():
    print("\n" + "=" * 50)
    print("🚀 DÉBUT DU DIAGNOSTIC DE CONNEXION")
    print("=" * 50)

    try:
        # Étape 1 : Initialisation
        print("\n1️⃣ Tentative d'initialisation du client...")
        client = get_supabase_client()
        print("✅ Objet client créé avec succès.")

        # Étape 2 : Test de la base de données (Postgrest)
        print("\n2️⃣ Test de lecture sur la table 'utilisateurs'...")
        # .execute() est souvent le moment où l'argument 'proxy' est passé par erreur
        response = client.table("utilisateurs").select("*").limit(1).execute()

        print("✅ CONNEXION RÉUSSIE !")
        print(f"📊 Données trouvées : {len(response.data)} ligne(s).")

    except TypeError as e:
        print("\n❌ ERREUR DE TYPE (Argument inattendu détecté)")
        print(f"Message d'erreur : {e}")
        print("\n--- TRACEBACK DE L'ERREUR ---")
        traceback.print_exc()  # C'est CA dont j'ai besoin
        print("------------------------------")

    except Exception as e:
        print(f"\n❌ AUTRE ERREUR : {e}")
        traceback.print_exc()


if __name__ == "__main__":
    test_supabase_connection()