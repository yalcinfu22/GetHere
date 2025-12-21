from flask import Blueprint, render_template, request, redirect, url_for, session, current_app, jsonify, flash
import bcrypt
import uuid
from helpers import db_helper
import os
from werkzeug.utils import secure_filename

# Configuration for file uploads
UPLOAD_FOLDER = 'static/images/restaurants'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
                rm.rm_id,
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
            session['manager_id'] = manager_data['rm_id'] # The manager's unique ID
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
    manager_id = session.get('manager_id') # Get the specific manager's ID
    db = db_helper.get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        # Fetch data for the specific manager and their restaurant
        query = """
            SELECT 
                r.name as restaurant_name, r.city, r.address, r.cuisine, r.phone, r.description, r.photo_url,
                rm.name as manager_first_name, rm.surname as manager_last_name, rm.email
            FROM Restaurant r
            JOIN Restaurant_Manager rm ON r.r_id = rm.managesId
            WHERE r.r_id = %s AND rm.rm_id = %s
        """
        cursor.execute(query, (r_id, manager_id))
        data = cursor.fetchone() # Fetch the specific manager

        if not data:
            # This case might happen if data is inconsistent
            session.clear()
            flash('Your session was invalid. Please log in again.', 'warning')
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
    manager_id = session.get('manager_id') # Get manager's unique ID
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
        password = request.form.get("password")

        # Update Restaurant table (this is general for the restaurant)
        r_query = """
            UPDATE Restaurant 
            SET name=%s, city=%s, address=%s, cuisine=%s, phone=%s, description=%s
            WHERE r_id = %s
        """
        cursor.execute(r_query, (restaurant_name, city, address, cuisine, phone, description, r_id))

        # Start building the manager update query
        rm_query_parts = ["name=%s", "surname=%s", "email=%s"]
        rm_values = [manager_first_name, manager_last_name, email]

        # If a new password is provided, hash it and add to query
        if password:
            password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
            rm_query_parts.append("password=%s")
            rm_values.append(password_hash)

        # Finalize and execute the manager update query
        rm_query = f"UPDATE Restaurant_Manager SET {', '.join(rm_query_parts)} WHERE rm_id = %s"
        rm_values.append(manager_id)
        cursor.execute(rm_query, tuple(rm_values))

        db.commit()
        
        # Update the session if the manager's name changed
        session['manager_name'] = manager_first_name
        
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
    lic_no = request.form.get("lic_no") # New field
    link = request.form.get("link")     # New field
    
    manager_first_name = request.form.get("manager_first_name")
    manager_last_name = request.form.get("manager_last_name")
    email = request.form.get("email")
    password = request.form.get("password")

    if not all([restaurant_name, city, address, cuisine, phone, manager_first_name, email, password]):
        return "All required fields must be filled out.", 400

    db = db_helper.get_db_connection()
    cursor = db.cursor(dictionary=True)

    photo_filename = None
    if 'photo' in request.files:
        file = request.files['photo']
        if file and allowed_file(file.filename):
            photo_filename = secure_filename(file.filename)
            file.save(os.path.join(UPLOAD_FOLDER, photo_filename))

    try:
        # 1. Create Restaurant
        restaurant_query = """
            INSERT INTO Restaurant (name, city, address, cuisine, phone, description, photo_url, lic_no, link, rating, rating_count)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 3.0, 0)
        """
        restaurant_values = (restaurant_name, city, address, cuisine, phone, description, photo_filename, lic_no, link)
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
    user_type = session.get('user_type')
    user_id = session.get('user_id')

    db = db_helper.get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    try:
        # Fetch restaurant details including the photo
        cursor.execute("SELECT name, photo_url FROM Restaurant WHERE r_id = %s", (r_id,))
        restaurant_data = cursor.fetchone()
        
        if not restaurant_data:
            return "Restaurant not found", 404
            
    except Exception as e:
        print(f"Error fetching restaurant details: {e}")
        return "An error occurred", 500
    finally:
        cursor.close()
        db.close()

    is_manager = (user_type == 'restaurant' and str(user_id) == str(r_id))
    is_customer = (user_type == 'user')

    current_user = {
        "is_authenticated": user_id is not None,
        "username": session.get('manager_name') or session.get('restaurant_name') or session.get('user_name') or 'User',
        "id": user_id
    }
    
    return render_template(
        'restaurant_detail.html', 
        r_id=r_id, 
        restaurant=restaurant_data,
        is_manager=is_manager,
        is_customer=is_customer,
        current_user=current_user
    )

