# views/courier_view.py
import mysql.connector
from flask import Blueprint, request, jsonify, render_template
from helpers.db_helper import get_db_connection # Basit helper'ı import et

courier = Blueprint('courier', __name__)

def _safe_int(value, default=None):
    """Convert form inputs to integers without raising errors."""
    try:
        if value is None or value == "":
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


@courier.route("/", methods=["POST"])
def create_courier():
    """Creates a new courier."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No input data provided"}), 400
        
    name = data.get('name')
    surname = data.get('surname')
    email = data.get('email')
    password = data.get('password') # güvenlik için hashlenecek
    age = data.get('age')
    gender = data.get('gender')
    marital_status = data.get('maritalStatus')
    experience = data.get('experience', 0)
    r_id = data.get('r_id') 

    # db'ye atmadan önce varlıklarını validate ediyorum
    if not email or not password or not name:
        return jsonify({"error": "Missing required fields: email, password, or name"}), 400

    db = get_db_connection()
    if not db:
        return jsonify({"error": "Database connection failed"}), 500
        
    mycursor = db.cursor()
    try:
        query = (
            "INSERT INTO `Courier` "
            "(`r_id`, `name`, `surname`, `email`, `password`, `age`, `gender`, "
            "`maritalStatus`, `experience`) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
        )
        values = (
            r_id, name, surname, email, password, age, gender,
            marital_status, experience
        )
        mycursor.execute(query, values)
        db.commit()
        new_courier_id = mycursor.lastrowid
        
    except mysql.connector.Error as err:
        db.rollback() 
        # bozuk e-posta hatalarını vs yakalar
        return jsonify({"error": f"Database error: {err}"}), 500
    finally:
        mycursor.close()
        db.close()

    return jsonify({
        "message": "Courier created successfully",
        "c_id": new_courier_id
    }), 201

@courier.route("/", methods=["GET"])
def get_all_couriers():
    """Fetches all couriers."""
    db = get_db_connection()
    if not db:
        return jsonify({"error": "Database connection failed"}), 500
    
    mycursor = db.cursor(dictionary=True) 
    try:
        mycursor.execute("SELECT * FROM Courier")
        couriers = mycursor.fetchall()
        return jsonify(couriers)
    except mysql.connector.Error as err:
        return jsonify({"error": f"Database error: {err}"}), 500
    finally:
        mycursor.close()
        db.close()

@courier.route("/<int:courier_id>", methods=["GET"])
def get_courier(courier_id):
    """Fetches a single courier by c_id."""
    db = get_db_connection()
    if not db:
        return jsonify({"error": "Database connection failed"}), 500
        
    mycursor = db.cursor(dictionary=True)
    try:
        query = "SELECT * FROM Courier WHERE c_id = %s"
        mycursor.execute(query, (courier_id,))
        courier_data = mycursor.fetchone()
        
        if courier_data:
            return jsonify(courier_data)
        else:
            return jsonify({"error": "Courier not found"}), 404
            
    except mysql.connector.Error as err:
        return jsonify({"error": f"Database error: {err}"}), 500
    finally:
        # Sorgu ne olursa olsun bağlantıyı kapat
        mycursor.close()
        db.close()

def courier_signup():
    """Render the courier registration form."""
    return render_template("courier_agent.html", form_values={})


def courier_submit_signup_form():
    """Handle courier form submissions from the UI."""
    form_values = request.form.to_dict(flat=True)

    first_name = form_values.get("first_name", "").strip()
    last_name = form_values.get("last_name", "").strip()
    email = form_values.get("email", "").strip()
    password = form_values.get("password")
    age = _safe_int(form_values.get("age"))
    experience = _safe_int(form_values.get("experience"), 0)
    gender = form_values.get("gender")
    marital_status = form_values.get("marital_status")
    r_id = _safe_int(form_values.get("restaurant_id"))

    if not first_name or not last_name or not email or not password:
        return render_template(
            "courier_agent.html",
            error="Please fill out the required fields (name, email and password).",
            form_values=form_values,
        ), 400

    db = get_db_connection()
    if not db:
        return render_template(
            "courier_agent.html",
            error="Database connection failed. Please try again later.",
            form_values=form_values,
        ), 500

    mycursor = db.cursor()
    try:
        query = (
            "INSERT INTO `Courier` "
            "(`r_id`, `name`, `surname`, `email`, `password`, `age`, `gender`, "
            "`maritalStatus`, `experience`) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
        )
        values = (
            r_id,
            first_name,
            last_name,
            email,
            password,
            age,
            gender,
            marital_status,
            experience,
        )
        mycursor.execute(query, values)
        db.commit()
    except mysql.connector.Error as err:
        db.rollback()
        return render_template(
            "courier_agent.html",
            error=f"Database error: {err}",
            form_values=form_values,
        ), 500
    finally:
        mycursor.close()
        db.close()

    return render_template(
        "courier_agent.html",
        success=True,
        courier_name=first_name,
        form_values={},
    )

courier.courier_signup = courier_signup
courier.courier_submit_signup_form = courier_submit_signup_form