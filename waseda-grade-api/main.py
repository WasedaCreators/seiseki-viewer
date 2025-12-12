from fastapi import FastAPI, Form, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from bs4 import BeautifulSoup
import uvicorn
import requests
import json
import csv
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import traceback
import re
import datetime
import math
import mysql.connector
import hashlib
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    try:
        init_db()
    except Exception as e:
        print(f"WARNING: Database initialization failed: {e}")
        print("The application will start, but database features may not work.")
    yield
    # Shutdown logic (if any)

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for now, or specify localhost:3001
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database Connection
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
        print(f"Docker connection failed: {e}")
        
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
        print(f"Localhost connection failed: {e}")
        raise e

def init_db():
    max_retries = 10
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Create gpadata table
            # student_id is now a SHA-256 hash (64 chars)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS gpadata (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    student_id VARCHAR(64) UNIQUE,
                    avg_gpa FLOAT,
                    timestamp DATETIME
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(255) UNIQUE,
                    pw VARCHAR(128)
                )
            """)

            # Ensure legacy tables have the columns we now rely on
            cursor.execute("SHOW COLUMNS FROM users LIKE 'username'")
            if cursor.fetchone() is None:
                cursor.execute("ALTER TABLE users ADD COLUMN username VARCHAR(255) UNIQUE AFTER id")

            cursor.execute("SHOW COLUMNS FROM users LIKE 'pw'")
            pw_column = cursor.fetchone()
            if pw_column and pw_column[1].lower() != "varchar(128)":
                cursor.execute("ALTER TABLE users MODIFY pw VARCHAR(128)")
            
            conn.commit()
            
            cursor.close()
            conn.close()
            print("Database initialized successfully.")
            return
        except Exception as e:
            print(f"Database initialization attempt {attempt+1}/{max_retries} failed: {e}")
            time.sleep(retry_delay)
    
    print("Could not initialize database after multiple attempts.")


@app.get("/", response_class=HTMLResponse)
async def login_form():
    return """
    <html>
        <head>
            <title>総機GPAジェネレータ</title>
        </head>
        <body>
            <h1>総機GPAジェネレータ</h1>
            <form action="/grades" method="post">
                <label for="username">Waseda ID / Email:</label>
                <input type="text" id="username" name="username" required><br><br>
                <label for="password">Password:</label>
                <input type="password" id="password" name="password" required><br><br>
                <input type="submit" value="Get Grades">
            </form>
        </body>
    </html>
    """

@app.post("/grades")
def get_grades(username: str = Form(...), password: str = Form(...)):
    # Target URL for grades
    grade_url = "https://gradereport-ty.waseda.jp/kyomu/epb2051.htm"
    # Entry point for login (MyWaseda)
    login_entry_url = "https://my.waseda.jp/login/login"
    
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")  # Use new headless mode for better stability
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    # options.add_argument("--remote-debugging-port=9222") # Removed to avoid port conflicts
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-setuid-sandbox")
    options.add_argument("--disable-application-cache")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--mute-audio")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-features=VizDisplayCompositor")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = None
    try:
        # Check if running in Docker (CHROMEDRIVER_PATH set)
        chromedriver_path = os.environ.get("CHROMEDRIVER_PATH")
        if chromedriver_path:
            service = Service(executable_path=chromedriver_path)
        else:
            # Try to find system installed chromedriver
            import shutil
            system_chromedriver = shutil.which("chromedriver")
            if system_chromedriver:
                 service = Service(executable_path=system_chromedriver)
            else:
                 service = Service(ChromeDriverManager().install())
            
        driver = webdriver.Chrome(service=service, options=options)
        
        # 1. Start authentication flow from MyWaseda login page
        print(f"Accessing login entry point: {login_entry_url}...")
        driver.get(login_entry_url)
        
        # Wait for page load
        time.sleep(3)
        
        # Check for an explicit "Login" button on the landing page
        try:
            login_links = driver.find_elements(By.XPATH, "//a[contains(text(), 'Login') or contains(text(), 'ログイン')]")
            if login_links:
                print("Found Login link/button, clicking...")
                login_links[0].click()
                print("Clicked Login button. Waiting for navigation...")
                time.sleep(3)
        except Exception as e:
            print(f"Check for login button failed (non-fatal): {e}")

        # Wait for redirect to Microsoft Login or Portal
        wait = WebDriverWait(driver, 20)
        
        try:
            # Wait until we are either on Microsoft login or Waseda portal
            wait.until(lambda d: "login.microsoftonline.com" in d.current_url or "my.waseda.jp/portal" in d.current_url)
        except Exception:
            print(f"Timeout waiting for redirect. Current URL: {driver.current_url}")
        
        current_url = driver.current_url
        print(f"Current URL after entry: {current_url}")
        
        if "login.microsoftonline.com" in current_url:
            print("Detected Microsoft Login")
            
            # Enter Email
            email_input = wait.until(EC.presence_of_element_located((By.NAME, "loginfmt")))
            email_input.clear()
            email_input.send_keys(username)
            
            # Click Next
            next_btn = wait.until(EC.element_to_be_clickable((By.ID, "idSIButton9")))
            next_btn.click()
            
            # Enter Password
            # Wait for password field to be visible
            password_input = wait.until(EC.visibility_of_element_located((By.NAME, "passwd")))
            password_input.send_keys(password)
            
            # Click Sign in
            signin_btn = wait.until(EC.element_to_be_clickable((By.ID, "idSIButton9")))
            signin_btn.click()
            
            # Handle "Stay signed in?" (Click No)
            try:
                stay_signed_in_no = wait.until(EC.element_to_be_clickable((By.ID, "idBtn_Back")))
                stay_signed_in_no.click()
            except:
                print("Stay signed in prompt did not appear or was skipped.")
                pass
                
            # Wait for login to complete and redirect to portal
            print("Waiting for login to complete...")
            try:
                wait.until(lambda d: "my.waseda.jp/portal" in d.current_url)
                print("Login successful, redirected to portal.")
            except:
                print(f"Timed out waiting for portal redirect. Current URL: {driver.current_url}")
                if "login.microsoftonline.com" in driver.current_url:
                     return JSONResponse(content={"status": "error", "message": "Login incomplete. Possible 2FA required or wrong credentials.", "current_url": driver.current_url}, status_code=401)
            
        elif "my.waseda.jp/portal" in current_url:
            print("Already logged in to portal.")
        
        menu_url = "https://coursereg.waseda.jp/portal/simpleportal.php?HID_P14=JA"
        print(f"Navigating to Grades & Course registration menu: {menu_url}...")
        driver.get(menu_url)
        
        # Wait for the menu page to load
        time.sleep(3)
        
        print("Clicking '成績照会' link...")
        try:
            grade_link = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(., '成績照会')]")))
            grade_link.click()
            
            # Wait for the new window to open
            wait.until(EC.number_of_windows_to_be(2))
            
            # Switch to the new window
            windows = driver.window_handles
            driver.switch_to.window(windows[-1])
            print(f"Switched to new window: {driver.current_url}")
            time.sleep(5)
            
            html_content = driver.page_source
            
            if "成績照会" in html_content:
                if "科目名" not in html_content:
                    print("On search condition page. Trying to display grades...")
                    try:
                        # Look for a submit button
                        display_btn = driver.find_element(By.XPATH, "//input[@type='submit' or @value='表示']")
                        display_btn.click()
                        time.sleep(3)
                        html_content = driver.page_source
                    except:
                        print("Could not find display button, or already on list page.")
            
            print("Successfully accessed grade page.")
            
            # Extract Student ID
            student_id = "unknown"
            
            # Search for student ID pattern: 1[A-Z][0-9]{2}[A-Z][0-9]+
            # e.g. 1X24B044
            id_match = re.search(r"(1[A-Z])(\d{2})([A-Z])\d+", html_content)
            
            if id_match:
                full_id = id_match.group(0)
                prefix = id_match.group(1) # e.g. 1X
                year = id_match.group(2)   # e.g. 24
                dept = id_match.group(3)   # e.g. B
                
                print(f"Detected Student ID: {full_id}")
                
                if prefix != "1X" or dept != "B":
                    return JSONResponse(content={"status": "error", "message": "総合機械工学科専用だよ"}, status_code=400)
                
                # 2. Check Year: Must be 23 or 24
                if year not in ["23", "24"]:
                    return JSONResponse(content={"status": "error", "message": "学年が違うよ"}, status_code=400)
                
                student_id = full_id
            else:
                print("Student ID not found in page content.")

            grades = parse_grades(html_content)
            
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

            total_weighted_points = 0
            total_weighted_credits = 0
            
            # Point mapping: A+=9, A=8, B=7, C=6, F=0, S=0
            point_map = {"A+": 9, "A": 8, "B": 7, "C": 6, "F": 0, "S": 0}
            
            print("--- Calculation Details ---")
            print(f"Parsed {len(grades)} grades.")
            
            # Key: hisshu_name, Value: {points: ..., w_credits: ..., grade_val: ..., subject: ..., grade: ...}
            hisshu_best_matches = {}

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
                print(f"Subject: {data['subject']} (Matched: {h_name}), Grade: {data['grade']} (Pt:{data['grade_val']}) -> Points: {data['points']}, W.Credits: {data['w_credits']}")
            
            print(f"Total Weighted Points: {total_weighted_points}")
            print(f"Total Weighted Credits: {total_weighted_credits}")

            average_score = 0
            if total_weighted_credits > 0:
                average_score = total_weighted_points / total_weighted_credits
            
            print(f"Calculated Average: {average_score}")
            print("---------------------------")
            
            # --- Database Operations ---
            timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Hash student_id
            hashed_student_id = hashlib.sha256(hashlib.sha512(student_id.encode()).hexdigest().encode()).hexdigest()
            
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                # 2. Save/Update GPA to 'gpadata'
                # Use INSERT ... ON DUPLICATE KEY UPDATE
                cursor.execute("""
                    INSERT INTO gpadata (student_id, avg_gpa, timestamp)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE avg_gpa = %s, timestamp = %s
                """, (hashed_student_id, average_score, timestamp_str, average_score, timestamp_str))
                
                conn.commit()
                
                cursor.close()
                conn.close()
                print(f"Database updated for {hashed_student_id} (Original: {student_id})")
                
            except Exception as e:
                print(f"Database error: {e}")
                # Fallback or error handling?
                # For now, just print error, but scores list might be empty if DB failed.
                # scores = [average_score] # Fallback to self score

            json_content = json.dumps({
                "status": "success", 
                "grades": grades, 
                "student_id": student_id,
                "average_score": f"{average_score:.2f}",
                # "deviation_score": f"{deviation_score:.2f}",
                # "rank": rank,
                # "total_students": total_students,
                # "distribution": distribution
            }, ensure_ascii=False)
            return Response(content=json_content, media_type="application/json; charset=utf-8")
            
        except Exception as e:
            error_msg = f"Failed to navigate via menu: {str(e)}\nTraceback: {traceback.format_exc()}"
            print(error_msg)
            return JSONResponse(content={"status": "error", "message": error_msg, "current_url": driver.current_url}, status_code=500)
            
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}\nTraceback: {traceback.format_exc()}"
        print(error_msg)
        return JSONResponse(content={"status": "error", "message": error_msg}, status_code=500)
    finally:
        if driver:
            driver.quit()


def parse_grades(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    grades = []
    
    # The grades are in rows with class 'operationboxf'
    rows = soup.find_all('tr', class_='operationboxf')
    
    for row in rows:
        cols = row.find_all('td')
        if not cols:
            continue
        col_texts = [col.get_text(strip=True).replace('\xa0', ' ') for col in cols]
        
        if len(col_texts) >= 6:
            subject = col_texts[0]
            year = col_texts[1]
            semester = col_texts[2]
            credit = col_texts[3]
            grade = col_texts[4]
            gp = col_texts[5]
            
            # If year is empty, it's likely a section header
            if not year:
                continue
                
            grades.append({
                "subject": subject,
                "year": year,
                "semester": semester,
                "credit": credit,
                "grade": grade,
                "gp": gp
            })
            
    return grades

# --- Admin Endpoints ---

class AdminLogin(BaseModel):
    username: str
    password: str

def get_user_password_hash(username: str):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT pw FROM users WHERE username = %s", (username,))
        result = cursor.fetchone()
        if result:
            return result.get("pw")
    except Exception as e:
        print(f"Failed to fetch credentials for {username}: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return None

def verify_token(token: str) -> bool:
    if not token:
        return False
    hashed_token = hashlib.sha512(token.encode()).hexdigest()
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM users WHERE pw = %s", (hashed_token,))
        return cursor.fetchone() is not None
    except Exception as e:
        print(f"Token verification failed: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.post("/admin/login")
async def admin_login(data: AdminLogin):
    stored_hash = get_user_password_hash(data.username)
    if not stored_hash:
        return JSONResponse(content={"status": "error", "message": "Invalid credentials"}, status_code=401)

    incoming_hash = hashlib.sha512(data.password.encode()).hexdigest()
    if incoming_hash == stored_hash:
        return {"status": "success", "message": "Login successful"}

    return JSONResponse(content={"status": "error", "message": "Invalid credentials"}, status_code=401)

@app.get("/admin/data")
async def get_admin_data(request: Request):
    token = request.headers.get("X-Admin-Token")
    if not verify_token(token):
         return JSONResponse(content={"status": "error", "message": "Unauthorized"}, status_code=401)

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT student_id, avg_gpa, timestamp FROM gpadata")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Convert datetime to string
        for row in rows:
            if isinstance(row['timestamp'], datetime.datetime):
                row['timestamp'] = row['timestamp'].strftime("%Y-%m-%d %H:%M:%S")
        
        return {"status": "success", "data": rows}
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

class UpdateGPA(BaseModel):
    avg_gpa: float

@app.delete("/admin/data/{student_id}")
async def delete_student_data(student_id: str, request: Request):
    token = request.headers.get("X-Admin-Token")
    if not verify_token(token):
         return JSONResponse(content={"status": "error", "message": "Unauthorized"}, status_code=401)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM gpadata WHERE student_id = %s", (student_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return {"status": "success", "message": f"Deleted {student_id}"}
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@app.put("/admin/data/{student_id}")
async def update_student_data(student_id: str, data: UpdateGPA, request: Request):
    token = request.headers.get("X-Admin-Token")
    if not verify_token(token):
         return JSONResponse(content={"status": "error", "message": "Unauthorized"}, status_code=401)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("UPDATE gpadata SET avg_gpa = %s, timestamp = %s WHERE student_id = %s", (data.avg_gpa, timestamp_str, student_id))
        conn.commit()
        cursor.close()
        conn.close()
        return {"status": "success", "message": f"Updated {student_id}"}
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001, timeout_keep_alive=300)
