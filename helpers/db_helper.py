# helpers/db_helper.py
import mysql.connector
from flask import current_app

def get_db_connection():
    db_config = current_app.config['DB_CONFIG']
    try:
        db = mysql.connector.connect(
            host=db_config['DB_HOST'],
            user=db_config['DB_USER'],
            password=db_config['DB_PASSWORD'],
            database=db_config['DB_NAME']
        )
        return db
    except mysql.connector.Error as err:
        print(f"Error connecting to database: {err}")
        return None