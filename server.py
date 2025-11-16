# server.py
from flask import Flask, jsonify


# viewlerimiz ana dal server'da herkes views folderında kendi endpointlerini yazcak
from views.courier_view import courier
from views.menu_view import menu
from views.food_view import food
from views.order_view import order
from views.restaurant_view import restaurant
import app_views
# from views.user_view import user
# from views.restaurant_view import restaurant


def create_app():
    app = Flask(__name__,template_folder="template", static_folder="static")
    
    app.config.from_object("config.settings")
    app.config.update(app.config["DB_CONFIG"])

    #app.register_blueprint(user, url_prefix='/users')
    app.add_url_rule("/user_signup",view_func= app_views.user_signup)
    app.add_url_rule("/",view_func= app_views.home_page)
    app.add_url_rule("/user_submit_form",view_func= app_views.user_submit_signup_form, methods=["POST"])

    # --- views baseleri burada tekrar tekrar yazmayalım ve kirletmeyelim burayı diye
    app.register_blueprint(courier, url_prefix='/couriers')
    app.add_url_rule("/courier_signup",view_func= courier.courier_signup)
    app.add_url_rule("/courier_submit_form",view_func= courier.courier_submit_signup_form, methods=["POST"])

    app.register_blueprint(menu, url_prefix='/menus')
    app.register_blueprint(food, url_prefix='/foods')

    app.register_blueprint(order, url_prefix='/orders')
    return app

    #app.register_blueprint(restaurant, url_prefix='/restaurants')


    # --- DB ve API check ---- #


if __name__ == "__main__":
    app = create_app()
    port = app.config.get("PORT", 8080)
    
    app.run(
        host="0.0.0.0", 
        port=port, 
        debug=app.config.get("DEBUG", True)
    )