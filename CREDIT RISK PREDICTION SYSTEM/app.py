from email.mime import text
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session, send_file, make_response
from fpdf import FPDF
import io
import pandas as pd
import joblib
import numpy as np
from db_connection import save_prediction, fetch_predictions, verify_password
from config import DB_CONFIG, FLASK_SECRET_KEY, MODEL_THRESHOLD
import plotly.express as px
import plotly.graph_objects as go
import json, plotly, os, bcrypt, pymysql
import pymysql.cursors
from datetime import datetime, timedelta
from functools import wraps
import uuid
import os, re
from werkzeug.utils import secure_filename
import pdfplumber
import pytesseract
from PIL import Image
import PyPDF2


from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY
app.config["WTF_CSRF_ENABLED"] = True
csrf = CSRFProtect(app)

from flask_wtf.csrf import CSRFError

@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    print(f"CSRF ERROR: {e.description}")
    flash(f"Security Token Error: {e.description}", "danger")
    return redirect(request.url)


import fpdf
print(f"FinGuard PDF Engine: {fpdf.__version__}")

def get_db_connection():
    return pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# ------------------ LOAD MODEL ------------------
model = joblib.load("model02.joblib")
scaler = joblib.load("scaler_1.pkl")
encoders = joblib.load("encoders_1.pkl")
feature_names = joblib.load("feature_names_1.pkl")

categorical_cols = [
    "ORGANIZATION_TYPE",
    "WEEKDAY_APPR_PROCESS_START",
    "OCCUPATION_TYPE"
]

# ------------------ ROLE DECORATOR ------------------
def role_required(role):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if "role" not in session or session["role"] != role:
                return redirect("/")
            return f(*args, **kwargs)
        return wrapper
    return decorator

