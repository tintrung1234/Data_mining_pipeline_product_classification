import json
import math

# ==============================
# LOAD JSON DATA
# ==============================
with open("merged_cleaned.json", "r", encoding="utf-8") as f:
    data = json.load(f)

transformed_data = []

# ==============================
# FEATURE ENGINEERING
# ==============================
for item in data:
    quantity_sold = item.get("quantity_sold_value", 0)
    rating_avg = item.get("rating_average", 0)
    review_count = item.get("review_count", 0)

    # Feature 1: Sold velocity (relative)
    sold_velocity = math.log(quantity_sold + 1)

    # Feature 2: Rating score (weighted)
    rating_score = rating_avg * math.log(review_count + 1)

    # Feature 3: Discount percent
    discount_percent = item.get("discount_rate", 0)

    # Feature 4: Popularity score
    popularity_score = 0.7 * quantity_sold + 0.3 * review_count

    # Add new features to item
    new_item = item.copy()
    new_item["sold_velocity"] = round(sold_velocity, 4)
    new_item["rating_score"] = round(rating_score, 4)
    new_item["discount_percent"] = round(discount_percent, 2)
    new_item["popularity_score"] = round(popularity_score, 2)

    transformed_data.append(new_item)

# ==============================
# SAVE NEW JSON
# ==============================
with open("featured_data.json", "w", encoding="utf-8") as f:
    json.dump(transformed_data, f, ensure_ascii=False, indent=2)

print("Feature engineering completed. Output: featured_data.json")
