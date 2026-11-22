# RAM Price Tracker


RAM Price Tracker is my individual project: a Django app that stores its data in MongoDB rather than a relational database. You can search a catalogue of RAM kits, compare what retailers charge, see how a price has moved and keep a watchlist. Staff accounts manage the catalogue; everyone else can browse.

## What it does

- Search and filter by brand, DDR generation, capacity and price.
- Compare what several retailers charge for the same kit.
- Show a price history and flag a kit as a deal when it drops below its earlier low.
- Let a signed-in user keep a watchlist with a target price for each kit.
- Give staff the tools to add products and record new prices, through the site or the Django admin.

## Built with

Python 3.13, Django 5.2 LTS, MongoDB (local Community Server or Atlas), django-mongodb-backend, and Bootstrap 5.3.9 with HTML, CSS and JavaScript.

## Running it

You need Python 3.10 or newer and MongoDB 6.0 or newer .

### 1. Get the code

```bash
git clone https://github.com/HaiderAttiya/RAM-Price-Tracker.git
cd RAM-Price-Tracker/source
```

### 2. Create a virtual environment

```bash
# Windows PowerShell
py -m venv .venv
.\.venv\Scripts\Activate.ps1

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Start MongoDB

Run MongoDB locally on the default port, 27017. The app uses a database called `ram_price_tracker` and creates it on the first migration. If yours runs somewhere else, set `MONGODB_URI` in your environment; `.env.example` lists the settings I used.

### 5. Set up and run

From the `source` folder:

```bash
python manage.py migrate
python manage.py seed_data
python manage.py runserver
```

The site is then at http://127.0.0.1:8000/

## Demo accounts

`seed_data` creates two accounts so you can try both roles straight away:

| Account | Username | Password |
|---|---|---|
| Administrator | `admin` | `AdminPass123!` |
| Standard user | `demo` | `DemoPass123!` |

These are for local use only, so change them before putting the app anywhere public. The sign-up page also works, and accounts made that way are standard users.

## Database scripts and tests

The `mongo_scripts` folder holds the database work described in the report: the CRUD examples, the index creation and the two explain plans. Run them from `source` with mongosh:

```bash
mongosh "mongodb://localhost:27017" --file mongo_scripts/01_crud_demo.js
mongosh "mongodb://localhost:27017" --file mongo_scripts/02_indexes.js
mongosh "mongodb://localhost:27017/ram_price_tracker" --file mongo_scripts/03_explain.js
```

The Django tests are run with:

```bash
python manage.py test tracker
```

## About the price data

Every price in the app is made up. The brands and retailers are real so the catalogue looks familiar, but nothing is scraped or fetched live. Prices only change when a staff account adds them, so sign in as the admin when you want to test the history and deals pages.

## Folder layout

```text
RAM-Price-Tracker/
├── source/
│   ├── ram_tracker/       # settings and URLs
│   ├── tracker/           # models, views and logic
│   ├── templates/         # HTML templates
│   ├── static/            # CSS, JavaScript and assets
│   ├── mongo_scripts/     # CRUD, index and explain scripts
│   ├── mongo_migrations/  # migrations
│   ├── manage.py
│   └── requirements.txt
├── IT7405_Project_Report.docx
├── README.docx
└── README.md
```
