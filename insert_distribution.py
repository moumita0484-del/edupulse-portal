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
        data = [
            (11, 20, 30, 10, 40),
            (12, 20, 30, 10, 40),
            (13, 20, 30, 10, 40),
            (14, 20, 30, 10, 40),
            (15, 20, 30, 10, 40),
        ]
        for row in data:
            cur.execute(
                "INSERT INTO course_marks_distribution "
                "(course_id, ct_max, mid_max, assignment_max, final_max) "
                "VALUES (%s, %s, %s, %s, %s)",
                row,
            )
        conn.commit()
        print(len(data), "ta row dhukeche")

        cur.execute("""
            SELECT c.course_code, c.course_name,
                   d.ct_max, d.mid_max, d.assignment_max, d.final_max
            FROM course_marks_distribution d
            JOIN course c ON c.course_id = d.course_id
            ORDER BY c.course_id
        """)
        for r in cur.fetchall():
            print(r)
finally:
    conn.close()