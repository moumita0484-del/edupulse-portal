import getpass
import pymysql

password = getpass.getpass("Aiven password: ")
conn = pymysql.connect(
    host="mysql-259b84ee-moumita0484-fba4.f.aivencloud.com",
    port=24843, user="avnadmin", password=password,
    database="defaultdb", ssl={"ca": "ca.pem"},
)
cols = {
    "file_name": "VARCHAR(255) NULL",
    "file_mime": "VARCHAR(100) NULL",
    "file_data": "LONGBLOB NULL",
}
with conn.cursor() as cur:
    cur.execute("""
        SELECT COLUMN_NAME FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'resource'
    """)
    existing = {r[0] for r in cur.fetchall()}
    for name, ddl in cols.items():
        if name not in existing:
            cur.execute(f"ALTER TABLE resource ADD COLUMN {name} {ddl}")
            print("Added:", name)
        else:
            print("Already exists:", name)
conn.commit()
conn.close()
print("Done! Resource table ready for file upload.")