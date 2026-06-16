# 📊 Vehicle Price Analysis Dashboard

An internal analytics dashboard for tracking and comparing vehicle prices across 18 automotive brands in the Turkish market. Built with a custom Excel-to-database pipeline and a Flask backend serving 11 REST API endpoints.

> **Status:** Live in production at Skoda Yuce Auto — 18 brands, 1341 models, live data

---

## 🖼️ Screenshots

### Landing Page
![Landing](docs/screenshots/landing.png)
*Dark-themed entry screen showing live stats — 18 brands, 1341 models. Data loads in the background before the user enters.*

### Overview Panel — Genel Bakış
![Overview](docs/screenshots/genel_bakis.png)
*KPI cards (total brands, most expensive brand, average price), YTD price increase ranking by brand as a bar chart, and monthly change spark lines for each brand.*

### Filter Panel
![Filter](docs/screenshots/filtre_panel.png)
*Multi-brand and multi-model selector with search. Date range presets: 1M, 3A, 6M, 1Y, 2Y, All. Shows selected count live.*

### Detail Analysis — Price Trend Chart
![Trend](docs/screenshots/fiyat_trendi.png)
*Step-chart showing exact price change events per model. Dots mark real change dates. KPI cards show most increased and most decreased model this month.*

### Model Comparison
![Comparison](docs/screenshots/model_kiyaslama.png)
*Bar chart comparing current prices across selected models. Period change rate chart on the right. Model cards below show active price and last updated date.*

### Navigation Tabs
![Tabs](docs/screenshots/tabs.png)
*Detay Analiz section tabs: Fiyat Trendi, Model Kıyaslama, Marka Özeti, Veri Tablosu*

---

## 💡 What This System Does

Excel file (monthly, network share)

↓

exel_to_db.py  (current year)

exel_to_db_for_last_years.py  (historical)

↓

MS SQL Server — Car_Price_List

(brand, model_name, price, price_date, excel_year)

↓

Flask — 11 REST API endpoints

↓

Interactive frontend dashboard
---

## 📁 Project Structure
/

├── exel_to_db.py                 # Current year Excel → DB

├── exel_to_db_for_last_years.py  # Historical years Excel → DB

├── urun_dashboard.html           # Frontend — full dashboard UI

└── docs/

└── screenshots/
> Backend Flask routes are not included (internal company code).  
> `config.py` with DB credentials is excluded from this repo.

---

## ⚙️ Excel Pipeline

### exel_to_db.py — Current Year

Reads the monthly price list Excel from a network share and loads it into the database.

What it does step by step:
- Loops through every sheet (each sheet = one brand)
- Skips non-brand sheets (`Özet`, `Kampanyalar`, etc.)
- Removes duplicate columns (`.1` suffix cleanup)
- Filters out summary rows (`Ortalama`, `Toplam`)
- Extracts model year from model name — keeps only current year rows
- Strips the year from model name string after filtering
- Detects date columns dynamically — stops at `Yıllık`, `%`, `Değişim` keywords
- Converts Turkish month names to English for date parsing
- Unpivots wide format → long format (one row per model per date)
- Cleans price values (removes `.` separators, converts to INT, nulls out `-`)
- Deletes today's records before inserting — safe to re-run anytime

### exel_to_db_for_last_years.py — Historical Data

Same logic as above but loops over a list of past file paths for previous years. This enables multi-year trend analysis in the dashboard.

> **Note in code:** When a new year starts, `excel_yil` must be updated in `exel_to_db.py` and the finished year's file path must be added to the `paths` list in `exel_to_db_for_last_years.py`.

---

## 🔌 Backend API Endpoints

| Endpoint | What it returns |
|---|---|
| `/urun_dashboard_markalar` | Distinct brand list |
| `/urun_dashboard_modeller` | Models grouped by brand |
| `/urun_dashboard_tarih_araligi` | Min/max date in DB |
| `/urun_dashboard_ham_fiyatlar` | Raw price records with filters |
| `/urun_dashboard_fiyat_trendi` | Daily step-series per model for trend chart |
| `/urun_dashboard_ozet_kartlar` | KPI cards — most increased/decreased model |
| `/urun_dashboard_genel_bakis` | Brand ranking, recent changes, price distribution |
| `/urun_dashboard_aylik_degisim` | Monthly change % per brand with 7-month spark data |
| `/urun_dashboard_yillik_ozet` | YTD summary per brand and model |
| `/urun_dashboard_guncel_fiyatlar` | Latest active price per model |
| `/urun_dashboard_veri_tablosu` | Snapshot table with trend and status per model |

---

## 📐 Key Technical Decisions

**Step-chart instead of interpolation**
Prices don't change every day — they hold until the next update. The backend generates a full daily series using a step function: the last known price is carried forward until a new one appears. This makes the chart accurately reflect real pricing history.

**Idempotent runs**
Before every insert, the script deletes existing records for that `excel_year`. The pipeline can be re-run at any time without creating duplicates.

**Dynamic column detection**
Date columns are detected automatically. The script stops when it hits keywords like `Yıllık` or `Değişim`. This makes it resilient to new columns being added to the Excel file.

**Momentum and event detection**
The backend computes price change percentage day by day and flags only real change events as dots on the trend chart — no visual noise on flat periods.

**Status indicators**
Each model in the data table gets a status: 🟢 full data, 🟡 has gaps, 🔴 no current price. Trend direction shown as 🔺🔻➖.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3 |
| Data processing | pandas |
| Database connector | pyodbc |
| Database | MS SQL Server |
| Backend | Flask |
| Frontend | HTML, CSS, JavaScript |

---

## 🔒 What's Not Included

- Flask backend routes (internal company code)
- `config.py` — DB connection string
- Source Excel files — internal company data

---

## 👩‍💻 Author

Built by [Sude Bayhan](https://linkedin.com/in/sude-bayhan) at Skoda Yuce Auto.  
Pipeline, backend API design, and full dashboard architecture.

© 2026 Sude Bayhan. All rights reserved. This project is not licensed for use, modification, or distribution.


Automotive price lists are published monthly as Excel files. These files have messy structure — Turkish month names as headers, mixed date formats, duplicate columns, totals rows, and multiple model years on the same sheet.

This system solves that with two pipeline scripts that clean and normalize the data, then loads it into SQL Server as a time-series. The Flask backend then serves it through 11 REST endpoints to the dashboard frontend.