@restaurant.route('/<int:r_id>')
def restaurant_info(r_id):
    """Restaurant statistics and information page."""
    db = db_helper.get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    try:
        # 1. Basic Restaurant Info
        cursor.execute("SELECT * FROM Restaurant WHERE r_id = %s", (r_id,))
        restaurant_data = cursor.fetchone()
        if not restaurant_data:
            return "Restaurant not found", 404

        # 2. Key Performance Indicators (KPIs)
        kpi_query = """
            SELECT
                COUNT(o_id) AS total_orders,
                SUM(sales_amount) AS total_revenue,
                COUNT(DISTINCT user_id) AS unique_customers,
                AVG(sales_amount) AS avg_order_value
            FROM Orders
            WHERE r_id = %s
        """
        cursor.execute(kpi_query, (r_id,))
        kpi_data = cursor.fetchone()

        # 3. Menu Analysis
        menu_query = "SELECT COUNT(*) AS total_menu_items FROM Menu WHERE r_id = %s"
        cursor.execute(menu_query, (r_id,))
        menu_data = cursor.fetchone()

        # 4. Bestseller & Top Courier Spotlight (The Complex Query)
        spotlight_query = """
            SELECT
                c.name AS courier_name,
                f.item AS food_item,
                COUNT(o.o_id) AS delivery_count,
                AVG(o.courier_rate) AS avg_rating_for_this_item
            FROM Orders o
            JOIN Courier c ON o.c_id = c.c_id
            JOIN Menu m ON o.m_id = m.m_id
            JOIN Food f ON m.f_id = f.f_id
            WHERE
                o.r_id = %s
                AND m.f_id = (
                    SELECT m2.f_id
                    FROM Orders o2
                    JOIN Menu m2 ON o2.m_id = m2.m_id
                    WHERE o2.r_id = %s
                    GROUP BY m2.f_id
                    ORDER BY COUNT(o2.o_id) DESC
                    LIMIT 1
                )
            GROUP BY c.c_id, f.item
            ORDER BY delivery_count DESC, avg_rating_for_this_item DESC
            LIMIT 1;
        """
        cursor.execute(spotlight_query, (r_id, r_id))
        spotlight_data = cursor.fetchone()
        
        # Convert Decimal types to float for template rendering
        if restaurant_data and 'rating' in restaurant_data:
            restaurant_data['rating'] = float(restaurant_data['rating'])
        if kpi_data:
            if 'total_revenue' in kpi_data and kpi_data['total_revenue']:
                kpi_data['total_revenue'] = float(kpi_data['total_revenue'])
            if 'avg_order_value' in kpi_data and kpi_data['avg_order_value']:
                kpi_data['avg_order_value'] = float(kpi_data['avg_order_value'])
        if spotlight_data and 'avg_rating_for_this_item' in spotlight_data and spotlight_data['avg_rating_for_this_item']:
            spotlight_data['avg_rating_for_this_item'] = round(float(spotlight_data['avg_rating_for_this_item']), 2)

        return render_template(
            'restaurant_info.html',
            restaurant=restaurant_data,
            kpis=kpi_data,
            menu=menu_data,
            spotlight=spotlight_data
        )

    except Exception as e:
        print(f"Restaurant Info Page Error: {e}")
        return "An error occurred while fetching restaurant data.", 500
    finally:
        cursor.close()
        db.close()

