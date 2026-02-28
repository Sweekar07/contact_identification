import os
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)


@contextmanager
def get_connection():
    connection = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    try:
        yield connection
    finally:
        connection.close()


async def init_db():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS contacts (
                    id SERIAL PRIMARY KEY,
                    phone_number VARCHAR(20),
                    email VARCHAR(255),
                    linked_id INTEGER,
                    link_precedence VARCHAR(20) NOT NULL DEFAULT 'primary'
                        CHECK (link_precedence IN ('primary', 'secondary')),
                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    deleted_at TIMESTAMPTZ NULL
                );
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_contacts_email ON contacts(email);"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_contacts_phone_number ON contacts(phone_number);"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_contacts_linked_id ON contacts(linked_id);"
            )
        connection.commit()


async def close_db():
    return
