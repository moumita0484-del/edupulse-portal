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

# course_id: credit
CREDITS = {
    1: 3.0,   2: 3.0,   3: 3.0,   4: 3.0,   5: 3.0,
    16: 1.5,  17: 1.0,  18: 1.0,
    6: 3.0,   7: 3.0,   8: 3.0,   9: 3.0,   10: 2.0,
    19: 1.5,  20: 1.0,  21: 1.5,  22: 1.0,
    11: 3.0,  12: 3.0,  13: 3.0,  14: 3.0,  15: 3.0,
    23: 1.5,  24: 1.0,  25: 1.5,  26: 1.0,
}

try:
    with conn.cursor() as cur:
        try:
            cur.execute("ALTER TABLE course ADD COLUMN credit DECIMAL(3,1) NOT NULL DEFAULT 0")
        except pymysql.err.OperationalError as e:
            if e.args[0] != 1060:      # 1060 = column age thekei ache
                raise

        for cid, cr in CREDITS.items():
            cur.execute("UPDATE course SET credit = %s WHERE course_id = %s", (cr, cid))
        conn.commit()

        cur.execute("SELECT course_id, course_code, course_name, credit FROM course ORDER BY course_id")
        rows = cur.fetchall()
        print("Mot course:", len(rows))
        for r in rows:
            print(r)

        cur.execute("""
            SELECT semester, COUNT(*) AS course_sonkha, SUM(credit) AS mot_credit
            FROM course
            GROUP BY semester
            ORDER BY semester
        """)
        print("--- Semester wise ---")
        for r in cur.fetchall():
            print(r)
finally:
    conn.close()