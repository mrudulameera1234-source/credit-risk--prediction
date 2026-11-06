import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, classification_report
import os
import json

# Configuration
DATA_PATH = "data/application.csv"
MODEL_PATH = "model02.joblib"
SCALER_PATH = "scaler_1.pkl"
ENCODER_PATH = "encoders_1.pkl"
FEATURE_NAMES_PATH = "feature_names_1.pkl"

def train_model():
    print("🚀 Starting Model Training Pipeline...")

    # 1. Load Data
    if not os.path.exists(DATA_PATH):
        print(f"❌ Error: Dataset not found at {DATA_PATH}")
        return

    print("📊 Loading dataset...")
    df = pd.read_csv(DATA_PATH)
    
    # Use a subset for faster training if dataset is huge, or full dataset
    # df = df.sample(n=50000, random_state=42) 

    # 2. Preprocessing
    print("🧹 Preprocessing data...")
    
    # Target variable
    target = 'TARGET'
    
    # Define features based on app.py usage + common features
    # (Simplified feature set for demonstration, aligning with app inputs)
    features = [
        'AMT_INCOME_TOTAL', 'AMT_CREDIT', 'AMT_ANNUITY', 'AMT_GOODS_PRICE',
        'DAYS_BIRTH', 'DAYS_EMPLOYED', 'DAYS_REGISTRATION', 'DAYS_ID_PUBLISH',
        'DAYS_LAST_PHONE_CHANGE', 'OWN_CAR_AGE', 'REGION_POPULATION_RELATIVE',
        'OBS_30_CNT_SOCIAL_CIRCLE', 'AMT_REQ_CREDIT_BUREAU_YEAR',
        'EXT_SOURCE_1', 'EXT_SOURCE_2', 'EXT_SOURCE_3',
        'ORGANIZATION_TYPE', 'OCCUPATION_TYPE', 'WEEKDAY_APPR_PROCESS_START',
        'HOUR_APPR_PROCESS_START'
    ]
    
    # Filter only available columns
    available_features = [f for f in features if f in df.columns]
    X = df[available_features]
    y = df[target]

    # Handle Missing Values
    print("filling missing values...")
    # Numerical Imputer
    num_cols = X.select_dtypes(include=['int64', 'float64']).columns
    cat_cols = X.select_dtypes(include=['object']).columns

    imputer = SimpleImputer(strategy='median')
    X[num_cols] = imputer.fit_transform(X[num_cols])

    # 3. Encoding
    print("🔠 Encoding categorical variables...")
    encoders = {}
    for col in cat_cols:
        le = LabelEncoder()
        # Handle nan/unknown by filling first
        X[col] = X[col].fillna("Unknown").astype(str)
        X[col] = le.fit_transform(X[col])
        encoders[col] = le
    
    # 4. Scaling
    print("⚖️ Scaling numerical features...")
    scaler = StandardScaler()
    X[num_cols] = scaler.fit_transform(X[num_cols])

    # 5. Split Data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # 6. Train XGBoost
    print("🧠 Training XGBoost Model...")
    model = XGBClassifier(
        n_estimators=100, 
        learning_rate=0.1, 
        max_depth=5, 
        use_label_encoder=False, 
        eval_metric='logloss'
    )
    model.fit(X_train, y_train)

    # 7. Evaluate
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"✅ Model Training Complete. Accuracy: {acc:.4f}")
    print(classification_report(y_test, y_pred))

    # 8. Save Artifacts
    print("💾 Saving artifacts...")
    joblib.dump(model, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    joblib.dump(encoders, ENCODER_PATH)
    joblib.dump(list(X.columns), FEATURE_NAMES_PATH)
    
    # Save metrics
    metrics = {"accuracy": acc}
    with open("model_metrics.json", "w") as f:
        json.dump(metrics, f)

    print("🎉 All files saved successfully!")

if __name__ == "__main__":
    try:
        train_model()
    except Exception as e:
        print(f"❌ Error during training: {str(e)}")
