# Giải thích Labeling (Hybrid: Rule seeds + AI model)

File code chính: [labeling.py](labeling.py)

Mục tiêu: gán 4 nhãn sản phẩm:
- `Best Seller`: bán chạy
- `Best Deal`: ưu đãi tốt
- `Hot Trend`: đang nổi
- `Normal`: còn lại

## Vì sao dùng Hybrid?
Nếu chỉ dùng rule (ngưỡng/percentile), kết quả dễ “cứng” và nhạy với thay đổi dữ liệu.
Hybrid giúp:
1) Rule chỉ gán nhãn cho các case **rất chắc chắn** (precision cao) → tạo tập "seed".
2) Model học từ seed để gán nhãn cho các case **mơ hồ** hơn.
3) Nếu không đủ seed hoặc thiếu thư viện ML, hệ thống tự **fallback** về rule đầy đủ.

## Pipeline tổng quan
1. `_calculate_thresholds()`
   - Tính các phân vị (P75, P85, P90…) cho các feature quan trọng.

2. `_assign_seed_labels()`
   - Dùng các rule **chặt hơn** (stricter) để gán `seed_label` cho các sản phẩm chắc chắn.
   - Các sản phẩm không chắc chắn sẽ có `seed_label = NaN`.

3. `_train_and_predict_from_seeds()`
   - Chọn feature tabular đã engineering (số + category).
   - One-hot cho các cột category.
   - Train model (mặc định `RandomForestClassifier`) trên dữ liệu seed.
   - Predict nhãn cho phần còn lại.
   - Nếu `max_proba < --prob-threshold` → gán về `Normal` để giảm nhãn sai.

4. Fallback (khi cần)
   - Nếu không đủ seed cho tối thiểu 2 class (hoặc dưới `--min-seed-per-class`) hoặc thiếu `scikit-learn`:
     - chạy `_assign_labels()` (rule-based full) để gán nhãn cho tất cả.

---

## Chi tiết về Model ML (scikit-learn)

Model ML trong code này đóng vai trò **mở rộng nhãn** từ seed sang các mẫu mơ hồ (hybrid approach).

### 1) Vai trò của Model
- Rule-based chỉ gán nhãn cho các case **rất chắc chắn** → tạo cột `seed_label`.
- Model scikit-learn học từ các dòng có `seed_label` để dự đoán nhãn cho các dòng còn lại.
- Nếu không đủ điều kiện train (thiếu seed, thiếu sklearn, ...) → fallback về rule-based full.

### 2) Nguồn dữ liệu Train
Trong `_train_and_predict_from_seeds()`:
- Chỉ lấy các dòng đã có `seed_label` (không phải `NaN`).
- Kiểm tra số lượng seed tối thiểu theo `--min-seed-per-class` (mặc định 50).
- Cần ít nhất 2 lớp hợp lệ, nếu không sẽ return `False` → fallback.

**Quan trọng:** Model không train trên nhãn "final", mà train trên nhãn seed (độ tin cậy cao).

### 3) Features đầu vào (X)
Code xây dựng feature matrix từ 2 nhóm:

**Numeric features (mặc định):**
- `quantity_sold`, `rating_average`, `num_reviews`
- `current_price`, `original_price`, `discount_rate`
- `discount_intensity_score`, `value_score`, `engagement_score`

**Categorical features (mặc định):**
- `quality_category`, `popularity_category`, `price_segment`
- `seller_tier`, `brand_strength`, `lifecycle_status`, `discount_intensity`

**Preprocessing:**
- Numeric: thay `inf/-inf` → NaN → `fillna(0.0)`
- Categorical: ép kiểu object → `fillna('Unknown')` → one-hot encoding (`pd.get_dummies()`)
- Ghép: `X = concat([X_num, X_cat])`

**Lưu ý:** Model này là **tabular model**, không sử dụng text (`product_name`).

### 4) Train/Validation Split
- Chia 80/20 train/val, có `stratify=y` để giữ phân bố nhãn seed.
- In ra `val acc` (accuracy trên tập val) để kiểm tra nhanh chất lượng model.

### 5) Chọn Model

