from datetime import timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

import subprocess
import psycopg2
import os


DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "postgres"),
    "port": int(os.environ.get("DB_PORT", 5432)),
    "dbname": os.environ.get("DB_NAME", "restaurant_db"),
    "user": os.environ.get("DB_USER", "admin"),
    "password": os.environ.get("DB_PASSWORD", "admin"),
}


default_args = {
    "owner": "restaurant-pipeline",
    "retries": 3,
    "retry_delay": timedelta(minutes=1),
}


def check_restaurants():
    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM restaurants;")
            count = cur.fetchone()[0]

            print(f"Restaurant count: {count}")

            if count == 0:
                raise ValueError("restaurants table is empty")


def check_orders():
    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM orders;")
            count = cur.fetchone()[0]

            print(f"Order count: {count}")

            if count < 10000:
                raise ValueError("orders table contains less than 10000 rows")


def build_summary():
    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:

            cur.execute("""
                DELETE FROM city_cuisine_summary;
            """)

            cur.execute("""
                INSERT INTO city_cuisine_summary (
                    summary_date,
                    city,
                    cuisines,
                    restaurant_count,
                    average_rating,
                    average_cost_for_two,
                    online_delivery_ratio,
                    order_count,
                    total_order_amount,
                    average_order_amount
                )

                SELECT
                    CURRENT_DATE,
                    r.city,
                    COALESCE(r.cuisines, 'Unknown') AS cuisines,
                    COUNT(DISTINCT r.restaurant_id),
                    AVG(r.aggregate_rating),
                    AVG(r.average_cost_for_two),

                    AVG(
                        CASE
                            WHEN r.has_online_delivery THEN 1
                            ELSE 0
                        END
                    ),

                    COUNT(o.order_id),
                    COALESCE(SUM(o.order_amount), 0),
                    COALESCE(AVG(o.order_amount), 0)

                FROM restaurants r
                LEFT JOIN orders o
                    ON r.restaurant_id = o.restaurant_id

                GROUP BY r.city, COALESCE(r.cuisines, 'Unknown');;
            """)

            conn.commit()

    print("city_cuisine_summary table updated")


def index_summary():

    result = subprocess.run(
        ["python", "/opt/airflow/scripts/index_summary.py"],
        capture_output=True,
        text=True,
    )

    print(result.stdout)

    if result.returncode != 0:
        raise RuntimeError(result.stderr)


with DAG(
    dag_id="restaurant_pipeline",
    default_args=default_args,
    start_date=days_ago(1),
    schedule_interval=None,
    catchup=False,
) as dag:

    task_check_restaurants = PythonOperator(
        task_id="check_restaurants",
        python_callable=check_restaurants,
    )

    task_check_orders = PythonOperator(
        task_id="check_orders",
        python_callable=check_orders,
    )

    task_build_summary = PythonOperator(
        task_id="build_summary",
        python_callable=build_summary,
    )

    task_index_summary = PythonOperator(
    task_id="index_summary",
    python_callable=index_summary,
)

    (
        task_check_restaurants
        >> task_check_orders
        >> task_build_summary
        >> task_index_summary
    )