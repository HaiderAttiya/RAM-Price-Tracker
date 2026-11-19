# Demonstration video script (target 7-9 minutes, MP4 with audio)

Record the screen with narration (OBS Studio, Windows Game Bar, QuickTime or similar). Start the app first (`python manage.py runserver`), have the dataset seeded (`seed_data --reset`), a terminal and `mongosh` ready. Say these points in your own words.

| Time | On screen | Say |
|---|---|---|
| 0:00 | Title slide or home page | Your name, course IT7405, project "RAM Price Tracker". |
| 0:20 | Home page | **Problem:** buyers cannot easily tell whether a RAM price is genuinely good. **Motivation:** price changes, many retailers, specifications matter. |
| 1:00 | Slide or `docs/02_architecture_and_risks.md` | Stack: Python, Django 5.2, MongoDB 8, Bootstrap 5. Why the official django-mongodb-backend instead of Djongo. |
| 1:40 | `mongosh`: `show collections`, one document from each of products, price_records, watchlist | **Database design:** three collections; price history **referenced** (grows without limit), specs embedded; Decimal128 for money; ISODate for time. |
| 3:00 | `mongosh`: run `mongo_scripts/03_explain.js` summary or open saved output | Two queries with `explain("executionStats")`: Query 2 examines 12 documents with the index vs 4,119 without; no in-memory sort. Mention indexes (`getIndexes`). |
| 4:00 | Code: `settings.py` (DATABASES, MIGRATION_MODULES), `models.py` | **Connectivity:** `parse_uri`, ObjectId auto field, custom app configs, Mongo-specific migrations. MVT: model - view - template. |
| 4:50 | Browser: product list | Search "corsair"; filter DDR5, 32 GB, price range; sort; show pagination. |
| 5:40 | Compare | Tick three kits, Compare; point out best-value highlights. |
| 6:10 | Product detail | Specs, price per GB, true latency, price history chart (hover) and table. Explain the deal rule: 90-day baseline of the same retailer, 10 % / 20 %, at least 3 records. |
| 7:00 | Log in as `demo` | Add price record; add to watchlist with a target; show watchlist and deal status. Add and delete a product (confirmation page). Show a validation error. |
| 8:00 | `/admin/` | Admin: product with inline price records. |
| 8:30 | Terminal | `python manage.py test tracker` - 116 tests passing. Resize browser to show mobile layout. |
| 9:00 | Closing | Summary, limitations (synthetic prices, no live scraping), next steps. |

Checklist before recording: log out first (to show the login step), close unrelated tabs and notifications, test the microphone, export as MP4, play the file once to confirm the audio is there, then upload and put the link in `submission/video_link.txt`.
