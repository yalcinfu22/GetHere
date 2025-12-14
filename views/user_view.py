# views/user_view.py
from flask import Blueprint, render_template, request, redirect, url_for, session, current_app
import bcrypt
from helpers import db_helper

user = Blueprint('user', __name__)

@user.route('/login')
def user_login():
    """User login page"""
    return render_template('user_login.html')

@user.route('/submit_login', methods=['POST'])
def user_submit_login():
    """Handle user login"""
    email = request.form.get("email")
    password = request.form.get("password")
    
    if not email or not password:
        return "Email and password are required", 400
    
    # Database lookup
    db_config = current_app.config['DB_CONFIG']
    db = db_helper.get_db_connection()
    if not db:
        return "Database connection failed", 500
    
    cursor = db.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT * FROM User WHERE email = %s", (email,))
        user_data = cursor.fetchone()
        print(user_data)
        if user_data and bcrypt.checkpw(password.encode("utf-8"), user_data['password'].encode("utf-8")):
            # Login successful
            session['user_id'] = user_data['user_id']
            session['user_name'] = user_data['name']
            session['user_type'] = 'user'
            print("Giriş başarılı")
            return redirect(url_for('home_page.home_page'))
        else:
            print("Giriş başarısız")
            return "Invalid email or password", 401
    except Exception as e:
        print(f"Login error: {e}")
        return f"An error occurred: {e}", 500
    finally:
        cursor.close()
        db.close()

@user.route('/logout')
def user_logout():
    """User logout"""
    session.clear()
    return redirect(url_for('home_page.home_page'))

@user.route('/signup')
def user_signup():
    """User signup page"""
    return render_template('user_signup.html')

