import mysql.connector
import hashlib
import os
import time

def get_db_connection():
    # Get credentials from environment variables with defaults for backward compatibility
    db_user = os.getenv("MYSQL_USER", "seiseki")
    db_password = os.getenv("MYSQL_PASSWORD", "seiseki-mitai")
    db_name = os.getenv("MYSQL_DATABASE", "seiseki")
    
    # Try connecting to 'mysql' host (docker) first, then localhost
    try:
        conn = mysql.connector.connect(
            host="mysql",
            user=db_user,
            password=db_password,
            database=db_name,
            connection_timeout=3
        )
        print("Connected to MySQL (Docker)")
        return conn
    except Exception as e:
        pass
        
    try:
        conn = mysql.connector.connect(
            host="127.0.0.1",
            user=db_user,
            password=db_password,
            database=db_name,
            connection_timeout=3
        )
        print("Connected to MySQL (Localhost)")
        return conn
    except Exception as e:
        print(f"Connection failed: {e}")
        raise e

def migrate():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("ALTER TABLE gpadata MODIFY COLUMN student_id VARCHAR(64)")
        conn.commit()
        print("Altered student_id column to VARCHAR(64)")
    except Exception as e:
        print(f"Column alteration skipped or failed (might already be 64): {e}")

    print("Fetching all records...")
    cursor.execute("SELECT * FROM gpadata")
    rows = cursor.fetchall()

    print(f"Found {len(rows)} records.")

    for row in rows:
        original_id = row['student_id']
        
        # Check if already hashed (simple heuristic: len 64 and hex)
        if len(original_id) == 64:
            try:
                int(original_id, 16)
                # It's likely a hash, skip
                continue
            except ValueError:
                pass
        
        # Calculate hash
        hashed_id = hashlib.sha256(original_id.encode()).hexdigest()
        
        print(f"Migrating {original_id} -> {hashed_id}")
        
        try:
            # Try to update
            cursor.execute("UPDATE gpadata SET student_id = %s WHERE id = %s", (hashed_id, row['id']))
            conn.commit()
        except mysql.connector.errors.IntegrityError as e:
            # Duplicate entry?
            if e.errno == 1062: # Duplicate entry
                print(f"Hash {hashed_id} already exists. Deleting old unhashed record {row['id']}...")
                cursor.execute("DELETE FROM gpadata WHERE id = %s", (row['id'],))
                conn.commit()
            else:
                print(f"Error updating {original_id}: {e}")
        except Exception as e:
             print(f"Error updating {original_id}: {e}")

    cursor.close()
    conn.close()
    print("Migration completed.")

if __name__ == "__main__":
    migrate()
