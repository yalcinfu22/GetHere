# GetHere

A full-stack food delivery platform built as a database systems term project. GetHere connects three distinct user roles — **Customers**, **Couriers**, and **Restaurant Managers** — around a MySQL-backed ordering, dispatch, and delivery pipeline.

The application is a Flask monolith rendering server-side Jinja templates, with a MySQL schema of 9 related tables covering users, restaurants, menus, orders, couriers, job positions, and delivery tasks.

---

## Features

### For Customers
- Sign up / log in with bcrypt-hashed credentials
- Browse restaurants and their menus
- Place orders (quantity, pricing, currency)
- View order history and order details
- Rate the menu item and the courier after delivery

### For Couriers
- Sign up / log in with experience, age, and expected-payment preferences
- Personal **dashboard** showing active tasks and recent delivery reviews
- Editable profile (personal info, experience, payment expectations)
- **Job board**: browse open positions across restaurants, filter by city / minimum payment / specific restaurant, and filter by eligibility (rating & experience requirements)
- Apply to a position — enforces one-restaurant-at-a-time and checks eligibility
- **My Restaurant** page with restaurant details, current payment info, and a GROUP-BY leaderboard ranking couriers by `deliveries × avg rating` since their hire date
- Complete deliveries (updates `Task`, `Orders.IsDelivered`, `Positions.deliveries_made`, `Courier.TotalDeliveries`)
- Full **delivery history** with multi-join query (Task ⋈ Orders ⋈ User ⋈ Restaurant, LEFT JOIN Menu / Food) and per-restaurant aggregation
- Leave current position (blocked if the courier has pending deliveries)

### For Restaurant Managers
- Sign up / log in as a manager tied to a specific `Restaurant`
- Restaurant dashboard with an overview of orders, menu, and couriers
- Manage restaurant info (address, cuisine, cost, photo upload, description)
- Manage the menu: add / edit food items and prices
- Create open courier **positions** with required experience, required rating, and payment — position city is pinned to the restaurant's city
- View orders associated with the restaurant

### Ordering & Dispatch Flow
When a customer places an order:
1. `Orders` row is created.
2. A courier is auto-selected from the restaurant's roster via `find_available_courier` — sorted by lowest `taskCount`, then highest `rating`.
3. A `Task` row is created linking order → courier → user.
4. The courier's `taskCount` is incremented; on completion it is decremented and `TotalDeliveries` is incremented.

---

## Tech Stack

- **Backend:** Python 3, Flask (Blueprints)
- **Database:** MySQL (InnoDB, utf8mb4) via `mysql-connector-python`
- **Auth:** `bcrypt` password hashing, Flask session cookies
- **Frontend:** Jinja2 templates, HTML/CSS (server-rendered)
- **Data ingest:** `pandas` + `numpy` for batch loading the Kaggle Zomato dataset
- **Config:** `python-dotenv` for environment-based settings

---

## Project Structure

```
Gethere/
├── server.py                 # Flask app factory + blueprint registration
├── insert_data.py            # Batch loader for the Kaggle Zomato CSVs
├── requirements.txt
├── config/
│   └── settings.py           # Reads DB_* from .env
├── databases/
│   └── term_project.sql      # Full schema (9 tables, constraints, indexes)
├── helpers/
│   └── db_helper.py          # MySQL connection helper
├── views/                    # One blueprint per domain
│   ├── main_view.py          #   /             - home, router by role
│   ├── user_view.py          #   /users        - customer auth & pages
│   ├── courier_view.py       #   /couriers     - courier auth, dashboard, jobs, history
│   ├── restaurant_view.py    #   /restaurant   - manager auth, dashboard, menu/info mgmt
│   ├── menu_view.py          #   /menus        - menu CRUD
│   ├── order_view.py         #   /orders       - order creation & queries
│   ├── food_view.py          #   /foods        - food CRUD
│   └── task_view.py          #   internal task creation
├── template/                 # Jinja2 templates for all pages
├── static/                   # CSS + uploaded restaurant photos
└── raw_data/                 # (not committed) Kaggle Zomato CSVs
```

