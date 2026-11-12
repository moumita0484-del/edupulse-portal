import pymysql
import getpass

# Password input
password = getpass.getpass("Aiven password paste koro: ")

# Database connection
conn = pymysql.connect(
    host="mysql-259b84ee-moumita0484-fba4.f.aivencloud.com",
    port=24843, user="avnadmin", password=password,
    database="defaultdb", ssl={"ca": "ca.pem"},
)

try:
    with conn.cursor() as cur:
        # Query to see all registered users
        cur.execute("SELECT student_roll, email, role FROM student ORDER BY student_roll")
        rows = cur.fetchall()
        
        print("\n--- Registered Users ---")
        print(f"{'Roll':<10} | {'Email':<25} | {'Role'}")
        print("-" * 50)
        for row in rows:
            print(f"{row[0]:<10} | {row[1]:<25} | {row[2]}")
        print(f"\nTotal users: {len(rows)}")
        
finally:
    conn.close()