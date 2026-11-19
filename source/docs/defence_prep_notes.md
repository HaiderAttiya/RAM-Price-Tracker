# Project Defence preparation (35 marks)

In the defence you must explain and modify code you submit as your own. Read each file once and be able to answer the questions below without notes.

## Be able to explain
1. **Why django-mongodb-backend, not Djongo?** Official, maintained, matches Django 5.2; Djongo translates SQL and lags behind. (`docs/02_architecture_and_risks.md`)
2. **What does `MIGRATION_MODULES` do and why is it needed?** Django's built-in apps use integer ids; MongoDB needs ObjectId, so Mongo-specific migrations replace them. (`ram_tracker/settings.py`, `apps.py`)
3. **Embedding vs referencing** for price history, with the 16 MB and unbounded growth argument. (report 2.1)
4. **Why Decimal128 for money?** Exact decimal arithmetic; floats give rounding errors.
5. **Each index:** which query it serves and why the keys are in that order (equality, equality, range/sort). Read an `explain` output: winning plan, `totalKeysExamined`, `totalDocsExamined`, in-memory SORT.
6. **Denormalised `Product.price`:** why it exists, and how it stays correct (`PriceRecord.save/delete`, `refresh_price_from_history`, admin per-object delete).
7. **The deal formula** and why the baseline uses the same retailer. Worked example: baseline 100.00, current 88.00 -> 12.0 %, a deal; 9.99 % is not.
8. **MVT flow** of one request (product list): urls -> view -> form -> queryset -> template.
9. **Forms:** where validation lives (`clean()` in the model, `clean_brand`, field validators), and what `BootstrapFormMixin.full_clean` does.
10. **Access control:** `LoginRequiredMixin`, ownership filter on watchlist (404 for other users).
11. **Migration commands** and what each does.

## Likely modification tasks - practise these
- Add a new field (e.g. `rgb` boolean) to `Product`: model -> `makemigrations tracker` -> `migrate` -> form -> template.
- Change the deal threshold (settings only) or add a new filter (form + view queryset).
- Add a new index and show it with `getIndexes()` and `explain`.
- Add a new page (url -> view -> template -> nav link).

## Honest points to be ready for
- Prices are synthetic; there is no live retailer data.
- Transactions are not used (they need a replica set).
- Tested on Linux with MongoDB 8.0.23; not on Windows/macOS/Atlas.
