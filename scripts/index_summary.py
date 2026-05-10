import os

import psycopg2
from elasticsearch import Elasticsearch


DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "postgres"),
    "port": int(os.environ.get("DB_PORT", 5432)),
    "dbname": os.environ.get("DB_NAME", "restaurant_db"),
    "user": os.environ.get("DB_USER", "admin"),
    "password": os.environ.get("DB_PASSWORD", "admin"),
}

ES_HOST = os.environ.get("ES_HOST", "http://elasticsearch:9200")


def main():

    es = Elasticsearch(ES_HOST)

    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:

            cur.execute("""
                SELECT
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
                FROM city_cuisine_summary;
            """)

            rows = cur.fetchall()

            for row in rows:

                document = {
                    "summary_date": str(row[0]),
                    "city": row[1],
                    "cuisines": row[2],
                    "restaurant_count": row[3],
                    "average_rating": float(row[4]) if row[4] else None,
                    "average_cost_for_two": float(row[5]) if row[5] else None,
                    "online_delivery_ratio": float(row[6]) if row[6] else None,
                    "order_count": row[7],
                    "total_order_amount": float(row[8]) if row[8] else None,
                    "average_order_amount": float(row[9]) if row[9] else None,
                }

                doc_id = f"{row[1]}_{row[2]}"

                es.index(
                    index="city_cuisine_summary",
                    id=doc_id,
                    document=document,
                )

    print(f"Indexed {len(rows)} documents into Elasticsearch")


if __name__ == "__main__":
    main()