@restaurant.route('/<int:r_id>/orders')
def restaurant_orders(r_id):
    """Restaurant orders page"""
    # Security check
    is_manager = (
        session.get('user_type') == 'restaurant' and
        str(session.get('user_id')) == str(r_id)
    )

    return render_template(
        'orders.html',
        r_id=r_id,
        is_manager=is_manager
    )

@restaurant.route('/<int:r_id>/<int:o_id>')
def restaurant_order_details(r_id, o_id):
    """Restaurant orders page"""
    # Security check
    is_manager = (
        session.get('user_type') == 'restaurant' and
        str(session.get('user_id')) == str(r_id)
    )

    return render_template(
        'order_detail.html',
        r_id=r_id,
        o_id=o_id,
        is_manager=is_manager
    )

@restaurant.route('/<int:r_id>/menu/<int:m_id>')
def make_order(r_id, m_id):
    user_type = session.get('user_type')
    user_id = session.get('user_id')

    is_customer = (user_type == 'user')

    db = db_helper.get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT 
                m.price,
                f.item AS food_name,
                f.veg_or_non_veg AS veg,
                m.cuisine
            FROM Menu m
            JOIN Food f ON m.f_id = f.f_id
            WHERE m.m_id = %s AND m.r_id = %s
        """, (m_id, r_id))

        menu = cursor.fetchone()
        if not menu:
            return "Menu item not found", 404

    finally:
        cursor.close()
        db.close()

    return render_template(
        'make_order.html',
        m_id=m_id,
        r_id=r_id,
        user_id=user_id,
        is_customer=is_customer,
        price=menu['price'],
        food_name=menu['food_name'],
        veg=menu['veg'],
        cuisine=menu['cuisine']
    )


@restaurant.route('/api/restaurants', methods=['GET'])
def list_restaurants():
    db = db_helper.get_db_connection()
    if not db:
        return jsonify({"error": "Database connection failed"}), 500

    cursor = db.cursor(dictionary=True)
    try:
        # Get parameters from request URL
        search_query = request.args.get('q')
        sort_by = request.args.get('sort_by')
        min_rating = request.args.get('min_rating')

        # Start building the query
        sql_query = """
            SELECT DISTINCT r.r_id, r.name, r.city, r.rating, r.cuisine, r.address, r.photo_url 
            FROM Restaurant r
            LEFT JOIN Menu m ON r.r_id = m.r_id
            LEFT JOIN Food f ON m.f_id = f.f_id
        """
        conditions = []
        params = []

        # Add search condition (Name OR Food Item OR Cuisine)
        if search_query:
            conditions.append("(r.name LIKE %s OR f.item LIKE %s OR r.cuisine LIKE %s OR m.cuisine LIKE %s)")
            wildcard = f"%{search_query}%"
            params.extend([wildcard, wildcard, wildcard, wildcard])
        
        # Add rating condition
        if min_rating and min_rating != 'any':
            try:
                rating_val = float(min_rating)
                conditions.append("r.rating >= %s")
                params.append(rating_val)
            except ValueError:
                pass # Ignore invalid rating values

        # Append WHERE clause if there are conditions
        if conditions:
            sql_query += " WHERE " + " AND ".join(conditions)

        # Add sorting
        if sort_by == 'rating':
            sql_query += " ORDER BY r.rating DESC"
        elif sort_by == 'popular':
            # Assuming popularity is based on rating for now
            sql_query += " ORDER BY r.rating DESC"
        # The 'delivery' sort option is not implemented as there's no data for it yet.

        # Add a limit to avoid sending too much data
        sql_query += " LIMIT 40"

        cursor.execute(sql_query, tuple(params))
        restaurants = cursor.fetchall()
        
        return jsonify(restaurants)
    except Exception as e:
        print(f"Error fetching restaurants: {e}")
        return jsonify({"error": "Failed to fetch restaurants"}), 500
    finally:
        cursor.close()
        db.close()

@restaurant.route('/api/<int:r_id>/opportunities', methods=['GET'])
def get_opportunities(r_id):
    db = db_helper.get_db_connection()
    cursor = db.cursor(dictionary=True)
    try:
        # Find top 5 items in global food catalog NOT in this restaurant's menu
        # Sorted by how many OTHER restaurants have them (popularity)
        sql = """
            SELECT f.f_id, f.item, f.veg_or_non_veg, COUNT(m.m_id) as popularity
            FROM Food f
            LEFT JOIN Menu m ON f.f_id = m.f_id
            WHERE f.f_id NOT IN (
                SELECT f_id FROM Menu WHERE r_id = %s
            )
            GROUP BY f.f_id
            ORDER BY popularity DESC
            LIMIT 5
        """
        cursor.execute(sql, (r_id,))
        items = cursor.fetchall()
        return jsonify(items)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        db.close()

@restaurant.route('/positions/create', methods=['POST'])
def create_position():
    """
    Creates a new position (job listing) for the logged-in restaurant manager's restaurant.
    Accepts both JSON and form data.
    """
    if session.get('user_type') != 'restaurant':
        return jsonify({"error": "Unauthorized"}), 401

    r_id = session.get('user_id') # Get r_id from session

    # Get data from either JSON or form
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()
    
    # Required fields
    payment = data.get('payment')
    
    if not payment:
        return jsonify({"error": "Payment is required"}), 400
    
    # Optional fields with defaults
    city = data.get('city')
    req_exp = data.get('req_exp', 0)
    req_rating = data.get('req_rating', 0)
    
    db = db_helper.get_db_connection()
    cursor = db.cursor(dictionary=True, buffered=True)
    
    try:
        # Verify restaurant exists (redundant since r_id comes from session, but good for data integrity)
        cursor.execute("SELECT r_id, name, city FROM Restaurant WHERE r_id = %s", (r_id,))
        restaurant_data = cursor.fetchone()
        
        if not restaurant_data:
            return jsonify({"error": "Restaurant not found in session"}), 404
        
        # Use restaurant's city from DB if not provided in form
        if not city:
            city = restaurant_data['city']
        
        # Insert new position
        cursor.execute("""
            INSERT INTO Positions (r_id, city, req_exp, req_rating, payment, isOpen)
            VALUES (%s, %s, %s, %s, %s, TRUE)
        """, (r_id, city, req_exp, req_rating, payment))
        
        db.commit()
        new_position_id = cursor.lastrowid
        
        return jsonify({
            "success": True,
            "message": "Position created successfully",
            "position_id": new_position_id,
            "restaurant_name": restaurant_data['name']
        }), 201

    except Exception as e:
        db.rollback()
        print(f"Create position error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        db.close()
@restaurant.route('/api/positions')
def get_positions():
    """
    API endpoint to get all open positions for the logged-in restaurant.
    """
    if session.get('user_type') != 'restaurant':
        return jsonify({"error": "Unauthorized"}), 401
    
    r_id = session.get('user_id')
    db = db_helper.get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT p_id, city, payment, req_exp, req_rating, created_at
            FROM Positions 
            WHERE r_id = %s AND isOpen = TRUE 
            ORDER BY created_at DESC
        """, (r_id,))
        
        positions = cursor.fetchall()
        
        # Convert decimal and datetime to string for JSON compatibility
        for pos in positions:
            if pos['payment']:
                pos['payment'] = str(pos['payment'])
            if pos['created_at']:
                pos['created_at'] = pos['created_at'].strftime('%Y-%m-%d %H:%M')
        
        return jsonify(positions)
        
    except Exception as e:
        print(f"API Get Positions Error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        db.close()

@restaurant.route('/api/positions/delete', methods=['POST'])
def delete_position():
    """
    Deletes a position for the logged-in restaurant.
    """
    if session.get('user_type') != 'restaurant':
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    p_id_to_delete = data.get('p_id')
    r_id = session.get('user_id')

    if not p_id_to_delete:
        return jsonify({"error": "Position ID is required"}), 400

    db = db_helper.get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        # Verify the position belongs to the restaurant before deleting
        cursor.execute("SELECT r_id FROM Positions WHERE p_id = %s", (p_id_to_delete,))
        position = cursor.fetchone()
        
        if not position:
            return jsonify({"error": "Position not found."}), 404
        
        if position['r_id'] != r_id:
            return jsonify({"error": "Forbidden. You can only delete your own positions."}), 403

        # Proceed with deletion
        cursor.execute("DELETE FROM Positions WHERE p_id = %s", (p_id_to_delete,))
        db.commit()
        
        if cursor.rowcount == 0:
            # This case is unlikely if we passed the check above, but for safety
            return jsonify({"error": "Position not found or already deleted."}), 404
            
        return jsonify({"message": "Position deleted successfully!"})

    except Exception as e:
        db.rollback()
        print(f"Delete position error: {e}")
        return jsonify({"error": "An internal error occurred."}), 500
    finally:
        cursor.close()
        db.close()

@restaurant.route('/api/managers', methods=['GET'])
def get_managers():
    if session.get('user_type') != 'restaurant':
        return jsonify({"error": "Unauthorized"}), 401
    
    r_id = session.get('user_id')
    db = db_helper.get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT rm_id, name, surname, email FROM Restaurant_Manager WHERE managesId = %s", (r_id,))
        managers = cursor.fetchall()
        return jsonify(managers)
    except Exception as e:
        print(f"API Get Managers Error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        db.close()

@restaurant.route('/api/managers/add', methods=['POST'])
def add_manager():
    if session.get('user_type') != 'restaurant':
        return jsonify({"error": "Unauthorized"}), 401

    r_id = session.get('user_id')
    data = request.get_json()
    name = data.get('name')
    surname = data.get('surname')
    email = data.get('email')
    password = data.get('password')

    if not all([name, email, password]):
        return jsonify({"error": "Name, email, and password are required"}), 400

    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    
    db = db_helper.get_db_connection()
    cursor = db.cursor()

    try:
        cursor.execute("""
            INSERT INTO Restaurant_Manager (name, surname, email, password, managesId)
            VALUES (%s, %s, %s, %s, %s)
        """, (name, surname, email, password_hash, r_id))
        db.commit()
        return jsonify({"message": "Manager added successfully!"}), 201
    except Exception as e:
        db.rollback()
        print(f"Add manager error: {e}")
        return jsonify({"error": "Failed to add manager"}), 500
    finally:
        cursor.close()
        db.close()

@restaurant.route('/api/managers/delete', methods=['POST'])
def delete_manager():
    """
    Deletes a manager, ensuring at least one manager remains and a manager cannot delete themselves.
    """
    if session.get('user_type') != 'restaurant':
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    rm_id_to_delete = data.get('rm_id')
    current_manager_id = session.get('manager_id')
    r_id = session.get('user_id')

    if not rm_id_to_delete:
        return jsonify({"error": "Manager ID is required"}), 400

    if rm_id_to_delete == current_manager_id:
        return jsonify({"error": "You cannot delete your own account from this panel."}), 403

    db = db_helper.get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        # Check how many managers are left
        cursor.execute("SELECT COUNT(*) as count FROM Restaurant_Manager WHERE managesId = %s", (r_id,))
        manager_count = cursor.fetchone()['count']

        if manager_count <= 1:
            return jsonify({"error": "Cannot delete the last manager of the restaurant."}), 403

        # Proceed with deletion
        cursor.execute("DELETE FROM Restaurant_Manager WHERE rm_id = %s", (rm_id_to_delete,))
        db.commit()
        
        if cursor.rowcount == 0:
            return jsonify({"error": "Manager not found or already deleted."}), 404
            
        return jsonify({"message": "Manager deleted successfully!"})

    except Exception as e:
        db.rollback()
        print(f"Delete manager error: {e}")
        return jsonify({"error": "An internal error occurred."}), 500
    finally:
        cursor.close()
        db.close()
