import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

print(f"Tentative avec URL: {url}")

try:
    # Test sans aucune config compliquée
    client = create_client(url, key)
    res = client.table("utilisateurs").select("*").limit(1).execute()
    print("✅ ENFIN ! La connexion fonctionne en direct.")
    print(f"Données : {res.data}")
except Exception as e:
    print(f"❌ Erreur persistante : {e}")