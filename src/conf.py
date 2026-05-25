import os
import pathlib

from dotenv import load_dotenv

load_dotenv()

TEMP_DIR = pathlib.Path(__file__).parent / "temp"
TEMP_DIR.mkdir(exist_ok=True)  # Make sure we have the dir

POSTGRES_IMAGE = "postgres:18.3"
POSTGRES_DB = "mlofoam"
POSTGRES_USER = "mlofoam"
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASS")
POSTGRES_URL = os.getenv("POSTGRES_URL")

POSTGRES_JDBC_URL = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_URL}/{POSTGRES_DB}"
)