def validate_password(password):
    """
    Validates that the password meets enterprise security standards:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit."
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character."
    return True, ""

def send_system_notification(email, subject, body):
    """
    Simulated Institutional Notification Engine.
    Logs notifications to system logs for audit purposes.
    In production, this would use SMTP/SendGrid.
    """
    try:
        log_path = "system_notifications.log"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_path, "a") as f:
            f.write(f"\n[{timestamp}] TO: {email}\nSUBJECT: {subject}\n{body}\n{'-'*50}\n")
        print(f"Notification dispatched to {email}")
    except Exception as e:
        print(f"NOTIFICATION ERROR (Non-critical): {e}")

# ----------------- REGISTER -----------------
@app.route("/user_register", methods=["GET", "POST"])
def user_register():
    if request.method == "POST":
        try:
            username = request.form["username"].strip()
            full_name = request.form["full_name"].strip()
    
        
            if not re.match(r"^[A-Za-z\s]+$", full_name):
                flash("Full name must contain only alphabets and spaces.", "danger")
                return render_template("user_register.html")
            email = request.form["email"].strip()
            password = request.form["password"].strip()

            is_strong, msg = validate_password(password)
            if not is_strong:
                flash(msg, "danger")
                return render_template("user_register.html")

            hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO users (username, full_name, email, password_hash, role) VALUES (%s, %s, %s, %s, %s)",
                (username, full_name, email, hashed_password, "user")
            )
            conn.commit()
            conn.close()
            
            flash("Registration successful! Please login.", "success")
            return redirect(url_for("user_login"))

        except pymysql.err.IntegrityError:
            flash("Username already registered. Please login.", "warning")
            return render_template("user_register.html")
        except Exception as e:
            print(f"REGISTRATION ERROR: {e}")
            flash(f"An internal error occurred during setup.", "danger")
            return render_template("user_register.html")

    return render_template("user_register.html")




# ------------------ LANDING PAGE ------------------
@app.route("/")
def index():
    return render_template("index.html")

# ----------------- LOGIN -----------------
@app.route("/user_login", methods=["GET", "POST"])
def user_login():
    if request.method == "POST":
        try:
            username = request.form["username"]
            password = request.form["password"]

            user = get_user(username)

            if user and user["role"] == "user":
                db_hash = user["password_hash"]
                if isinstance(db_hash, str):
                    db_hash = db_hash.encode()
                
                if bcrypt.checkpw(password.encode(), db_hash):
                    session["user_id"] = user["id"]
                    session["username"] = user["username"]
                    session["full_name"] = user.get("full_name")
                    session["role"] = "user"
                    flash(f"Welcome {user['username']}!", "success")
                    return redirect("/user_dashboard")
            
            flash("Invalid username or password.", "danger")
            return render_template("user_login.html")
        except Exception as e:
            print(f"LOGIN ERROR: {e}")
            flash("An internal authentication error occurred.", "danger")
            return render_template("user_login.html")

    return render_template("user_login.html")



# ----------------- LOGOUT -----------------
@app.route("/logout")
def logout():
    role = session.get("role")
    session.clear()
    flash("You have been logged out.", "info")
    if role == "bank":
        return redirect(url_for("bank_login"))
    elif role == "admin":
        return redirect(url_for("admin_login"))
    return redirect(url_for("user_login"))


# ----------------- FORGOT PASSWORD -----------------
@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form["email"]
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()

        if user:
            # Check if this user is a 'user' or 'bank'. (Admins are usually reset manually or via different flow)
            if user['role'] not in ['user', 'bank']:
                flash("Security Limitation: Institutional accounts must contact high-clearance administrators for reset.", "danger")
                return redirect(url_for("forgot_password"))

            token = str(uuid.uuid4())
            expiry = datetime.now() + timedelta(hours=1)
            cur.execute("UPDATE users SET reset_token = %s, reset_token_expiry = %s WHERE id = %s", 
                        (token, expiry, user["id"]))
            conn.commit()
            
            # Simulate Email Sending
            reset_link = url_for('reset_password', token=token, _external=True)
            send_system_notification(email, "FinGuard Security: Password Reset Request", 
                f"Identity: {user['username']}\nRole: {user['role'].upper()}\n\nUse this secure mandate to reset your credentials: {reset_link}\nValid for 60 minutes.")
            flash(f"Reset directive dispatched to {email}. Check systems (logs).", "success")
        else:
            flash("System Error: Identity not found in database.", "danger")
        
        conn.close()
        return redirect(url_for("forgot_password"))

    return render_template("forgot_password.html")

@app.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE reset_token = %s AND reset_token_expiry > NOW()", (token,))
    user = cur.fetchone()

    if not user:
        conn.close()
        flash("Authorization Failed: Invalid or expired reset mandate.", "danger")
        return redirect(url_for("forgot_password"))

    if request.method == "POST":
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]
        
        if password != confirm_password:
            flash("Validation Error: Passwords do not match.", "danger")
            return render_template("reset_password.html")
            
        is_strong, msg = validate_password(password)
        if not is_strong:
            flash(msg, "danger")
            return render_template("reset_password.html")

        hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        cur.execute("UPDATE users SET password_hash = %s, reset_token = NULL, reset_token_expiry = NULL WHERE id = %s", 
                    (hashed_password, user["id"]))
        conn.commit()
        conn.close()
        
        # Logic to redirect back to correct login page based on role
        if user['role'] == 'bank':
            flash("Mandate Updated: Banker credentials reset. Please authenticate.", "success")
            return redirect(url_for("bank_login"))
        else:
            flash("Status Updated: User credentials reset. Please login.", "success")
            return redirect(url_for("user_login"))
        
    conn.close()
    return render_template("reset_password.html")


# ------------------ ADMIN LOGIN ------------------
@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if verify_password(username, password):
            session["username"] = username
            session["role"] = "admin"
            return redirect("/dashboard")

        flash("Invalid username or password.", "danger")
        return render_template("login.html")

    return render_template("login.html")

# ------------------ BANK LOGIN ------------------
@app.route("/bank_login", methods=["GET", "POST"])
def bank_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = get_user(username)
        if user and user["role"] == "bank":
            if bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
                session["user_id"] = user["id"]
                session["role"] = "bank"
                # Store the bank name this user is responsible for.
                # If None, they might be a general banker or it needs to be set.
                session["bank_affiliation"] = user.get("bank_affiliation") 
                return redirect("/bank_dashboard")

        flash("Invalid username or password.", "danger")
        return render_template("bank_login.html")

    return render_template("bank_login.html")

# ------------------ BANK DASHBOARD ------------------
@app.route('/bank_dashboard', methods=['GET', 'POST'])
@role_required('bank')
def bank_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Focused only on HIGH-IMPACT active review (Pending)
    risk_filter = request.args.get('risk', '')             
    bank_name = session.get('bank_affiliation')

    query = """
        SELECT a.application_id, a.user_id, a.income, a.loan_amount, a.credit_score,
               a.risk_level, a.probability, a.status, a.system_explanation, a.created_at, 
               a.banker_reason, a.bank_name, u.username, u.email
        FROM applications a
        JOIN users u ON a.user_id = u.id
        WHERE a.status = 'Pending'
    """
    params = []

    # If banker has a specific bank affiliation, ONLY show those applications.
    if bank_name:
        query += " AND a.bank_name = %s"
        params.append(bank_name)

    if risk_filter:
        query += " AND a.risk_level = %s"
        params.append(risk_filter)

    query += " ORDER BY a.created_at DESC"

    cursor.execute(query, params)
    applications = cursor.fetchall()
    conn.close()

    return render_template(
        'bank_dashboard.html',
        applications=applications,
        risk_filter=risk_filter,
        current_bank=bank_name if bank_name else "All Banks (Superuser)"
    )


@app.route('/bank_action', methods=['POST'])
@role_required('bank')
def bank_action():
    application_id = request.form['application_id']
    status = request.form['status']
    reason = request.form['banker_reason']
    banker_id = session['user_id']

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE applications
        SET status=%s,
            banker_reason=%s,
            banker_id=%s,
            decision_at=NOW()
        WHERE application_id=%s
    """, (status, reason, banker_id, application_id))

    # Fetch User Email for Notification
    cursor.execute("""
        SELECT u.email, u.username, a.loan_amount 
        FROM users u 
        JOIN applications a ON u.id = a.user_id 
        WHERE a.application_id = %s
    """, (application_id,))
    user_data = cursor.fetchone()
    
    conn.commit()
    conn.close()

    if user_data:
        subject = f"Official Mandate Update: #{application_id}"
        body = f"Identity: {user_data['username']}\n"
        body += f"Decision: {status.upper()}\n"
        body += f"Fiscal Value: INR {user_data['loan_amount']:,.2f}\n"
        body += f"Officer Remarks: {reason or 'No additional remarks.'}\n\n"
        body += "You may download the full mandate report from your dashboard."
        send_system_notification(user_data['email'], subject, body)

    flash(f"Application #{application_id} has been {status}.", "success")
    return redirect(url_for('bank_dashboard'))


@app.route('/bank/history')
@role_required('bank')
def bank_history():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Decisions and Audit trail
    status_filter = request.args.get('status', '') # Approved/Rejected/None
    risk_filter = request.args.get('risk', '')
    bank_name = session.get('bank_affiliation')

    query = """
        SELECT application_id,user_id, income, loan_amount, credit_score,
               risk_level, probability, status, banker_reason, created_at, bank_name
        FROM applications a
        WHERE a.status != 'Pending'
    """
    params = []

    if bank_name:
        query += " AND bank_name = %s"
        params.append(bank_name)

    if status_filter:
        query += " AND status = %s"
        params.append(status_filter)
    
    if risk_filter:
        query += " AND risk_level = %s"
        params.append(risk_filter)

    query += " ORDER BY created_at DESC"
    
    cursor.execute(query, params)
    records = cursor.fetchall()
    conn.close()

    return render_template(
        "bank_history.html",
        records=records,
        status_filter=status_filter,
        risk_filter=risk_filter
    )

