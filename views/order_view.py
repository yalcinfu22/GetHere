import mysql.connector
from flask import Blueprint, request, jsonify
from helpers.db_helper import get_db_connection

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