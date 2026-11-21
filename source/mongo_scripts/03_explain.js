
const appDb = db.getSiblingDB("ram_price_tracker");

function planChain(stage) {
  const names = [];
  while (stage) { names.push(stage.stage); stage = stage.inputStage || (stage.inputStages && stage.inputStages[0]); }
  return names.join(" > ");
}
function indexUsed(stage) {
  while (stage) { if (stage.indexName) return stage.indexName; stage = stage.inputStage; }
  return "(none)";
}
function summarise(label, explain) {
  const s = explain.executionStats;
  const plan = explain.queryPlanner.winningPlan;
  print("  " + label);
  print("    winning plan        : " + planChain(plan.queryPlan || plan));
  print("    index used          : " + indexUsed(plan.queryPlan || plan));
  print("    nReturned           : " + s.nReturned);
  print("    totalKeysExamined   : " + s.totalKeysExamined);
  print("    totalDocsExamined   : " + s.totalDocsExamined);
  print("    executionTimeMillis : " + s.executionTimeMillis);
  const sortInMemory = JSON.stringify(plan).indexOf('"SORT"') !== -1;
  print("    in-memory SORT stage: " + (sortInMemory ? "yes" : "no"));
}
function banner(text) { print("\n" + "=".repeat(78) + "\n" + text + "\n" + "=".repeat(78)); }

print("products: " + appDb.products.countDocuments() + " documents, price_records: " + appDb.price_records.countDocuments() + " documents");

// ===========================================================================
banner("QUERY 1 - filter products by DDR generation, capacity and price range, cheapest first");
// ===========================================================================
// This is the main product-list query (filters + "Price: low to high").
const q1 = () => appDb.products.find({
  ddr_generation: "DDR5", capacity_gb: 32,
  price: { $gte: NumberDecimal("55"), $lte: NumberDecimal("85") }
}).sort({ price: 1 });

print("Query: db.products.find({ ddr_generation: 'DDR5', capacity_gb: 32, price: { $gte: 55, $lte: 85 } }).sort({ price: 1 })");
const q1_idx   = q1().explain("executionStats");
const q1_scan  = q1().hint({ $natural: 1 }).explain("executionStats");
summarise("WITH the compound index prod_ddr_cap_price_idx", q1_idx);
summarise("WITHOUT an index (forced collection scan)", q1_scan);
print("\n--- full explain('executionStats') output, WITH index ---");
printjson(q1_idx);
print("\n--- full explain('executionStats') output, forced COLLSCAN ---");
printjson(q1_scan);

// ===========================================================================
banner("QUERY 2 - price history of one product, newest first (product page / chart)");
// ===========================================================================
const product = appDb.products.findOne({ brand: "G.Skill", model: "Trident Z5 RGB", capacity_gb: 32, speed_mhz: 6000 });
print("Product: " + product.brand + " " + product.model + "  _id=" + product._id);
const q2 = () => appDb.price_records.find({ product_id: product._id }).sort({ recorded_at: -1 }).limit(12);

print("Query: db.price_records.find({ product_id: <_id> }).sort({ recorded_at: -1 }).limit(12)");
const q2_idx  = q2().explain("executionStats");
const q2_scan = q2().hint({ $natural: 1 }).explain("executionStats");
summarise("WITH the compound index price_product_time_idx", q2_idx);
summarise("WITHOUT an index (forced collection scan)", q2_scan);
print("\n--- full explain('executionStats') output, WITH index ---");
printjson(q2_idx);
print("\n--- full explain('executionStats') output, forced COLLSCAN ---");
printjson(q2_scan);
