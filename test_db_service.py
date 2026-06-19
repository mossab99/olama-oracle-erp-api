import oracledb

oracledb.init_oracle_client(lib_dir=r"C:\oracle\instantclient_19")

dsn = oracledb.makedsn(
    "192.168.0.118",
    1521,
    service_name="orcl"
)

print("DSN:", dsn)

conn = oracledb.connect(
    user="demo",
    password="accotimez",
    dsn=dsn
)

cur = conn.cursor()
cur.execute("SELECT 1 FROM dual")
print(cur.fetchone())

cur.close()
conn.close()