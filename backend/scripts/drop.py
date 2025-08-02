import psycopg

# Connect to PostgreSQL
conn = psycopg.connect("host=postgres port=5432 dbname=digipin user=digipin_user password=digipin_pass")

with conn.cursor() as cur:
    # Disable foreign key checks
    cur.execute("SET session_replication_role = replica;")

    # Fetch all table names in the public schema
    cur.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
    """)
    tables = cur.fetchall()

    # Drop each table
    for (table,) in tables:
        print(f"Dropping table: {table}")
        cur.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE;')

    # Re-enable foreign key checks
    cur.execute("SET session_replication_role = DEFAULT;")

# Commit and close connection
conn.commit()
conn.close()