@user.route('/submit_form', methods=['POST'])
def user_submit_signup_form():
    first_name = request.form.get("first_name")
    last_name = request.form.get("last_name")
    password = request.form.get("password")
    address = request.form.get("address")
    city = request.form.get("city")
    email = request.form.get("email")
    gender = request.form.get("gender")
    salary = request.form.get("salary")
    status = request.form.get("martial_status")
    occupation = request.form.get("occupation")
    age = request.form.get("age")
    if age == '':
        age = None
    else:
        age = int(age)
    # Hash password

    if address == '':
        address = None
    if occupation == '':
        occupation = None   
    # Hash password
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

    # DB Insert
    db_config = current_app.config['DB_CONFIG']
    db = db_helper.get_db_connection()
    if not db:
        return "Database connection failed", 500
        
    cursor = db.cursor()
    
    query = """
        INSERT INTO User 
        (name, email, password, Age, Gender, Marital_Status, Occupation, Monthly_Income, city, address) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    # Combining First/Last name because DB has 'name' column
    full_name = f"{first_name} {last_name}"
    
    values = (full_name, email, password_hash, age, gender, status, occupation, salary, city, address)
    
    try:
        cursor.execute(query, values)
        db.commit()
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        return f"Registration failed: {e}", 500
    finally:
        cursor.close()
        db.close()

    return redirect(url_for("home_page.home_page"))
@user.route('/user_id=<int:user_id>')
def user_home(user_id):
    user_id_stored = session.get('user_id') # the user id stored in the session
    user_name = session.get('user_name')
    user_type = session.get('user_type')
    current_user = {
    "is_authenticated": user_id is not None and user_id == user_id_stored,
    "id": user_id,
    "type": user_type,
    "name": user_name,
    }
    if(current_user["is_authenticated"]== True and user_type == "user"):
        return render_template("home_page.html", active_page="home", cart_count=0, current_user = current_user) # to do  update cart count
    else :
        return redirect(url_for("home_page.home_page"))
@user.route('profile/user_id=<int:user_id>')
def update_user_page(user_id):
    user_id_stored = session.get('user_id') # the user id stored in the session
    user_name = session.get('user_name')
    user_type = session.get('user_type')

    if(user_id is not None and user_id == user_id_stored and user_type == "user"):
        db_config = current_app.config['DB_CONFIG']
        db = db_helper.get_db_connection()
        if not db:
            return "Database connection failed", 500
        cursor = db.cursor(dictionary=True)
    
        try:
            cursor.execute("SELECT * FROM User WHERE user_id = %s", (user_id,))
            user_data = cursor.fetchone()
            if user_data:
                # Login successful
                return render_template("user_info.html", user = user_data)
            else:
                return "This user do not exist", 401
        except Exception as e:
            return f"An error occurred: {e}", 500
        finally:
            cursor.close()
            db.close()
        
         # to do  update cart count
    else :
        return redirect(url_for("home_page.home_page"))
@user.route('update/user_id=<int:user_id>',  methods=['POST'])
def update_user(user_id):
        user_id_stored = session.get('user_id') # the user id stored in the session
        user_type = session.get('user_type')

        if(user_id is not None and user_id == user_id_stored and user_type == "user"):
            db_config = current_app.config['DB_CONFIG']
            db = db_helper.get_db_connection()
            if not db:
                return "Database connection failed", 500
            cursor = db.cursor(dictionary=True)
            first_name = request.form.get("first_name")
            last_name = request.form.get("last_name")
            password = request.form.get("password")
            address = request.form.get("address")
            city = request.form.get("city")
            email = request.form.get("email")
            gender = request.form.get("gender")
            salary = request.form.get("salary")
            status = request.form.get("martial_status")
            occupation = request.form.get("occupation")
            age = request.form.get("age")
            name = first_name +  " "+last_name
            if age == '':
                    age = None
            else:
                    age = int(age)
            if address == '':
                    address = None
            if occupation == '':
                occupation = None   
            if password == '':
                    try:
                        cursor.execute("UPDATE User Set name = %s, email = %s, Age = %s, Gender= %s, Marital_Status = %s, Occupation = %s, Monthly_Income =%s, city= %s, address" \
                    "=%s where user_id=%s", (name, email, age, gender, status, occupation, salary, city, address, user_id))
                        db.commit()
                    except Exception as e:
                        print(f"Error: {e}")
                        db.rollback()
                        return f"Update failed: {e}", 500
                    finally:
                        cursor.close()
            else:
                 password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
                 try:
                        cursor.execute("UPDATE User Set name = %s, email = %s, Age = %s, Gender= %s, Marital_Status = %s, Occupation = %s, Monthly_Income =%s, city= %s, address" \
                    "=%s,password = %s  where user_id=%s", (name, email, age, gender, status, occupation, salary, city, address, password_hash, user_id))
                        db.commit()
                 except Exception as e:
                        print(f"Error: {e}")
                        db.rollback()
                        return f"Update failed: {e}", 500
                 finally:
                        cursor.close()

            return redirect(url_for("user.update_user_page", user_id = user_id))
        else: 
            return redirect(url_for("home_page.home_page"))
@user.route('delete/<int:user_id>',  methods=['POST'])
def delete(user_id):
    user_id_stored = session.get('user_id')
    user_type = session.get('user_type')
    if(user_id is not None and user_id == user_id_stored and user_type == "user"):
            db_config = current_app.config['DB_CONFIG']
            db = db_helper.get_db_connection()
            if not db:
                return "Database connection failed", 500
            cursor = db.cursor(dictionary=True)
            try:
                  cursor.execute("DELETE FROM User WHERE user_id=%s", (user_id,))
                  db.commit()
            except Exception as e:
                 print(f"Error: {e}")
                 db.rollback()
                 return f"Delete failed: {e}", 500
            finally:
                 cursor.close()
            return redirect(url_for("user.user_logout"))
    else :
         return redirect(url_for("user.user_logout"), user_id = user_id)
@user.route('profile/user_id=<int:user_id>/cart')
def user_cart(user_id):
    user_id_stored = session.get('user_id') # the user id stored in the session
    user_name = session.get('user_name')
    user_type = session.get('user_type')

    if(user_id is not None and user_id == user_id_stored and user_type == "user"):
        return render_template('cart.html')
        db_config = current_app.config['DB_CONFIG']
        db = db_helper.get_db_connection()
        if not db:
            return "Database connection failed", 500
        cursor = db.cursor(dictionary=True)
    
        try:
            cursor.execute("SELECT * FROM User WHERE user_id = %s", (user_id,))
            user_data = cursor.fetchone()
            if user_data:
                # Login successful
                return render_template("user_info.html", user = user_data)
            else:
                return "This user do not exist", 401
        except Exception as e:
            return f"An error occurred: {e}", 500
        finally:
            cursor.close()
            db.close()
        
         # to do  update cart count
    else :
        return redirect(url_for("home_page.home_page"))