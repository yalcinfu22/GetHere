import mysql.connector
from flask import Blueprint, request, jsonify
from helpers.db_helper import get_db_connection

menu = Blueprint("menu", __name__)


def _get_db():
    db = get_db_connection()
    if not db:
        raise RuntimeError("Database connection failed")
    return db

def _ensure_restaurant(cur, r_id):
    cur.execute("SELECT 1 FROM Restaurant WHERE r_id=%s", (r_id,))
    return cur.fetchone() is not None

def _find_food_by_name(cur, name):
    # case-insensitive lookup
    cur.execute("SELECT f_id FROM Food WHERE LOWER(item)=LOWER(%s) LIMIT 1", (name,))
    row = cur.fetchone()
    return row[0] if row else None

def _next_food_id(cur):
    # expects ids like fd0, fd1, ...
    cur.execute("SELECT COALESCE(MAX(CAST(SUBSTRING(f_id, 3) AS UNSIGNED)), -1) FROM Food")
    mx = cur.fetchone()[0]
    return f"fd{int(mx) + 1}"

def _ensure_food(cur, item, veg):
    # returns existing f_id or creates a new one
    fid = _find_food_by_name(cur, item)
    if fid:
        return fid
    fid = _next_food_id(cur)
    cur.execute(
        "INSERT INTO Food (f_id, item, veg_or_non_veg) VALUES (%s,%s,%s)",
        (fid, item, veg or "Non-Veg"),
    )
    return fid





@menu.route("/", methods=["POST"])
def create_menu_item():
    """
    Accepts either:
      { "menu_id": "mn0", "r_id": 123, "f_id": "fd7", "cuisine": "...", "price": 40.0 }
    OR
      { "menu_id": "mn0", "r_id": 123, "food_name": "Double Burger", "veg_or_non_veg": "Veg", "cuisine": "...", "price": 40.0 }
    """
    data = request.get_json() or {}
    menu_id = data.get("menu_id")
    r_id    = data.get("r_id")
    f_id    = data.get("f_id")                # optional if food_name is provided
    food_nm = data.get("food_name")          # optional alternative to f_id
    veg     = data.get("veg_or_non_veg")     # optional (defaults to Non-Veg)
    cuisine = data.get("cuisine")
    price   = data.get("price")

    if r_id is None or price is None or (not f_id and not food_nm):
        return jsonify({"error": "Required: r_id, price and (f_id OR food_name)."}), 400

    try:
        db = _get_db()
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500

    cur = db.cursor()
    try:
        if not _ensure_restaurant(cur, r_id):
            return jsonify({"error": "Unknown r_id"}), 400

        # Auto-generate menu_id if missing
        if not menu_id:
            cur.execute("SELECT COALESCE(MAX(CAST(SUBSTRING(menu_id, 3) AS UNSIGNED)), 0) FROM Menu")
            row = cur.fetchone()
            next_val = (row[0] if row else 0) + 1
            menu_id = f"mn{next_val}"

        # Ensure/resolve Food
        if not f_id:
            f_id = _ensure_food(cur, food_nm, veg)

        cur.execute(
            """
            INSERT INTO Menu (menu_id, r_id, f_id, cuisine, price)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (menu_id, r_id, f_id, cuisine, price),
        )
        db.commit()
        new_id = cur.lastrowid
        return jsonify({"message": "Menu item created", "m_id": new_id, "f_id": f_id}), 201
    except mysql.connector.Error as err:
        db.rollback()
        return jsonify({"error": f"Database error: {err}"}), 500
    finally:
        cur.close(); db.close()

@menu.route("/", methods=["GET"])
def get_all_menu_items():
    try:
        db = _get_db()
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500
    cur = db.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT m.m_id, m.menu_id, m.r_id, m.f_id, m.cuisine, m.price, m.created_at,
                   f.item AS food_name, f.veg_or_non_veg AS veg
            FROM Menu m
            LEFT JOIN Food f ON f.f_id = m.f_id
        """)
        return jsonify(cur.fetchall())
    except mysql.connector.Error as err:
        return jsonify({"error": f"Database error: {err}"}), 500
    finally:
        cur.close(); db.close()

