# GetHere

A food delivery and courier management web application built by a **five-person team** for a database systems term project. Customers place orders, restaurant managers maintain menus and courier positions, and couriers manage applications and deliveries.

**Python · Flask · MySQL · Jinja2 · HTML/CSS/JavaScript**

This repository is a fork of the team's [original repository](https://github.com/amrtaweel12/Database). The features below describe the team's application.

## What the application does

| Role | Main workflows |
| --- | --- |
| Customer | Register and sign in, browse restaurants and menus, place orders, view order history, and submit food and courier ratings. |
| Courier | Maintain a profile, search restaurant positions by city, payment and eligibility, join a restaurant, complete delivery tasks, and review delivery history. |
| Restaurant manager | Register a restaurant, update its details, manage menu items, view orders, and create courier positions with experience, rating and payment requirements. |

The application uses Flask Blueprints for its domains, server-rendered Jinja2 pages, JSON endpoints for interactive actions, and direct SQL through `mysql-connector-python`. Registration flows hash passwords with bcrypt; sign-in uses Flask sessions.

## Engineering highlights

- **Order and delivery workflow:** the ordering endpoint selects a restaurant's courier by active task count, then rating. It creates the order and delivery task and increments the courier's task count using a shared database transaction. Delivery completion updates the task, order, position and courier records.
- **Courier job matching:** position searches build parameterized filters for city, restaurant, minimum payment, experience and rating. Joining a position checks eligibility and whether the courier already works for another restaurant.
- **Relational reporting:** delivery history joins six tables, including two left joins. Restaurant statistics and courier leaderboards use aggregation; the leaderboard also uses a nested subquery and filters deliveries by hire date.
- **Database constraints:** the schema contains nine related tables, foreign keys, indexes, unique keys and checks for values such as courier age, ratings and nonnegative prices.
- **Data import:** a pandas-based loader prepares CSV data and inserts it in batches of 2,000 rows.

### Read the code

| Area | Starting point |
| --- | --- |
| Application setup and Blueprint registration | [`server.py`](server.py) |
| Order creation and ratings | [`views/order_view.py`](views/order_view.py) |
| Courier selection, positions, delivery completion and reporting | [`views/courier_view.py`](views/courier_view.py) |
| Delivery task creation with a shared cursor | [`views/task_view.py`](views/task_view.py) |
| Restaurant and manager workflows | [`views/restaurant_view.py`](views/restaurant_view.py) |
| Schema and constraints | [`databases/term_project.sql`](databases/term_project.sql) |
| CSV import | [`insert_data.py`](insert_data.py) |

## Database model

| Table | Responsibility |
| --- | --- |
| `User` | Customer accounts and addresses |
| `Restaurant` | Restaurant details and aggregate ratings |
| `Food` | Food catalogue |
| `Menu` | Restaurant–food association and price |
| `Courier` | Courier accounts, employment and delivery counters |
| `Orders` | Orders, delivery status and customer ratings |
| `Restaurant_Manager` | Manager accounts linked to restaurants |
| `Positions` | Courier vacancies, requirements and employment details |
| `Task` | Delivery assignments linking orders, couriers and customers |

## Run locally

### Prerequisites

- Python 3 with `pip` and `venv`
- A local MySQL server and the `mysql` command-line client
- Git

The commands below follow the repository's current entry points and configuration. Dependencies are listed without version pins in [`requirements.txt`](requirements.txt).

### 1. Clone and install

```sh
git clone https://github.com/yalcinfu22/GetHere.git
cd GetHere
python -m venv .venv
```

Activate the environment on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Or on macOS/Linux:

```sh
source .venv/bin/activate
```

Then install the dependencies:

```sh
python -m pip install -r requirements.txt
```

### 2. Configure the database connection

Create a `.env` file in the repository root:

```dotenv
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_local_mysql_password
DB_NAME=term_project
```

The Flask application reads all four values through [`config/settings.py`](config/settings.py). The optional data loader currently fixes its host, user and database to `localhost`, `root` and `term_project`; only its password comes from `.env`. If you use a different connection, also update `db_config` in `insert_data.py` before importing data.

### 3. Initialize the schema

**The schema script drops and recreates `term_project`, deleting any existing data in that database. Use a disposable local database.**

From the repository root, open the MySQL client:

```sh
mysql -u root -p
```

At its prompt, run:

```sql
SOURCE databases/term_project.sql;
EXIT;
```

Some queries use lowercase table names while the schema uses names such as `Orders`, `Courier` and `Restaurant`. On a MySQL installation with case-sensitive table names, normalize these references before running the affected workflows.

### 4. Optionally import sample data

The repository currently includes `food.csv`, `users.csv`, `restaurant.csv`, `couriers.csv`, `menu.csv` and `orders.csv` under [`raw_data/`](raw_data/). The original README attributes the seed dataset to [Zomato Database on Kaggle](https://www.kaggle.com/datasets/anas123siddiqui/zomato-database/data).

```sh
python insert_data.py
```

The loader imports these files, creates sample restaurant managers, and maps historical orders to menu items and a legacy courier. For a manual walkthrough, create fresh accounts through the registration pages; imported customer and courier passwords are copied from the CSV files without being rehashed by the loader.

### 5. Start the application

```sh
python server.py
```

Open <http://localhost:8080>. `PORT` and `DEBUG` are Python settings in `config/settings.py`.

| Entry point | Purpose |
| --- | --- |
| `/` | Home page |
| `/users/signup`, `/users/login` | Customer registration and sign-in |
| `/couriers/signup`, `/couriers/login` | Courier registration and sign-in |
| `/restaurant/signup`, `/restaurant/login` | Restaurant manager registration and sign-in |
| `/couriers/positions/search` | Courier job board |
| `/couriers/dashboard` | Delivery dashboard |
| `/couriers/restaurant/my` | Current restaurant and courier leaderboard |
| `/couriers/history` | Delivery history |
| `/restaurant/dashboard` | Restaurant management dashboard |

To explore the order flow with new accounts, first create a restaurant and menu item, create a courier position, and have a courier join it. Customer orders require a courier associated with the selected restaurant.

## Development notes

This is an academic project. `server.py` contains a development session secret, binds to `0.0.0.0`, and runs with debug mode enabled by default. Review these settings and application security before exposing it beyond a local development environment.

`.env` is ignored by Git. The CSV files under `raw_data/` are tracked; only `raw_data/*.local.*` is ignored.

## Credits and project documents

Term project by the GetHere team. UI/UX design and final-report PDF (`GetHere (1).pdf`) are included in the repo. Seed data: [Zomato Database on Kaggle](https://www.kaggle.com/datasets/anas123siddiqui/zomato-database/data).

- [GetHere project document](GetHere%20%281%29.pdf)
- [Project report](report.pdf)
- [Original team repository](https://github.com/amrtaweel12/Database)

