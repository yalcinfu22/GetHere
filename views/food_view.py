# views/food_view.py
import mysql.connector
from flask import Blueprint, request, jsonify
from helpers.db_helper import get_db_connection

food = Blueprint("food", __name__)

@food.route("/", methods=["POST"])
def create_food():
    data = request.get_json() or {}
    f_id  = data.get("f_id")
    item  = data.get("item")
    veg   = data.get("veg_or_non_veg")
    if not f_id or not item:
        return jsonify({"error": "Missing fields: f_id, item"}), 400

    db = get_db_connection()
    if not db:
        return jsonify({"error": "Database connection failed"}), 500
    cur = db.cursor()
    try:
        cur.execute(
            "INSERT INTO Food (f_id, item, veg_or_non_veg) VALUES (%s,%s,%s)",
            (f_id, item, veg),
        )
        db.commit()
        return jsonify({"message": "Food created", "f_id": f_id}), 201
    except mysql.connector.Error as err:
        db.rollback()
        return jsonify({"error": f"Database error: {err}"}), 500
    finally:
        cur.close(); db.close()


@food.route("/", methods=["GET"])
def list_foods():
    db = get_db_connection()
    if not db:
        return jsonify({"error": "Database connection failed"}), 500
    cur = db.cursor(dictionary=True)
    try:
        cur.execute("SELECT f_id, item, veg_or_non_veg FROM Food")
        return jsonify(cur.fetchall())
    except mysql.connector.Error as err:
        return jsonify({"error": f"Database error: {err}"}), 500
    finally:
        cur.close(); db.close()


@food.route("/<string:f_id>", methods=["GET"])
def get_food(f_id):
    db = get_db_connection()
    if not db:
        return jsonify({"error": "Database connection failed"}), 500
    cur = db.cursor(dictionary=True)
    try:
        cur.execute("SELECT f_id, item, veg_or_non_veg FROM Food WHERE f_id=%s", (f_id,))
        row = cur.fetchone()
        return jsonify(row) if row else (jsonify({"error":"Food not found"}), 404)
    except mysql.connector.Error as err:
        return jsonify({"error": f"Database error: {err}"}), 500
    finally:
        cur.close(); db.close()


@food.route("/<string:f_id>", methods=["DELETE"])
def delete_food(f_id):
    db = get_db_connection()
    if not db:
        return jsonify({"error": "Database connection failed"}), 500
    cur = db.cursor()
    try:
        # prevent deleting if referenced by Menu
        cur.execute("SELECT 1 FROM Menu WHERE f_id=%s LIMIT 1", (f_id,))
        if cur.fetchone():
            return jsonify({"error": "Food is referenced by Menu; delete related Menu items first"}), 409
        cur.execute("DELETE FROM Food WHERE f_id=%s", (f_id,))
        db.commit()
        return jsonify({"deleted": cur.rowcount > 0})
    except mysql.connector.Error as err:
        db.rollback()
        return jsonify({"error": f"Database error: {err}"}), 500
    finally:
        cur.close(); db.close()
