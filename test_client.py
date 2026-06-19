import os
import oracledb

client_dir = r"C:\oracle\instantclient_19"

print("Client directory:", client_dir)
print("Folder exists:", os.path.isdir(client_dir))
print("oci.dll exists:", os.path.exists(os.path.join(client_dir, "oci.dll")))

print("\nFiles in client directory:")
for file in os.listdir(client_dir):
    print(" -", file)

print("\nTrying to load Oracle Client...")
oracledb.init_oracle_client(lib_dir=client_dir)

print("Oracle Client loaded successfully")
print("Client version:", oracledb.clientversion())