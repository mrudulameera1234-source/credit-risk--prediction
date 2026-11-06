"""
Configuration file for Credit Risk Prediction System
Store database credentials and Flask settings here.
"""

# MySQL Database Configuration
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "#circle@1405#",  # Change this to your MySQL password
    "database": "credit_risk"
}

# Flask Configuration
FLASK_SECRET_KEY = "my_super_secret_key_123_change_in_production"  # Change this in production

# Model Configuration
MODEL_THRESHOLD = 0.35  # Decision threshold for risk classification

