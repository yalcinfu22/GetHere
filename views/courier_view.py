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
    cursor = db.cursor(dictionary=True, buffered=True)  # Added buffered=True
    
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
    cursor = db.cursor(dictionary=True, buffered=True)
    
    try:
        cursor.execute("""
            SELECT c_id, name, surname, r_id, rating, ratingCount, taskCount 
            FROM Courier 
            WHERE c_id = %s
        """, (courier_id,))
        courier_info = cursor.fetchone()
        
        # Update session with latest r_id
        session['courier_r_id'] = courier_info.get('r_id')

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
    """
    Courier Profile Page - View and edit courier information.
    """
    if 'user_id' not in session or session.get('user_type') != 'courier':
        return redirect(url_for('courier.courier_login'))
    
    courier_id = session['user_id']
    db = db_helper.get_db_connection()
    cursor = db.cursor(dictionary=True, buffered=True)
    
    try:
        cursor.execute("""
            SELECT c_id, r_id, name, surname, email, Age, Gender, Marital_Status,
                   experience, rating, ratingCount, taskCount, TotalDeliveries,
                   expected_payment_min, expected_payment_max, created_at
            FROM Courier 
            WHERE c_id = %s
        """, (courier_id,))
        courier_info = cursor.fetchone()
        
        if not courier_info:
            return "Courier not found", 404
        
        # Convert Decimals to float for template
        if courier_info['rating']:
            courier_info['rating'] = float(courier_info['rating'])
        if courier_info['expected_payment_min']:
            courier_info['expected_payment_min'] = float(courier_info['expected_payment_min'])
        if courier_info['expected_payment_max']:
            courier_info['expected_payment_max'] = float(courier_info['expected_payment_max'])
        
        # Get restaurant name if employed
        restaurant_name = None
        if courier_info['r_id']:
            cursor.execute("SELECT name FROM Restaurant WHERE r_id = %s", (courier_info['r_id'],))
            restaurant = cursor.fetchone()
            restaurant_name = restaurant['name'] if restaurant else None
        
        return render_template('courier_profile.html',
                             courier=courier_info,
                             restaurant_name=restaurant_name)

    except Exception as e:
        print(f"Profile page error: {e}")
        return f"Error: {e}", 500
    finally:
        cursor.close()
        db.close()


@courier.route('/profile/update', methods=['POST'])
def update_profile():
    """
    Update courier profile information.
    """
    if 'user_id' not in session or session.get('user_type') != 'courier':
        return redirect(url_for('courier.courier_login'))
    
    courier_id = session['user_id']
    
    # Get form data
    name = request.form.get('first_name')
    surname = request.form.get('last_name')
    email = request.form.get('email')
    password = request.form.get('password')
    age = request.form.get('age')
    gender = request.form.get('gender')
    marital_status = request.form.get('marital_status')
    experience = request.form.get('experience')
    expected_payment_min = request.form.get('expected_payment_min')
    
    db = db_helper.get_db_connection()
    cursor = db.cursor(dictionary=True, buffered=True)
    
    try:
        # Build update query dynamically
        update_fields = []
        params = []
        
        if name:
            update_fields.append("name = %s")
            params.append(name)
        if surname:
            update_fields.append("surname = %s")
            params.append(surname)
        if email:
            update_fields.append("email = %s")
            params.append(email)
        if password and password.strip():
            password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
            update_fields.append("password = %s")
            params.append(password_hash)
        if age:
            update_fields.append("Age = %s")
            params.append(int(age))
        if gender:
            update_fields.append("Gender = %s")
            params.append(gender)
        if marital_status:
            update_fields.append("Marital_Status = %s")
            params.append(marital_status)
        if experience is not None and experience != '':
            update_fields.append("experience = %s")
            params.append(int(experience))
        if expected_payment_min:
            min_pay = float(expected_payment_min)
            max_pay = min_pay * 1.2
            update_fields.append("expected_payment_min = %s")
            update_fields.append("expected_payment_max = %s")
            params.append(min_pay)
            params.append(max_pay)
        
        if update_fields:
            params.append(courier_id)
            query = f"UPDATE Courier SET {', '.join(update_fields)} WHERE c_id = %s"
            cursor.execute(query, params)
            db.commit()
            
            # Update session name if changed
            if name:
                session['user_name'] = name
            if surname:
                session['user_surname'] = surname
        
        return redirect(url_for('courier.profile_page'))

    except Exception as e:
        db.rollback()
        print(f"Update profile error: {e}")
        return f"Error updating profile: {e}", 500
    finally:
        cursor.close()
        db.close()


