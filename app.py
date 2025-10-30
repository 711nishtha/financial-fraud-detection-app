from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import joblib
import numpy as np
import pandas as pd
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)

# Load model and scaler
MODEL_PATH = 'model/fraud_detection_model.pkl'
SCALER_PATH = 'model/feature_scaler.pkl'

# Optimal threshold from business analysis (maximizes net savings)
OPTIMAL_THRESHOLD = 0.1

print("Loading model and scaler...")
try:
    model = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    print("✅ Model and scaler loaded successfully!")
    print(f"✅ Model type: {type(model).__name__}")
    print(f"✅ Using optimal fraud threshold: {OPTIMAL_THRESHOLD}")
except Exception as e:
    print(f"❌ Error loading model: {e}")
    model = None
    scaler = None

# Feature engineering function (matches your notebook exactly)
def engineer_features(data):
    """
    Create all engineered features exactly as in the training notebook
    """
    # Extract base features
    amount = data['amount']
    old_balance_orig = data['oldbalanceOrg']
    new_balance_orig = data['newbalanceOrig']
    old_balance_dest = data['oldbalanceDest']
    new_balance_dest = data['newbalanceDest']
    transaction_type = data['type']
    
    # Use current hour as step (or you can pass it from frontend)
    step = datetime.now().hour
    
    # Derived features - Balance changes
    balance_diff_orig = old_balance_orig - new_balance_orig
    balance_diff_dest = new_balance_dest - old_balance_dest
    
    # Derived features - Ratios
    amount_to_oldbalance_orig_ratio = amount / (old_balance_orig + 1)
    amount_to_oldbalance_dest_ratio = amount / (old_balance_dest + 1)
    
    # Derived features - Indicators
    is_amount_rounded = 1 if (amount % 1000 == 0) else 0
    is_weekend = 1 if (step % 24 >= 18) else 0
    orig_balance_consistent = 1 if (balance_diff_orig == amount) else 0
    dest_balance_consistent = 1 if (balance_diff_dest == amount) else 0
    orig_zero_balance = 1 if (old_balance_orig == 0) else 0
    dest_zero_balance = 1 if (old_balance_dest == 0) else 0
    transaction_hour = step % 24
    
    # One-hot encode transaction types
    type_CASH_IN = 1 if transaction_type == 'CASH_IN' else 0
    type_CASH_OUT = 1 if transaction_type == 'CASH_OUT' else 0
    type_DEBIT = 1 if transaction_type == 'DEBIT' else 0
    type_PAYMENT = 1 if transaction_type == 'PAYMENT' else 0
    type_TRANSFER = 1 if transaction_type == 'TRANSFER' else 0
    
    # Customer type indicators (simplified - assuming C2C for non-payment types)
    orig_is_customer = 1
    dest_is_customer = 1 if transaction_type != 'PAYMENT' else 0
    orig_is_merchant = 0
    dest_is_merchant = 1 if transaction_type == 'PAYMENT' else 0
    
    # Customer interaction patterns
    c_to_c = 1 if (orig_is_customer == 1 and dest_is_customer == 1) else 0
    c_to_m = 1 if (orig_is_customer == 1 and dest_is_merchant == 1) else 0
    m_to_c = 0  # Merchants don't originate transactions in this model
    
    # Create feature array in exact order (29 features)
    features = [
        step,
        amount,
        old_balance_orig,
        new_balance_orig,
        old_balance_dest,
        new_balance_dest,
        balance_diff_orig,
        balance_diff_dest,
        amount_to_oldbalance_orig_ratio,
        amount_to_oldbalance_dest_ratio,
        is_amount_rounded,
        is_weekend,
        orig_balance_consistent,
        dest_balance_consistent,
        orig_zero_balance,
        dest_zero_balance,
        transaction_hour,
        type_CASH_IN,
        type_CASH_OUT,
        type_DEBIT,
        type_PAYMENT,
        type_TRANSFER,
        orig_is_customer,
        dest_is_customer,
        orig_is_merchant,
        dest_is_merchant,
        c_to_c,
        c_to_m,
        m_to_c
    ]
    
    return np.array(features).reshape(1, -1)

# Risk level calculation
def calculate_risk_level(probability):
    """Determine risk level based on fraud probability"""
    if probability >= 0.7:
        return "High"
    elif probability >= 0.4:
        return "Medium"
    else:
        return "Low"

# ===== PAGE ROUTES =====

# Home route - Interactive demo
@app.route('/')
def home():
    return render_template('index.html')

# Analysis page - Data insights & patterns
@app.route('/analysis')
def analysis():
    return render_template('analysis.html')

# Performance page - Model metrics & comparisons
@app.route('/performance')
def performance():
    return render_template('performance.html')

# Business page - Financial impact & ROI
@app.route('/business')
def business():
    return render_template('business.html')

# Methodology page - Technical showcase (WOW FACTOR)
@app.route('/methodology')
def methodology():
    return render_template('methodology.html')

# About page - Project story & journey
@app.route('/about')
def about():
    return render_template('about.html')

# ===== API ROUTES =====

# Prediction endpoint
@app.route('/predict', methods=['POST'])
def predict():
    try:
        # Check if model is loaded
        if model is None:
            return jsonify({
                'error': 'Model not loaded. Please check server logs.'
            }), 500
        
        # Get JSON data from request
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['amount', 'type', 'oldbalanceOrg', 'newbalanceOrig', 
                          'oldbalanceDest', 'newbalanceDest']
        
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Validate transaction type
        valid_types = ['CASH_IN', 'CASH_OUT', 'DEBIT', 'PAYMENT', 'TRANSFER']
        if data['type'] not in valid_types:
            return jsonify({
                'error': f'Invalid transaction type. Must be one of: {", ".join(valid_types)}'
            }), 400
        
        # Engineer features
        features = engineer_features(data)
        
        # Make prediction (Random Forest/XGBoost trained on raw features)
        probability = model.predict_proba(features)[0]
        
        # Get fraud probability (class 1)
        fraud_probability = probability[1]
        
        # Use optimal threshold from business analysis
        # Threshold of 0.1 maximizes net savings according to notebook analysis
        prediction = 1 if fraud_probability >= OPTIMAL_THRESHOLD else 0
        prediction_label = "Fraud" if prediction == 1 else "Legitimate"
        
        # Calculate risk level
        risk_level = calculate_risk_level(fraud_probability)
        
        # Generate transaction ID
        transaction_id = f"TXN_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Log prediction details
        print(f"\n{'='*60}")
        print(f"🔍 TRANSACTION ANALYSIS:")
        print(f"   Type: {data['type']}")
        print(f"   Amount: ${data['amount']:,.2f}")
        print(f"   Fraud Probability: {fraud_probability:.4f} ({fraud_probability*100:.2f}%)")
        print(f"   Prediction: {prediction_label}")
        print(f"   Risk Level: {risk_level}")
        print(f"   Threshold Used: {OPTIMAL_THRESHOLD}")
        print(f"{'='*60}\n")
        
        # Prepare response
        response = {
            'prediction': prediction_label,
            'confidence': round(float(fraud_probability), 4),
            'risk_level': risk_level,
            'transaction_id': transaction_id,
            'details': {
                'amount': data['amount'],
                'type': data['type'],
                'timestamp': datetime.now().isoformat()
            }
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        print(f"\n❌ ERROR during prediction: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': f'Prediction failed: {str(e)}'
        }), 500

# Health check endpoint
@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'model_loaded': model is not None,
        'scaler_loaded': scaler is not None,
        'model_type': type(model).__name__ if model else None,
        'optimal_threshold': OPTIMAL_THRESHOLD
    }), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)