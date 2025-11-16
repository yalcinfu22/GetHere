from flask import current_app, render_template,request,redirect,url_for
import mysql.connector
from flask import jsonify
import bcrypt
from helpers import db_helper
def home_page():
        try:
            db = mysql.connector.connect(
                host="localhost",
                user="root",
                password="123654",
                database="term_project"
            )
            db.close()
            return jsonify({"status": "online", "message": "API is running and DB connection is successful."})
        except mysql.connector.Error as err:
            return jsonify({"status": "error", "message": f"API is running, but DB connection failed: {err}"}), 500
def user_signup():
    return render_template("/user_agent.html")
def  user_submit_signup_form():
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
     db = db_helper.get_db_connection("localhost", "root", "227maram","term_project")
     query = (
                    "INSERT INTO `user` "
                    "(user_name, email, password, age, gender, martial_status, occuption, monthly_income, city, address) "
                    "VALUES ( %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")
     values = (first_name + " " + last_name, email, password, age, gender,
                          status, occupation, salary, city,
                          address)
     mycursor = db.cursor()
     mycursor.execute(query, values)
     db.commit()
     return redirect(url_for("home_page"))
     