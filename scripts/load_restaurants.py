import os
import json
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values


DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "postgres"),
    "port": int(os.environ.get("DB_PORT", 5432)),
    "dbname": os.environ.get("DB_NAME", "restaurant_db"),
    "user": os.environ.get("DB_USER", "admin"),
    "password": os.environ.get("DB_PASSWORD", "admin"),
}


def yes_no_to_bool(value):
    if pd.isna(value):
        return None
    return str(value).strip().lower() == "yes"


def main():
    restaurants = pd.read_csv("data/zomato.csv", encoding="latin1")
    countries = pd.read_csv("data/Country-Code.csv")

    df = restaurants.merge(countries, on="Country Code", how="left")

    valid_rows = []
    invalid_rows = []

    for _, row in df.iterrows():
        restaurant_id = int(row["Restaurant ID"])
        lat = row["Latitude"]
        lon = row["Longitude"]

        reason = None
        if pd.isna(lat) or pd.isna(lon):
            reason = "missing_coordinates"
        elif not (-90 <= float(lat) <= 90 and -180 <= float(lon) <= 180):
            reason = "invalid_coordinates"

        if reason:
            invalid_rows.append((
                str(restaurant_id),
                reason,
                json.dumps(row.to_dict(), default=str)
            ))
            continue

        valid_rows.append((
            restaurant_id,
            row["Restaurant Name"],
            int(row["Country Code"]),
            row["Country"],
            row["City"],
            row["Locality"],
            row["Cuisines"] if pd.notna(row["Cuisines"]) else None,
            float(row["Average Cost for two"]) if pd.notna(row["Average Cost for two"]) else None,
            row["Currency"],
            yes_no_to_bool(row["Has Table booking"]),
            yes_no_to_bool(row["Has Online delivery"]),
            int(row["Price range"]) if pd.notna(row["Price range"]) else None,
            float(row["Aggregate rating"]) if pd.notna(row["Aggregate rating"]) else None,
            row["Rating text"],
            int(row["Votes"]) if pd.notna(row["Votes"]) else None,
            float(lat),
            float(lon),
        ))

    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO restaurants (
                    restaurant_id, name, country_code, country, city, locality,
                    cuisines, average_cost_for_two, currency,
                    has_table_booking, has_online_delivery,
                    price_range, aggregate_rating, rating_text, votes,
                    latitude, longitude
                )
                VALUES %s
                ON CONFLICT (restaurant_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    country_code = EXCLUDED.country_code,
                    country = EXCLUDED.country,
                    city = EXCLUDED.city,
                    locality = EXCLUDED.locality,
                    cuisines = EXCLUDED.cuisines,
                    average_cost_for_two = EXCLUDED.average_cost_for_two,
                    currency = EXCLUDED.currency,
                    has_table_booking = EXCLUDED.has_table_booking,
                    has_online_delivery = EXCLUDED.has_online_delivery,
                    price_range = EXCLUDED.price_range,
                    aggregate_rating = EXCLUDED.aggregate_rating,
                    rating_text = EXCLUDED.rating_text,
                    votes = EXCLUDED.votes,
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude;
                """,
                valid_rows,
            )

            if invalid_rows:
                execute_values(
                    cur,
                    """
                    INSERT INTO invalid_restaurants (
                        raw_restaurant_id, reason, raw_data
                    )
                    VALUES %s;
                    """,
                    invalid_rows,
                )

    print(f"Loaded valid restaurants: {len(valid_rows)}")
    print(f"Invalid restaurants: {len(invalid_rows)}")


if __name__ == "__main__":
    main()