**Random Forest (mặc định):**
```python
RandomForestClassifier(
    n_estimators=400,
    class_weight='balanced_subsample',
    n_jobs=-1
)
```
- ✅ Mạnh cho dữ liệu tabular
- ✅ Bắt quan hệ phi tuyến tốt
- ✅ Ít cần scale/normalize
- ⚠️ Nặng hơn, khó giải thích

**Logistic Regression (khi dùng `--model logistic_regression`):**
```python
LogisticRegression(
    max_iter=1000,
    multi_class='auto'
)
```
- ✅ Nhanh, baseline dễ hiểu
- ✅ Ranh giới tuyến tính, dễ giải thích
- ⚠️ Kém nếu quan hệ phi tuyến phức tạp

Tóm tắt:

Chạy python labeling.py → dùng Random Forest (mặc định)
Chạy python [labeling.py](http://_vscodecontentref_/2) --model logistic_regression → dùng Logistic Regression

### 6) Dự đoán với Ngưỡng Xác suất
Model dự đoán cho các dòng chưa có seed (`seed_label = NaN`):

```python
if best_prob >= prob_threshold:
    label = predicted_class
else:
    label = 'Normal'
```

**Tác động của `--prob-threshold`:**
- Threshold cao (0.65–0.75) → model "khó tính", nhiều mẫu về `Normal`
- Threshold thấp (0.5) → model "phủ" nhãn rộng hơn

Mục tiêu: giảm việc model "gán bừa" vào các nhãn đặc biệt khi không chắc chắn.

### 7) Merge kết quả và `label_source`
Sau khi dự đoán:
- Dòng có seed: `label = seed_label`, `label_source = 'rule_seed'` (model không override)
- Dòng không seed: `label = predicted_label`, `label_source = 'model'`
- Nếu fallback: tất cả `label_source = 'rule_full'`

### 8) Gợi ý Tinh chỉnh Model
- **Model gán nhãn lung tung:** tăng `--prob-threshold` (0.65–0.75)
- **Model không chạy vì seed ít:** giảm `--min-seed-per-class` (20–30) hoặc nới rule seed
- **Muốn nhanh/nhẹ:** dùng `--model logistic_regression` hoặc `--no-model` (rule-only)
- **Cần đánh giá tốt hơn:** xuất confusion matrix / classification report trên seed-val

---

## Output columns
Sau khi chạy, output JSON sẽ có thêm các cột:
- `label`: nhãn cuối cùng
- `seed_label`: nhãn seed (chỉ có ở các case chắc chắn)
- `seed_reason`: lý do gán seed
- `label_source`:
  - `rule_seed`: nhãn lấy trực tiếp từ seed (model không override)
  - `model`: nhãn do model dự đoán
  - `rule_full`: nhãn do rule-based full (fallback hoặc dùng `--no-model`)

## Tham số quan trọng
- `--prob-threshold` (mặc định 0.55)
  - Tăng lên (0.6–0.75) nếu bạn muốn model chỉ gán nhãn khi rất chắc.
  - Giảm xuống (0.5) nếu bạn muốn model “phủ” nhãn rộng hơn.

- `--min-seed-per-class` (mặc định 50)
  - Seed quá ít → model học kém hoặc bị lệch nhãn.
  - Nếu dataset nhỏ, có thể giảm xuống 20–30.

- `--model`
  - `random_forest` (mặc định): mạnh cho tabular, ít cần tuning.
  - `logistic_regression`: baseline nhanh, dễ giải thích (tuyến tính).

## Cách chạy
- Chạy hybrid (mặc định):
  - `python labeling.py`

- Chỉ chạy rule-based full (không train model):
  - `python labeling.py --no-model`

- Tùy chỉnh tham số:
  - `python labeling.py --prob-threshold 0.65 --min-seed-per-class 80 --model random_forest`

## Gợi ý tối ưu tiếp
- Nếu seed quá ít: nới rule seed (bớt chặt) hoặc giảm `--min-seed-per-class`.
- Nếu model gán sai nhiều: tăng `--prob-threshold`, hoặc làm seed chặt hơn (precision cao hơn).
- Nếu muốn kiểm soát chất lượng: xuất thêm report (confusion matrix) bằng cách tự gán nhãn tay 200–500 mẫu để đánh giá.
