import mysql.connector
import csv

mydb = mysql.connector.connect(host="localhost",
                               user="root",
                               password="password",
                               database="term_project")
mycursor = mydb.cursor()


## This file aim to insert data from users our csv to database tables
def insert_user():
    with open("users.csv") as file_obj:
        read_csv = csv.reader(file_obj)
        i = 0
        for row in read_csv:
            if i == 1:
                id, name, email, password, age, gender, marital_status, occupation, monthly_income = int(
                    row[1]), row[2], row[3], row[4], int(
                        row[5]), row[6], row[7], row[8], row[9]
                address, city = "", ""
                query = (
                    "INSERT INTO `user` "
                    "(user_id, user_name, email, password, age, gender, martial_status, occuption, monthly_income, city, address) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")
                values = (id, name, email, password, age, gender,
                          marital_status, occupation, monthly_income, city,
                          address)
                          
                mycursor.execute(query, values)
            i = 1
        mydb.commit()


##This function insert couriers data in the database from couriers.csv
def insert_couriers():
    with open("couriers.csv", mode='r') as file_obj:
        read_csv = csv.reader(file_obj)

        i = 0
        for row in read_csv:
            if i == 1:

                r_id = int(row[0]) if row[0] else None

                name = row[1]
                surname = row[2]
                email = row[3]
                password = row[4]
                age = int(row[5])
                gender = row[6]
                marital_status = row[7]
                experience = int(row[8])
                rating = float(row[9])
                rating_count = int(row[10])
                task_count = int(row[11])

                query = (
                    "INSERT INTO `Courier` "
                    "(`r_id`, `name`, `surname`, `email`, `password`, `Age`, `Gender`, "
                    "`MaritalStatus`, `experience`, `rating`, `ratingCount`, `taskCount`) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")

                # values to be inserted to the db
                values = (r_id, name, surname, email, password, age, gender,
                          marital_status, experience, rating, rating_count,
                          task_count)
                # use the query with the values
                mycursor.execute(query, values)
            # flag to skip the header line
            i = 1
    # apply all changes
    mydb.commit()


## This function insert orders in db fron orders.csv
def insert_orders():
    TABLE_NAME = "orders"
    # --- CONNECT TO DATABASE -

    # --- OPTIONAL: Create table if not exists ---
    create_table_query = f"""
    CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
        id INT PRIMARY KEY,
        order_date DATE,
        sales_qty INT,
        sales_amount FLOAT,
        currency VARCHAR(10),
        user_id INT,
        r_id FLOAT
    );
    """
    mycursor.execute(create_table_query)
    # --- READ AND INSERT DATA FROM CSV ---
    with open('../raw_data/orders.csv', 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            sql = f"""
            INSERT INTO {TABLE_NAME}
            (id, order_date, sales_qty, sales_amount, currency, user_id, r_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            vals = (int(row['Unnamed: 0']), row['order_date'],
                    int(row['sales_qty']), float(row['sales_amount']),
                    row['currency'], int(row['user_id']),
                    float(row['r_id']) if row['r_id'] else None)
            mycursor.execute(sql, vals)

    mydb.commit()
    mycursor.close()
    mydb.close()

    print("✅ Data inserted successfully!")


## This function is insert menu from menu.csv
def insert_menu_from_csv(csv_path="raw_data/menu.csv"):
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            menu_id = row.get("menu_id")
            r_id = int(row["r_id"]) if row.get("r_id") else None
            f_id    = row.get("f_id")
            cuisine = row.get("cuisine")
            price = float(
                row["price"]) if row.get("price") not in (None, "") else None
            
            mycursor.execute("SELECT 1 FROM Food WHERE f_id=%s", (f_id,))
            if not mycursor.fetchone():
                print(f"[WARN] Skipping Menu row menu_id={menu_id}, f_id={f_id} (Food missing)")
                continue

            mycursor.execute(
                """
                INSERT IGNORE INTO Menu (menu_id, r_id, f_id, cuisine, price)
                VALUES (%s, %s, %s, %s, %s)
            """, (menu_id, r_id, f_id, cuisine, price))
    mydb.commit()
    mycursor.close()
    mydb.close()


def insert_food_from_csv(csv_path="raw_data/food.csv"):
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            f_id = row.get("f_id")
            item = row.get("item")
            veg  = row.get("veg_or_non_veg")
            if not f_id or not item:
                continue
            mycursor.execute(
                """
                INSERT IGNORE INTO Food (f_id, item, veg_or_non_veg)
                VALUES (%s, %s, %s)
                """,
                (f_id, item, veg),
            )
    mydb.commit()

def insert_Restaurant_from_csv(csv_path="restaurant.csv"):
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            id = int(row["id"]) if row.get("id") else None
            name = row.get("name")
            city = row.get("city")
            rating = row.get("rating")
            rating_count = row.get("rating_count")
            cost = row.get("cost")
            cuisine = row.get("cuisine")
            lic_no = row.get("lic_no")
            link = row.get("link")
            address = row.get("address")
            menu = row.get("menu")
            sql = """
                INSERT IGNORE INTO Restaurant (
                    id, name, city, rating, rating_count, 
                    cost, cuisine, lic_no, link, address, menu
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            val = (id, name, city, rating, rating_count, cost, cuisine, lic_no,
                   link, address, menu)
            mycursor.execute(sql, val)
    mydb.commit()
    mycursor.close()
    mydb.close()
