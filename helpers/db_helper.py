# helpers/db_helper.py
import mysql.connector
from flask import current_app

def get_db_connection(host=None, user=None, password=None, db_name=None):
    # Fall back to Flask config if not provided
    host = host or current_app.config.get("DB_HOST")
    user = user or current_app.config.get("DB_USER")
    password = password or current_app.config.get("DB_PASSWORD")
    db_name = db_name or current_app.config.get("DB_NAME")

    try:
        db = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=db_name
        )
        return db

    except mysql.connector.Error as err:
        print(f"Error connecting to database: {err}")
        return None
