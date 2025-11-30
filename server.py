from flask import Flask
from views.main_view import main
from views.user_view import user
from views.courier_view import courier
from views.restaurant_view import restaurant
from views.menu_view import menu
from views.order_view import order

def create_app():
    app = Flask(__name__, template_folder="template", static_folder="static")
    
    # IMPORTANT: Secret key for session management (required for login)
    app.secret_key = 'gethere-secret-key-change-this-in-production'
    
    app.config.from_object("config.settings")

    # Register Blueprints
    app.register_blueprint(main, url_prefix='/')
    app.register_blueprint(user, url_prefix='/users')
    app.register_blueprint(courier, url_prefix='/couriers')
    app
    app.register_blueprint(restaurant, url_prefix='/restaurant')
    app.register_blueprint(menu, url_prefix='/menus')
    app.register_blueprint(order, url_prefix='/orders')

    return app

if __name__ == "__main__":
    app = create_app()
    port = app.config.get("PORT", 8080)
    
    app.run(
        host="0.0.0.0", 
        port=port, 
        debug=app.config.get("DEBUG", True)
    )