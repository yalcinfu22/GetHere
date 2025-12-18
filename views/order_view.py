import mysql.connector
from flask import Blueprint, request, jsonify, session
from helpers.db_helper import get_db_connection

# 1. IMPORTS NEEDED
# You must import these to use the logic you defined in the other files
from views.courier_view import find_available_courier
from views.task_view import create_task

order = Blueprint('order', __name__)


@order.route("/", methods=["POST"])
def create_order():

    data = request.get_json()
    if not data:
        return jsonify({"error": "No input data provided"}), 400

    order_date = data.get('order_date') # otomatik gelecek
    sales_qty = data.get('sales_qty')
    sales_amount = data.get('sales_amount') # toplam fiyat
    currency = data.get('currency')  # default value verilecek
    user_id = data.get('user_id')
    r_id = data.get('r_id')


    if not user_id or not r_id or not order_date or not sales_amount:
        return jsonify({"error": "Missing required fields: user_id, r_id, order_date or sales_amount"}), 400

    db = get_db_connection()
    if not db:
        return jsonify({"error": "Database connection failed"}), 500

    mycursor = db.cursor()
    try:
        query = (
            "INSERT INTO `orders` "
            "(`user_id`, `r_id`, `order_date`, `sales_amount`, `sales_qty`, `currency`) "
            "VALUES (%s, %s, %s, %s, %s, %s)"
        )
        values = (
            user_id, r_id, order_date, sales_amount, sales_qty, currency
        )
        mycursor.execute(query, values)
        db.commit()
        new_order_id = mycursor.lastrowid

    # except mysql.connector.Error as err:
        # db.rollback()
        # bozuk e-posta hatalarını vs yakalar
        # return jsonify({"error": f"Database error: {err}"}), 500
    finally:
        mycursor.close()
        db.close()

    return jsonify({
        "message": "Order created successfully",
        "order_id": new_order_id
    }), 201


@order.route("/", methods=["GET"])
def get_all_orders():
    db = get_db_connection()
    if not db:
        return jsonify({"error": "Database connection failed"}), 500

    mycursor = db.cursor(dictionary=True)
    try:
        mycursor.execute("SELECT * FROM orders")
        orders = mycursor.fetchall()
        return jsonify(orders)
    except mysql.connector.Error as err:
        return jsonify({"error": f"Database error: {err}"}), 500
    finally:
        mycursor.close()
        db.close()


@order.route("/<int:order_id>", methods=["GET"])
def get_order(order_id):
    db = get_db_connection()
    if not db:
        return jsonify({"error": "Database connection failed"}), 500

    mycursor = db.cursor(dictionary=True)
    try:
        query = "SELECT * FROM order WHERE id = %s"
        mycursor.execute(query, (order_id,))
        order_data = mycursor.fetchone()

        if order_data:
            return jsonify(order_data)
        else:
            return jsonify({"error": "Order not found"}), 404

    except mysql.connector.Error as err:
        return jsonify({"error": f"Database error: {err}"}), 500
    finally:
        mycursor.close()
        db.close()

@order.route("/search", methods=["GET"])
def search_order():
    r_id = request.args.get("r_id", type=int)

    raw_delivered = request.args.get("IsDelivered")
    IsDelivered = None
    if raw_delivered == "0":
        IsDelivered = 0
    elif raw_delivered == "1":
        IsDelivered = 1

    order_by = request.args.get("order_by", default="o.order_date")
    order = request.args.get("order", default="asc")

    valid_cols = {"o.order_date", "o.sales_qty", "o.IsDelivered"}
    if order_by not in valid_cols:
        order_by = "o.order_date"

    order_map = {
        "order_date": "o.order_date",
        "sales_qty": "o.sales_qty",
        "IsDelivered": "o.IsDelivered"
    }

    order_col = order_map.get(order_by, "o.o_id")
    order_dir = "DESC" if order == "desc" else "ASC"

    limit = request.args.get("limit", default=50, type=int)
    offset = request.args.get("offset", default=0, type=int)

    try:
        db = get_db_connection()
        if not db:
            return jsonify({"error": "Database connection failed"}), 500
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500

    cur = db.cursor(dictionary=True)

    try:
        sql = ["""
            SELECT o.o_id, o.r_id, o.order_date, o.sales_qty, o.sales_amount,
                   o.currency, o.m_id, o.IsDelivered, f.item AS food_name
            FROM orders o
            INNER JOIN menu m ON o.m_id = m.m_id
            INNER JOIN food f ON f.f_id = m.f_id 
            WHERE 1=1
        """]
        params = []

        if r_id is not None:
            sql.append("AND o.r_id = %s")
            params.append(r_id)

        if IsDelivered is not None:
            sql.append("AND o.IsDelivered = %s")
            params.append(IsDelivered)

        sql.append(f"ORDER BY {order_col} {order_dir}")
        sql.append("LIMIT %s OFFSET %s")
        params.extend([limit, offset])

        cur.execute(" ".join(sql), tuple(params))
        return jsonify(cur.fetchall())

    except mysql.connector.Error as err:
        print(err)
        return jsonify({"error": f"Database error: {err}"}), 500

    finally:
        cur.close()
        db.close()

