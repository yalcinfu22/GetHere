from flask import Blueprint, render_template, request, redirect, url_for, session, current_app, jsonify
import bcrypt
import uuid
from helpers import db_helper

restaurant = Blueprint('restaurant', __name__)

@restaurant.route('/login')
def restaurant_login():
    """Restaurant manager login page"""
    return render_template('restaurant_login.html')

@restaurant.route('/submit_login', methods=['POST'])
def restaurant_submit_login():
    """Handle restaurant manager login"""
    email = request.form.get("email")
    password = request.form.get("password")
    
    if not email or not password:
        return "Email and password are required", 400
    
    db_config = current_app.config['DB_CONFIG']
    db = db_helper.get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT * FROM Restaurant WHERE email = %s", (email,))
        restaurant_data = cursor.fetchone()
        
        if restaurant_data and bcrypt.checkpw(password.encode("utf-8"), restaurant_data['password'].encode("utf-8")):
            # Login successful
            session['user_id'] = restaurant_data['r_id']
            session['user_name'] = restaurant_data['restaurant_name']
            session['user_type'] = 'restaurant'
            return redirect(url_for('home_page.home_page'))
        else:
            return "Invalid email or password", 401
    except Exception as e:
        print(f"Login error: {e}")
        return f"An error occurred: {e}", 500
    finally:
        cursor.close()
        db.close()

@restaurant.route('/logout')
def restaurant_logout():
    """Restaurant logout"""
    session.clear()
    return redirect(url_for('home_page.home_page'))

@restaurant.route('/signup')
def restaurant_signup():
    """Restaurant manager signup page"""
    return render_template('restaurant_signup.html')

@restaurant.route('/submit_signup', methods=['POST'])
def restaurant_submit_signup():
    """Handle restaurant signup form submission"""
    restaurant_name = request.form.get("restaurant_name")
    manager_name = request.form.get("manager_name")
    email = request.form.get("email")
    password = request.form.get("password")
    phone = request.form.get("phone")
    city = request.form.get("city")
    address = request.form.get("address")
    cuisine = request.form.get("cuisine")
    description = request.form.get("description", "")

    if not password:
        return "Password required", 400

    db = db_helper.get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        # 1. Create Restaurant
        secret_key = uuid.uuid4().hex
        restaurant_query = """
            INSERT INTO Restaurant (name, city, address, cuisine, secret)
            VALUES (%s, %s, %s, %s, %s)
        """
        restaurant_values = (restaurant_name, city, address, cuisine, secret_key)
        cursor.execute(restaurant_query, restaurant_values)
        new_restaurant_id = cursor.lastrowid

        # 2. Create Restaurant Manager
        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        manager_query = """
            INSERT INTO Restaurant_Manager (name, email, password, managesId)
            VALUES (%s, %s, %s, %s)
        """
        manager_values = (manager_name, email, password_hash, new_restaurant_id)
        cursor.execute(manager_query, manager_values)

        db.commit()
        print("Restaurant and Manager Registered Successfully")

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        return f"Registration failed: {e}", 500
    finally:
        cursor.close()
        db.close()

    return redirect(url_for("home_page.home_page"))

@restaurant.route('/<int:r_id>/menu')
def restaurant_detail(r_id):
    """Restaurant detail page"""
    # DEMO MODE: Always admin
    is_manager = True
    # is_manager = (
    #     session.get('user_type') == 'restaurant' and 
    #     str(session.get('user_id')) == str(r_id)
    # )
    
    return render_template(
        'restaurant_detail.html', 
        r_id=r_id, 
        is_manager=is_manager
    )

@restaurant.route('/api/restaurants', methods=['GET'])
def list_restaurants():
    db = db_helper.get_db_connection()
    if not db:
        return jsonify({"error": "Database connection failed"}), 500

    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("SELECT r_id, name, city, rating, cuisine, address FROM Restaurant LIMIT 20")
        restaurants = cursor.fetchall()
        return jsonify(restaurants)
    except Exception as e:
        print(f"Error fetching restaurants: {e}")
        return jsonify({"error": "Failed to fetch restaurants"}), 500
    finally:
        cursor.close()
        db.close()