@app.route('/bank/user_history/<int:user_id>')
@role_required('bank')
def bank_user_history(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get user details
    cursor.execute("SELECT username, email FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    
    current_bank = session.get("bank_affiliation")
    
    # Get application history - Strictly showing only APPROVED mandates 
    # to assess historical creditworthiness.
    query = """
        SELECT * FROM applications 
        WHERE user_id = %s 
        AND status = 'Approved'
        ORDER BY created_at DESC
    """
    params = (user_id,)
        
    cursor.execute(query, params)
    history = cursor.fetchall()
    conn.close()
    
    return render_template("bank_user_history.html", user=user, history=history, current_bank=session.get("bank_affiliation"))

# Redirecting legacy banklogout to unified logout
@app.route("/banklogout")
def banklogout():
    return redirect(url_for("logout"))

# ------------------ FETCH APPLICATIONS ------------------
def fetch_applications():
    conn = get_db_connection()
    query = """
        SELECT 
            a.application_id,
            u.username,
            u.email,
            a.income,
            a.loan_amount,
            a.credit_score,
            a.risk_level,
            a.probability,
            a.bank_name,
            a.status,
            a.created_at,
            a.system_explanation,
            a.banker_reason
        FROM applications a
        JOIN users u ON a.user_id = u.id
        ORDER BY a.created_at DESC
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df



# ------------------ GET USER ------------------
def get_user(username):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username=%s", (username,))
    user = cur.fetchone()
    conn.close()
    return user

# ------------------ USER: APPLY LOAN ------------------
@app.route("/apply_loan", methods=["GET", "POST"])
@role_required("user")
def apply_loan():
    if request.method == "POST":
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # ---------------- FORM INPUTS ----------------
        bank_name = request.form.get("bank_name", "General")
        user_salary = int(request.form["income"])
        file = request.files.get("salary_slip")
        
        # ---------------- CHECK PENDING/ACTIVE LOANS (BANK-SPECIFIC) ----------------
        # We block if the user has a pending or active loan with the SELECTED bank.
        # This allows applying to multiple banks if needed.
        cursor.execute("""
            SELECT status FROM applications 
            WHERE user_id = %s 
            AND TRIM(bank_name) = %s 
            AND (status = 'Pending' OR status = 'Approved')
            LIMIT 1
        """, (session["user_id"], bank_name))
        existing = cursor.fetchone()
        
        if existing:
            conn.close()
            if existing['status'] == 'Pending':
                flash(f"Action Blocked: You already have a pending application with {bank_name}. Please wait for a decision before submitting another mandate for this institution.", "danger")
            else:
                flash(f"Action Blocked: You have an active loan mandate with {bank_name}. Our protocol requires full repayment or closure of existing mandates at this bank before applying for a new one.", "danger")
            return redirect(url_for('my_applications'))
        
        # Close connection after check
        conn.close()
        
        # ---------------- SALARY INPUT ----------------

        if not file or file.filename == "":
            return render_template("error.html", message="Salary slip is required")

        # ---------------- FILE VALIDATION ----------------
        ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
        def allowed_file(filename):
            return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

        if not allowed_file(file.filename):
            return render_template("error.html", message="Unsupported file type. Only PDF and Images (.jpg, .jpeg, .png) are allowed.")

        # Check file size (5MB limit)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        if file_size > 5 * 1024 * 1024:
            return render_template("error.html", message="File too large. Maximum size allowed is 5MB.")

        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(file_path)

        # ---------------- TEXT EXTRACTION ----------------
        if filename.lower().endswith(".pdf"):
            doc_text = extract_text_from_pdf(file_path)
        else:
            doc_text = extract_text_from_image(file_path)
        
        if doc_text == "ERROR_TESSERACT_NOT_FOUND":
            return render_template("error.html", message="OCR Engine (Tesseract) is not installed on this system. Please upload a PDF version of your salary slip or contact support.")

        extracted_salary = extract_salary(doc_text)
        extracted_name = extract_name(doc_text) # New function

        # Debugging
        print("OCR Text:", doc_text)
        print("User Input Salary:", user_salary)
        print("Extracted Salary:", extracted_salary)
        print("Extracted Name:", extracted_name)
        print("Registered Name:", session.get("full_name"))

        # ---------------- NAME VERIFICATION ----------------
        registered_name = session.get("full_name", "").lower().strip()
        if not extracted_name or registered_name not in extracted_name.lower():
            return render_template("error.html", message="Salary slip name does not match registered user name.")

        # ---------------- DATE VERIFICATION ----------------
        extracted_date = extract_date(doc_text)
        is_date_valid, date_message = verify_slip_date(extracted_date)
        if not is_date_valid:
            return render_template("error.html", message=date_message)

        # ---------------- SALARY VERIFICATION ----------------
        is_valid, message = verify_salary(user_salary, extracted_salary)
        if not is_valid:
            error_details = f"{message} (Declared: ₹{user_salary}, Detected in Slip: ₹{extracted_salary})"
            return render_template("error.html", message=error_details)

        # ---------------- ML INPUT ----------------
        user_input = {
            "AMT_INCOME_TOTAL": user_salary,
            "AMT_CREDIT": float(request.form["loan_amount"]),
            "DAYS_BIRTH": -int(request.form["age"]) * 365,
            "ORGANIZATION_TYPE": request.form["ORGANIZATION_TYPE"],
            "OCCUPATION_TYPE": request.form["OCCUPATION_TYPE"]
        }

        full_data = enrich_user_data(user_input)

        # ---------------- LIABILITY ASSESSMENT (NEW) ----------------
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT SUM(loan_amount) as total_debt, COUNT(*) as loan_count 
            FROM applications 
            WHERE user_id = %s AND status = 'Approved'
        """, (session["user_id"],))
        liability_data = cursor.fetchone()
        conn.close()

        existing_debt = liability_data['total_debt'] if liability_data['total_debt'] else 0
        active_loans = liability_data['loan_count'] if liability_data['loan_count'] else 0
        total_exposure = existing_debt + user_input["AMT_CREDIT"]
        
        # Calculate DTI (Debt-to-Income) Ratio
        dti_ratio = (total_exposure / user_salary) if user_salary > 0 else 100

        # ---------------- ML PREDICTION & RISK ADJUSTMENT ----------------
        risk, prob = run_prediction_logic(full_data)
        
        # Apply Liability Penalties
        liability_penalty = 0
        if dti_ratio > 15:
            liability_penalty += 0.40 # Extreme risk
        elif dti_ratio > 8:
            liability_penalty += 0.25 # Significant risk
        elif dti_ratio > 5:
            liability_penalty += 0.15 # Moderate risk
            
        if active_loans >= 2:
            liability_penalty += 0.15 # Multi-loan penalty

        # Update Probability and recalculate Score
        prob = min(0.99, prob + liability_penalty)
        risk = "High Risk" if prob > MODEL_THRESHOLD else "Low Risk"
        
        credit_score = int(850 - (float(prob) * 550))
        
        # Override for extreme cases
        if dti_ratio > 20 or (user_salary < 15000 and user_input["AMT_CREDIT"] > 500000):
            risk = "High Risk"
            prob = max(prob, 0.95)
            credit_score = min(credit_score, 450)

        credit_score = max(300, min(credit_score, 850))

        # Add liability metadata to full_data for explanation engine
        full_data["existing_debt"] = existing_debt
        full_data["active_loans"] = active_loans
        full_data["dti_ratio"] = dti_ratio

        # ---------------- RECOMMENDED LOAN ----------------
        # Always assign recommended loan, interest rate, tenure
        if credit_score >= 750:
            recommended_loan = "Up to 10 Lakhs"
            interest_rate = "8.5%"
            tenure = "20 Years"
        elif credit_score >= 650:
            recommended_loan = "Up to 5 Lakhs"
            interest_rate = "11%"
            tenure = "10 Years"
        else:
            recommended_loan = "Up to 1 Lakh"
            interest_rate = "15%"
            tenure = "3–5 Years"

        # ---------------- EXPLANATION ----------------
        system_explanation = generate_explanation(full_data, risk, prob)

        # ---------------- SAVE APPLICATION ----------------
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO applications 
            (user_id, income, loan_amount, risk_level, probability, 
             credit_score, recommended_loan, interest_rate, tenure, system_explanation, bank_name, salary_slip, salary_verified)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s, %s, %s, %s, %s)
        """, (
            session["user_id"],
            user_salary,
            user_input["AMT_CREDIT"],
            risk,
            prob,
            credit_score,
            recommended_loan,
            interest_rate,
            tenure,
            system_explanation,
            bank_name,
            filename,
            "Yes"
        ))
        conn.commit()
        conn.close()

        # 🔹 GLOBAL ANALYTICS SYNC: Save to predictions table so it shows up in Admin Dashboard Charts
        save_prediction(
            age=int(user_input["DAYS_BIRTH"] / -365),
            income=float(user_salary),
            loan_amount=float(user_input["AMT_CREDIT"]),
            prediction=risk,
            probability=float(prob),
            credit_score=credit_score,
            recommended_loan=recommended_loan,
            interest_rate=interest_rate,
            tenure=tenure
        )

        # ---------------- RESPONSE ----------------
        return render_template(
            "user_result.html",
            risk_level=risk,
            probability=round(prob, 4),
            credit_score=credit_score,
            recommended_loan=recommended_loan,
            interest_rate=interest_rate,
            tenure=tenure,
            salary_status=f"{date_message} | {message}",
            explanation=system_explanation
        )

    return render_template("apply_loan.html")
# ------------------ SALARY EXTRACTION ----------------
def extract_salary(text):
    """
    Extracts Net Pay from salary slip text robustly.
    Handles OCR artifacts, special symbols, commas, etc.
    """
    text = text.replace("\n", " ").replace("\r", " ")
    text = text.replace(",", "").replace("₹", "").replace("INR", "")
    text = re.sub(r"\s+", " ", text)

    # Look for Net Pay pattern
    net_pay_match = re.search(r'Net\s*Pay[:\s][^0-9]([0-9]{3,})', text, re.IGNORECASE)
    if net_pay_match:
        return int(net_pay_match.group(1))

    # Fallback: largest number in text
    numbers = [int(num) for num in re.findall(r'\b\d{4,}\b', text)]
    if numbers:
        return max(numbers)

    return None


def extract_name(text):
    """
    Attempts to extract the employee name from salary slip text.
    Looks for common patterns like 'Employee Name', 'Name:', 'Worker:', etc.
    """
    # Clean text for pattern matching
    text_clean = re.sub(r'\s+', ' ', text)
    
    # Try to find Name pattern
    patterns = [
        r"(?:Employee|Account|Member|Staff|Principal|Official)\s*Name[:\s]*([A-Z\s]{3,30})",
        r"Name[:\s]*([A-Z\s]{3,30})",
        r"([A-Z][a-z]+\s[A-Z][a-z]+)" # Fallback to capitalized word pairs
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            extracted = match.group(1).strip()
            if len(extracted) > 3:
                return extracted
                
    return None


def extract_date(text):
    """
    Extracts the most relevant date from the salary slip text.
    Looks for patterns like 'Date:', 'Salary Month:', 'For the month of', etc.
    """
    # Common date patterns
    patterns = [
        r"(?:Date|Dated)\s*[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"(?:Month|Period|For the month of)\s*[:\s]*([A-Za-z]+\s*,?\s*\d{4})",
        r"(\d{1,2}\s[A-Za-z]+\s\d{4})", # 12 Jan 2026
        r"([A-Za-z]{3}\s\d{4})" # Jan 2026
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            date_str = match.group(1).strip()
            # Try to parse the date string
            date_formats = ["%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y", "%B %Y", "%b %Y", "%d %b %Y", "%d %B %Y"]
            for fmt in date_formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
    
    # Fallback: look for any date-like string in the text
    any_date_match = re.search(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", text)
    if any_date_match:
        date_str = any_date_match.group(1).strip()
        date_formats = ["%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y"]
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

    return None


def verify_slip_date(extracted_date):
    """
    Checks if the extracted date is within the last 3 months from current date.
    """
    if not extracted_date:
        return False, "Could not identify a valid date on the salary slip."
    
    current_date = datetime.now()
    three_months_ago = current_date - timedelta(days=90) # Approximation of 3 months
    
    if extracted_date >= three_months_ago:
        return True, "Salary slip date verified (within last 3 months)."
    else:
        return False, "Salary slip must be from the last 3 months to apply for loan."


def verify_salary(user_salary, extracted_salary):
    if extracted_salary is None:
        return False, "Salary not detected in document"

    extracted_salary = int(str(extracted_salary).replace(" ", "").strip())

    # ±500 tolerance
    allowed_diff = 500
    diff = abs(user_salary - extracted_salary)

    if diff <= allowed_diff:
        return True, f"Verified within ±{allowed_diff} units"
    else:
        return False, "Salary mismatch beyond acceptable limit"


# ------------------ PDF / IMAGE OCR ----------------
# Auto-configure Tesseract path for Windows
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.path.exists(TESSERACT_PATH):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() + " "
    except Exception as e:
        print(f"PDF Extraction Error: {e}")
    return text


def extract_text_from_image(img_path):
    try:
        img = Image.open(img_path)
        text = pytesseract.image_to_string(img)
        return text
    except pytesseract.TesseractNotFoundError:
        print("Tesseract OCR not found on system.")
        return "ERROR_TESSERACT_NOT_FOUND"
    except Exception as e:
        print(f"Image Extraction Error: {e}")
        return ""


@app.route("/my_applications")
@role_required("user")
def my_applications():
    user_id = session.get("user_id")

    conn = get_db_connection()
    query = """
        SELECT
            application_id,
            income,
            loan_amount,
            risk_level,
            probability,
            status,
            banker_reason,
            created_at,
            bank_name
        FROM applications
        WHERE user_id = %s
        ORDER BY created_at DESC
    """
    df = pd.read_sql(query, conn, params=(user_id,))
    conn.close()

    return render_template(
        "my_applications.html",
        records=df.to_dict("records")
    )

# ------------------ ADMIN NAVIGATION ------------------
@app.route("/dashboard")
@role_required("admin")
def dashboard():
    try:
        df = fetch_predictions()

        total = len(df)
        high = len(df[df["prediction"] == "High Risk"])
        low = len(df[df["prediction"] == "Low Risk"])

        high_pct = round((high / total) * 100, 2) if total else 0
        low_pct = round((low / total) * 100, 2) if total else 0

        # Pie Chart
        risk_counts = df["prediction"].value_counts()
        risk_color_map = {"Low Risk": "#10b981", "High Risk": "#ef4444"}
        fig1 = px.pie(values=risk_counts.values, names=risk_counts.index, 
                      hole=0.4, color=risk_counts.index, color_discrete_map=risk_color_map)
        fig1.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#94a3b8', family="Plus Jakarta Sans"),
            margin=dict(t=0, b=0, l=0, r=0),
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5)
        )
        graphJSON = json.dumps(fig1, cls=plotly.utils.PlotlyJSONEncoder)

        # Feature Importance Chart
        importances = model.feature_importances_
        fi_df = pd.DataFrame({"Feature": feature_names, "Importance": importances})
        fi_df = fi_df.sort_values(by="Importance", ascending=False).head(20)
        fig2 = px.bar(fi_df, x="Importance", y="Feature", orientation="h",
                      color_discrete_sequence=["#4f46e5"])
        fig2.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#94a3b8', family="Plus Jakarta Sans"),
            margin=dict(t=20, b=20, l=150, r=20),
            xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', title=""),
            yaxis=dict(showgrid=False, title="", autorange="reversed")
        )
        featureJSON = json.dumps(fig2, cls=plotly.utils.PlotlyJSONEncoder)

        # Model Performance Chart
        metrics_path = "model_metrics.json"
        if os.path.exists(metrics_path):
            with open(metrics_path, "r") as f:
                metrics_data = json.load(f)

            perf_data = []
            for m_name, vals in metrics_data.items():
                perf_data.append({"Model": m_name, "Metric": "Accuracy", "Score": vals.get("accuracy", 0)})
                perf_data.append({"Model": m_name, "Metric": "F1 Score", "Score": vals.get("f1", 0)})
            
            comparison_df = pd.DataFrame(perf_data)
            fig3 = px.bar(comparison_df, x="Model", y="Score", color="Metric",
                          barmode="group", color_discrete_map={"Accuracy": "#4f46e5", "F1 Score": "#818cf8"})
            fig3.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#94a3b8', family="Plus Jakarta Sans"),
                margin=dict(t=20, b=50, l=50, r=20),
                xaxis=dict(gridcolor='rgba(255,255,255,0.05)', title=""),
                yaxis=dict(gridcolor='rgba(255,255,255,0.05)', title="", range=[0, 1.05]),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            modelJSON = json.dumps(fig3, cls=plotly.utils.PlotlyJSONEncoder)
            
            # Confusion Matrix
            if "XGBoost" in metrics_data and "confusion_matrix" in metrics_data["XGBoost"]:
                cm = np.array(metrics_data["XGBoost"]["confusion_matrix"])
                fig4 = go.Figure(data=go.Heatmap(
                    z=cm, x=['Predicted Safe', 'Predicted At-Risk'], y=['Actual Safe', 'Actual At-Risk'],
                    colorscale=[[0, '#0f172a'], [1, '#4f46e5']], text=cm, texttemplate='%{text}',
                    textfont={"size": 14, "family": "Plus Jakarta Sans"}, showscale=False
                ))
                fig4.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#94a3b8', family="Plus Jakarta Sans"),
                    margin=dict(t=20, b=50, l=100, r=20),
                    xaxis=dict(title=""), yaxis=dict(title="")
                )
                confusionJSON = json.dumps(fig4, cls=plotly.utils.PlotlyJSONEncoder)
            else:
                confusionJSON = None
        else:
            # Fallback if metrics file not found
            comparison_df = pd.DataFrame({"Model": ["No metrics"], "Metric": ["N/A"], "Score": [0]})
            fig3 = px.bar(comparison_df, x="Model", y="Score")
            modelJSON = json.dumps(fig3, cls=plotly.utils.PlotlyJSONEncoder)
            confusionJSON = None

        # SEND **ALL FOUR** JSON objects to HTML
        return render_template(
            "dashboard.html",
            total_records=total,
            high_risk_pct=high_pct,
            low_risk_pct=low_pct,
            graphJSON=graphJSON,
            featureJSON=featureJSON,
            modelJSON=modelJSON,
            confusionJSON=confusionJSON
        )

    except Exception as e:
        return f"Dashboard Error: {str(e)}"

class FinguardReport(fpdf.FPDF):
    def header(self):
        # Header background
        self.set_fill_color(2, 6, 23)  # Dark background
        self.rect(0, 0, 210, 40, 'F')
        
        # Title
        self.set_font('Helvetica', 'B', 24)
        self.set_text_color(255, 255, 255)
        self.set_y(10)
        self.cell(0, 12, 'FinGuard Enterprise', ln=True, align='C')
        
        self.set_font('Helvetica', 'I', 10)
        self.set_text_color(200, 200, 200)
        self.cell(0, 8, 'Institutional Credit Risk Mandate', ln=True, align='C')
        self.ln(15)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f'Page {self.page_no()} | {datetime.now().strftime("%Y-%m-%d %H:%M")} | Generated by AI Governance Alpha', align='C')

@app.route("/download_report/<int:application_id>")
def download_report(application_id):
    # Ensure user is logged in
    if "role" not in session:
        return redirect("/")

    conn = get_db_connection()
    cur = conn.cursor()
    
    # Secure check: Users can only download their own reports, Bankers/Admins can download any
    query = "SELECT a.*, u.username FROM applications a JOIN users u ON a.user_id = u.id WHERE a.application_id = %s"
    params = [application_id]
    
    if session["role"] == "user":
        query += " AND a.user_id = %s"
        params.append(session["user_id"])
        
    cur.execute(query, params)
    data = cur.fetchone()
    conn.close()

    # --- Robust PDF Generation Engine ---
    def clean_text(text):
        """Ensures text is compatible with standard PDF fonts (Latin-1)."""
        if not text: return ""
        # Explicitly handle common special characters that cause PDF crashes
        text = str(text)
        text = text.replace('₹', 'INR').replace('â‚¹', 'INR') # Handle Rupee symbol variants
        text = text.replace('–', '-').replace('—', '-')     # Handle long dashes
        text = text.replace('“', '"').replace('”', '"')     # Handle smart quotes
        text = text.replace('‘', "'").replace('’', "'")
        
        # Final safety filter: Force into Latin-1 (the encoding supported by Helvetica/Arial)
        try:
            return text.encode('latin-1', 'replace').decode('latin-1')
        except Exception:
            return "???"

    # Generate PDF
    try:
        # Check if data exists
        if not data:
            return "Mandate not found or access denied.", 404

        pdf = FinguardReport()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        
        # Section: Identity
        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_text_color(79, 70, 229) # Primary indigo
        pdf.cell(0, 10, clean_text("1. IDENTITY & MANDATE OVERVIEW"), ln=True)
        pdf.set_font('Helvetica', '', 11)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(50, 8, clean_text("Identity Name:"), border=0)
        pdf.cell(0, 8, clean_text(data['username']), ln=True)
        pdf.cell(50, 8, clean_text("Application Ref:"), border=0)
        pdf.cell(0, 8, clean_text(f"#MANDATE-{data['application_id']}"), ln=True)
        pdf.cell(50, 8, clean_text("Submission Time:"), border=0)
        pdf.cell(0, 8, clean_text(str(data['created_at'])), ln=True)
        pdf.ln(5)

        # Section: Fiscal Metrics
        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_text_color(79, 70, 229)
        pdf.cell(0, 10, clean_text("2. FISCAL EXPOSURE METRICS"), ln=True)
        pdf.set_font('Helvetica', '', 11)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(50, 8, clean_text("Declared Income:"), border=0)
        pdf.cell(0, 8, clean_text(f"INR {data['income']:,.2f}"), ln=True)
        pdf.cell(50, 8, clean_text("Requested Limit:"), border=0)
        pdf.cell(0, 8, clean_text(f"INR {data['loan_amount']:,.2f}"), ln=True)
        pdf.ln(5)

        # Section: AI Assessment
        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_text_color(79, 70, 229)
        pdf.cell(0, 10, clean_text("3. AI SYSTEM DIAGNOSIS"), ln=True)
        pdf.set_font('Helvetica', 'B', 12)
        
        if data['risk_level'] == 'Low Risk':
            pdf.set_text_color(16, 185, 129)
        else:
            pdf.set_text_color(239, 68, 68)
            
        pdf.cell(50, 10, clean_text("System Verdict:"), border=0)
        pdf.cell(0, 10, clean_text(data['risk_level']), ln=True)
        
        pdf.set_font('Helvetica', '', 11)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(50, 8, clean_text("System Credit Score:"), border=0)
        pdf.set_font('Helvetica', 'B', 11)
        pdf.cell(0, 8, clean_text(f"{data['credit_score']} / 850"), ln=True)
        pdf.set_font('Helvetica', '', 11)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(50, 8, clean_text("AI Probability:"), border=0)
        pdf.cell(0, 8, clean_text(f"{round(data['probability']*100, 2)}%"), ln=True)
        
        pdf.set_font('Helvetica', 'B', 11)
        pdf.cell(50, 8, clean_text("AI Reasoning:"), border=0)
        pdf.ln(8)
        pdf.set_font('Helvetica', 'I', 10)
        pdf.multi_cell(0, 6, clean_text(data['system_explanation'] or "No system metadata provided."))
        pdf.ln(5)

        # Section: Banker Decision
        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_text_color(79, 70, 229)
        pdf.cell(0, 10, clean_text("4. INSTITUTIONAL FINAL DECISION"), ln=True)
        pdf.set_font('Helvetica', 'B', 12)
        
        status_colors = {'Approved': (16, 185, 129), 'Rejected': (239, 68, 68), 'Pending': (245, 158, 11)}
        pdf.set_text_color(*status_colors.get(data['status'], (0,0,0)))
        pdf.cell(50, 10, clean_text("Final Status:"), border=0)
        pdf.cell(0, 10, clean_text(data['status']), ln=True)
        
        pdf.set_font('Helvetica', '', 11)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(50, 8, clean_text("Officer Remarks:"), border=0)
        pdf.ln(8)
        pdf.set_font('Helvetica', 'I', 10)
        pdf.multi_cell(0, 6, clean_text(data['banker_reason'] or "Pending officer review."))

        # Watermark
        pdf.set_font('Helvetica', 'B', 60)
        pdf.set_text_color(240, 240, 240)
        try:
            pdf.rotate(45, 100, 150)
            pdf.text(50, 190, "FINGUARD OFFICIAL")
            pdf.rotate(0)
        except Exception:
            pass # Skip watermark if rotation fails

        # --- Binary Output Handling ---
        try:
            # First try used for fpdf 1.7.x (installed in environment) to prevent printing to stdout
            pdf_output = pdf.output(dest='S')
        except TypeError:
            # Fallback for fpdf2 which removed 'dest' parameter
            pdf_output = pdf.output()
        if isinstance(pdf_output, str):
            pdf_bytes = pdf_output.encode('latin-1')
        else:
            pdf_bytes = bytes(pdf_output)

        # Build Response directly with binary data
        response = make_response(pdf_bytes)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=Finguard_Report_{application_id}.pdf'
        response.headers['Content-Length'] = len(pdf_bytes)
        return response

    except Exception as e:
        print(f"CRITICAL PDF ERROR: {str(e)}")
        # Return a clean error message that won't be mistaken for a broken PDF
        return f"Protocol Error: Could not generate mandate report. details: {str(e)}", 500


@app.route("/admin_logout")
def admin_logout():
    return redirect(url_for("logout"))



# ------------------ PREDICTION LOGIC ------------------
def run_prediction_logic(data):
    df = pd.DataFrame([data])

    for col in df.columns:
        if col not in categorical_cols:
            df[col] = df[col].astype(float)

    for col in categorical_cols:
        df[col] = encoders[col].transform(df[col])

    df = df[feature_names]
    scaled = scaler.transform(df)

    prob = model.predict_proba(scaled)[0][1]
    risk = "High Risk" if prob > MODEL_THRESHOLD else "Low Risk"

    return risk, round(float(prob), 4)

def generate_explanation(data, risk, prob):
    """
    Generates a human-friendly explanation for the prediction.
    """
    reasons = []
    income = data.get("AMT_INCOME_TOTAL", 0)
    loan = data.get("AMT_CREDIT", 0)
    ratio = loan / income if income > 0 else 10
    
    if risk == "High Risk":
        if ratio > 5:
            reasons.append(f"High loan-to-income ratio ({ratio:.1f}x).")
        if data.get("DAYS_BIRTH", 0) > -10000: # Younger than ~27
            reasons.append("Applicant is in a younger age demographic linked to higher volatility.")
        if prob > 0.7:
            reasons.append("Multiple historical indicators suggest potential repayment challenges.")
        if not reasons:
            reasons.append("Combined financial metrics exceed the safety threshold for low-risk classification.")
    else:
        if ratio < 2:
            reasons.append("Very healthy income-to-loan ratio.")
        if data.get("DAYS_BIRTH", 0) < -15000: # Older than ~41
            reasons.append("Mature applicant profile with stable demographic history.")
        reasons.append("Overall financial stability meets institutional standards.")

    return " ".join(reasons)

# ------------------ DATA ENRICH ------------------
def enrich_user_data(user_input):
    loan_amount = user_input["AMT_CREDIT"]

    return {
        # -------- USER INPUT --------
        "AMT_INCOME_TOTAL": user_input["AMT_INCOME_TOTAL"],
        "AMT_CREDIT": loan_amount,
        "DAYS_BIRTH": user_input["DAYS_BIRTH"],
        "ORGANIZATION_TYPE": user_input["ORGANIZATION_TYPE"],
        "OCCUPATION_TYPE": user_input["OCCUPATION_TYPE"],

        # -------- REQUIRED MODEL FEATURES --------
        "AMT_ANNUITY": loan_amount / 12,
        "AMT_GOODS_PRICE": loan_amount,

        "DAYS_EMPLOYED": -1500,
        "DAYS_REGISTRATION": -3000,
        "DAYS_ID_PUBLISH": -2000,
        "DAYS_LAST_PHONE_CHANGE": -500,         
        "OWN_CAR_AGE": 0,                         
        "REGION_POPULATION_RELATIVE": 0.02,      

        "OBS_30_CNT_SOCIAL_CIRCLE": 2,
        "AMT_REQ_CREDIT_BUREAU_YEAR": 1,

        # -------- EXTERNAL SOURCES --------
        "EXT_SOURCE_1": 0.5,
        "EXT_SOURCE_2": 0.5,
        "EXT_SOURCE_3": 0.5,

        # -------- TIME FEATURES --------
        "WEEKDAY_APPR_PROCESS_START": datetime.now().strftime("%A").upper(),
        "HOUR_APPR_PROCESS_START": datetime.now().hour
    }

# ------------------ USER MANAGEMENT ROUTES ------------------
@app.route("/manage_users")
@role_required("admin")
def admin_manage_users():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, username, email, role, created_at FROM users")
    users = cur.fetchall()
    conn.close()
    return render_template("manage_users.html", users=users)

@app.route("/update_user_role", methods=["POST"])
@role_required("admin")
def admin_update_role():
    user_id = request.form.get("user_id")
    new_role = request.form.get("role")
    
    # Prevent creating multiple admins
    if new_role == "admin":
        flash("Security Restriction: Cannot assign admin role. Only one admin is allowed in the system.", "danger")
        return redirect(url_for("admin_manage_users"))
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET role = %s WHERE id = %s", (new_role, user_id))
    conn.commit()
    conn.close()
    
    flash(f"User role updated successfully to {new_role}.", "success")
    return redirect(url_for("admin_manage_users"))

@app.route("/delete_user/<int:user_id>", methods=["POST"])
@role_required("admin")
def admin_delete_user(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Check if trying to delete admin
    cur.execute("SELECT role FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()
    
    if user and user['role'] == 'admin':
        flash("Security Restriction: Cannot delete the admin account.", "danger")
        conn.close()
        return redirect(url_for("admin_manage_users"))
    
    # Delete user
    cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
    conn.commit()
    conn.close()
    
    flash("User account has been permanently removed.", "success")
    return redirect(url_for("admin_manage_users"))

@app.route("/history")
@role_required("admin")
def history():
    df = fetch_applications()
    return render_template(
        "history.html",
        records=df.to_dict("records")
    )

@app.route("/export_csv")
@role_required("admin")
def export_csv():
    df = fetch_applications()
    
    # Create CSV in memory
    output = io.StringIO()
    df.to_csv(output, index=False)
    
    # Build response
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=finguard_audit_trail_export.csv"
    response.headers["Content-type"] = "text/csv"
    return response

# ------------------ PREDICT API ------------------
@app.route("/predict", methods=["POST"])
@role_required("user")
def predict():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No input data provided"}), 400

        # Ensure required fields exist even if not provided by minimal simulator
        required_fields = ["AMT_INCOME_TOTAL", "AMT_CREDIT", "age", "ORGANIZATION_TYPE", "OCCUPATION_TYPE"]
        for field in required_fields:
            if field not in data:
                 # Provide defaults or return error if critical
                 if field == "age": data["age"] = 30
                 elif field == "AMT_INCOME_TOTAL": data["AMT_INCOME_TOTAL"] = 50000
                 elif field == "AMT_CREDIT": data["AMT_CREDIT"] = 100000
                 else: return jsonify({"error": f"Missing required field: {field}"}), 400

        # Convert simple inputs to model-compatible negative days
        data["DAYS_BIRTH"] = -float(data["age"]) * 365
        
        # Enrich data with default features for the model
        full_data = enrich_user_data(data)
        
        # 🔹 ML Prediction
        income = float(data["AMT_INCOME_TOTAL"])
        loan = float(data["AMT_CREDIT"])
        
        # Override Logic
        if income > 0 and (loan / income) > 20:
             risk = "High Risk"
             probability = 0.95
        elif income < 20000 and loan > 500000:
             risk = "High Risk"
             probability = 0.92
        else:
             risk, probability = run_prediction_logic(full_data)

        # Credit Score & Recommendation
        credit_score = int(850 - (float(probability) * 550))
        credit_score = max(300, min(credit_score, 850))

        if credit_score >= 750:
            recommended_loan, interest_rate, tenure = "Up to 10 Lakhs", "8.5%", "20 Years"
        elif credit_score >= 650:
            recommended_loan, interest_rate, tenure = "Up to 5 Lakhs", "11%", "10 Years"
        else:
            recommended_loan, interest_rate, tenure = "Up to 1 Lakh", "15%", "3–5 Years"

        # Save record
        save_prediction(
            age=int(data["age"]),
            income=income,
            loan_amount=loan,
            prediction=risk,
            probability=float(probability),
            credit_score=credit_score,
            recommended_loan=recommended_loan,
            interest_rate=interest_rate,
            tenure=tenure
        )

        return jsonify({
            "risk_level": risk,
            "probability": round(float(probability), 4),
            "credit_score": credit_score,
            "recommended_loan": recommended_loan,
            "interest_rate": interest_rate,
            "tenure": tenure
        })

    except Exception as e:
        print(f"PREDICTION API ERROR: {e}")
        return jsonify({"error": "Internal diagnostic system failure. Verification failed."}), 500
    
    
@app.route("/check_credit_risk")
@role_required("user")
def check_credit_risk():
    return render_template("credit_risk.html")

@app.route("/user_dashboard")
@role_required("user")
def user_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Fetch total applications
    cursor.execute("SELECT COUNT(*) as total FROM applications WHERE user_id = %s", (session["user_id"],))
    count_data = cursor.fetchone()
    app_count = count_data['total'] if count_data else 0
    
    # Fetch latest credit score
    cursor.execute("""
        SELECT credit_score FROM applications 
        WHERE user_id = %s 
        ORDER BY created_at DESC LIMIT 1
    """, (session["user_id"],))
    score_data = cursor.fetchone()
    last_score = score_data['credit_score'] if score_data else "N/A"
    
    conn.close()
    
    return render_template(
        "user_dashboard.html", 
        app_count=app_count,
        last_score=last_score
    )


# ------------------ RUN ------------------
if __name__ == "__main__":
    app.run(debug=True)
