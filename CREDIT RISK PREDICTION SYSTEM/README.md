# FinGuard: Credit Risk Prediction System 🛡️

An advanced, enterprise-grade AI solution for predicting credit risk using Machine Learning and automated Salary Slip verification (OCR).

---

## 🚀 Student Handover Guide

Welcome to the **FinGuard** project! This system is designed to simulate a professional banking Environment. To get started, follow the instructions below carefully.

### 📦 1. Initial Setup (From ZIP)
1.  **Extract**: Extract the project folder to a location on your drive (e.g., `C:\credit-risk-system`).
2.  **Verify Files**: High-level structure:
    *   `app.py`: Main Flask application.
    *   `db_connection.py`: Database management engine.
    *   `model02.joblib`: The trained Machine Learning model.
    *   `templates/`: UI components.
    *   `uploads/`: Storage for submitted salary slips.

### 🐍 2. Python Environment
Ensure you have Python 3.9+ installed.
1.  **Open Terminal**: Navigate to the project folder.
2.  **Create Virtual Environment**:
    ```bash
    python -m venv .venv
    ```
3.  **Activate Environment**:
    *   Windows: `.venv\Scripts\activate`
    *   Mac/Linux: `source .venv/bin/activate`
4.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

### 👁️ 3. OCR Engine Installation (CRITICAL for Images)
The system uses **Tesseract OCR** to read text from `.png` and `.jpg` salary slips. 
1.  **Download**: [Tesseract OCR for Windows](https://github.com/UB-Mannheim/tesseract/wiki).
2.  **Install**: Run the installer. Use the default path: `C:\Program Files\Tesseract-OCR`.
3.  **Note**: If you do not install Tesseract, you must upload salary slips in **PDF format** (PDF reading is built-in and does not require Tesseract).

### 🗄️ 4. Database Configuration (MySQL)
1.  **Open MySQL Workbench**: Log in to your local instance.
2.  **Connect**: Open `config.py` and update the `DB_CONFIG` credentials (host, user, password) to match your local setup.
3.  **Initialize**: Run the initialization script to create the database and tables automatically:
    ```bash
    python db_connection.py
    ```

### 🏁 5. Running the Application
Once the database is ready, launch the server:
```bash
python app.py
```
Visit: **`http://127.0.0.1:5000`**

---

## 👤 Default Credentials
*   **Admin Console**: `admin` / `admin123`
*   **Banker Portals** (Password for all: `pass@123`):
    *   SBI: `sbi_admin`
    *   HDFC: `hdfc_admin`
    *   ICICI: `icici_admin`
    *   Axis: `axis_admin`
    *   PNB: `pnb_admin`
    *   Bank of Baroda: `bob_admin`
*   **User Access**: Create your own account via the "Register" page.

## 🛠️ Key Features for Students to Study
1.  **Machine Learning**: `run_prediction_logic()` in `app.py` handles the Random Forest classification.
2.  **OCR Verification**: See `extract_text_from_pdf` and `extract_text_from_image` functions.
3.  **Authentication**: Modern password security using `bcrypt` and `Session` management.
4.  **CSRF Security**: Protective tokens enabled on all institutional forms.

---
**Institutional Standard Protocol Active.**
