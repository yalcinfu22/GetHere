import mysql.connector
import bcrypt
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, session, current_app
from helpers import db_helper
from datetime import datetime

courier = Blueprint('courier', __name__)

# ==========================================
# WEB FORM ROUTES (Browser Interaction)
# ==========================================

@courier.route('/login')
def courier_login():
    """Renders the courier login HTML page."""
    return render_template("courier_login.html")

@courier.route('/submit_login', methods=['POST'])
def courier_submit_login():
    """Handle courier login"""
    email = request.form.get("email")
    password = request.form.get("password")
    
    if not email or not password:
        return "Email and password are required", 400
    
    # Database lookup
    db = db_helper.get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT * FROM Courier WHERE email = %s", (email,))
        courier_data = cursor.fetchone()
        
        if courier_data and bcrypt.checkpw(password.encode("utf-8"), courier_data['password'].encode("utf-8")):
            # Login successful - Store courier info in session
            session['user_id'] = courier_data['c_id']
            session['user_name'] = courier_data['name']
            session['user_surname'] = courier_data.get('surname', '')
            session['user_type'] = 'courier'
            session['courier_r_id'] = courier_data.get('r_id')  # Restaurant ID if assigned
            
            print("Giriş başarılı - Redirecting to dashboard")
            return redirect(url_for('courier.courier_dashboard'))  # Go to dashboard instead of home
        else:
            print("Giriş başarısız")
            return "Invalid email or password", 401
    except Exception as e:
        print(f"Login error: {e}")
        return f"An error occurred: {e}", 500
    finally:
        cursor.close()
        db.close()

