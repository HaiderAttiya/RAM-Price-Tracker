/*
 * 01_crud_demo.js  -  MongoDB CRUD demonstration for the RAM Price Tracker
 *
 * Run:   mongosh --quiet "mongodb://localhost:27017" --file mongo_scripts/01_crud_demo.js
 *
 * The script works in its OWN database ("ram_crud_demo"), which it drops and
 * re-creates every time, so it is safe to run repeatedly and never touches the
 * data of the Django application ("ram_price_tracker").
 *
 * The documents use exactly the field names and BSON types that
 * django-mongodb-backend writes for the Django models:
 *     CharField -> String        PositiveIntegerField -> Int32
 *     DecimalField -> Decimal128 DateTimeField -> Date (UTC)
 *     ForeignKey  -> ObjectId stored in "<field>_id"   AutoField -> ObjectId "_id"
 */
const demo = db.getSiblingDB("ram_crud_demo");
demo.dropDatabase();

function heading(text) { print("\n=== " + text + " ==="); }

// ---------------------------------------------------------------------------
heading("0. Create the collections (with a $jsonSchema validator on products)");
// ---------------------------------------------------------------------------
demo.createCollection("products", {
  validator: { $jsonSchema: {
    bsonType: "object",
    required: ["brand", "model", "ddr_generation", "capacity_gb", "speed_mhz", "cas_latency", "voltage", "price"],
    properties: {
      brand:          { bsonType: "string" },
      model:          { bsonType: "string" },
      ddr_generation: { enum: ["DDR3", "DDR4", "DDR5"] },
      capacity_gb:    { bsonType: "int", minimum: 1 },
      speed_mhz:      { bsonType: "int", minimum: 800 },
      cas_latency:    { bsonType: "int", minimum: 5 },
      voltage:        { bsonType: "decimal" },
      price:          { bsonType: "decimal" },
      best_retailer:  { bsonType: "string" }
    }
  } }
});
demo.createCollection("price_records");
demo.createCollection("watchlist");
print("Collections: " + demo.getCollectionNames().join(", "));

// ---------------------------------------------------------------------------
heading("1. CREATE");
// ---------------------------------------------------------------------------
// 1a. insertOne  (data types: String, Int32, Decimal128, Date)
const kit = demo.products.insertOne({
  brand: "Corsair", model: "Vengeance DDR5", ddr_generation: "DDR5",
  capacity_gb: NumberInt(32), modules: NumberInt(2), speed_mhz: NumberInt(6000), cas_latency: NumberInt(30),
  voltage: NumberDecimal("1.35"), price: NumberDecimal("189.99"), best_retailer: "Amazon",
  created_at: new Date()
});
print("insertOne -> _id " + kit.insertedId);

// 1b. insertMany
const many = demo.products.insertMany([
  { brand: "G.Skill", model: "Trident Z5 RGB", ddr_generation: "DDR5", capacity_gb: NumberInt(32), modules: NumberInt(2),
    speed_mhz: NumberInt(6000), cas_latency: NumberInt(30), voltage: NumberDecimal("1.40"), price: NumberDecimal("199.99"), best_retailer: "Computia" },
  { brand: "Kingston", model: "Fury Beast", ddr_generation: "DDR4", capacity_gb: NumberInt(16), modules: NumberInt(2),
    speed_mhz: NumberInt(3200), cas_latency: NumberInt(16), voltage: NumberDecimal("1.35"), price: NumberDecimal("59.99"), best_retailer: "Amazon" },
  { brand: "Crucial", model: "Pro", ddr_generation: "DDR5", capacity_gb: NumberInt(64), modules: NumberInt(2),
    speed_mhz: NumberInt(5600), cas_latency: NumberInt(46), voltage: NumberDecimal("1.10"), price: NumberDecimal("289.99"), best_retailer: "Cazasouq" },
  { brand: "Corsair", model: "Vengeance LPX", ddr_generation: "DDR4", capacity_gb: NumberInt(32), modules: NumberInt(2),
    speed_mhz: NumberInt(3200), cas_latency: NumberInt(16), voltage: NumberDecimal("1.35"), price: NumberDecimal("114.99"), best_retailer: "Advanti" }
]);
print("insertMany -> " + Object.keys(many.insertedIds).length + " documents");

