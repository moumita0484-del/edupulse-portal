import getpass
import pymysql

HOST = "mysql-259b84ee-moumita0484-fba4.f.aivencloud.com"
PORT = 24843
USER = "avnadmin"
DATABASE = "defaultdb"

password = getpass.getpass("Aiven password paste kore Enter chapo: ")

with open("new_tables.sql", encoding="utf-8") as f:
    sql = f.read()

statements = [s.strip() for s in sql.split(";") if s.strip()]

conn = pymysql.connect(
    host=HOST,
    port=PORT,
    user=USER,
    password=password,
    database=DATABASE,
    ssl={"ca": "ca.pem"},
)

try:
    with conn.cursor() as cur:
        for i, stmt in enumerate(statements, start=1):
            cur.execute(stmt)
            print(f"{i} no. command choleche")
        conn.commit()

        cur.execute("SHOW TABLES")
        tables = [row[0] for row in cur.fetchall()]
        print("Table sonkha:", len(tables))
        for t in tables:
            print("-", t)
finally:
    conn.close()