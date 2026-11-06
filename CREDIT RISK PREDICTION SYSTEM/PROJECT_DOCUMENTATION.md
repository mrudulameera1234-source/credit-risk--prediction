# FinGuard - Enterprise Credit Risk Prediction System
### *AI-Powered Application for Financial Mandate Assessment*

## 📌 Project Overview
FinGuard is a comprehensive, enterprise-grade credit risk assessment platform designed for banks and financial institutions. It leverages Machine Learning (XGBoost) and AI-driven document verification (OCR) to evaluate loan applications, predict default probability, and assign credit scores (300-850).

The system supports a **Multi-Bank Architecture**, allowing multiple banking institutions (SBI, HDFC, ICICI, etc.) to operate on a single platform with segregated data and workflows.

---

## 🛠 Technology Stack
- **Backend:** Python (Flask)
- **Database:** MySQL 8.0 (Relational Data Model)
- **Machine Learning:** XGBoost, Scikit-Learn
- **Document AI:** Tesseract OCR (for Salary Slips)
- **Frontend:** HTML5, CSS3, JavaScript (Glassmorphism Design)
- **Security:** Bcrypt Hashing, Role-Based Access Control (RBAC)

---

## 📂 Project Structure
```
CREDIT RISK PREDICTION SYSTEM/
├── app.py                 # Main application entry point (Routes & Logic)
├── db_connection.py       # Database connection & initialization
├── config.py              # Configuration settings (DB credentials, Keys)
├── train.py               # ML Model Training Script (Generates models)
├── requirements.txt       # Python dependencies
├── model02.joblib         # Trained XGBoost Model
├── scaler_1.pkl           # Data Scaler
├── encoders_1.pkl         # Label Encoders
├── data/                  # Dataset folder
│   └── application.csv    # Historical credit data
├── static/                # CSS, Images, JS assets
├── templates/             # HTML Templates (Jinja2)
└── uploads/               # Temporary storage for uploaded documents
```

---

## 🚀 How It Works (Workflow)

### 1. **User Role (Borrower)**
1.  **Registration/Login:** User creates an account.
2.  **Dashboard:** Views current application status (Pending/Approved/Rejected).
3.  **Apply for Loan:**
    - Fills financial details (Income, Employment, Age).
    - Selects **Target Bank** (e.g., SBI, HDFC).
    - **Uploads Salary Slip:** System performs *OCR* to extract and verify income automatically.
4.  **AI Analysis:** System runs ML model to predict:
    - **Risk Level:** (Low/High)
    - **Probability of Default:** (%)
    - **Credit Score:** (300-850)
5.  **Tracking:** User sees real-time updates from the bank.

### 2. **Banker Role (Credit Officer)**
1.  **Login:** Banker logs in (mapped to a specific bank, e.g., SBI Admin).
2.  **Bank Dashboard:** Sees *only* applications submitted to their bank.
3.  **Review Process:**
    - Updates Status (`Approved` / `Rejected`).
    - Adds Remarks ("Insufficient collateral", "Authorized").
    - System prevents approving high-risk applicants without reason.
4.  **Notifications:** System triggers email alerts to the user upon decision.

### 3. **Admin Role (System Administrator)**
1.  **Governance:** View global audit trail of all applications across all banks.
2.  **User Management:** Manage identities.
3.  **Single Admin Policy:** System enforces strict security (only 1 Admin allowed).
4.  **Audit:** Export data logs for compliance.

---

## 🤖 Machine Learning Pipeline (`train.py`)
The system uses `train.py` to regenerate the predictive models.
1.  **Data Loading:** Reads `data/application.csv`.
2.  **Preprocessing:**
    - Handles missing values.
    - Encodes categorical variables (Organization Type, Occupation).
    - Scales numerical features.
3.  **Training:** Fits an **XGBoost Classifier** on the processed data.
4.  **Artifact Generation:** Saves `.pkl` and `.joblib` files for the web app to use.

---

## ⚙️ How to Run
1.  **Install Requirements:**
    ```bash
    pip install -r requirements.txt
    ```
2.  **Setup Database:** 
    Ensure MySQL is running and `db_connection.py` config is correct.
3.  **Train Model (Optional):**
    ```bash
    python train.py
    ```
4.  **Run Application:**
    ```bash
    python app.py
    ```
5.  **Access:** Open `http://127.0.0.1:5000` in your browser.

---

## 🔐 Security Features
- **Duplicate Prevention:** Users blocked from applying to a bank if they have a generic *Pending* or *Active* loan.
- **Role Isolation:** Bankers cannot see other banks' data.
- **Password Security:** All passwords hashed with Bcrypt.
