import pymysql
import bcrypt
import pandas as pd
from config import DB_CONFIG

def init_db():
    """
    Institutional Database Initialization Engine.
    Creates all necessary tables for Users, Loan Applications, and Risk Predictions.
    """
    conn = pymysql.connect(
        host=DB_CONFIG["host"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"]
    )
    cursor = conn.cursor()

    # Create Database
    cursor.execute("CREATE DATABASE IF NOT EXISTS credit_risk")
    conn.commit()
    conn.select_db(DB_CONFIG["database"])

    # 1. Users Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            full_name VARCHAR(100) NOT NULL,
            email VARCHAR(120) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role ENUM('admin', 'user', 'bank') DEFAULT 'user',
            reset_token VARCHAR(100) DEFAULT NULL,
            reset_token_expiry DATETIME DEFAULT NULL,
            bank_affiliation VARCHAR(100) DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2. Applications Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            application_id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            income FLOAT NOT NULL,
            loan_amount FLOAT NOT NULL,
            risk_level VARCHAR(20),
            probability FLOAT,
            credit_score INT,
            recommended_loan VARCHAR(50),
            interest_rate VARCHAR(10),
            tenure VARCHAR(20),
            status ENUM('Pending', 'Approved', 'Rejected') DEFAULT 'Pending',
            system_explanation TEXT,
            banker_reason TEXT,
            banker_id INT,
            bank_name VARCHAR(100),
            salary_slip VARCHAR(255),
            salary_verified VARCHAR(10) DEFAULT 'No',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            decision_at DATETIME NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # 3. Predictions Table (Global Audit Trail)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            age INT,
            income FLOAT,
            loan_amount FLOAT,
            prediction VARCHAR(50),
            probability FLOAT,
            credit_score INT,
            recommended_loan VARCHAR(50),
            interest_rate VARCHAR(10),
            tenure VARCHAR(20),
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    
    # 🔹 AUTO-SEEDING: Create Default Identity Accounts
    print("Seeding institutional accounts...")
    def seed_user(user, name, email, pwd, role, affiliation=None):
        hashed = bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()
        # Use INSERT ... ON DUPLICATE KEY UPDATE to ensure affiliation is set even if user exists
        query = """
            INSERT INTO users (username, full_name, email, password_hash, role, bank_affiliation) 
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE bank_affiliation = VALUES(bank_affiliation)
        """
        cursor.execute(query, (user, name, email, hashed, role, affiliation))

    # Admin
    seed_user('admin', 'System Administrator', 'admin@finguard.com', 'admin123', 'admin')
    
    # Regional Bankers
    bank_pass = "pass@123"
    seed_user('sbi_admin', 'SBI Reviewer', 'sbi@finguard.com', bank_pass, 'bank', 'State Bank of India')
    seed_user('hdfc_admin', 'HDFC Reviewer', 'hdfc@finguard.com', bank_pass, 'bank', 'HDFC Bank')
    seed_user('icici_admin', 'ICICI Reviewer', 'icici@finguard.com', bank_pass, 'bank', 'ICICI Bank')
    seed_user('axis_admin', 'Axis Reviewer', 'axis@finguard.com', bank_pass, 'bank', 'Axis Bank')
    seed_user('pnb_admin', 'PNB Reviewer', 'pnb@finguard.com', bank_pass, 'bank', 'Punjab National Bank')
    seed_user('bob_admin', 'BOB Reviewer', 'bob@finguard.com', bank_pass, 'bank', 'Bank of Baroda')

    conn.commit()
    conn.close()
    print("Success: Database 'credit_risk' initialized and seeded with 7 official accounts.")

def save_prediction(age, income, loan_amount, prediction, probability, credit_score=None, recommended_loan=None, interest_rate=None, tenure=None):
    """Saves a risk analysis record to the global audit trail."""
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    query = """
        INSERT INTO predictions
        (age, income, loan_amount, prediction, probability,
         credit_score, recommended_loan, interest_rate, tenure)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    cursor.execute(query, (age, income, loan_amount, prediction, probability, credit_score, recommended_loan, interest_rate, tenure))
    conn.commit()
    conn.close()

def fetch_predictions():
    """Fetches all prediction records for the Admin Dashboard."""
    conn = pymysql.connect(**DB_CONFIG)
    df = pd.read_sql("SELECT * FROM predictions", conn)
    conn.close()
    return df

def create_user(username, password, full_name=None, email=None, role='user'):
    """Creates a new enterprise user with a hashed password."""
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    
    # Defaults for internal scripts
    if not full_name: full_name = username
    if not email: email = f"{username}@finguard.com"
    
    try:
        cursor.execute(
            "INSERT INTO users (username, full_name, email, password_hash, role) VALUES (%s, %s, %s, %s, %s)",
            (username, full_name, email, hashed_password, role)
        )
        conn.commit()
        return True
    except pymysql.err.IntegrityError:
        return False
    finally:
        conn.close()

def verify_password(username, password):
    """Verifies user credentials using bcrypt."""
    conn = pymysql.connect(**DB_CONFIG)
    cur = conn.cursor(pymysql.cursors.DictCursor)
    cur.execute("SELECT password_hash FROM users WHERE username=%s", (username,))
    user = cur.fetchone()
    conn.close()
    if not user: return False
    return bcrypt.checkpw(password.encode(), user["password_hash"].encode())

if __name__ == "__main__":
    init_db()