// 1c. Related documents use REFERENCING: each price record stores the product's _id.
const productId = kit.insertedId;
const now = new Date();
const daysAgo = (n) => new Date(now.getTime() - n * 86400000);
demo.price_records.insertMany([
  { product_id: productId, retailer: "Amazon",  price: NumberDecimal("199.99"), recorded_at: daysAgo(30), retailer_url: "" },
  { product_id: productId, retailer: "Amazon",  price: NumberDecimal("194.99"), recorded_at: daysAgo(15), retailer_url: "" },
  { product_id: productId, retailer: "Amazon",  price: NumberDecimal("189.99"), recorded_at: daysAgo(1),  retailer_url: "" },
  { product_id: productId, retailer: "Computia",  price: NumberDecimal("197.99"), recorded_at: daysAgo(20), retailer_url: "" },
  { product_id: productId, retailer: "Computia",  price: NumberDecimal("192.99"), recorded_at: daysAgo(2),  retailer_url: "" }
]);
demo.watchlist.insertOne({ user_id: ObjectId(), product_id: productId, target_price: NumberDecimal("175.00"), created_at: new Date() });
print("price_records: " + demo.price_records.countDocuments() + ", watchlist: " + demo.watchlist.countDocuments());

// 1d. The schema validator rejects bad data (price is a string, DDR generation not allowed)
try {
  demo.products.insertOne({ brand: "Bad", model: "Kit", ddr_generation: "DDR9", capacity_gb: NumberInt(8), speed_mhz: NumberInt(3200),
    cas_latency: NumberInt(16), voltage: NumberDecimal("1.35"), price: "cheap" });
} catch (e) { print("Validator rejected the bad document (code " + e.code + "): " + e.message); }

// ---------------------------------------------------------------------------
heading("2. READ");
// ---------------------------------------------------------------------------
print("-- 2a. equality match");
printjson(demo.products.find({ ddr_generation: "DDR5" }, { _id: 0, brand: 1, model: 1, price: 1 }).toArray());

print("-- 2b. field selection (projection) - only brand and model");
printjson(demo.products.find({ brand: "Corsair" }, { _id: 0, brand: 1, model: 1 }).toArray());

print("-- 2c. comparison operators ($gte/$lte on Decimal128) + sort + limit");
printjson(demo.products.find({ price: { $gte: NumberDecimal("100"), $lte: NumberDecimal("200") } },
                             { _id: 0, model: 1, price: 1 }).sort({ price: 1 }).limit(3).toArray());

print("-- 2d. logical operators ($and / $or) and $in");
printjson(demo.products.find({ $or: [ { ddr_generation: "DDR4" }, { $and: [ { capacity_gb: { $gte: 64 } }, { brand: "Crucial" } ] } ] },
                             { _id: 0, brand: 1, model: 1, ddr_generation: 1, capacity_gb: 1 }).toArray());
print("brands in (Corsair, Kingston): " + demo.products.countDocuments({ brand: { $in: ["Corsair", "Kingston"] } }));

print("-- 2e. case-insensitive text search with a regular expression (what the app's search box does)");
printjson(demo.products.find({ model: /vengeance/i }, { _id: 0, brand: 1, model: 1 }).toArray());

print("-- 2f. price history of one product, newest first (referencing: price_records.product_id -> products._id)");
printjson(demo.price_records.find({ product_id: productId }, { _id: 0, retailer: 1, price: 1, recorded_at: 1 }).sort({ recorded_at: -1 }).limit(3).toArray());

