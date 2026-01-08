# Labeling sản phẩm từ `transformed_data.json`

Repo nhỏ này dùng để **gán nhãn (label)** cho từng sản phẩm dựa trên các chỉ số đã được transform sẵn trong file JSON.

## File trong thư mục

- `labeling.py`: Script đọc dữ liệu, tính percentile và gán nhãn.
- `transformed_data.json`: Dữ liệu đầu vào (đã transform).
- `labeled_data.json`: Dữ liệu đầu ra sau khi gán nhãn (được tạo ra khi chạy script).

## Yêu cầu

- Python 3.8+ (khuyến nghị 3.10+)
- Thư viện: `pandas`

Cài đặt:

```bash
pip install pandas
```

## Cách chạy

Chạy trong đúng thư mục chứa file:

```bash
python labeling.py
```

Sau khi chạy xong, script sẽ tạo file `labeled_data.json` và in ra:

```
Gán nhãn hoàn tất – Đã xuất labeled_data.json
```

## Input / Output

### Input: `transformed_data.json`

Script hiện đang đọc bằng:

```python
df = pd.read_json("transformed_data.json")
```

Vì vậy file JSON cần nằm cùng thư mục và có các cột tối thiểu:

- `sold_velocity`
- `rating_score`
- `discount_percent`
- `popularity_score`

### Output: `labeled_data.json`

Script ghi ra JSON dạng mảng record:

- `orient="records"`
- `force_ascii=False` (giữ tiếng Việt)
- `indent=2`

Mỗi record sẽ có thêm trường:

- `label`: nhãn được gán

## Logic gán nhãn

Script tính các ngưỡng theo percentile trên toàn bộ dataset:

- `p85_discount` = percentile 85% của `discount_percent`
- `p80_sold` = percentile 80% của `sold_velocity`
- `p70_sold` = percentile 70% của `sold_velocity`
- `p80_rating` = percentile 80% của `rating_score`
- `p80_popularity` = percentile 80% của `popularity_score`

Hàm gán nhãn (`assign_label`) theo thứ tự ưu tiên:

1. **`uu_dai`**: nếu `discount_percent >= p85_discount`
2. **`ban_chay`**: nếu `sold_velocity >= p80_sold` và `popularity_score >= p80_popularity`
3. **`hot_trend`**: nếu `sold_velocity >= p70_sold` và `rating_score >= p80_rating`
4. **`binh_thuong`**: còn lại

Lưu ý: do có **thứ tự ưu tiên**, nếu một record thỏa nhiều điều kiện thì sẽ nhận nhãn ở điều kiện xuất hiện trước.

## Gợi ý kiểm tra nhanh

Bạn có thể kiểm tra phân bố nhãn sau khi chạy bằng cách mở `labeled_data.json` hoặc in nhanh trong Python:

```python
import pandas as pd

df = pd.read_json("labeled_data.json")
print(df["label"].value_counts())
```
