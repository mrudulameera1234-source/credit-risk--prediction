
-- =========================================================
-- CREDIT RISK PREDICTION SYSTEM: DATABASE SCHEMA
-- Version: 3.0 (Enterprise Protocol)
-- =========================================================

CREATE DATABASE IF NOT EXISTS credit_risk;
USE credit_risk;

-- 1. Users Table
-- Stores all authentication data, roles, and identity for OCR verification.
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    full_name VARCHAR(100) NOT NULL,              -- Critical for Salary Slip Verification
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'user', 'bank') DEFAULT 'user',
    reset_token VARCHAR(100) DEFAULT NULL,
    reset_token_expiry DATETIME DEFAULT NULL,
    bank_affiliation VARCHAR(100) DEFAULT NULL,    -- For banker accounts
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Applications Table
-- Stores official loan mandates submitted for institutional review.
CREATE TABLE IF NOT EXISTS applications (
    application_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    
    -- Financial Data
    income FLOAT NOT NULL,
    loan_amount FLOAT NOT NULL,
    
    -- AI Prediction Engine Outputs
    risk_level VARCHAR(20),                       -- 'High Risk', 'Low Risk'
    probability FLOAT,                            -- Confidence Score (0-1)
    credit_score INT,                             -- Synthetic Credit Score (300-850)
    system_explanation TEXT,                      -- ML Logic Explanation
    
    -- Dynamic Loan Terms
    recommended_loan VARCHAR(50),
    interest_rate VARCHAR(10),
    tenure VARCHAR(20),
    
    -- Business Workflow
    bank_name VARCHAR(100),                        -- Selected Bank for mandate
    status ENUM('Pending', 'Approved', 'Rejected') DEFAULT 'Pending',
    banker_reason TEXT,                            -- Remarks from Human Reviewer
    banker_id INT,                                 -- ID of Reviewer
    
    -- OCR Verification Data
    salary_slip VARCHAR(255),                      -- Secure binary path
    salary_verified VARCHAR(10) DEFAULT 'No',       -- OCR Validation Status
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    decision_at DATETIME NULL,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 3. Predictions Table (Global Audit Trail)
-- Stores all risk analyses (including simulator tests) for Dashboard Analytics.
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
);

-- =========================================================
-- SYSTEM SEEDING: DEFAULT ACCOUNTS
-- =========================================================

-- Admin Account (Password: admin123)
-- Role: Access to Global Analytics & User Management
INSERT INTO users (username, full_name, email, password_hash, role) 
VALUES ('admin', 'System Administrator', 'admin@finguard.com', '$2b$12$4mU3vJ9zJqFz.r6.rY/J5.8zK0pLw.u2wY/W/m8X6n3g3g3g3g3g3g', 'admin')
ON DUPLICATE KEY UPDATE role='admin';

-- Bank Manager Accounts (Password for all: pass@123)
-- Role: Review Loan Mandates for specific banks
INSERT INTO users (username, full_name, email, password_hash, role) VALUES 
('sbi_admin', 'SBI Reviewer', 'sbi_admin@finguard.com', '$2b$12$K1R2Tf9pM9V9f9f9f9f9f.e/C/m8X6n3g3g3g3g3g3g3g3g3g3g', 'bank'),
('hdfc_admin', 'HDFC Reviewer', 'hdfc_admin@finguard.com', '$2b$12$K1R2Tf9pM9V9f9f9f9f9f.e/C/m8X6n3g3g3g3g3g3g3g3g3g3g', 'bank'),
('icici_admin', 'ICICI Reviewer', 'icici_admin@finguard.com', '$2b$12$K1R2Tf9pM9V9f9f9f9f9f.e/C/m8X6n3g3g3g3g3g3g3g3g3g3g', 'bank'),
('axis_admin', 'Axis Reviewer', 'axis_admin@finguard.com', '$2b$12$K1R2Tf9pM9V9f9f9f9f9f.e/C/m8X6n3g3g3g3g3g3g3g3g3g3g', 'bank'),
('pnb_admin', 'PNB Reviewer', 'pnb_admin@finguard.com', '$2b$12$K1R2Tf9pM9V9f9f9f9f9f.e/C/m8X6n3g3g3g3g3g3g3g3g3g3g', 'bank'),
('bob_admin', 'BOB Reviewer', 'bob_admin@finguard.com', '$2b$12$K1R2Tf9pM9V9f9f9f9f9f.e/C/m8X6n3g3g3g3g3g3g3g3g3g3g', 'bank');
-- Note: Use initialize_bankers.py for generating exact local bcrypt hashes.

