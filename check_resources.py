import getpass
import pymysql

password = getpass.getpass("Aiven password paste kore Enter chapo: ")

conn = pymysql.connect(
    host="mysql-259b84ee-moumita0484-fba4.f.aivencloud.com",
    port=24843,
    user="avnadmin",
    password=password,
    database="defaultdb",
    ssl={"ca": "ca.pem"},
)

queries = [
    "SELECT * FROM book_resource",
    "SELECT * FROM note_resource",
    "SELECT * FROM question_resource",
]

with conn.cursor() as cur:
    for q in queries:
        print(f"\n--- {q} ---")
        cur.execute(q)
        rows = cur.fetchall()
        if not rows:
            print("(khali - kono row nai)")
        for row in rows:
            print(row)

conn.close()
print("\nDone!")