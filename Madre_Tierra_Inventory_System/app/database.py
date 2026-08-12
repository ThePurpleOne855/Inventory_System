from sqlmodel import create_engine, SQLModel
import os
from dotenv import load_dotenv

load_dotenv()
password = os.environ.get("DB_PASSWORD")

DATABASE_URL = f"postgresql+psycopg2://<root>:{password}@localhost:5432/postgres"

engine = create_engine(DATABASE_URL, echo=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)