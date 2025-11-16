import mysql.connector
from flask import Blueprint, request, jsonify
from helpers.db_helper import get_db_connection

menu = Blueprint("menu", __name__)

@menu.route("/", methods=["POST"])
def create_menu_item():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No input data provided"}), 400

    menu_id = data.get("menu_id")
    r_id    = data.get("r_id")
    f_id    = data.get("f_id")
    cuisine = data.get("cuisine")
    price   = data.get("price")

    if menu_id is None or r_id is None or f_id is None or price is None:
        return jsonify({
            "error": "Missing fields: menu_id, r_id, f_id, price"
        }), 400

    db = get_db_connection()
    if not db:
        return jsonify({"error": "Database connection failed"}), 500

    cur = db.cursor()
    try:
        cur.execute("SELECT 1 FROM Food WHERE f_id=%s", (f_id,))
        if not cur.fetchone():
            return jsonify({"error": "Unknown f_id; create the Food first"}), 400
        cur.execute(
            """
            INSERT INTO Menu (menu_id, r_id, f_id, cuisine, price)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (menu_id, r_id, f_id, cuisine, price),
        )
        db.commit()
        new_id = cur.lastrowid
    except mysql.connector.Error as err:
        db.rollback()
        return jsonify({"error": f"Database error: {err}"}), 500
    finally:
        cur.close()
        db.close()

    return jsonify({
        "message": "Menu item created successfully",
        "m_id": new_id
    }), 201


@menu.route("/", methods=["GET"])
def get_all_menu_items():
    db = get_db_connection()
    if not db:
        return jsonify({"error": "Database connection failed"}), 500

    cur = db.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT m.m_id, m.menu_id, m.r_id, m.f_id, m.cuisine, m.price,
                   f.item AS food_name, f.veg_or_non_veg AS veg
            FROM Menu m
            LEFT JOIN Food f ON m.f_id = f.f_id
        """)
        rows = cur.fetchall()
        return jsonify(rows)
    except mysql.connector.Error as err:
        return jsonify({"error": f"Database error: {err}"}), 500
    finally:
        cur.close()
        db.close()


@menu.route("/<int:m_id>", methods=["GET"])
def get_menu_item(m_id):
    db = get_db_connection()
    if not db:
        return jsonify({"error": "Database connection failed"}), 500

    cur = db.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT m.m_id, m.menu_id, m.r_id, m.f_id, m.cuisine, m.price,
                   f.item AS food_name, f.veg_or_non_veg AS veg
            FROM Menu m
            LEFT JOIN Food f ON m.f_id = f.f_id
            WHERE m.m_id = %s
        """, (m_id,))
        row = cur.fetchone()
        if row:
            return jsonify(row)
        return jsonify({"error": "Menu item not found"}), 404
    except mysql.connector.Error as err:
        return jsonify({"error": f"Database error: {err}"}), 500
    finally:
        cur.close()
        db.close()


@menu.route("/by-restaurant/<int:r_id>", methods=["GET"])
def get_menu_by_restaurant(r_id):
    db = get_db_connection()
    if not db:
        return jsonify({"error": "Database connection failed"}), 500

    cur = db.cursor(dictionary=True)
    try:
        cur.execute("SELECT * FROM Menu WHERE r_id = %s", (r_id,))
        rows = cur.fetchall()
        return jsonify(rows)
    except mysql.connector.Error as err:
        return jsonify({"error": f"Database error: {err}"}), 500
    finally:
        cur.close()
        db.close()

@menu.route("/search", methods=["GET"])
def search_menu():
    r_id = request.args.get("r_id", type=int)
    cuisine = request.args.get("cuisine")       
    veg = request.args.get("veg")              
    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)

    db = get_db_connection()
    if not db:
        return jsonify({"error": "Database connection failed"}), 500

    cur = db.cursor(dictionary=True)
    try:
        sql = ["""
            SELECT m.m_id, m.menu_id, m.r_id, m.f_id, m.cuisine, m.price,
                   f.item AS food_name, f.veg_or_non_veg AS veg
            FROM Menu m
            LEFT JOIN Food f ON m.f_id = f.f_id
            WHERE 1=1
        """]
        params = []

        if r_id is not None:
            sql.append("AND m.r_id = %s"); params.append(r_id)
        if cuisine:
            sql.append("AND m.cuisine LIKE %s"); params.append(f"%{cuisine}%")
        if veg in ("Veg", "Non-veg", "Other"):
            sql.append("AND f.veg_or_non_veg = %s"); params.append(veg)
        if min_price is not None:
            sql.append("AND m.price >= %s"); params.append(min_price)
        if max_price is not None:
            sql.append("AND m.price <= %s"); params.append(max_price)

        cur.execute(" ".join(sql), tuple(params))
        return jsonify(cur.fetchall())
    except mysql.connector.Error as err:
        return jsonify({"error": f"Database error: {err}"}), 500
    finally:
        cur.close(); db.close()


@menu.route("/<int:m_id>", methods=["DELETE"])
def delete_menu_item(m_id):
    db = get_db_connection()
    if not db:
        return jsonify({"error": "Database connection failed"}), 500

    cur = db.cursor()
    try:
        cur.execute("DELETE FROM Menu WHERE m_id=%s", (m_id,))
        db.commit()
        return jsonify({"deleted": cur.rowcount > 0})
    except mysql.connector.Error as err:
        db.rollback()
        return jsonify({"error": f"Database error: {err}"}), 500
    finally:
        cur.close(); db.close()