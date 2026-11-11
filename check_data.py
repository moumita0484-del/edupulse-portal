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
        cur.execute("SELECT student_id, student_roll, semester FROM student")
        print("--- STUDENT ---")
        for row in cur.fetchall():
            print(row)

        cur.execute("SELECT course_id, course_code, course_name, semester FROM course ORDER BY course_id")
        print("--- COURSE ---")
        for row in cur.fetchall():
            print(row)
finally:
    conn.close()