print("-- 2g. an aggregation: average price per retailer for that product");
printjson(demo.price_records.aggregate([
  { $match: { product_id: productId } },
  { $group: { _id: "$retailer", avg_price: { $avg: "$price" }, records: { $sum: 1 } } },
  { $sort: { avg_price: 1 } }
]).toArray());

// ---------------------------------------------------------------------------
heading("3. UPDATE");
// ---------------------------------------------------------------------------
print("-- 3a. update ONE document ($set)");
let r = demo.products.updateOne({ brand: "Kingston", model: "Fury Beast" }, { $set: { price: NumberDecimal("54.99"), best_retailer: "Computia" } });
print("matched " + r.matchedCount + ", modified " + r.modifiedCount);

print("-- 3b. update MANY documents (10% off every DDR4 kit, rounded to 2 decimals, using an update pipeline)");
r = demo.products.updateMany({ ddr_generation: "DDR4" },
  [ { $set: { price: { $round: [ { $multiply: ["$price", NumberDecimal("0.90")] }, 2 ] } } } ]);
print("matched " + r.matchedCount + ", modified " + r.modifiedCount);
printjson(demo.products.find({ ddr_generation: "DDR4" }, { _id: 0, model: 1, price: 1 }).toArray());

print("-- 3c. $inc, $currentDate and $unset");
demo.products.updateOne({ model: "Pro" }, { $inc: { cas_latency: NumberInt(-2) }, $currentDate: { updated_at: true }, $unset: { modules: "" } });
printjson(demo.products.findOne({ model: "Pro" }, { _id: 0, model: 1, cas_latency: 1, modules: 1, updated_at: 1 }));

print("-- 3d. upsert: update if found, otherwise insert");
r = demo.products.updateOne({ brand: "Lexar", model: "Ares RGB", ddr_generation: "DDR5", capacity_gb: NumberInt(32) },
                            { $set: { speed_mhz: NumberInt(6400), cas_latency: NumberInt(32), voltage: NumberDecimal("1.40"), price: NumberDecimal("205.00") } },
                            { upsert: true });
print("matched " + r.matchedCount + ", upserted (inserted) " + r.upsertedCount);

print("-- 3e. REPLACE a whole document (everything except _id is swapped)");
r = demo.products.replaceOne({ brand: "Lexar", model: "Ares RGB" },
  { brand: "Lexar", model: "Ares RGB (revised)", ddr_generation: "DDR5", capacity_gb: NumberInt(32), speed_mhz: NumberInt(6400),
    cas_latency: NumberInt(32), voltage: NumberDecimal("1.40"), price: NumberDecimal("199.00"), best_retailer: "Amazon" });
print("matched " + r.matchedCount + ", modified " + r.modifiedCount);
printjson(demo.products.findOne({ brand: "Lexar" }, { _id: 0 }));

// ---------------------------------------------------------------------------
heading("4. DELETE");
// ---------------------------------------------------------------------------
print("-- 4a. delete ONE document");
let d = demo.products.deleteOne({ brand: "Lexar" });
print("deleted " + d.deletedCount);

print("-- 4b. delete MANY documents (old price records, older than 25 days)");
d = demo.price_records.deleteMany({ recorded_at: { $lt: daysAgo(25) } });
print("deleted " + d.deletedCount + ", remaining price_records: " + demo.price_records.countDocuments());

print("-- 4c. cascade by hand: removing a product also removes the documents that reference it");
// (Django does this automatically with on_delete=CASCADE; in plain MongoDB you do it yourself.)
d = demo.price_records.deleteMany({ product_id: productId });
const w = demo.watchlist.deleteMany({ product_id: productId });
const p = demo.products.deleteOne({ _id: productId });
print("price_records removed: " + d.deletedCount + ", watchlist removed: " + w.deletedCount + ", product removed: " + p.deletedCount);

print("\nFinal counts -> products: " + demo.products.countDocuments() + ", price_records: " + demo.price_records.countDocuments() + ", watchlist: " + demo.watchlist.countDocuments());
