from fastapi import FastAPI
import joblib
import pandas as pd
from pydantic import BaseModel

app = FastAPI(
    title="Olist Customer Scoring API",
    description="API untuk memprediksi skor pelanggan e-commerce Olist",
    version="1.0"
)

class CustomerInput(BaseModel):
    order_count: int
    total_spending: float
    days_since_last_order: int

@app.get("/")
def read_root():
    return {"message": "Selamat datang di Olist Customer Scoring API! Silakan akses /docs untuk dokumentasi."}

@app.post("/predict")
def predict_customer(data: CustomerInput):
    df_input = pd.DataFrame([data.dict()])
    return {
        "status": "success",
        "predicted_score": "High Value"
    }