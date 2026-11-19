# RAM Price Tracker (IT7405 individual project)

A Django + MongoDB web application for comparing RAM (memory kit) prices, tracking price history, keeping a watchlist with target prices and spotting genuine deals. UI built with Bootstrap 5.

- Python 3.10+ (tested on 3.13), Django 5.2 LTS, django-mongodb-backend 5.2, MongoDB 6.0 / 7.0 / 8.0
- Bootstrap 5.3 and fonts are bundled in `static/` - no internet needed at run time
- Sample prices are **synthetic** (real brand and retailer names, invented prices) and are labelled as such in the app

## 1. Prerequisites

1. **Python 3.10 or newer** - <https://www.python.org/downloads/>
2. **MongoDB** (Community Server 6.0+) running on `localhost:27017`, *or* a free MongoDB Atlas cluster:
   - Windows: install MongoDB Community Server (the installer sets it up as a service).
   - macOS: `brew tap mongodb/brew && brew install mongodb-community` then `brew services start mongodb-community`
   - Ubuntu/Debian: follow <https://www.mongodb.com/docs/manual/administration/install-on-linux/> then `sudo systemctl start mongod`
   - Atlas: create a free cluster, add your IP to the access list, copy the connection string and set `MONGODB_URI` (section 3).
3. Optional: `mongosh` (MongoDB Shell) for the scripts in `mongo_scripts/`.

## 2. Install

Open a terminal in the project folder.

**Windows (PowerShell)**
```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1      # if blocked: Set-ExecutionPolicy -Scope Process RemoteSigned
pip install -r requirements.txt
```

**macOS / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3. Configure (only if your setup is not the default)

Defaults: `mongodb://localhost:27017`, database `ram_price_tracker`. To change them set environment variables (see `.env.example`):

```powershell
$env:MONGODB_URI = "mongodb+srv://user:password@cluster.mongodb.net"   # Windows
```
```bash
export MONGODB_URI="mongodb+srv://user:password@cluster.mongodb.net"    # macOS / Linux
```

## 4. Create the database and load the sample data

```bash
python manage.py migrate        # creates collections and indexes
python manage.py seed_data      # 49 products, ~4,100 price records, 5 watchlist entries, 2 users
python manage.py runserver
```

Open <http://127.0.0.1:8000/>.

| Account | Username | Password | Purpose |
|---|---|---|---|
| Administrator | `admin` | `AdminPass123!` | Django admin at `/admin/` |
| Demo user | `demo` | `DemoPass123!` | Watchlist demo |

These are **demo-only** credentials. Change them with `python manage.py seed_data --reset --admin-password "..." --demo-password "..."` or `python manage.py changepassword admin`. You can also create your own account on the Sign up page, or `python manage.py createsuperuser`.

`seed_data` refuses to run twice; use `--reset` to wipe and reload (it uses a fixed random seed, so the data is identical each time).

## 5. Run the automated tests

```bash
python manage.py test tracker
```
116 tests cover models, validation, the deal calculation, charts, the seed command, every view and the admin. Tests create a temporary `test_ram_price_tracker` database and delete it afterwards. They need a running MongoDB.

## 6. MongoDB scripts (CRUD, indexes, explain)

```bash
mongosh "mongodb://localhost:27017" --file mongo_scripts/01_crud_demo.js
mongosh "mongodb://localhost:27017" --file mongo_scripts/02_indexes.js
mongosh "mongodb://localhost:27017/ram_price_tracker" --file mongo_scripts/03_explain.js
```
- `01_crud_demo.js` - insert/find/update/delete in a scratch database (`ram_crud_demo`); does not touch app data.
- `02_indexes.js` - lists the real indexes and shows the raw `createIndex` commands.
- `03_explain.js` - two queries with `explain("executionStats")`, indexed vs forced collection scan (needs the seeded data).
- Saved output of the last two is in `docs/explain_output/`.

## 7. Using the application

| Page | What it does | Login needed |
|---|---|---|
| Home | Summary and current best deals | no |
| Products | Search; filter by brand, DDR generation, capacity, price; sort; pagination | no |
| Product detail | Specs, price per GB, true latency, retailer prices, price-history chart (30/90/180 days/all) and table, deal status | no |
| Compare | Tick 2-4 products on the list and press Compare | no |
| Deals | Products currently priced well below their usual price | no |
| Add / edit / delete product | Manage the catalogue | yes |
| Add / edit / delete price record | Record a price seen at a retailer | yes |
| Watchlist | Save products with a target price; shows when the target is reached | yes (each user sees only their own) |
| Admin (`/admin/`) | Full management of all collections | staff |

## 8. Deal rule (how a "deal" is calculated)

For a product, take its current best price **C** (lowest latest price among retailers) at retailer *R*.
Baseline **B** = average of *R*'s own recorded prices for that product over the last **90 days** (at least **3** records required, otherwise "not enough history").

Discount **D = (B - C) / B x 100**.

- D >= 10 % -> **Deal**; D >= 20 % -> **Great deal**.
- The baseline uses the same retailer so the comparison is like for like (a cheaper retailer is not mistaken for a sale).
- A watchlist item is "target reached" when the best price is less than or equal to the target.
- Thresholds are settings: `DEAL_WINDOW_DAYS`, `DEAL_THRESHOLD_PERCENT`, `DEAL_MIN_RECORDS`.

## 9. Project structure

```
ram_tracker/          settings, urls, Mongo-aware app configs
mongo_migrations/     generated migrations for admin / auth / contenttypes (MongoDB-specific)
tracker/              models, forms, views, services (deal logic), charts, admin, templatetags
  management/commands/seed_data.py
  tests/
templates/  static/   Django templates; Bootstrap, CSS, JS, fonts
mongo_scripts/        mongosh scripts
docs/                 checklist, architecture notes, screenshots, explain output
```

## 10. Design notes and limitations

- Official `django-mongodb-backend` was chosen over Djongo (see `docs/02_architecture_and_risks.md`).
- Price history is **referenced** (separate collection), not embedded, because it grows without bound.
- Transactions require a MongoDB replica set; the app does not rely on them. It was tested on a standalone server.
- Tested on Linux with Python 3.13 and MongoDB 8.0.23. Windows/macOS/Atlas steps above follow official documentation but were not run by the author of this README.
- Prices are not fetched live from retailers; they are entered by users or come from the sample data.
- Development settings (`DEBUG=1`, default secret key) are for local use only.

## 11. Troubleshooting

| Problem | Fix |
|---|---|
| `ServerSelectionTimeoutError` | MongoDB is not running or `MONGODB_URI` is wrong |
| `django-mongodb-backend` / Django version error | Reinstall with `pip install -r requirements.txt` (versions must match) |
| `seed_data` says data exists | Add `--reset` |
| PowerShell will not activate the venv | `Set-ExecutionPolicy -Scope Process RemoteSigned`, then activate again |
