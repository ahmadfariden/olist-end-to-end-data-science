from pydantic import BaseModel, ConfigDict, Field

class CustomerFeatures(BaseModel):
    days_since_last_order: int = Field(..., description='Recency', json_schema_extra={'example': 30})
    order_count: int = Field(..., description='Frequency', json_schema_extra={'example': 3})
    total_spending: float = Field(..., description='Monetary', json_schema_extra={'example': 250.50})
    avg_order_value: float = Field(..., description='Avg Value', json_schema_extra={'example': 83.50})
    avg_delivery_days: float = Field(..., description='Delivery Days', json_schema_extra={'example': 7.5})
    unique_categories: int = Field(..., description='Categories', json_schema_extra={'example': 2})
    avg_review_score: float = Field(..., description='Review Score', json_schema_extra={'example': 4.5})

    model_config = ConfigDict(
        json_schema_extra={
            'example': {
                'days_since_last_order': 30,
                'order_count': 3,
                'total_spending': 250.50,
                'avg_order_value': 83.50,
                'avg_delivery_days': 7.5,
                'unique_categories': 2,
                'avg_review_score': 4.5
            }
        }
    )

class PredictionResponse(BaseModel):
    customer_status: str
    repeat_probability: float
    is_repeat_customer: bool
    priority_quadrant: str
