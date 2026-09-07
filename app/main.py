import json
import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.schema import CustomerFeatures, PredictionResponse

app = FastAPI(
    title='Olist Customer Retention Prediction API',
    description='API Enterprise-grade untuk memprediksi probabilitas repeat purchase pelanggan Olist.',
    version='1.0.0'
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

FEATURE_COLUMNS = [
    'days_since_last_order',
    'order_count',
    'total_spending',
    'avg_order_value',
    'avg_delivery_days',
    'unique_categories',
    'avg_review_score'
]

try:
    model = joblib.load('models/logistic_regression.pkl')
    with open('models/threshold_top_k.json', 'r') as f:
        threshold_data = json.load(f)
        DECISION_THRESHOLD = threshold_data.get('optimal_threshold', 0.5)
except Exception:
    model = None
    DECISION_THRESHOLD = 0.5

@app.get('/')
def health_check():
    return {
        'status': 'online',
        'service': 'Olist ML Serving API',
        'model_loaded': model is not None
    }

@app.post('/predict', response_model=PredictionResponse)
def predict_repeat_purchase(features: CustomerFeatures):
    if model is None:
        raise HTTPException(status_code=500, detail='File model tidak ditemukan.')
    
    input_data = pd.DataFrame([features.model_dump()])[FEATURE_COLUMNS]
    
    try:
        prob = float(model.predict_proba(input_data)[0][1])
    except Exception as err:
        raise HTTPException(status_code=500, detail=f'Gagal memprediksi: {str(err)}')

    is_repeat = prob >= DECISION_THRESHOLD
    
    if is_repeat and features.total_spending > 200:
        quadrant = 'High Value - High Intent (Priority 1)'
    elif is_repeat:
        quadrant = 'Low Value - High Intent (Priority 2)'
    elif features.total_spending > 200:
        quadrant = 'High Value - At Risk (Priority 3)'
    else:
        quadrant = 'Low Value - Low Intent (Priority 4)'

    return PredictionResponse(
        customer_status='Repeat' if is_repeat else 'One-time',
        repeat_probability=round(prob, 4),
        is_repeat_customer=is_repeat,
        priority_quadrant=quadrant
    )
