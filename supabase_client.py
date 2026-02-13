from supabase import create_client
import os
from dotenv import load_dotenv

# FORCE load .env from project root
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise Exception("Supabase environment variables not loaded")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
