-- ====================================================
-- OLIST BIGQUERY DATA MART & FEATURE EXTRACTION QUERY
-- ====================================================

CREATE OR REPLACE TABLE `olist_data_mart.fact_customer_features` AS
SELECT
    c.customer_unique_id,
    DATE_DIFF(CURRENT_DATE(), MAX(o.order_purchase_timestamp), DAY) AS days_since_last_order,
    COUNT(DISTINCT o.order_id) AS order_count,
    ROUND(SUM(p.payment_value), 2) AS total_spending,
    ROUND(AVG(p.payment_value), 2) AS avg_order_value,
    ROUND(AVG(DATE_DIFF(o.order_delivered_customer_date, o.order_purchase_timestamp, DAY)), 1) AS avg_delivery_days,
    COUNT(DISTINCT pc.product_category_name) AS unique_categories,
    ROUND(AVG(r.review_score), 2) AS avg_review_score
FROM `olist_raw.orders` o
JOIN `olist_raw.customers` c ON o.customer_id = c.customer_id
LEFT JOIN `olist_raw.order_payments` p ON o.order_id = p.order_id
LEFT JOIN `olist_raw.order_items` i ON o.order_id = i.order_id
LEFT JOIN `olist_raw.products` pr ON i.product_id = pr.product_id
LEFT JOIN `olist_raw.product_category_name_translation` pc ON pr.product_category_name = pc.product_category_name
LEFT JOIN `olist_raw.order_reviews` r ON o.order_id = r.order_id
WHERE o.order_status = 'delivered'
GROUP BY c.customer_unique_id;
