import getpass
import pymysql

HOST = "mysql-259b84ee-moumita0484-fba4.f.aivencloud.com"
PORT = 24843
USER = "avnadmin"
DATABASE = "defaultdb"

password = getpass.getpass("Aiven password paste kore Enter chapo: ")

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
        cur.execute("""
            CREATE TABLE login_token (
                token      VARCHAR(64) PRIMARY KEY,
                student_id INT NOT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES student(student_id) ON DELETE CASCADE
            )
        """)
        conn.commit()
        print("login_token table toiri hoyeche")

        cur.execute("SHOW TABLES")
        tables = [row[0] for row in cur.fetchall()]
        print("Table sonkha:", len(tables))
        for t in tables:
            print("-", t)
finally:
    conn.close()