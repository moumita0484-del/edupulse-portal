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

NEW_COLS = [
    "attendance", "lab_performance", "lab_test1", "lab_test2",
    "quiz", "report", "implementation", "presentation",
]

# (ct1, mid, assignment, final, attendance, lab_performance,
#  lab_test1, lab_test2, quiz, report, implementation, presentation)
THEORY = (10, 20, 10, 50, 10, 0, 0, 0, 0, 0, 0, 0)
LAB    = (0, 0, 0, 0, 10, 10, 10, 20, 20, 10, 10, 10)

theory_ids = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
lab_ids    = [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26]


def add_column(cur, table, ddl):
    try:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")
    except pymysql.err.OperationalError as e:
        if e.args[0] != 1060:      # 1060 = column age thekei ache
            raise


try:
    with conn.cursor() as cur:
        for c in NEW_COLS:
            add_column(cur, "course_marks_distribution",
                       f"{c}_max DECIMAL(5,2) NOT NULL DEFAULT 0")
            add_column(cur, "marks", f"{c}_marks DECIMAL(5,2) NULL")

        cur.execute("DELETE FROM course_marks_distribution")

        sql = (
            "INSERT INTO course_marks_distribution "
            "(course_id, ct_max, mid_max, assignment_max, final_max, "
            "attendance_max, lab_performance_max, lab_test1_max, lab_test2_max, "
            "quiz_max, report_max, implementation_max, presentation_max) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        )
        for cid in theory_ids:
            cur.execute(sql, (cid, *THEORY))
        for cid in lab_ids:
            cur.execute(sql, (cid, *LAB))
        conn.commit()

        cur.execute("""
            SELECT c.course_id, c.course_code,
                   (d.ct_max + d.mid_max + d.assignment_max + d.final_max
                    + d.attendance_max + d.lab_performance_max
                    + d.lab_test1_max + d.lab_test2_max + d.quiz_max
                    + d.report_max + d.implementation_max
                    + d.presentation_max) AS total
            FROM course_marks_distribution d
            JOIN course c ON c.course_id = d.course_id
            ORDER BY c.course_id
        """)
        rows = cur.fetchall()
        print("Mot row:", len(rows))
        for r in rows:
            print(r)
finally:
    conn.close()