import getpass
import pymysql

HOST = "mysql-259b84ee-moumita0484-fba4.f.aivencloud.com"
PORT = 24843
USER = "avnadmin"
DATABASE = "defaultdb"

password = input("Aiven password পেস্ট করে Enter চাপো: ")

with open("setup_cloud.sql", encoding="utf-8") as f:
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
        conn.commit()

        print(f"{len(statements)}টি কমান্ড সফলভাবে চলেছে।")

        cur.execute("SELECT semester, COUNT(*) FROM course GROUP BY semester ORDER BY semester")
        print("কোর্সের সংখ্যা:")
        for semester, count in cur.fetchall():
            print(f"  {semester}: {count}")

        cur.execute("SHOW TABLES")
        print("টেবিল:", ", ".join(row[0] for row in cur.fetchall()))
finally:
    conn.close()