import pandas as pd
import os

# ======================
# 1. ĐỌC FILE
# ======================
input_file = "merged_all_data.json"
df = pd.read_json(input_file)

# Add source
if "source" not in df.columns:
    df["source"] = os.path.splitext(os.path.basename(input_file))[0]

print("Tổng dòng ban đầu:", df.shape[0])
print("Cột ban đầu:", df.columns.tolist())

# ======================
# 2. HÀM CHỌN CỘT (SCHEMA-AGNOSTIC)
# ======================
def pick_column(df, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return None

price_col  = pick_column(df, ["price_sale", "price", "price_value", "price_original"])
sold_col   = pick_column(df, ["sold_count", "sold", "sales"])
rating_col = pick_column(df, ["rating_score", "rating_avg", "rating", "rating_star"])
id_col     = pick_column(df, ["product_id", "item_id", "id"])

print("Cột được chọn:")
print("price:", price_col)
print("sold:", sold_col)
print("rating:", rating_col)
print("id:", id_col)

# ======================
# 3. XÓA TRÙNG
# ======================
subset_cols = [c for c in [id_col, "source"] if c]

if subset_cols:
    df.drop_duplicates(subset=subset_cols, inplace=True)

print("Sau khi xóa trùng:", df.shape[0])

# ======================
# 4. XỬ LÝ GIÁ TRỊ THIẾU
# ======================

# Không có giá → không dùng được → loại
if price_col:
    df = df[df[price_col].notna()]

# Không có dữ liệu bán → coi như chưa bán
if sold_col:
    df[sold_col] = df[sold_col].fillna(0)

# Rating thiếu → thay bằng giá trị trung vị
if rating_col:
    df[rating_col] = df[rating_col].fillna(df[rating_col].median())

# ======================
# 5. CHUẨN HÓA KIỂU DỮ LIỆU
# ======================
# PRICE EX: "120.000đ" → 120000
if price_col:
    df[price_col] = (
        df[price_col]
        .astype(str)
        .str.replace(r"[^\d]", "", regex=True)
    )
    df = df[df[price_col] != ""]
    df[price_col] = df[price_col].astype(int)

# SOLD EX: "1.2k" → 1200 ; "10+" → 10
def clean_sold(x):
    if pd.isna(x):
        return 0
    if isinstance(x, str):
        x = x.lower().replace("+", "")
        if "k" in x:
            return int(float(x.replace("k", "")) * 1000)
    return int(x)

if sold_col:
    df[sold_col] = df[sold_col].apply(clean_sold)

# RATING EX: "4.6" → 4.6 ; "4.6/5" → 4.6 ; "4.6 (123)" → 4.6
if rating_col:
    df[rating_col] = df[rating_col].clip(0, 5)

# ======================
# 6. XUẤT FILE JSON THƯỜNG
# ======================
output_file = "clean_data.json"

df.to_json(
    output_file,
    orient="records",
    indent=2,
    force_ascii=False
)

print(f"Đã xuất {output_file} (JSON thường)")