@order.route("/create", methods=["POST"])
def make_an_order():
    user_id = session.get('user_id')
    user_type = session.get('user_type')

    # Security Check
    if not user_id or user_type != 'user':
        return jsonify({"error": "Unauthorized: Please log in as a customer."}), 401

    data = request.get_json() or {}

    try:
        m_id = data.get("m_id")
        r_id = data.get("r_id")
        qty = int(data.get("qty", 1))
        price = float(data.get("price", 0))

        if not m_id or not r_id:
            return jsonify({"error": "Missing info"}), 400

        # --- START TRANSACTION ---
        db = get_db_connection()
        if not db: return jsonify({"error": "DB Connection Fail"}), 500
        
        cursor = db.cursor(dictionary=True)

        # 2. USE THE IMPORTED HELPER (Pass the cursor!)
        c_id = find_available_courier(cursor, r_id)
        
        if not c_id:
            return jsonify({"error": "No courier available"}), 400

        # 3. CREATE ORDER
        cursor.execute("""
            INSERT INTO orders 
            (user_id, r_id, m_id, c_id, sales_amount, sales_qty, currency, IsDelivered)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (user_id, r_id, m_id, c_id, (qty * price), qty, "INR", 0))
        
        o_id = cursor.lastrowid

        # 4. USE THE IMPORTED HELPER (Pass the cursor!)
        t_id = create_task(cursor, o_id, c_id, user_id, m_id)

        db.commit() # Success!
        
        return jsonify({"message": "Success", "o_id": o_id}), 201

    except mysql.connector.Error as err:
        db.rollback()
        print(f"DB Error: {err}")
        if err.errno == 1452:
            return jsonify({"error": "Data integrity error (User/Menu not found)"}), 400
        return jsonify({"error": str(err)}), 500
        
    except Exception as e:
        if 'db' in locals() and db: db.rollback()
        print(f"Logic Error: {e}")
        return jsonify({"error": str(e)}), 500
        
    finally:
        if 'cursor' in locals() and cursor: cursor.close()
        if 'db' in locals() and db: db.close()

@order.route("/view", methods=["GET"])
def view_order():
    o_id = request.args.get("o_id", type=int)

    try:
        db = get_db_connection()
        if not db:
            return jsonify({"error": "Database connection failed"}), 500
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500

    cur = db.cursor(dictionary=True)

    try:
        sql = ["""
            SELECT o.o_id, o.r_id, o.order_date, o.sales_qty, o.sales_amount, o.courier_rate,
                   o.currency, o.m_id, o.c_id, o.IsDelivered, o.menu_rate, f.item AS food_name,
                   f.veg_or_non_veg AS veg, c.name AS courier_name, c.surname AS courier_surname,
                   m.price AS price, r.name AS restaurant_name, r.rating AS restaurant_rating
            FROM orders o
            INNER JOIN menu m ON o.m_id = m.m_id
            INNER JOIN food f ON f.f_id = m.f_id
            INNER JOIN restaurant r ON o.r_id = r.r_id
            INNER JOIN courier c ON o.c_id = c.c_id  
            WHERE o.o_id = %s
        """]
        params = [o_id]

        cur.execute(" ".join(sql), tuple(params))
        return jsonify(cur.fetchone())

    except mysql.connector.Error as err:
        return jsonify({"error": f"Database error: {err}"}), 500

    finally:
        cur.close()
        db.close()

@order.route("/update/<int:o_id>", methods=["PUT"])
def update_order(o_id):
    data = request.get_json() or {}
    try:
        sales_qty = int(data.get("new_qty"))

        db = get_db_connection()
        if not db: return jsonify({"error": "DB Connection Fail"}), 500
        
        cur = db.cursor(dictionary=True)

        cur.execute("""
            UPDATE orders o
            INNER JOIN menu m ON o.m_id = m.m_id 
            SET sales_qty = %s, sales_amount = %s * m.price
            WHERE o_id = %s
        """, (sales_qty, sales_qty, o_id))

        db.commit()
        return jsonify({"message": "Success", "o_id": o_id})
    
    except mysql.connector.Error as err:
        return jsonify({"error": f"Database error: {err}"}), 500
    
    finally:
        cur.close()
        db.close()

@order.route("/rate/<int:o_id>", methods=["PUT"])
def update_ratings(o_id):
    data = request.get_json() or {}

    try:
        menu_rate = data.get("menu_rate")
        courier_rate = data.get("courier_rate")

        if menu_rate is None or courier_rate is None:
            return jsonify({"error": "Missing ratings"}), 400

        menu_rate = int(menu_rate)
        courier_rate = int(courier_rate)

        if not (1 <= menu_rate <= 5 and 1 <= courier_rate <= 5):
            return jsonify({"error": "Ratings must be between 1 and 5"}), 400

        db = get_db_connection()
        if not db:
            return jsonify({"error": "DB Connection Fail"}), 500

        cur = db.cursor()

        cur.execute("""
            UPDATE orders o
            JOIN courier c ON c.c_id = o.c_id
            JOIN restaurant r ON r.r_id = o.r_id
            SET
                c.rating =
                    CASE
                        WHEN o.courier_rate IS NULL AND c.ratingCount = 0
                            THEN %s
                        WHEN o.courier_rate IS NULL AND c.ratingCount > 0
                            THEN (COALESCE(c.rating, 0) * c.ratingCount + %s) / (c.ratingCount + 1)
                        WHEN o.courier_rate IS NOT NULL AND c.ratingCount > 0
                            THEN (COALESCE(c.rating, 0) * c.ratingCount - o.courier_rate + %s) / c.ratingCount
                        ELSE c.rating
                    END,
                c.ratingCount =
                    CASE
                        WHEN o.courier_rate IS NULL THEN c.ratingCount + 1
                        ELSE c.ratingCount
                    END,

                r.rating =
                    CASE
                        WHEN o.menu_rate IS NULL AND r.rating_count = 0
                            THEN %s
                        WHEN o.menu_rate IS NULL AND r.rating_count > 0
                            THEN (COALESCE(r.rating, 0) * r.rating_count + %s) / (r.rating_count + 1)
                        WHEN o.menu_rate IS NOT NULL AND r.rating_count > 0
                            THEN (COALESCE(r.rating, 0) * r.rating_count - o.menu_rate + %s) / r.rating_count
                        ELSE r.rating
                    END,
                r.rating_count =
                    CASE
                        WHEN o.menu_rate IS NULL THEN r.rating_count + 1
                        ELSE r.rating_count
                    END,

                o.menu_rate = %s,
                o.courier_rate = %s
            WHERE o.o_id = %s
        """, (courier_rate, courier_rate, courier_rate, menu_rate, menu_rate, menu_rate, menu_rate, courier_rate, o_id))

        db.commit()
        return jsonify({"message": "Success", "o_id": o_id})

    except Exception as err:
        print(err)
        return jsonify({"error": str(err)}), 500

    finally:
        cur.close()
        db.close()


@order.route("/delete/<int:o_id>", methods=["DELETE"])
def delete_order(o_id):
    data = request.get_json() or {}
    try:
        db = get_db_connection()
        if not db: return jsonify({"error": "DB Connection Fail"}), 500
        
        cur = db.cursor(dictionary=True)

        cur.execute("""
            DELETE FROM orders WHERE o_id = %s
        """, (o_id,))

        db.commit()
        return jsonify({"message": "Success"})
    
    except mysql.connector.Error as err:
        return jsonify({"error": f"Database error: {err}"}), 500
    
    finally:
        cur.close()
        db.close()


    
