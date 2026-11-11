import getpass
import pymysql

password = getpass.getpass("Aiven password paste kore Enter chapo: ")
conn = pymysql.connect(
    host="mysql-259b84ee-moumita0484-fba4.f.aivencloud.com",
    port=24843, user="avnadmin", password=password,
    database="defaultdb", ssl={"ca": "ca.pem"},
)

with conn.cursor() as cur:
    # 1. Check if role column already exists
    cur.execute("""
        SELECT COLUMN_NAME FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'student' AND COLUMN_NAME = 'role'
    """)
    if not cur.fetchone():
        cur.execute("ALTER TABLE student ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'student'")
        print("✅ Added 'role' column to student table")
    else:
        print("ℹ️  'role' column already exists")

    # 2. Make sure all existing students have role='student'
    cur.execute("UPDATE student SET role='student' WHERE role IS NULL OR role=''")
    print(f"✅ Updated {cur.rowcount} existing student(s) to role='student'")

    # 3. Ask which student_roll should be admin
    admin_roll = input("\nWhich student_roll should be ADMIN? (your roll): ").strip()
    if admin_roll:
        cur.execute("UPDATE student SET role='admin' WHERE student_roll = %s", (admin_roll,))
        if cur.rowcount > 0:
            print(f"✅ {admin_roll} is now ADMIN")
        else:
            print(f"⚠️  Roll {admin_roll} not found. Login first with this roll, then re-run.")

conn.commit()

# 4. Verify
with conn.cursor() as cur:
    cur.execute("SELECT student_roll, role FROM student ORDER BY student_roll")
    rows = cur.fetchall()
    print("\n--- Current roles ---")
    for r in rows:
        print(r)

conn.close()
print("\n🎉 Done! Step 1 complete.")