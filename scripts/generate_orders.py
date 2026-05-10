import os
import random
from datetime import datetime, timedelta

import psycopg2
from psycopg2.extras import execute_values


DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "postgres"),
    "port": int(os.environ.get("DB_PORT", 5432)),
    "dbname": os.environ.get("DB_NAME", "restaurant_db"),
    "user": os.environ.get("DB_USER", "admin"),
    "password": os.environ.get("DB_PASSWORD", "admin"),
}

ORDER_COUNT = int(os.environ.get("ORDER_COUNT", "50000"))


def weighted_hour():
    # Lunch and dinner are more likely
    hours = list(range(24))
    weights = []

    for h in hours:
        if 12 <= h <= 14:
            weights.append(5)
        elif 18 <= h <= 22:
            weights.append(8)
        elif 8 <= h <= 11:
            weights.append(2)
        else:
            weights.append(1)

    return random.choices(hours, weights=weights, k=1)[0]


def random_timestamp():
    base_date = datetime.now() - timedelta(days=random.randint(0, 29))

    # Weekend boost
    if random.random() < 0.35:
        days_until_weekend = (5 - base_date.weekday()) % 7
        base_date = base_date + timedelta(days=days_until_weekend)

    hour = weighted_hour()
    minute = random.randint(0, 59)
    second = random.randint(0, 59)

    return base_date.replace(hour=hour, minute=minute, second=second, microsecond=0)


def delivery_type(has_online_delivery):
    if has_online_delivery:
        return random.choices(
            ["online", "pickup", "dine_in"],
            weights=[0.65, 0.20, 0.15],
            k=1,
        )[0]

    return random.choices(
        ["pickup", "dine_in"],
        weights=[0.35, 0.65],
        k=1,
    )[0]


def order_amount(avg_cost):
    if avg_cost is None or avg_cost <= 0:
        base = random.uniform(150, 700)
    else:
        base = float(avg_cost) / 2

    multiplier = random.uniform(0.6, 1.8)
    return round(max(50, base * multiplier), 2)


def restaurant_weight(row):
    restaurant_id, avg_cost, rating, votes, has_online_delivery = row

    rating = float(rating or 0)
    votes = int(votes or 0)

    weight = 1
    weight += max(rating, 0) * 3
    weight += min(votes, 1000) / 100

    if has_online_delivery:
        weight += 8

    return max(weight, 1)


def main():
    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    restaurant_id,
                    average_cost_for_two,
                    aggregate_rating,
                    votes,
                    has_online_delivery
                FROM restaurants;
            """)

            restaurants = cur.fetchall()

            if not restaurants:
                raise RuntimeError("No restaurants found. Load restaurants first.")
            

            cur.execute("SELECT COUNT(*) FROM orders;")
            existing_order_count = cur.fetchone()[0]

            if existing_order_count >= ORDER_COUNT:
                print(f"Orders already exist: {existing_order_count}. Skipping generation.")
                return

            weights = [restaurant_weight(row) for row in restaurants]

            orders = []

            for i in range(1, ORDER_COUNT + 1):
                selected = random.choices(restaurants, weights=weights, k=1)[0]

                restaurant_id = selected[0]
                avg_cost = selected[1]
                has_online_delivery = selected[4]

                orders.append((
                    f"ORD-{i:06d}",
                    restaurant_id,
                    random_timestamp(),
                    order_amount(avg_cost),
                    delivery_type(has_online_delivery),
                ))

            execute_values(
                cur,
                """
                INSERT INTO orders (
                    order_id,
                    restaurant_id,
                    order_timestamp,
                    order_amount,
                    delivery_type
                )
                VALUES %s
                ON CONFLICT (order_id) DO UPDATE SET
                    restaurant_id = EXCLUDED.restaurant_id,
                    order_timestamp = EXCLUDED.order_timestamp,
                    order_amount = EXCLUDED.order_amount,
                    delivery_type = EXCLUDED.delivery_type;
                """,
                orders,
            )

    print(f"Generated synthetic orders: {ORDER_COUNT}")


if __name__ == "__main__":
    main()