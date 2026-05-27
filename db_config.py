import os


def get_db_config():
    password = os.environ.get("INTEREST_DB_PASSWORD")
    if not password:
        raise RuntimeError("INTEREST_DB_PASSWORD environment variable is required")

    return {
        "host": os.environ.get("INTEREST_DB_HOST") or "localhost",
        "port": int(os.environ.get("INTEREST_DB_PORT") or "5433"),
        "dbname": os.environ.get("INTEREST_DB_NAME") or "interest_crawler",
        "user": os.environ.get("INTEREST_DB_USER") or "postgres",
        "password": password,
    }
