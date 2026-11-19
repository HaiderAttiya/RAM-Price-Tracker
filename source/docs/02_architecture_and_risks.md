# Architecture, versions and compatibility risks

## 1. Choice of Django-MongoDB integration

| Option | Verdict |
|---|---|
| **django-mongodb-backend** (official, maintained by MongoDB; PyMongo underneath) | **Chosen.** Supports Django ORM, migrations, admin and auth on MongoDB. Releases track Django minor versions. |
| Djongo (SQL-to-Mongo translator) | Rejected: not kept up with current Django, known compatibility problems, AGPL licence. |
| MongoEngine / raw PyMongo | Rejected: would not give Django forms, admin and auth for free, and the brief asks for Django's MVT with MongoDB. |

## 2. Versions

| Component | Version | Reason |
|---|---|---|
| Python | 3.13 (backend needs 3.10+) | Current and supported |
| Django | 5.2.19 (LTS) | Backend 5.2.x requires Django 5.2.x |
| django-mongodb-backend | 5.2.4 | Latest for Django 5.2 |
| PyMongo | 4.20.1 | Pulled in by the backend |
| MongoDB | 8.0.23 (backend supports 6.0, 7.0, 8.0) | Current |
| Bootstrap | 5.3.9, vendored locally | Works offline; no CDN |

## 3. Compatibility risks identified before implementation, and how they were handled

| Risk | Handling |
|---|---|
| Django's built-in apps use integer AutoField, unsupported on MongoDB | Custom AppConfigs in `ram_tracker/apps.py` using `ObjectIdAutoField`; `MIGRATION_MODULES` points admin/auth/contenttypes at generated Mongo-specific migrations in `mongo_migrations/` |
| URLs need ObjectId primary keys | Custom `objectid` path converter (24 hex characters) |
| Decimal and date types | Decimal -> Decimal128, DateTime -> ISODate; verified in mongosh |
| Transactions need a replica set | App does not depend on transactions; denormalised price is refreshed explicitly. Tests use standalone mongod |
| Backend minor version must match Django | Versions pinned in `requirements.txt` |
| Joins are not native in MongoDB | Referencing with `product_id`; queries use indexes; lookups kept per-page |

## 4. Data model

- `products` - one document per RAM kit, with denormalised current `price`, `best_retailer`, `price_updated_at`.
- `price_records` - **referenced** one-to-many (`product_id`): history grows without bound, so embedding would approach the 16 MB document limit and make every product read heavier.
- `watchlist` - references `user_id` and `product_id`; unique pair.
- The denormalised price is recalculated only from price records, so product price and history cannot disagree.

## 5. Application layout

`ram_tracker/` (settings, urls) - `tracker/` (models, forms, views, services, charts, admin, tests, seed command) - `templates/` - `static/` - `mongo_scripts/` - `docs/`.
