import pandas as pd

# ==============================
# 0. LOAD DATA (JSON)
# ==============================

df = pd.read_json("transformed_data.json")

# ==============================
# 1. TÍNH PERCENTILE
# ==============================

p80_sold = df["sold_velocity"].quantile(0.80)
p70_sold = df["sold_velocity"].quantile(0.70)
p80_rating = df["rating_score"].quantile(0.80)
p85_discount = df["discount_percent"].quantile(0.85)
p80_popularity = df["popularity_score"].quantile(0.80)

# ==============================
# 2. HÀM GÁN LABEL
# ==============================
def assign_label(row):
    # ƯU ĐÃI
    if row["discount_percent"] >= p85_discount:
        return "uu_dai"
    
    # BÁN CHẠY
    elif (
        row["sold_velocity"] >= p80_sold and
        row["popularity_score"] >= p80_popularity
    ):
        return "ban_chay"
    
    # HOT TREND
    elif (
        row["sold_velocity"] >= p70_sold and
        row["rating_score"] >= p80_rating
    ):
        return "hot_trend"
    
    # BÌNH THƯỜNG
    else:
        return "binh_thuong"

# ==============================
# 3. APPLY LABELING
# ==============================
df["label"] = df.apply(assign_label, axis=1)

# ==============================
# 4. XUẤT FILE (JSON)
# ==============================
df.to_json(
    "labeled_data.json",
    orient="records",
    force_ascii=False,
    indent=2
)

print("Gán nhãn hoàn tất – Đã xuất labeled_data.json")