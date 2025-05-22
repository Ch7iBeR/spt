import os
from dotenv import load_dotenv

load_dotenv()  # Charge les variables depuis .env

DB_CONFIG = {
    "host": "db.ezkzuetrkofwxkmztpor.supabase.co",
    "port": 5432,
    "user": "postgres",
    "password": "medbough123",
    "dbname": "postgres"
}
SECRET_KEY = os.getenv('SECRET_KEY', 'votre-cle-secrete')