import pymysql
import sys

# Connect to MySQL
conn = pymysql.connect(
    host='localhost',
    user='root',
    password='administrator',
    database='EchoDB_test'
)

cursor = conn.cursor()

# Read schema file
with open('schema.sql', 'r', encoding='utf-8') as f:
    schema_sql = f.read()

# Split and clean statements
statements = []
for stmt in schema_sql.split(';'):
    stmt = stmt.strip()
    # Skip empty, comments, or database/USE statements
    if not stmt:
        continue
    if stmt.startswith('--'):
        continue
    if 'CREATE DATABASE' in stmt.upper():
        continue
    if stmt.upper().startswith('USE '):
        continue
    
    # Remove SQL comments
    lines = []
    for line in stmt.split('\n'):
        if not line.strip().startswith('--'):
            lines.append(line)
    stmt = '\n'.join(lines).strip()
    
    if stmt:
        statements.append(stmt)

# Execute statements
success = 0
for stmt in statements:
    try:
        cursor.execute(stmt)
        success += 1
    except pymysql.err.OperationalError as e:
        # Table already exists - OK
        if '1050' in str(e):
            success += 1
        else:
            print(f"Error: {e}")
            print(f"Statement: {stmt[:100]}...")

conn.commit()
cursor.close()
conn.close()

print(f"✓ Test database schema initialized ({success} statements executed)")
