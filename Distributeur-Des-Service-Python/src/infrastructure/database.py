import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv(override=True)

def get_supabase_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    return create_client(url, key)