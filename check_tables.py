import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.execute('SELECT name FROM sqlite_master WHERE type="table"')
tables = cursor.fetchall()

print('Tablas existentes:')
for row in tables:
    print(f'  - {row[0]}')

conn.close() 