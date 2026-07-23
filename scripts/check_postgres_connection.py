import os

import psycopg
from dotenv import load_dotenv


load_dotenv()

database_url = os.environ.get("DATABASE_URL")

if not database_url:
    raise SystemExit("DATABASE_URL is not set in .env")


with psycopg.connect(database_url) as connection:
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_database(), current_user")
        database_name, database_user = cursor.fetchone()


print("PostgreSQL connection successful")
print(f"Database: {database_name}")
print(f"User: {database_user}")