from flask import Blueprint, render_template, request, redirect, url_for, session, current_app, jsonify, flash
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
    
    db = db_helper.get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    try:
        # Use explicit column aliases to avoid name collision
        query = """
            SELECT
                rm.name AS manager_name,
                rm.password,
                r.r_id,
                r.name AS restaurant_name
            FROM Restaurant_Manager rm
            JOIN Restaurant r ON rm.managesId = r.r_id
            WHERE rm.email = %s
        """
        cursor.execute(query, (email,))
        manager_data = cursor.fetchone()
        
        if manager_data and bcrypt.checkpw(password.encode("utf-8"), manager_data['password'].encode("utf-8")):
            # Store all relevant info in the session
            session['user_id'] = manager_data['r_id'] # The restaurant ID
            session['user_type'] = 'restaurant'
            session['restaurant_name'] = manager_data['restaurant_name']
            session['manager_name'] = manager_data['manager_name']
            
            # Redirect to the new dashboard
            return redirect(url_for('restaurant.restaurant_dashboard'))
        else:
            return "Invalid email or password", 401
    except Exception as e:
        print(f"Login error: {e}")
        return f"An error occurred: {e}", 500
    finally:
        cursor.close()
        db.close()

@restaurant.route('/dashboard')
def restaurant_dashboard():
    """Display the restaurant manager's dashboard."""
    # Protect the route: only logged-in restaurant managers can see it
    if session.get('user_type') != 'restaurant':
        return redirect(url_for('restaurant.restaurant_login'))

    r_id = session.get('user_id')
    db = db_helper.get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        # Fetch all data for the restaurant and its manager
        query = """
            SELECT 
                r.name as restaurant_name, r.city, r.address, r.cuisine, r.phone, r.description,
                rm.name as manager_first_name, rm.surname as manager_last_name, rm.email
            FROM Restaurant r
            JOIN Restaurant_Manager rm ON r.r_id = rm.managesId
            WHERE r.r_id = %s
        """
        cursor.execute(query, (r_id,))
        data = cursor.fetchone()

        if not data:
            # This case might happen if data is inconsistent
            session.clear()
            return redirect(url_for('restaurant.restaurant_login'))

        return render_template('restaurant_dashboard.html', data=data)

    except Exception as e:
        print(f"Dashboard error: {e}")
        return "An error occurred while fetching your data.", 500
    finally:
        cursor.close()
        db.close()

@restaurant.route('/update', methods=['POST'])
def restaurant_update():
    """Handle updates for restaurant and manager info."""
    if session.get('user_type') != 'restaurant':
        return redirect(url_for('restaurant.restaurant_login'))

    r_id = session.get('user_id')
    db = db_helper.get_db_connection()
    cursor = db.cursor()

    try:
        # Get data from form
        restaurant_name = request.form.get("restaurant_name")
        city = request.form.get("city")
        address = request.form.get("address")
        cuisine = request.form.get("cuisine")
        phone = request.form.get("phone")
        description = request.form.get("description")
        
        manager_first_name = request.form.get("manager_first_name")
        manager_last_name = request.form.get("manager_last_name")
        email = request.form.get("email")

        # Update Restaurant table
        r_query = """
            UPDATE Restaurant 
            SET name=%s, city=%s, address=%s, cuisine=%s, phone=%s, description=%s
            WHERE r_id = %s
        """
        cursor.execute(r_query, (restaurant_name, city, address, cuisine, phone, description, r_id))

        # Update Restaurant_Manager table
        rm_query = """
            UPDATE Restaurant_Manager
            SET name=%s, surname=%s, email=%s
            WHERE managesId = %s
        """
        cursor.execute(rm_query, (manager_first_name, manager_last_name, email, r_id))

        db.commit()
        flash('Your information has been updated successfully!', 'success')

    except Exception as e:
        db.rollback()
        print(f"Update error: {e}")
        flash('An error occurred during the update.', 'danger')
    finally:
        cursor.close()
        db.close()
    
    return redirect(url_for('restaurant.restaurant_dashboard'))

