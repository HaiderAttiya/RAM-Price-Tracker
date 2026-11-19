/*
 * 02_indexes.js  -  the indexes used by the RAM Price Tracker
 *
 * Run:   mongosh --quiet "mongodb://localhost:27017" --file mongo_scripts/02_indexes.js
 *
 * Part A  lists the indexes that Django created in the real application
 *         database ("ram_price_tracker") from the Meta.indexes / constraints
 *         declared in tracker/models.py.  (Read-only.)
 * Part B  shows the equivalent createIndex() commands, run in the scratch
 *         database "ram_index_demo" so you can see the raw MongoDB syntax.
 */
function heading(text) { print("\n=== " + text + " ==="); }

// ---------------------------------------------------------------------------
heading("A. Indexes in the application database (created by `python manage.py migrate`)");
// ---------------------------------------------------------------------------
const app = db.getSiblingDB("ram_price_tracker");
["products", "price_records", "watchlist"].forEach(function (name) {
  print("\n" + name + "  (" + app.getCollection(name).countDocuments() + " documents)");
  app.getCollection(name).getIndexes().forEach(function (ix) {
    print("  " + ix.name.padEnd(30) + JSON.stringify(ix.key) + (ix.unique ? "   UNIQUE" : ""));
  });
});

// ---------------------------------------------------------------------------
heading("B. The same indexes written as raw MongoDB commands (scratch database)");
// ---------------------------------------------------------------------------
const demo = db.getSiblingDB("ram_index_demo");
demo.dropDatabase();

// products: supports  find({ddr_generation, capacity_gb, price: {$gte,$lte}}).sort({price: 1})
//   equality, equality, range/sort   (the ESR guideline for compound-index key order)
demo.products.createIndex({ ddr_generation: 1, capacity_gb: 1, price: 1 }, { name: "prod_ddr_cap_price_idx" });

// products: a kit can be catalogued only once (also speeds up lookups by brand / brand+model)
demo.products.createIndex(
  { brand: 1, model: 1, ddr_generation: 1, capacity_gb: 1, modules: 1, speed_mhz: 1, cas_latency: 1 },
  { name: "product_variant_unique", unique: true });

// price_records: price history of one product, newest first
//   find({product_id}).sort({recorded_at: -1})   -> index order == sort order, so no in-memory sort
demo.price_records.createIndex({ product_id: 1, recorded_at: -1 }, { name: "price_product_time_idx" });

// price_records: "everything recorded in the last 90 days" (the deal calculation window)
demo.price_records.createIndex({ recorded_at: 1 }, { name: "price_time_idx" });

// watchlist: one entry per user per product; its prefix (user_id) also serves "my watchlist"
demo.watchlist.createIndex({ user_id: 1, product_id: 1 }, { name: "watchlist_user_product_uniq", unique: true });
demo.watchlist.createIndex({ product_id: 1 });   // who watches this product? (also used by cascade deletes)

["products", "price_records", "watchlist"].forEach(function (name) {
  print("\n" + name);
  demo.getCollection(name).getIndexes().forEach(function (ix) {
    print("  " + ix.name.padEnd(30) + JSON.stringify(ix.key) + (ix.unique ? "   UNIQUE" : ""));
  });
});

// ---------------------------------------------------------------------------
heading("C. Unique indexes enforce data integrity");
// ---------------------------------------------------------------------------
const kit = { brand: "Corsair", model: "Vengeance DDR5", ddr_generation: "DDR5", capacity_gb: 32, modules: 2, speed_mhz: 6000, cas_latency: 30 };
demo.products.insertOne(Object.assign({}, kit));
try { demo.products.insertOne(Object.assign({}, kit)); }
catch (e) { print("Duplicate kit rejected: E" + e.code + " (duplicate key)"); }

demo.dropDatabase();
