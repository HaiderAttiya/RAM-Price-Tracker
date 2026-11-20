# IT7405 RAM Price Tracker - requirements checklist

Status key: **Done** = implemented and verified (how is stated) | **Manual** = needs action by the student | **Pending** = not yet produced.
This file is updated at the final audit.

## A. Application functionality

| # | Requirement (project description) | Where | Status / evidence |
|---|---|---|---|
| 1.1 | Add RAM product (brand, model, DDR generation, capacity, speed, latency, voltage, price) | `ProductCreateView`, `ProductCreateForm` | Done - unit + browser tests |
| 1.2 | Edit product | `ProductUpdateView` | Done - tests |
| 1.3 | View product list and detail | `ProductListView`, `ProductDetailView` | Done - tests |
| 1.4 | Delete product (with its price history and watchlist entries) | `ProductDeleteView` | Done - tests, `01_crud_demo.js` |
| 2.1 | Search and filter | `ProductFilterForm` | Done - tests |
| 2.2 | Filter by brand, DDR generation, capacity, price | same | Done - tests |
| 2.3 | Compare multiple products side by side | `compare` view (2-4 products) | Done - tests, browser check |
| 3.1 | Historical prices with timestamp and retailer | `PriceRecord` model | Done |
| 3.2 | Displayed price history | detail page: SVG chart + paginated table | Done - browser check |
| 3.3 | Watchlist with target price | `WatchlistItem`, watchlist views | Done - tests |
| 3.4 | Deal identification, clearly defined calculation | `tracker/services.py`, README section "Deal rule" | Done - unit tests |

## B. Technical requirements

| Requirement | Status / evidence |
|---|---|
| Research the supported Django-MongoDB approach before choosing | Done - `docs/02_architecture_and_risks.md` |
| Collections `products`, `price_records`, `watchlist` | Done - verified with mongosh |
| Genuine CRUD against MongoDB | Done - app views + `mongo_scripts/01_crud_demo.js` |
| Meaningful indexes | Done - `02_indexes.js`, 5 custom + automatic indexes |
| Two queries analysed with `explain("executionStats")` | Done - `03_explain.js`, output in `docs/explain_output/` |
| Django auth, forms, admin, MVT | Done - tests |
| Bootstrap responsive, professional UI | Done - desktop and mobile screenshots in `docs/screenshots/` |
| Realistic sample data | Done - `seed_data` (49 products, 3,929 price records) |
| No unnecessary dependencies | Done - 3 direct dependencies |

## C. Deliverables (PDF)

| Deliverable | Status |
|---|---|
| Django source code | Done |
| `requirements.txt` | Done |
| README as **Word** document | Done (`submission/README.docx`, converted from README.md; check formatting in Word) |
| Report (Word) in the required structure | Done - draft (`submission/IT7405_Project_Report.docx`, 24 pages); **Manual**: fill ID/name/date, links, personalise |
| Reflection 500-700 words | Draft done (573 words, `docs/reflection_draft.md`, also in report 4.5) - **Manual**: personalise |
| Demonstration video MP4 with audio | **Manual** (script: `docs/demo_video_script.md`) |
| `.txt` file with video link | **Manual** (template in `submission/`) |
| `.txt` file with GitHub link | **Manual** (template in `submission/`) |
| One ZIP named `IT7405_Student_ID` | **Manual** (student ID needed) |
| Cover page with ID/name/signature | **Manual** |
