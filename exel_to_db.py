import pandas as pd
import pyodbc
import re
# NOT: Bu script, mevcut yıla ait Excel dosyalarını okuyup veritabanına eklemek için tasarlanmıştır.
#mevcut yıl hard kod şeklinde  excel_yil dir
#yeni yıla geçişte burası update edilip last year scriptinde paths listesine  biten yıl tarihi eklenmelidir !!!

print("🚀 Script başladı")

# =========================
# MSSQL BAĞLANTI
# =========================
conn = pyodbc.connect(
   xxxxxx
)

cursor = conn.cursor()
print(" DB bağlantısı OK")

# =========================
# EXCEL PATH
# =========================
path = r"\\xx\data\YUCE AUTO GENEL\Urun_fiyat_excel\Urun_dpt_rpa_layout.xlsx"

# =========================
# EXCEL YIL MAPPING
# =========================
excel_yil = 2026

# =========================
# TABLO TEMİZLE
# =========================

cursor.execute("""
DELETE FROM [Raporlar].[dbo].[Car_Price_List]
WHERE excel_year = ?
""", excel_yil)


conn.commit()
print(f"🧹 model_name içinde {excel_yil} geçen kayıtlar silindi")

# =========================
# EXCEL OKU
# =========================
xls = pd.ExcelFile(path)

total_insert = 0

# =========================
# SHEET LOOP
# =========================
#eğer olursa eklenirse sayfalarda marka hariç olanalr varsa diye eklendi 

ignore_sheets = ["Özet", "Kampanyalar", "Liste - Transaction Geçiş"]

for sheet_name in xls.sheet_names:

    if sheet_name in ignore_sheets:
        print(f"⛔ Skip sheet: {sheet_name}")
        continue

    print(f"\n📄 Sheet: {sheet_name}")

    df = pd.read_excel(xls, sheet_name=sheet_name)

    seen = set()
    new_cols = []
    keep_mask = []

    for col in df.columns:
        col_clean = re.sub(r"\.\d+$", "", str(col))  # .1 temizle

        if col_clean in seen:
            keep_mask.append(False)  #  alma
        else:
            seen.add(col_clean)
            keep_mask.append(True)   #  al

        new_cols.append(col_clean)

    df.columns = new_cols
    df = df.loc[:, keep_mask]
    print("🧠 Final kolonlar:", df.columns.tolist())

    if df.shape[0] == 0:
        continue

    # ilk kolon = model
    df.rename(columns={df.columns[0]: "model_name"}, inplace=True)

    # model filtre (güçlendirildi)
    df = df[
        df["model_name"].notna() &
        ~df["model_name"].astype(str).str.contains("Ortalama|Toplam", case=False, na=False)
    ]

    print(f"➡ Model satır sayısı: {len(df)}")

    # =========================
    # MODEL YIL PARSE + FİLTRE
    # =========================

    # model_name içinden 4 haneli yıl bul (20xx)
    df["model_year"] = df["model_name"].astype(str).str.extract(r"\b(20\d{2})\b")[0]

    # numeric yap
    df["model_year"] = pd.to_numeric(df["model_year"], errors="coerce")

    # filtre:
    # 1. model_year == excel_yil → AL
    # 2. model_year NaN (yıl yok) → AL
    # diğerlerini AT
    df = df[
        (df["model_year"] == excel_yil) |
        (df["model_year"].isna())
    ]

    print(f"🎯 Filtre sonrası kalan model: {len(df)}")


    # =========================
    # MODEL NAME TEMİZLE (YIL SİL)
    # =========================

    df["model_name"] = df["model_name"].str.replace(
        rf"\b{excel_yil}\b", "", regex=True
    ).str.strip()

    # =========================
    # TARİH KOLONLARI
    # =========================
    stop_keywords = ["Yıllık", "%","Değişim","değişim","yıllık"]

    date_columns = []

    for col in df.columns[1:]:
        col_str = str(col)

        if "Unnamed" in col_str:
            continue

        if any(k in col_str for k in stop_keywords):
            print(f"⛔ Stop column bulundu: {col}")
            break

        date_columns.append(col)

    print(f"📅 Tarih kolonları: {len(date_columns)}")

    if len(date_columns) == 0:
        continue

    df = df[["model_name"] + date_columns]

    # =========================
    # UNPIVOT
    # =========================
    df_long = df.melt(
        id_vars=["model_name"],
        var_name="price_date",
        value_name="price"
    )

    print(f"➡ Melt sonrası: {len(df_long)}")

    # fiyat temizle boşlukları sil
    df_long["price"] = df_long["price"].astype(str).str.strip()

    # "-" veya boş → NULL yapıyor
    df_long["price"] = df_long["price"].replace(
        to_replace=r"^-?$",
        value=None,
        regex=True
    )

    # sayıya çevir
    df_long["price"] = pd.to_numeric(
        df_long["price"].str.replace(r"[^\d]", "", regex=True),
        errors="coerce"
    )

    # NaN → None (SQL NULL)
    df_long["price"] = df_long["price"].where(pd.notna(df_long["price"]), None)

    print(f"💰 Temiz fiyat sayısı: {len(df_long)}")

    if len(df_long) == 0:
        continue

    # =========================
    # TARİH (CASE SAFE)
    # =========================
    turkish_months = {
        "ocak": "January",
        "şubat": "February",
        "mart": "March",
        "nisan": "April",
        "mayıs": "May",
        "haziran": "June",
        "temmuz": "July",
        "ağustos": "August",
        "eylül": "September",
        "ekim": "October",
        "kasım": "November",
        "aralık": "December"
    }

    def convert_turkish_date(date_val):
        if isinstance(date_val, pd.Timestamp):
            return date_val

        date_str = str(date_val)
        date_str_lower = date_str.lower()

        for tr, en in turkish_months.items():
            if tr in date_str_lower:
                date_str = re.sub(tr, en, date_str, flags=re.IGNORECASE)

        try:
            return pd.to_datetime(date_str, dayfirst=True)
        except:
            print("❌ Tarih parse edilemedi:", date_val)
            return None

    df_long["price_date"] = df_long["price_date"].apply(convert_turkish_date)

    df_long = df_long[df_long["price_date"].notna()]

    # =========================
    # BRAND
    # =========================
    df_long["brand"] = sheet_name

    # =========================
    # INSERT
    # =========================
    insert_query = """
    INSERT INTO [Raporlar].[dbo].[Car_Price_List]
    (brand, model_name, price, price_date, excel_year)
    VALUES (?, ?, ?, ?, ?)
    """

    rows = [
        (
            row["brand"],
            row["model_name"],
            int(row["price"]) if pd.notna(row["price"]) else None,
            row["price_date"],
            excel_yil
        )
        for _, row in df_long.iterrows()
    ]

    if len(rows) > 0:
        cursor.executemany(insert_query, rows)
        total_insert += len(rows)
        print(f"✅ Insert edilen: {len(rows)}")

# =========================
# FINISH
# =========================
conn.commit()
cursor.close()
conn.close()

print(f"\n🎯 TOPLAM INSERT: {total_insert}")