
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


demo.products.createIndex({ ddr_generation: 1, capacity_gb: 1, price: 1 }, { name: "prod_ddr_cap_price_idx" });

demo.products.createIndex(
  { brand: 1, model: 1, ddr_generation: 1, capacity_gb: 1, modules: 1, speed_mhz: 1, cas_latency: 1 },
  { name: "product_variant_unique", unique: true });


demo.price_records.createIndex({ product_id: 1, recorded_at: -1 }, { name: "price_product_time_idx" });

demo.price_records.createIndex({ recorded_at: 1 }, { name: "price_time_idx" });

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