@menu.route("/<int:m_id>", methods=["GET"])
def get_menu_item(m_id):
    try:
        db = _get_db()
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500
    cur = db.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT m.m_id, m.menu_id, m.r_id, m.f_id, m.cuisine, m.price, m.created_at,
                   f.item AS food_name, f.veg_or_non_veg AS veg
            FROM Menu m
            LEFT JOIN Food f ON f.f_id = m.f_id
            WHERE m.m_id = %s
        """, (m_id,))
        row = cur.fetchone()
        return jsonify(row) if row else (jsonify({"error": "Not found"}), 404)
    except mysql.connector.Error as err:
        return jsonify({"error": f"Database error: {err}"}), 500
    finally:
        cur.close(); db.close()

@menu.route("/by-restaurant/<int:r_id>", methods=["GET"])
def get_menu_by_restaurant(r_id):
    try:
        db = _get_db()
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500
    cur = db.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT m.m_id, m.menu_id, m.r_id, m.f_id, m.cuisine, m.price, m.created_at,
                   f.item AS food_name, f.veg_or_non_veg AS veg
            FROM Menu m
            LEFT JOIN Food f ON f.f_id = m.f_id
            WHERE m.r_id = %s
        """, (r_id,))
        return jsonify(cur.fetchall())
    except mysql.connector.Error as err:
        return jsonify({"error": f"Database error: {err}"}), 500
    finally:
        cur.close(); db.close()

@menu.route("/<int:m_id>", methods=["PUT"])
def update_menu_item(m_id):
    data = request.get_json() or {}

    # allow updating via either f_id or (food_name + veg)
    new_food_name = data.pop("food_name", None)
    new_food_veg  = data.pop("veg_or_non_veg", None)

    fields, params = [], []
    for col in ("menu_id","r_id","f_id","cuisine","price"):
        if col in data:
            fields.append(f"{col}=%s"); params.append(data[col])
    if new_food_name:
        # resolve/create food and set f_id
        try:
            db = _get_db()
        except RuntimeError as e:
            return jsonify({"error": str(e)}), 500
        cur = db.cursor()
        try:
            fid = _ensure_food(cur, new_food_name, new_food_veg)
            fields.append("f_id=%s"); params.append(fid)
            db.commit()
        except mysql.connector.Error as err:
            db.rollback()
            return jsonify({"error": f"Database error: {err}"}), 500
        finally:
            cur.close(); db.close()

    if not fields:
        return jsonify({"error":"No fields to update"}), 400

    try:
        db = _get_db()
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500
    cur = db.cursor()
    try:
        sql = f"UPDATE Menu SET {', '.join(fields)} WHERE m_id=%s"
        cur.execute(sql, (*params, m_id))
        db.commit()
        return jsonify({"updated": cur.rowcount > 0})
    except mysql.connector.Error as err:
        db.rollback()
        return jsonify({"error": f"Database error: {err}"}), 500
    finally:
        cur.close(); db.close()

@menu.route("/<int:m_id>", methods=["DELETE"])
def delete_menu_item(m_id):
    try:
        db = _get_db()
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500
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

@menu.route("/search", methods=["GET"])
def search_menu():
    r_id = request.args.get("r_id", type=int)
    cuisine = request.args.get("cuisine")
    veg = request.args.get("veg")                # "Veg" | "Non-Veg" | "Other"
    q = request.args.get("q")                    # food_name LIKE
    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)

    order_by = request.args.get("order_by")      # price | food_name | cuisine
    order = request.args.get("order", "asc").lower()
    limit = request.args.get("limit", default=50, type=int)
    offset = request.args.get("offset", default=0, type=int)

    order_map = {"price":"m.price", "food_name":"f.item", "cuisine":"m.cuisine"}
    order_col = order_map.get(order_by or "", "m.m_id")
    order_dir = "DESC" if order == "desc" else "ASC"

    try:
        db = _get_db()
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500
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
        if veg in ("Veg","Non-Veg","Other"):
            sql.append("AND f.veg_or_non_veg = %s"); params.append(veg)
        if q:
            sql.append("AND f.item LIKE %s"); params.append(f"%{q}%")
        if min_price is not None:
            sql.append("AND m.price >= %s"); params.append(min_price)
        if max_price is not None:
            sql.append("AND m.price <= %s"); params.append(max_price)
        sql.append(f"ORDER BY {order_col} {order_dir}")
        sql.append("LIMIT %s OFFSET %s"); params.extend([limit, offset])

        cur.execute(" ".join(sql), tuple(params))
        return jsonify(cur.fetchall())
    except mysql.connector.Error as err:
        return jsonify({"error": f"Database error: {err}"}), 500
    finally:
        cur.close(); db.close()