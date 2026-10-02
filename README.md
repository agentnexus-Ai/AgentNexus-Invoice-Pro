# AGENTNEXUS INVOICE PRO — COMMERCIAL SOFTWARE (v1.0)
### Standalone Commercial Business Management, Invoicing & Delivery Challan System
*Engineered for Wholesale Traders, Retail Warehouses, Production Units & Apparel Manufacturers*

---

## 1. Quick Start Guide (1-Click Run)

1. Ensure **Python 3.8+** is installed on your computer.
2. **On Windows:** Double-click `run_agentnexus.bat` to launch the server and open the app in your browser.
3. **On Linux/macOS:** Run `./run_agentnexus.sh` or execute:
   ```bash
   python3 app.py
   ```
4. Access the web interface at: **`http://localhost:8080/`**

---

## 2. Pre-Configured Staff Profiles & Floor PIN Codes

| User ID | Username | Staff Name | Assigned Role | Floor PIN Code | System Permissions |
|---|---|---|---|:---:|---|
| `USR-0001` | `admin` | Muhammad Bilal | **Administrator** | **`1122`** | Full root access; exclusive credit limit overrides |
| `USR-0002` | `manager` | Ayesha Tariq | **Manager** | **`4455`** | Authorizes stock shortage overrides; operational queues |
| `USR-0003` | `accountant` | Kamran Akram | **Accountant** | **`7788`** | Logs payments, manages receivables aging, views ledger |
| `USR-0004` | `clerk` | Zohaib Khan | **Sales / Billing** | **`9900`** | Standard invoicing, customer lookups, receipt printing |
| `USR-0005` | `storekeeper` | Tariq Mehmood | **Storekeeper** | **`3322`** | Inward production stock-in receipts, physical gate passes |

---

## 3. Core Commercial Features Tested & Verified

### A. Dual-Unit Packaging: Carton-to-Piece Conversion
* Seamlessly bill in **Master Ratio Cartons**, **Solid-Size Boxes**, or **Loose Single Pieces**.
* Entering `5 Cartons` for a 24-piece garment automatically calculates:
  $$\text{5 Cartons} \times 24 = \mathbf{120\text{ Total Pieces}}$$

### B. Size-Ratio Pre-Pack Architecture
* Master cartons contain pre-defined size curves (e.g. 4S, 8M, 8L, 4XL = 24 pcs).
* Dispatches automatically deduct the exact individual size variants from warehouse stock.

### C. Manager PIN Shortage Override
* If variant stock is insufficient (e.g. Size 32 is short by 4 pcs), the system shows a soft amber warning.
* Billing clerks cannot bypass alone; entering Manager PIN `4455` immediately clears the dispatch.
* Dispatches immediately into temporary tracked negative stock without loading bay bottlenecks.

### D. Immediate Commercial Invoice & Gate Pass Generation
* A single click prints both the **Commercial Invoice** (A4 layout with Meezan Bank IBAN coordinates) and the **Delivery Challan / Gate Pass** with official Security Clearance Stamp.

### E. Administrator Customer Credit Limits
* Customer credit limits and allowable payment days are locked strictly to the **Administrator**.
* Projected exposure is audited prior to billing. Breaches require Administrator PIN `1122`.

### F. Auto-Reconciling Inward Stock Intake
* Checking in new factory production batches or vendor deliveries automatically pays down negative variant balances and flips override logs to `RECONCILED`.

### G. Version 2.0 Dark Mode Foundation
* Features an instant 1-click toggle to the **Midnight Obsidian & Electric Cyan Theme** adhering to WCAG AAA contrast standards.

### H. Offline Hardware-Locked Licensing
* Binds to local CPU and Motherboard UUID fingerprint (`MCH-XXXX-XXXX-XXXX`).
* Pre-activated with Perpetual Lifetime Commercial Key: `ANX-PRO-2026-LIFETIME-AUTH-9988`.

---
*© 2026 AgentNexus AI — Production Certified Commercial Release*