@courier.route('/dashboard')
def courier_dashboard():
    """
    Simplified Courier Dashboard based on the sketch.
    Loads: Profile info, Left-side Review/History list, and Active Tasks.
    """
    if 'user_id' not in session or session.get('user_type') != 'courier':
        return redirect(url_for('courier.courier_login'))
    
    courier_id = session['user_id']
    db = db_helper.get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT c_id, name, surname, r_id, rating, taskCount 
            FROM Courier 
            WHERE c_id = %s
        """, (courier_id,))
        courier_info = cursor.fetchone()

        # 2. Get Active Tasks (FIXED: Joining Food table to get item name)
        cursor.execute("""
            SELECT t.t_id, u.name as customer_name, u.address, 
                   f.item as menu_name  -- Get 'item' from Food table, not Menu
            FROM Task t
            JOIN User u ON t.user_id = u.user_id
            LEFT JOIN Menu m ON t.m_id = m.m_id
            LEFT JOIN Food f ON m.f_id = f.f_id  -- JOIN ADDED HERE
            WHERE t.c_id = %s AND t.status = 0
            ORDER BY t.task_date ASC
        """, (courier_id,))
        active_tasks = cursor.fetchall()

        # 3. Get Recent History (FIXED: Joining Food table here too)
        cursor.execute("""
            SELECT t.t_id, f.item as menu_name
            FROM Task t
            LEFT JOIN Menu m ON t.m_id = m.m_id
            LEFT JOIN Food f ON m.f_id = f.f_id  -- JOIN ADDED HERE
            WHERE t.c_id = %s AND t.status = 1
            ORDER BY t.task_date DESC
            LIMIT 5
        """, (courier_id,))
        recent_history = cursor.fetchall()

        # Add dummy data for fields missing in SQL
        for task in active_tasks:
            task['phone'] = "+90 555 123 4567"
            # Fallback if menu/food lookup failed (e.g. deleted item)
            if not task['menu_name']: task['menu_name'] = "Unknown Item"
            
        for review in recent_history:
            review['rating'] = 5.0
            review['comment'] = "Great service!"
            if not review['menu_name']: review['menu_name'] = "Unknown Item"

        return render_template('courier_dashboard.html',
                             courier=courier_info,
                             active_tasks=active_tasks,
                             reviews=recent_history)

    except Exception as e:
        print(f"Dashboard error: {e}")
        return f"Error: {e}", 500
    finally:
        cursor.close()
        db.close()
# --- Placeholder Routes for Navigation (As requested) ---

@courier.route('/profile')
def profile_page():
    return "Profile Page & Settings (To Be Implemented)"

@courier.route('/tasks/active')
def active_tasks_page():
    return "Detailed Active Tasks Page (To Be Implemented)"

@courier.route('/restaurant/my')
def my_restaurant_page():
    # Logic: Check if user has r_id, if not show error, else show details
    return "My Restaurant Details (To Be Implemented)"

@courier.route('/positions/search')
def search_positions_page():
    return "Search Available Positions (To Be Implemented)"

@courier.route('/history')
def delivery_history_page():
    return "Full Order History (To Be Implemented)"

@courier.route('/logout')
def courier_logout():
    """Courier logout"""
    session.clear()
    return redirect(url_for('home_page.home_page'))

@courier.route('/signup')
def courier_signup():
    """Renders the signup HTML page."""
    return render_template("courier_signup.html") 

@courier.route('/submit_signup', methods=['POST'])
def submit_signup():
    """Handles the HTML Form submission."""
    # 1. Get Data from HTML Form
    name = request.form.get("first_name")  # Updated to match template
    surname = request.form.get("last_name")  # Updated to match template
    email = request.form.get("email")
    password = request.form.get("password")
    age = request.form.get("age")
    city = request.form.get("city")
    phone = request.form.get("phone")
    
    # 2. Get Courier Specific Data
    experience = request.form.get("experience", 0)
    expected_payment = request.form.get("expected_payment", 100)

    # 3. Hash Password
    if password:
        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    else:
        return "Password required", 400

    # 4. Calculate Payment Range (Logic: Max is 20% higher than min preference)
    expected_min = float(expected_payment)
    expected_max = expected_min * 1.2 

    db = db_helper.get_db_connection()
    cursor = db.cursor()

    query = """
        INSERT INTO Courier 
        (name, surname, email, password, Age, experience, expected_payment_min, expected_payment_max, 
         rating, ratingCount, taskCount) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0.0, 0, 0)
    """
    
    values = (name, surname, email, password_hash, age, experience, expected_min, expected_max)

    try:
        cursor.execute(query, values)
        db.commit()
        print("Courier Registered Successfully via Form")
        return redirect(url_for("courier.courier_login"))  # Go to login after signup
    except Exception as e:
        print(f"Error registering courier: {e}")
        db.rollback()
        return f"Registration Failed: {e}", 500
    finally:
        cursor.close()
        db.close()

# ==========================================
# API ROUTES (JSON - For Mobile/External Apps)
# ==========================================

@courier.route("/", methods=["GET"])
def get_all_couriers():
    """Fetches all couriers as JSON."""
    db = db_helper.get_db_connection()
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
    db = db_helper.get_db_connection()
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
        mycursor.close()
        db.close()

@courier.route("/", methods=["POST"])
def create_courier_api():
    """Creates a new courier via JSON (API style)."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No input data provided"}), 400
        
    # Extracting data
    name = data.get('name')
    surname = data.get('surname')
    email = data.get('email')
    password = data.get('password')
    age = data.get('age')
    gender = data.get('gender')
    marital_status = data.get('marital_status')
    experience = data.get('experience', 0)
    expected_payment = data.get('expected_payment', 100)
    r_id = data.get('r_id', None)

    # Validations
    if not email or not password or not name:
        return jsonify({"error": "Missing required fields: email, password, or name"}), 400

    # Hashing
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    
    # Calc Payment
    expected_min = float(expected_payment)
    expected_max = expected_min * 1.2

    db = db_helper.get_db_connection()
    if not db:
        return jsonify({"error": "Database connection failed"}), 500
        
    mycursor = db.cursor()
    try:
        query = """
            INSERT INTO Courier 
            (r_id, name, surname, email, password, Age, Gender, 
             Marital_Status, experience, expected_payment_min, expected_payment_max, rating, ratingCount, taskCount) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0.0, 0, 0)
        """
        values = (
            r_id, name, surname, email, password_hash, age, gender,
            marital_status, experience, expected_min, expected_max
        )
        mycursor.execute(query, values)
        db.commit()
        new_courier_id = mycursor.lastrowid
        
    except mysql.connector.Error as err:
        db.rollback() 
        return jsonify({"error": f"Database error: {err}"}), 500
    finally:
        mycursor.close()
        db.close()

    return jsonify({
        "message": "Courier created successfully",
        "c_id": new_courier_id
    }), 201