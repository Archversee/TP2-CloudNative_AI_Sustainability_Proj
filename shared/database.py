from shared.config import Config
from supabase import create_client

def get_supabase_client():
    return create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
