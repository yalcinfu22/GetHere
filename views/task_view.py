import mysql.connector
import bcrypt
from flask import Blueprint, jsonify, session
from helpers import db_helper
from datetime import datetime

task = Blueprint('task', __name__)


def create_task(cursor, o_id, c_id, user_id, m_id):
    """
    Creates a delivery task.
    Uses the SHARED cursor to remain in the same transaction as the Order.
    This is a helper function, not a route.
    """

    # 1. Get User Address
    cursor.execute(
        "SELECT address FROM User WHERE user_id = %s",
        (user_id,)
    )
    user_row = cursor.fetchone()

    # 2. Insert Task
    cursor.execute("""
        INSERT INTO Task 
        (o_id, c_id, user_id, m_id, user_address, status)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (o_id, c_id, user_id, m_id, user_row["address"], 0))

    task_id = cursor.lastrowid

    # 3. Increment Courier taskCount
    cursor.execute("""
        UPDATE Courier
        SET taskCount = taskCount + 1
        WHERE c_id = %s
    """, (c_id,))

    return task_id