@restaurant.route('/delete', methods=['POST'])
def restaurant_delete():
    """Handle deletion of a restaurant and its manager account."""
    if session.get('user_type') != 'restaurant':
        return redirect(url_for('restaurant.restaurant_login'))

    r_id = session.get('user_id')
    db = db_helper.get_db_connection()
    cursor = db.cursor()

    try:
        cursor.execute("DELETE FROM Restaurant WHERE r_id = %s", (r_id,))
        
        if cursor.rowcount == 1:
            db.commit()
            flash('Your account and restaurant have been permanently deleted.', 'success')
            session.clear()
            return redirect(url_for('home_page.home_page'))
        else:
            db.rollback()
            flash('Error: Your account could not be found for deletion.', 'danger')
            return redirect(url_for('restaurant.restaurant_dashboard'))
            
    except Exception as e:
        db.rollback()
        print(f"Delete error: {e}")
        flash('An error occurred during account deletion.', 'danger')
        return redirect(url_for('restaurant.restaurant_dashboard'))
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
    # Get restaurant and manager details from the form
    restaurant_name = request.form.get("restaurant_name")
    city = request.form.get("city")
    address = request.form.get("address")
    cuisine = request.form.get("cuisine")
    phone = request.form.get("phone")
    description = request.form.get("description", "")
    
    manager_first_name = request.form.get("manager_first_name")
    manager_last_name = request.form.get("manager_last_name")
    email = request.form.get("email")
    password = request.form.get("password")

    if not all([restaurant_name, city, address, cuisine, phone, manager_first_name, email, password]):
        return "All required fields must be filled out.", 400

    db = db_helper.get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        # 1. Create Restaurant
        secret_key = uuid.uuid4().hex
        restaurant_query = """
            INSERT INTO Restaurant (name, city, address, cuisine, phone, description, secret)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        restaurant_values = (restaurant_name, city, address, cuisine, phone, description, secret_key)
        cursor.execute(restaurant_query, restaurant_values)
        new_restaurant_id = cursor.lastrowid

        # 2. Create Restaurant Manager
        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        manager_query = """
            INSERT INTO Restaurant_Manager (name, surname, email, password, managesId)
            VALUES (%s, %s, %s, %s, %s)
        """
        manager_values = (manager_first_name, manager_last_name, email, password_hash, new_restaurant_id)
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

    return redirect(url_for("restaurant.restaurant_login"))

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


@restaurant.route('/<int:r_id>/orders')
def restaurant_orders(r_id):
    """Restaurant orders page"""
    # DEMO MODE: Always admin
    is_manager = True
    # is_manager = (
    #     session.get('user_type') == 'restaurant' and
    #     str(session.get('user_id')) == str(r_id)
    # )

    return render_template(
        'orders.html',
        r_id=r_id,
        is_manager=is_manager
    )

@restaurant.route('/<int:r_id>/<int:o_id>')
def restaurant_order_details(r_id, o_id):
    """Restaurant orders page"""
    # DEMO MODE: Always admin
    is_manager = True
    # is_manager = (
    #     session.get('user_type') == 'restaurant' and
    #     str(session.get('user_id')) == str(r_id)
    # )

    return render_template(
        'order_detail.html',
        r_id=r_id,
        o_id=o_id,
        is_manager=is_manager
    )

@restaurant.route('/api/restaurants', methods=['GET'])
def list_restaurants():
    db = db_helper.get_db_connection()
    if not db:
        return jsonify({"error": "Database connection failed"}), 500

    cursor = db.cursor(dictionary=True)
    try:
        search_query = request.args.get('q')
        
        if search_query:
            sql_query = "SELECT r_id, name, city, rating, cuisine, address FROM Restaurant WHERE name LIKE %s LIMIT 20"
            cursor.execute(sql_query, (f"%{search_query}%",))
        else:
            sql_query = "SELECT r_id, name, city, rating, cuisine, address FROM Restaurant LIMIT 20"
            cursor.execute(sql_query)
            
        restaurants = cursor.fetchall()
        return jsonify(restaurants)
    except Exception as e:
        print(f"Error fetching restaurants: {e}")
        return jsonify({"error": "Failed to fetch restaurants"}), 500
    finally:
        cursor.close()
        db.close()
