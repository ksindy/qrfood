# database.py
import os
import psycopg2
from datetime import datetime, timedelta

DATABASE_URL = os.environ['DATABASE_URL']
DATABASE_URL = "postgres://frdzidjeclcxty:16551cea6bdcb55a4b5033306cd719c6cd73163cfc03e202c0500553e92ad12a@ec2-3-234-204-26.compute-1.amazonaws.com:5432/d521nossmt6tfl"
def connect_to_db():
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    return conn

def check_date_range(conn, days_range):
    with conn.cursor() as cur:
        current_date = datetime.now().date()
        min_date = current_date - timedelta(days=days_range)
        max_date = current_date + timedelta(days=days_range)

        query = f"""SELECT *
                    FROM food_items
                    WHERE expiration_date >= '{min_date}' AND expiration_date <= '{max_date}' AND id = %s
                    AND date_consumed is NULL
                    ORDER BY update_time DESC
                    LIMIT 1;"""
        cur.execute(query)
        results = cur.fetchall()

    return results
