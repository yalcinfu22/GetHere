from flask import Blueprint, render_template, session, redirect, url_for

# Defining the blueprint with the name 'home_page'
main = Blueprint('home_page', __name__)

@main.route('/')
def home_page():
    cart_count = 0  # logic to pull from session later
    user_id_stored = session.get('user_id') # the user id stored in the session
    user_name = session.get('user_name')
    user_type = session.get('user_type')
    current_user = {
    "is_authenticated": user_id_stored is not None,
    "id": user_id_stored,
    "type": user_type,
    "name": user_name,
    }
    if(current_user['is_authenticated'] == True  and user_type == "user"):
        print("te")
        return redirect(url_for("user.user_home",  user_id = user_id_stored))
    return render_template("home_page.html", active_page="home", cart_count=cart_count)

@main.route('/restaurants')
def restaurants():
    return render_template("restaurants.html")