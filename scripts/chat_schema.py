import psycopg

conn = psycopg.connect("host=postgres port=5432 dbname=digipin user=digipin_user password=digipin_pass")

with conn.cursor() as cur:
    cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'chat_message_history'")
    for row in cur.fetchall():
        print(row)
