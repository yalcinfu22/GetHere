# GetHere

A food delivery and courier management application built by a **five-person team** for a database systems term project. Customers place orders, restaurant managers maintain menus and courier positions, and couriers manage their work and deliveries.

**Python · Flask · MySQL · Jinja2 · HTML/CSS/JavaScript**

## Features

- **Customers:** restaurant and menu browsing, ordering, order history, and food and courier ratings.
- **Couriers:** profiles, job searches with eligibility filters, restaurant membership, delivery tasks, and delivery history.
- **Restaurant managers:** restaurant details, menu management, order views, and courier positions with experience, rating and payment requirements.

Flask Blueprints separate the application domains, with Jinja2 pages and JSON endpoints backed by direct SQL. The nine-table MySQL schema uses foreign keys, indexes and checks. Registration uses bcrypt password hashing and sign-in uses Flask sessions.

Order creation selects a courier by task count and rating, then creates the order and delivery task in one transaction. Reporting includes a six-table delivery-history query, grouped statistics and a courier leaderboard. Start with [`order_view.py`](views/order_view.py), [`courier_view.py`](views/courier_view.py) and the [database schema](databases/term_project.sql).

## Run locally

You need Python 3, Git, a local MySQL server and the `mysql` command-line client. Python dependencies are listed in [`requirements.txt`](requirements.txt).

### 1. Install

```sh
git clone https://github.com/yalcinfu22/GetHere.git
cd GetHere
python -m venv .venv
```

Activate the environment:

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

```sh
# macOS / Linux
source .venv/bin/activate
```

Then install dependencies:

```sh
python -m pip install -r requirements.txt
```

### 2. Configure MySQL

Create `.env` in the repository root:

```dotenv
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_local_mysql_password
DB_NAME=term_project
```

The application reads these values through [`config/settings.py`](config/settings.py). The optional data loader uses fixed values for host (`localhost`), user (`root`) and database (`term_project`); only its password comes from `.env`. Update `db_config` in [`insert_data.py`](insert_data.py) if your connection differs.

### 3. Create the schema

**The script drops and recreates `term_project`, deleting existing data in that database. Use a disposable local database.**

From the repository root, open MySQL:

```sh
mysql -u root -p
```

Then run at the MySQL prompt:

```sql
SOURCE databases/term_project.sql;
EXIT;
```

Some queries use lowercase table names while the schema uses names such as `Orders` and `Courier`. For MySQL installations with case-sensitive table names, normalize these references before using the affected workflows.

### 4. Import sample data (optional)

Six CSV files are included in [`raw_data/`](raw_data/). To load them:

```sh
python insert_data.py
```

The loader processes data in batches of 2,000 rows and creates sample restaurant managers. Imported customer and courier passwords are copied from CSVs without rehashing; create fresh accounts through the registration pages for a manual walkthrough.

### 5. Start the application

```sh
python server.py
```

Open <http://localhost:8080>. Register through `/users/signup`, `/couriers/signup` or `/restaurant/signup`.

To try the ordering flow, create a restaurant and menu item, create a courier position, and have a courier join it. Customer orders require a courier associated with that restaurant.

## Development notes

`PORT` and `DEBUG` are set in `config/settings.py`. The server uses a development session secret, enables debug mode and binds to `0.0.0.0`; review these settings and application security before exposing it beyond local development. `.env` is ignored by Git; the sample CSV files are tracked.

## Team and credits

GetHere is a team project; this repository is a fork of the [original team repository](https://github.com/amrtaweel12/Database).

The repository includes the team's [UI/UX and project document](GetHere%20%281%29.pdf) and [project report](report.pdf). Seed data is credited to [Zomato Database on Kaggle](https://www.kaggle.com/datasets/anas123siddiqui/zomato-database/data).
