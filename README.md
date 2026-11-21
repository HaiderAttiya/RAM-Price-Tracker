# RAM Price Tracker

**IT7405 – Individual Project**

RAM Price Tracker is a web application built with Django and MongoDB. It allows users to browse RAM products, compare prices from different retailers, view price history, identify deals, and manage a personal watchlist.

## Features

- Browse and search RAM products.
- Filter products by brand, DDR generation, capacity, and price.
- Compare prices between retailers.
- View price history and product specifications.
- Identify deals based on previous recorded prices.
- Add products and update their prices. (Admin Only)
- Create a personal watchlist with target prices.
- Manage application data through the Django admin panel.

## Technologies

- Python 3.13
- Django 5.2
- MongoDB
- Django MongoDB Backend
- Bootstrap 5.3
- HTML, CSS and JavaScript

## Installation

### Requirements

- Python 3.10 or newer
- MongoDB Community Server 6.0 or newer
- Git (optional)

### 1. Download the project

Clone the repository:

```bash
git clone https://github.com/HaiderAttiya/RAM-Price-Tracker.git
```

Open the project folder, then enter the source directory:

```bash
cd RAM-Price-Tracker/source
```

### 2. Create a virtual environment

**Windows (PowerShell):**

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Configure MongoDB

Make sure MongoDB is running locally on port `27017`.

The default database configuration is:

- Connection: `mongodb://localhost:27017`
- Database: `ram_price_tracker`

If you use MongoDB Atlas or a different connection, configure the `MONGODB_URI` environment variable. The available settings are listed in `.env.example`.

### 5. Prepare and run the application

Run the following commands from the `source` directory:

```bash
python manage.py migrate
python manage.py seed_data
python manage.py runserver
```

Open the application at:

http://127.0.0.1:8000/

## Demo Accounts

The sample data includes two accounts:

| Account | Username | Password |
|---|---|---|
| Administrator | `admin` | `AdminPass123!` |
| Demo user | `demo` | `DemoPass123!` |

These accounts are intended for local demonstration only. Change the passwords before using the application in any public or production environment.

Users can also register through the sign-up page.

## MongoDB Scripts and Tests

The project includes MongoDB scripts demonstrating database operations, indexes, and query performance.

Run these commands from the `source` directory:

```bash
mongosh "mongodb://localhost:27017" --file mongo_scripts/01_crud_demo.js
mongosh "mongodb://localhost:27017" --file mongo_scripts/02_indexes.js
mongosh "mongodb://localhost:27017/ram_price_tracker" --file mongo_scripts/03_explain.js
```

To run the automated tests:

```bash
python manage.py test tracker
```

## Price Data

The application currently uses sample data. Product and retailer names are based on real brands and stores, but the sample prices are synthetic and are not live prices fetched from retailers.

Prices can be added and updated through the application by signing in as an Admin.

## Project Structure

```text
RAM-Price-Tracker/
│
├── source/
│   ├── ram_tracker/       # Django project settings and URLs
│   ├── tracker/           # Application models, views and logic
│   ├── templates/         # HTML templates
│   ├── static/            # CSS, JavaScript and assets
│   ├── mongo_scripts/     # MongoDB scripts
│   ├── mongo_migrations/  # Database migrations
│   ├── docs/              # Project documentation
│   ├── manage.py
│   └── requirements.txt
│
├── IT7405_Project_Report.docx
└── README.md
```

