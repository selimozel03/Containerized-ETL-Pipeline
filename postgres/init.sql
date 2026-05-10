SELECT 'CREATE DATABASE airflow_db'
WHERE NOT EXISTS (
    SELECT FROM pg_database WHERE datname = 'airflow_db'
)\gexec

CREATE TABLE IF NOT EXISTS restaurants (
    restaurant_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    country_code INTEGER,
    country TEXT,
    city TEXT,
    locality TEXT,
    cuisines TEXT,
    average_cost_for_two NUMERIC,
    currency TEXT,
    has_table_booking BOOLEAN,
    has_online_delivery BOOLEAN,
    price_range INTEGER,
    aggregate_rating NUMERIC,
    rating_text TEXT,
    votes INTEGER,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    source_dataset TEXT DEFAULT 'zomato',
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS invalid_restaurants (
    raw_restaurant_id TEXT,
    reason TEXT,
    raw_data JSONB,
    rejected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    restaurant_id INTEGER REFERENCES restaurants(restaurant_id),
    order_timestamp TIMESTAMP NOT NULL,
    order_amount NUMERIC NOT NULL,
    delivery_type TEXT,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS city_cuisine_summary (
    summary_date DATE NOT NULL,
    city TEXT NOT NULL,
    cuisines TEXT NOT NULL,
    restaurant_count INTEGER,
    average_rating NUMERIC,
    average_cost_for_two NUMERIC,
    online_delivery_ratio NUMERIC,
    order_count INTEGER,
    total_order_amount NUMERIC,
    average_order_amount NUMERIC,
    PRIMARY KEY (summary_date, city, cuisines)
);