"""Truncate ALL data in the postcardv2 database.

Empties every table in the public schema (except Prisma's migration-history
table) and resets identity sequences, so migration runs can start from a
clean slate without rebuilding the schema.

Usage:
    python scripts/truncate_all.py          # asks for confirmation
    python scripts/truncate_all.py --yes    # no prompt (for notebooks/CI)
"""

import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

# tables that hold schema/tooling state, never data to migrate
SKIP_TABLES = {"_prisma_migrations"}

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def main() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        sys.exit("DATABASE_URL not set — check the .env file in the project root.")

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT tablename FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY tablename
                """
            )
            tables = [row[0] for row in cur.fetchall() if row[0] not in SKIP_TABLES]

        if not tables:
            print("No tables found — did you run the Prisma migration yet?")
            return

        print(f"Target : {database_url}")
        print(f"Tables : {len(tables)}")
        for t in tables:
            print(f"  - {t}")

        if "--yes" not in sys.argv:
            answer = input("\nTruncate ALL of the above? [y/N] ").strip().lower()
            if answer != "y":
                print("Aborted.")
                return

        qualified = ", ".join(f'"{t}"' for t in tables)
        with conn.cursor() as cur:
            cur.execute(f"TRUNCATE TABLE {qualified} RESTART IDENTITY CASCADE")
        conn.commit()
        print(f"\nDone — truncated {len(tables)} tables (identities reset).")


if __name__ == "__main__":
    main()
