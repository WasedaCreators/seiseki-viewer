import mysql.connector
import csv
import os
import hashlib
import datetime

def get_db_connection():
    # Try connecting to 'mysql' host (docker) first, then localhost
    try:
        conn = mysql.connector.connect(
            host="mysql",
            user="seiseki",
            password="seiseki-mitai",
            database="seiseki",
            connection_timeout=3
        )
        print("Connected to MySQL (Docker)")
        return conn
    except Exception as e:
        pass
        
    try:
        conn = mysql.connector.connect(
            host="127.0.0.1",
            user="seiseki",
            password="seiseki-mitai",
            database="seiseki",
            connection_timeout=3
        )
        print("Connected to MySQL (Localhost)")
        return conn
    except Exception as e:
        print(f"Connection failed: {e}")
        raise e

def load_hisshu():
    possible_paths = ["list/hisshu.csv", "../list/hisshu.csv", "/app/list/hisshu.csv"]
    hisshu_path = None
    for p in possible_paths:
        if os.path.exists(p):
            hisshu_path = p
            break
    
    hisshu_subjects = []
    if hisshu_path:
        print(f"Loading hisshu.csv from: {hisshu_path}")
        try:
            with open(hisshu_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if "name" in row:
                        w = row.get("重み", "1")
                        try:
                            w = float(w)
                        except:
                            w = 1.0
                        hisshu_subjects.append({"name": row["name"], "weight": w})
        except Exception as e:
            print(f"Failed to load hisshu.csv: {e}")
    else:
        print("Warning: hisshu.csv not found in any expected location.")
    return hisshu_subjects

def calculate_gpa(grades, hisshu_subjects):
    point_map = {"A+": 9, "A": 8, "B": 7, "C": 6, "F": 0, "S": 0}
    hisshu_best_matches = {}
    
    total_weighted_points = 0
    total_weighted_credits = 0

    for g in grades:
        subject = g["subject"]
        grade = g["grade"]
        credit_str = g["credit"]
        
        # Exclude * or ＊ or P
        if "＊" in grade or "*" in grade or "P" in grade:
            continue
        
        try:
            credit = float(credit_str)
        except:
            continue
        
        # Check if subject is required (contains name from list)
        matched_hisshu = None
        for h in hisshu_subjects:
            if h["name"] in subject:
                matched_hisshu = h
                break
        
        if matched_hisshu:
            h_name = matched_hisshu["name"]
            h_weight = matched_hisshu["weight"]
            p = point_map.get(grade, 0)
            
            # Calculate potential contribution
            points = p * credit * h_weight
            w_credits = credit * h_weight
            
            # Check if we already have a match for this hisshu subject
            if h_name in hisshu_best_matches:
                # Compare grades. Higher point value wins.
                if p > hisshu_best_matches[h_name]["grade_val"]:
                    hisshu_best_matches[h_name] = {
                        "points": points,
                        "w_credits": w_credits,
                        "grade_val": p,
                        "subject": subject,
                        "grade": grade
                    }
            else:
                hisshu_best_matches[h_name] = {
                    "points": points,
                    "w_credits": w_credits,
                    "grade_val": p,
                    "subject": subject,
                    "grade": grade
                }

    # Sum up results
    for h_name, data in hisshu_best_matches.items():
        total_weighted_points += data["points"]
        total_weighted_credits += data["w_credits"]
    
    average_score = 0
    if total_weighted_credits > 0:
        average_score = total_weighted_points / total_weighted_credits
        
    return average_score

def recalc():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Load hisshu subjects
    hisshu_subjects = load_hisshu()
    
    print("Fetching all records from userdata...")
    try:
        cursor.execute("SELECT * FROM userdata")
        rows = cursor.fetchall()
    except mysql.connector.Error as e:
        print(f"Error fetching userdata: {e}")
        print("Make sure the 'userdata' table exists and has data.")
        return

    if not rows:
        print("No data found in userdata table.")
        return

    # Group by student_id
    students = {}
    for row in rows:
        sid = row['student_id']
        if sid not in students:
            students[sid] = []
        students[sid].append(row)
    
    print(f"Found {len(students)} unique students.")
    
    timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    for student_id, grades in students.items():
        print(f"Processing student: {student_id}")
        
        # Calculate GPA
        avg_gpa = calculate_gpa(grades, hisshu_subjects)
        print(f"  -> Calculated GPA: {avg_gpa}")
        
        # Hash student_id
        # Check if it's already hashed? Assuming userdata has raw IDs as per request context.
        # But if userdata has mixed, we might double hash. 
        # Assuming raw IDs for now as 'userdata' was for raw data storage.
        hashed_id = hashlib.sha256(student_id.encode()).hexdigest()
        
        # Update gpadata
        try:
            cursor.execute("""
                INSERT INTO gpadata (student_id, avg_gpa, timestamp)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE avg_gpa = %s, timestamp = %s
            """, (hashed_id, avg_gpa, timestamp_str, avg_gpa, timestamp_str))
            conn.commit()
            print(f"  -> Saved to gpadata as {hashed_id}")
        except Exception as e:
            print(f"  -> Error saving to gpadata: {e}")

    cursor.close()
    conn.close()
    print("Recalculation completed.")

if __name__ == "__main__":
    recalc()