@courier.route('/rate/<int:courier_id>', methods=['POST'])
def rate_courier(courier_id):
    """
    Rate a courier after delivery.
    
    IMPORTANT: New couriers start with 3.0 rating (trust score).
    To preserve this trust weight, we calculate as if they have 1 initial rating:
    
    Formula: new_rating = (current_rating * (ratingCount + 1) + new_score) / (ratingCount + 2)
    
    This ensures the initial 3.0 trust rating has weight in the calculation.
    """
    # Get rating from request
    if request.is_json:
        data = request.get_json()
        new_score = data.get('rating')
    else:
        new_score = request.form.get('rating')
    
    if new_score is None:
        return jsonify({"error": "Rating is required"}), 400
    
    try:
        new_score = float(new_score)
        if new_score < 0 or new_score > 5:
            return jsonify({"error": "Rating must be between 0 and 5"}), 400
    except ValueError:
        return jsonify({"error": "Invalid rating value"}), 400
    
    db = db_helper.get_db_connection()
    cursor = db.cursor(dictionary=True, buffered=True)
    
    try:
        # Get current courier rating info
        cursor.execute("""
            SELECT c_id, rating, ratingCount 
            FROM Courier 
            WHERE c_id = %s
        """, (courier_id,))
        courier = cursor.fetchone()
        
        if not courier:
            return jsonify({"error": "Courier not found"}), 404
        
        current_rating = float(courier['rating'] or 3.0)
        rating_count = int(courier['ratingCount'] or 0)
        
        # Calculate new rating with trust weight (+1 for initial trust rating)
        # Formula: (current_rating * (ratingCount + 1) + new_score) / (ratingCount + 2)
        # This treats the initial 3.0 as a real rating that counts
        weighted_sum = current_rating * (rating_count + 1) + new_score
        new_rating = weighted_sum / (rating_count + 2)
        
        # Round to 1 decimal place
        new_rating = round(new_rating, 1)
        
        # Update courier
        cursor.execute("""
            UPDATE Courier 
            SET rating = %s, ratingCount = ratingCount + 1 
            WHERE c_id = %s
        """, (new_rating, courier_id))
        
        db.commit()
        
        return jsonify({
            "success": True,
            "message": "Courier rated successfully",
            "previous_rating": current_rating,
            "new_rating": new_rating,
            "total_ratings": rating_count + 1
        })

    except Exception as e:
        db.rollback()
        print(f"Rate courier error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        db.close()


@courier.route('/tasks/active')
def active_tasks_page():
    return "Detailed Active Tasks Page (To Be Implemented)"


@courier.route('/tasks/api/details/<int:task_id>', methods=['GET'])
def get_task_details(task_id):
    """
    API Endpoint to get full task details for the modal.
    Returns: customer info, food details, order info, addresses.
    """
    if 'user_id' not in session or session.get('user_type') != 'courier':
        return jsonify({"error": "Unauthorized"}), 401
    
    courier_id = session['user_id']
    db = db_helper.get_db_connection()
    cursor = db.cursor(dictionary=True, buffered=True)
    
    try:
        # Get complete task details with all related info
        cursor.execute("""
            SELECT 
                t.t_id, t.o_id, t.c_id, t.user_id, t.m_id, t.task_date, 
                t.user_address, t.status,
                u.name as customer_name, 
                u.email as customer_email, u.address as customer_full_address,
                u.city as customer_city,
                o.sales_qty, o.sales_amount, o.currency, o.order_date,
                f.item as food_name, f.veg_or_non_veg,
                m.price as food_price, m.cuisine as food_cuisine
            FROM Task t
            JOIN User u ON t.user_id = u.user_id
            JOIN Orders o ON t.o_id = o.o_id
            LEFT JOIN Menu m ON t.m_id = m.m_id
            LEFT JOIN Food f ON m.f_id = f.f_id
            WHERE t.t_id = %s AND t.c_id = %s
        """, (task_id, courier_id))
        
        task = cursor.fetchone()
        
        if not task:
            return jsonify({"error": "Task not found or does not belong to you"}), 404
        
        # Convert Decimal/datetime for JSON
        if task['sales_amount']:
            task['sales_amount'] = float(task['sales_amount'])
        if task['food_price']:
            task['food_price'] = float(task['food_price'])
        if task['task_date']:
            task['task_date'] = task['task_date'].strftime('%Y-%m-%d %H:%M')
        if task['order_date']:
            task['order_date'] = task['order_date'].strftime('%Y-%m-%d %H:%M')
        
        return jsonify({"success": True, "task": task})

    except Exception as e:
        print(f"Get task details error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        db.close()


@courier.route('/tasks/complete/<int:task_id>', methods=['POST'])
def complete_task(task_id):
    """
    Complete a delivery task.
    This will:
    1. Set Task.status = 1 (completed)
    2. Set Orders.IsDelivered = TRUE
    3. Increment Positions.deliveries_made (if courier has a position)
    4. Increment Courier.TotalDeliveries
    5. Decrement Courier.taskCount (active tasks)
    """
    if 'user_id' not in session or session.get('user_type') != 'courier':
        return jsonify({"error": "Unauthorized"}), 401
    
    courier_id = session['user_id']
    db = db_helper.get_db_connection()
    cursor = db.cursor(dictionary=True, buffered=True)
    
    try:
        # Verify task belongs to this courier and is not completed
        cursor.execute("""
            SELECT t.t_id, t.c_id, t.status, t.o_id, c.r_id
            FROM Task t
            JOIN Courier c ON t.c_id = c.c_id
            WHERE t.t_id = %s AND t.c_id = %s
        """, (task_id, courier_id))
        task = cursor.fetchone()
        
        if not task:
            return jsonify({"error": "Task not found or does not belong to you"}), 404
        
        if task['status'] == 1:
            return jsonify({"error": "Task is already completed"}), 400
        
        # 1. Mark task as completed
        cursor.execute("""
            UPDATE Task SET status = 1 WHERE t_id = %s
        """, (task_id,))
        
        # 2. Update Order.IsDelivered = TRUE
        cursor.execute("""
            UPDATE Orders SET IsDelivered = TRUE WHERE o_id = %s
        """, (task['o_id'],))
        
        # 3. Increment deliveries_made in Positions (if courier has a position)
        if task['r_id']:
            cursor.execute("""
                UPDATE Positions 
                SET deliveries_made = deliveries_made + 1 
                WHERE c_id = %s AND r_id = %s
            """, (courier_id, task['r_id']))
        
        # 4. Update Courier: increment TotalDeliveries, decrement taskCount (if > 0)
        cursor.execute("""
            UPDATE Courier 
            SET TotalDeliveries = TotalDeliveries + 1,
                taskCount = GREATEST(taskCount - 1, 0)
            WHERE c_id = %s
        """, (courier_id,))
        
        db.commit()
        
        return jsonify({
            "success": True,
            "message": "Delivery completed successfully!"
        })

    except Exception as e:
        db.rollback()
        print(f"Complete task error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        db.close()

@courier.route('/restaurant/my')
def my_restaurant_page():
    """
    My Restaurant page - Shows details of the restaurant where courier works.
    Includes option to leave the position.
    """
    if 'user_id' not in session or session.get('user_type') != 'courier':
        return redirect(url_for('courier.courier_login'))
    
    courier_id = session['user_id']
    db = db_helper.get_db_connection()
    cursor = db.cursor(dictionary=True, buffered=True)
    
    try:
        # Get courier info with restaurant
        cursor.execute("""
            SELECT c.c_id, c.name, c.surname, c.r_id, c.rating, c.experience, c.taskCount
            FROM Courier c
            WHERE c.c_id = %s
        """, (courier_id,))
        courier_info = cursor.fetchone()
        
        # Check if courier has a restaurant
        if not courier_info or not courier_info['r_id']:
            return render_template('my_restaurant.html', 
                                 courier=courier_info, 
                                 restaurant=None, 
                                 position=None)
        
        # Get restaurant details
        cursor.execute("""
            SELECT r.r_id, r.name, r.city, r.rating, r.rating_count, 
                   r.cuisine, r.address, r.link, r.cost, r.lic_no
            FROM Restaurant r
            WHERE r.r_id = %s
        """, (courier_info['r_id'],))
        restaurant = cursor.fetchone()
        
        # Get position details (payment info)
        cursor.execute("""
            SELECT p.p_id, p.payment, p.deliveries_made, p.created_at
            FROM Positions p
            WHERE p.c_id = %s AND p.r_id = %s
        """, (courier_id, courier_info['r_id']))
        position = cursor.fetchone()
        
        # Convert Decimal to float for template
        if restaurant and restaurant['rating']:
            restaurant['rating'] = float(restaurant['rating'])
        if position:
            if position['payment']:
                position['payment'] = float(position['payment'])
            if position['deliveries_made'] is None:
                position['deliveries_made'] = 0
        
        return render_template('my_restaurant.html',
                             courier=courier_info,
                             restaurant=restaurant,
                             position=position)

    except Exception as e:
        print(f"My Restaurant page error: {e}")
        return f"Error: {e}", 500
    finally:
        cursor.close()
        db.close()


@courier.route('/restaurant/leave', methods=['POST'])
def leave_restaurant():
    """
    Leave current restaurant position.
    This will:
    1. Set courier's r_id to NULL
    2. Delete the position from Positions table
    """
    if 'user_id' not in session or session.get('user_type') != 'courier':
        return jsonify({"error": "Unauthorized"}), 401
    
    courier_id = session['user_id']
    db = db_helper.get_db_connection()
    cursor = db.cursor(dictionary=True, buffered=True)
    
    try:
        # Get current courier info
        cursor.execute("""
            SELECT c_id, r_id, name, surname
            FROM Courier 
            WHERE c_id = %s
        """, (courier_id,))
        courier_info = cursor.fetchone()
        
        if not courier_info:
            return jsonify({"error": "Courier not found"}), 404
        
        if not courier_info['r_id']:
            return jsonify({"error": "You are not currently employed at any restaurant"}), 400
        
        restaurant_id = courier_info['r_id']
        
        # Get restaurant name for confirmation message
        cursor.execute("SELECT name FROM Restaurant WHERE r_id = %s", (restaurant_id,))
        restaurant = cursor.fetchone()
        restaurant_name = restaurant['name'] if restaurant else "Unknown"
        
        # Delete the position (this removes the job listing)
        cursor.execute("""
            DELETE FROM Positions 
            WHERE c_id = %s AND r_id = %s
        """, (courier_id, restaurant_id))
        
        # Update courier's r_id to NULL
        cursor.execute("""
            UPDATE Courier 
            SET r_id = NULL 
            WHERE c_id = %s
        """, (courier_id,))
        
        db.commit()
        
        # Update session
        session['courier_r_id'] = None
        
        return jsonify({
            "success": True,
            "message": f"You have successfully left {restaurant_name}. You can now apply to new positions."
        })

    except Exception as e:
        db.rollback()
        print(f"Leave restaurant error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        db.close()


# ==========================================
# POSITIONS SYSTEM - Search & Apply
# ==========================================

@courier.route('/positions/debug', methods=['GET'])
def debug_positions():
    """Debug endpoint to check positions in database."""
    db = db_helper.get_db_connection()
    cursor = db.cursor(dictionary=True, buffered=True)
    
    try:
        # Count positions
        cursor.execute("SELECT COUNT(*) as count FROM Positions")
        total = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM Positions WHERE isOpen = TRUE")
        open_count = cursor.fetchone()['count']
        
        # Get sample positions
        cursor.execute("""
            SELECT p.p_id, p.r_id, p.city, p.req_exp, p.req_rating, p.payment, p.isOpen,
                   r.name as restaurant_name
            FROM Positions p
            LEFT JOIN Restaurant r ON p.r_id = r.r_id
            LIMIT 10
        """)
        positions = cursor.fetchall()
        
        # Convert Decimals
        for pos in positions:
            pos['payment'] = float(pos['payment']) if pos['payment'] else 0
            pos['req_rating'] = float(pos['req_rating']) if pos['req_rating'] else 0
        
        return jsonify({
            "total_positions": total,
            "open_positions": open_count,
            "sample_positions": positions
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        db.close()


@courier.route('/positions/search')
def search_positions_page():
    """
    Search Jobs Page - Shows available positions with filtering.
    Displays highest paying jobs prominently and allows search by various criteria.
    """
    if 'user_id' not in session or session.get('user_type') != 'courier':
        return redirect(url_for('courier.courier_login'))
    
    courier_id = session['user_id']
    db = db_helper.get_db_connection()
    cursor = db.cursor(dictionary=True, buffered=True)
    
    try:
        # Get current courier info for eligibility checking
        cursor.execute("""
            SELECT c_id, name, surname, r_id, rating, experience, taskCount 
            FROM Courier 
            WHERE c_id = %s
        """, (courier_id,))
        courier_info = cursor.fetchone()
        
        # Get all unique cities for filter dropdown
        cursor.execute("SELECT DISTINCT city FROM Positions WHERE isOpen = TRUE AND city IS NOT NULL")
        cities = [row['city'] for row in cursor.fetchall()]
        
        # Get all restaurants that have open positions for filter dropdown
        cursor.execute("""
            SELECT DISTINCT r.r_id, r.name 
            FROM Positions p
            JOIN Restaurant r ON p.r_id = r.r_id
            WHERE p.isOpen = TRUE
            ORDER BY r.name
        """)
        restaurants = cursor.fetchall()
        
        return render_template('search_positions.html',
                             courier=courier_info,
                             cities=cities,
                             restaurants=restaurants)

    except Exception as e:
        print(f"Search positions page error: {e}")
        return f"Error: {e}", 500
    finally:
        cursor.close()
        db.close()


@courier.route('/positions/api/search', methods=['GET'])
def api_search_positions():
    """
    API Endpoint to search/filter positions.
    Query params: min_payment, restaurant_id, city, eligible_only, sort_by
    """
    if 'user_id' not in session or session.get('user_type') != 'courier':
        return jsonify({"error": "Unauthorized"}), 401
    
    courier_id = session['user_id']
    
    # Get filter parameters
    min_payment = request.args.get('min_payment', type=float)
    restaurant_id = request.args.get('restaurant_id', type=int)
    city = request.args.get('city', type=str)
    eligible_only = request.args.get('eligible_only', 'false').lower() == 'true'
    sort_by = request.args.get('sort_by', 'payment_desc')  # payment_desc, rating_req, exp_req
    
    print(f"[DEBUG] Search params: min_payment={min_payment}, restaurant_id={restaurant_id}, city={city}, eligible_only={eligible_only}, sort_by={sort_by}")
    
    db = db_helper.get_db_connection()
    cursor = db.cursor(dictionary=True, buffered=True)
    
    try:
        # Get courier info for eligibility
        cursor.execute("""
            SELECT c_id, rating, experience, r_id 
            FROM Courier 
            WHERE c_id = %s
        """, (courier_id,))
        courier_info = cursor.fetchone()
        
        print(f"[DEBUG] Courier info: rating={courier_info['rating']}, experience={courier_info['experience']}")
        
        # Build dynamic query
        query = """
            SELECT p.p_id, p.r_id, p.city, p.req_exp, p.req_rating, p.payment, p.isOpen,
                   r.name as restaurant_name, r.cuisine, r.rating as restaurant_rating
            FROM Positions p
            JOIN Restaurant r ON p.r_id = r.r_id
            WHERE p.isOpen = TRUE
        """
        params = []
        
        # Apply filters
        if min_payment is not None:
            query += " AND p.payment >= %s"
            params.append(min_payment)
        
        if restaurant_id:
            query += " AND p.r_id = %s"
            params.append(restaurant_id)
        
        if city:
            query += " AND p.city = %s"
            params.append(city)
        
        if eligible_only:
            # Filter by eligibility: courier rating >= req_rating AND experience >= req_exp
            courier_rating = float(courier_info['rating'] or 0)
            courier_exp = int(courier_info['experience'] or 0)
            query += " AND (p.req_rating IS NULL OR p.req_rating <= %s)"
            params.append(courier_rating)
            query += " AND (p.req_exp IS NULL OR p.req_exp <= %s)"
            params.append(courier_exp)
            print(f"[DEBUG] Filtering eligible: req_rating <= {courier_rating}, req_exp <= {courier_exp}")
        
        # Sorting
        if sort_by == 'payment_desc':
            query += " ORDER BY p.payment DESC"
        elif sort_by == 'rating_req':
            query += " ORDER BY p.req_rating ASC"
        elif sort_by == 'exp_req':
            query += " ORDER BY p.req_exp ASC"
        else:
            query += " ORDER BY p.payment DESC"
        
        print(f"[DEBUG] Final query: {query}")
        print(f"[DEBUG] Params: {params}")
        
        cursor.execute(query, params)
        positions = cursor.fetchall()
        
        print(f"[DEBUG] Found {len(positions)} positions")
        
        # Add eligibility status to each position
        for pos in positions:
            rating_ok = (pos['req_rating'] is None or float(pos['req_rating'] or 0) <= float(courier_info['rating'] or 0))
            exp_ok = (pos['req_exp'] is None or int(pos['req_exp'] or 0) <= int(courier_info['experience'] or 0))
            pos['is_eligible'] = rating_ok and exp_ok
            pos['already_employed'] = courier_info['r_id'] is not None
            
            # Convert Decimal to float for JSON serialization
            pos['payment'] = float(pos['payment']) if pos['payment'] else 0
            pos['req_rating'] = float(pos['req_rating']) if pos['req_rating'] else 0
            pos['req_exp'] = int(pos['req_exp']) if pos['req_exp'] else 0
            pos['restaurant_rating'] = float(pos['restaurant_rating']) if pos['restaurant_rating'] else 0
        
        return jsonify({
            "positions": positions,
            "courier": {
                "rating": float(courier_info['rating'] or 0),
                "experience": int(courier_info['experience'] or 0),
                "already_employed": courier_info['r_id'] is not None
            },
            "debug": {
                "eligible_only": eligible_only,
                "total_found": len(positions)
            }
        })

    except Exception as e:
        print(f"Search positions API error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        db.close()


@courier.route('/positions/api/top', methods=['GET'])
def api_top_positions():
    """
    API Endpoint to get top paying positions (for featured section).
    Returns top 5 highest paying open positions.
    """
    if 'user_id' not in session or session.get('user_type') != 'courier':
        return jsonify({"error": "Unauthorized"}), 401
    
    courier_id = session['user_id']
    
    print(f"[DEBUG TOP] Fetching top positions for courier_id={courier_id}")
    
    db = db_helper.get_db_connection()
    cursor = db.cursor(dictionary=True, buffered=True)
    
    try:
        # Get courier info
        cursor.execute("""
            SELECT c_id, rating, experience, r_id 
            FROM Courier 
            WHERE c_id = %s
        """, (courier_id,))
        courier_info = cursor.fetchone()
        
        print(f"[DEBUG TOP] Courier info: {courier_info}")
        
        # Get top 5 highest paying positions
        cursor.execute("""
            SELECT p.p_id, p.r_id, p.city, p.req_exp, p.req_rating, p.payment,
                   r.name as restaurant_name, r.cuisine, r.rating as restaurant_rating
            FROM Positions p
            JOIN Restaurant r ON p.r_id = r.r_id
            WHERE p.isOpen = TRUE
            ORDER BY p.payment DESC
            LIMIT 5
        """)
        positions = cursor.fetchall()
        
        print(f"[DEBUG TOP] Found {len(positions)} top positions")
        
        # Add eligibility status
        for pos in positions:
            courier_rating = float(courier_info['rating'] or 0)
            courier_exp = int(courier_info['experience'] or 0)
            req_rating = float(pos['req_rating'] or 0)
            req_exp = int(pos['req_exp'] or 0)
            
            rating_ok = req_rating == 0 or courier_rating >= req_rating
            exp_ok = req_exp == 0 or courier_exp >= req_exp
            pos['is_eligible'] = rating_ok and exp_ok
            pos['already_employed'] = courier_info['r_id'] is not None
            
            # Convert Decimal to float
            pos['payment'] = float(pos['payment']) if pos['payment'] else 0
            pos['req_rating'] = float(pos['req_rating']) if pos['req_rating'] else 0
            pos['req_exp'] = int(pos['req_exp']) if pos['req_exp'] else 0
            pos['restaurant_rating'] = float(pos['restaurant_rating']) if pos['restaurant_rating'] else 0
        
        return jsonify({"positions": positions})

    except Exception as e:
        print(f"[DEBUG TOP] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        db.close()


@courier.route('/positions/api/apply/<int:position_id>', methods=['POST'])
def api_apply_position(position_id):
    """
    API Endpoint to apply for a position.
    Checks eligibility and updates both Position and Courier tables.
    """
    if 'user_id' not in session or session.get('user_type') != 'courier':
        return jsonify({"error": "Unauthorized"}), 401
    
    courier_id = session['user_id']
    
    db = db_helper.get_db_connection()
    cursor = db.cursor(dictionary=True, buffered=True)
    
    try:
        # 1. Get courier info
        cursor.execute("""
            SELECT c_id, name, surname, rating, experience, r_id 
            FROM Courier 
            WHERE c_id = %s
        """, (courier_id,))
        courier_info = cursor.fetchone()
        
        if not courier_info:
            return jsonify({"error": "Courier not found"}), 404
        
        # 2. Check if courier already has a job
        if courier_info['r_id'] is not None:
            return jsonify({
                "error": "You are already employed at a restaurant. You must leave your current position before applying to a new one.",
                "already_employed": True
            }), 400
        
        # 3. Get position info
        cursor.execute("""
            SELECT p.p_id, p.r_id, p.req_exp, p.req_rating, p.payment, p.isOpen,
                   r.name as restaurant_name
            FROM Positions p
            JOIN Restaurant r ON p.r_id = r.r_id
            WHERE p.p_id = %s
        """, (position_id,))
        position = cursor.fetchone()
        
        if not position:
            return jsonify({"error": "Position not found"}), 404
        
        if not position['isOpen']:
            return jsonify({"error": "This position is no longer available"}), 400
        
        # 4. Check eligibility
        courier_rating = courier_info['rating'] or 0
        courier_exp = courier_info['experience'] or 0
        req_rating = position['req_rating'] or 0
        req_exp = position['req_exp'] or 0
        
        if courier_rating < req_rating:
            return jsonify({
                "error": f"Your rating ({courier_rating}) does not meet the minimum requirement ({req_rating})",
                "eligible": False
            }), 400
        
        if courier_exp < req_exp:
            return jsonify({
                "error": f"Your experience ({courier_exp} years) does not meet the minimum requirement ({req_exp} years)",
                "eligible": False
            }), 400
        
        # 5. All checks passed - Apply for position
        # Update Position: set c_id and close position
        cursor.execute("""
            UPDATE Positions 
            SET c_id = %s, isOpen = FALSE 
            WHERE p_id = %s
        """, (courier_id, position_id))
        
        # Update Courier: set r_id
        cursor.execute("""
            UPDATE Courier 
            SET r_id = %s 
            WHERE c_id = %s
        """, (position['r_id'], courier_id))
        
        db.commit()
        
        # Update session
        session['courier_r_id'] = position['r_id']
        
        return jsonify({
            "success": True,
            "message": f"Congratulations! You have been enrolled at {position['restaurant_name']}!",
            "restaurant_id": position['r_id'],
            "restaurant_name": position['restaurant_name'],
            "payment": float(position['payment'])
        })

    except Exception as e:
        db.rollback()
        print(f"Apply position error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        db.close()


# ==========================================
# POSITION CREATION (For Restaurant Manager)
# ==========================================

@courier.route('/positions/create', methods=['POST'])
def create_position():
    """
    Creates a new position (job listing).
    This will be used by Restaurant Managers.
    Accepts both JSON and form data.
    """
    # Get data from either JSON or form
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()
    
    # Required fields
    r_id = data.get('r_id')
    payment = data.get('payment')
    
    if not r_id or not payment:
        return jsonify({"error": "Restaurant ID and payment are required"}), 400
    
    # Optional fields with defaults
    city = data.get('city')
    req_exp = data.get('req_exp', 0)
    req_rating = data.get('req_rating', 0)
    
    db = db_helper.get_db_connection()
    cursor = db.cursor(dictionary=True, buffered=True)
    
    try:
        # Verify restaurant exists
        cursor.execute("SELECT r_id, name, city FROM Restaurant WHERE r_id = %s", (r_id,))
        restaurant = cursor.fetchone()
        
        if not restaurant:
            return jsonify({"error": "Restaurant not found"}), 404
        
        # Use restaurant's city if not provided
        if not city:
            city = restaurant['city']
        
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
            "restaurant_name": restaurant['name']
        }), 201

    except Exception as e:
        db.rollback()
        print(f"Create position error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        db.close()


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

    # New couriers start with 3.0 rating (trust score) but ratingCount=0
    query = """
        INSERT INTO Courier 
        (name, surname, email, password, Age, experience, expected_payment_min, expected_payment_max, 
         rating, ratingCount, taskCount, TotalDeliveries) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 3.0, 0, 0, 0)
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
    
    mycursor = db.cursor(dictionary=True, buffered=True) 
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
        
    mycursor = db.cursor(dictionary=True, buffered=True)
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
        # New couriers start with 3.0 rating (trust score) but ratingCount=0
        query = """
            INSERT INTO Courier 
            (r_id, name, surname, email, password, Age, Gender, 
             Marital_Status, experience, expected_payment_min, expected_payment_max, 
             rating, ratingCount, taskCount, TotalDeliveries) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 3.0, 0, 0, 0)
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

def find_available_courier(cursor, r_id):
    """
    Finds a courier linked to the restaurant.
    Accepts an existing DB cursor to ensure transaction safety.
    """
    # Logic: Find a courier assigned to this restaurant (r_id)
    # You might want to check if they are 'active' in a real app, 
    # but for now, we just pick one.
    cursor.execute("SELECT c_id FROM Courier WHERE r_id = %s LIMIT 1", (r_id,))
    row = cursor.fetchone()
    return row["c_id"] if row else None