---

## Database Schema

Nine related tables defined in `databases/term_project.sql`:

| Table                  | Purpose                                                                 |
|------------------------|-------------------------------------------------------------------------|
| `User`                 | Customer accounts                                                       |
| `Restaurant`           | Restaurant profile (name, city, cuisine, rating, photo, license no.)    |
| `Food`                 | Food item catalogue (veg/non-veg)                                       |
| `Menu`                 | Join table: which restaurant serves which food at what price            |
| `Courier`              | Courier accounts (rating, experience, taskCount, TotalDeliveries, …)    |
| `Orders`               | Customer orders with `menu_rate` and `courier_rate` ratings             |
| `Restaurant_Manager`   | Manager accounts, each tied to one `Restaurant` via `managesId`         |
| `Positions`            | Open/filled courier job listings with `req_exp`, `req_rating`, `payment`|
| `Task`                 | Delivery assignment linking an order to a courier                       |

Notable constraints: `Courier.Age >= 18`, rating bounds `[0.0, 5.0]`, `Menu.price >= 0`, email format check, cascading FKs chosen per relationship (CASCADE / SET NULL / RESTRICT).

---

## Setup

### 1. Clone and install

```bash
git clone <repo-url>
cd Gethere
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Download the dataset

The seed data comes from the Kaggle Zomato dataset. Download the CSVs from:

<https://www.kaggle.com/datasets/anas123siddiqui/zomato-database/data>

Place the `.csv` files inside `raw_data/` (the folder is kept out of version control to keep the repo small).

### 3. Configure the database

Create a MySQL database and user, then create a `.env` file at the project root:

```env
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=term_project
```

Initialize the schema:

```bash
mysql -u root -p < databases/term_project.sql
```

### 4. Load the data

```bash
python insert_data.py
```

This batch-loads users, restaurants, foods, menus, couriers, orders, and managers from the CSVs (batch size 2000).

### 5. Run the server

```bash
python server.py
```

The app runs on `http://localhost:8080` by default (configurable via `PORT` in `config/settings.py`).

---

## Entry Points

| Path                          | Who it's for                  |
|-------------------------------|-------------------------------|
| `/`                           | Landing page / role router    |
| `/users/login`, `/users/signup`         | Customers          |
| `/couriers/login`, `/couriers/signup`   | Couriers           |
| `/restaurant/login`, `/restaurant/signup` | Restaurant managers |
| `/couriers/dashboard`         | Courier home after login      |
| `/couriers/positions/search`  | Courier job board             |
| `/couriers/restaurant/my`     | Current restaurant + leaderboard |
| `/couriers/history`           | Full delivery history         |
| `/restaurant/dashboard`       | Manager home after login      |

---

## SQL Highlights

The project intentionally exercises a range of query patterns to satisfy the term-project requirements. Notable examples:

- **5-table multi-join with LEFT OUTER JOINs** — courier delivery history (`views/courier_view.py::delivery_history_page`)
- **GROUP BY + aggregation** — per-restaurant courier stats and restaurant leaderboard
- **Nested subquery** — restaurant leaderboard filters by `r_id = (SELECT r_id FROM Courier WHERE c_id = ?)`
- **Dynamic WHERE building** — job-board filters assembled based on user-selected criteria
- **CHECK constraints, cascading FKs, composite indexes** — defined in `databases/term_project.sql`

---

## Notes

- Default Flask secret key in `server.py` is a development placeholder — change before any real deployment.
- `debug=True` is on by default; disable via `DEBUG=False` in config for production.
- `raw_data/` and `.env` are gitignored.

---

## Credits

Term project by the GetHere team. UI/UX design and final-report PDF (`GetHere (1).pdf`) are included in the repo. Seed data: [Zomato Database on Kaggle](https://www.kaggle.com/datasets/anas123siddiqui/zomato-database/data).
