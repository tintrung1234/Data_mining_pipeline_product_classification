# Quy trình Xử lý và Gán nhãn Dữ liệu (Data Mining Pipeline)

Tài liệu này mô tả chi tiết 3 quy trình chính trong việc xử lý dữ liệu: **Làm sạch (Data Cleaning)**, **Tạo đặc trưng (Feature Engineering)**, và **Gán nhãn (Data Labeling)**.

---

## 1. Làm sạch dữ liệu (`data_cleaning.py`)

**Mục đích:**
Chuẩn hóa dữ liệu thô từ nhiều nguồn khác nhau về một định dạng thống nhất để phục vụ cho các bước phân tích tiếp theo.

*   **Input:** `merged_all_data.json`
*   **Output:** `clean_data.json`

**Các bước xử lý chính:**
1.  **Thêm nguồn dữ liệu (Source):** Ghi nhận tên file nguồn vào cột `source`.
2.  **Chọn cột (Schema-Agnostic):** Tự động tìm và ánh xạ các cột quan trọng (`price`, `sold`, `rating`, `id`) từ các tên biến thể khác nhau (ví dụ: `price_sale`, `price`, `sales`, `sold_count`...).
3.  **Xóa trùng lặp:** Loại bỏ các bản ghi trùng dựa trên `id` và `source`.
4.  **Xử lý giá trị thiếu (Missing Values):**
    *   Xóa dòng nếu thiếu giá trị `price`.
    *   Điền `0` nếu thiếu dữ liệu bán (`sold`).
    *   Điền giá trị trung vị (median) nếu thiếu `rating`.
5.  **Chuẩn hóa kiểu dữ liệu:**
    *   **Price:** Loại bỏ ký tự không phải số (ví dụ: "120.000đ" -> 120000), chuyển sang kiểu số nguyên.
    *   **Sold:** Chuyển đổi các định dạng rút gọn (ví dụ: "1.2k" -> 1200, "10+" -> 10).
    *   **Rating:** Giới hạn giá trị trong khoảng [0, 5].

---

## 2. Trích xuất đặc trưng (`feature.py`)

**Mục đích:**
Tạo ra các đặc trưng mới (new features) từ dữ liệu gốc để đo lường độ phổ biến, tốc độ bán và chất lượng sản phẩm một cách định lượng.

*   **Input:** `transformed_data.json` (Lưu ý: Code hiện tại đọc file này, cần đảm bảo dữ liệu đầu vào có các trường `quantity_sold_value`, `rating_average`, `review_count`, `discount_rate`).
*   **Output:** `featured_data.json`

**Các đặc trưng được tạo:**
1.  **Sold Velocity (Tốc độ bán tương đối):**
    *   Công thức: `log(quantity_sold + 1)`
    *   Ý nghĩa: Giảm sự chênh lệch quá lớn giữa các sản phẩm bán cực chạy và sản phẩm thông thường.
2.  **Rating Score (Điểm đánh giá có trọng số):**
    *   Công thức: `rating_avg * log(review_count + 1)`
    *   Ý nghĩa: Đánh giá cao các sản phẩm có rating cao VÀ nhiều lượt review (tin cậy hơn rating cao nhưng ít review).
3.  **Discount Percent:**
    *   Lấy trực tiếp từ `discount_rate`.
4.  **Popularity Score (Điểm phổ biến):**
    *   Công thức: `0.7 * quantity_sold + 0.3 * review_count`
    *   Ý nghĩa: Tổng hợp giữa số lượng bán ra (trọng số cao) và lượng tương tác (review).

---

## 3. Gán nhãn dữ liệu (`labeling.py`)

**Mục đích:**
Phân loại sản phẩm vào các nhóm nhãn (`label`) cụ thể dựa trên các ngưỡng thống kê (percentile) của các đặc trưng đã tạo.

*   **Input:** `transformed_data.json` (Code hiện tại đọc file này, yêu cầu phải chứa các trường feature đã tạo ở bước 2 như `sold_velocity`, `rating_score`...).
*   **Output:** `labeled_data.json`

**Logic gán nhãn:**
Code tính toán các phân vị (percentile) 70%, 80%, 85% của dữ liệu để làm ngưỡng so sánh. Quy tắc ưu tiên từ trên xuống dưới:

1.  **ƯU ĐÃI (`uu_dai`):**
    *   Điều kiện: `discount_percent` >= Top 15% cao nhất (85th percentile).
2.  **BÁN CHẠY (`ban_chay`):**
    *   Điều kiện: `sold_velocity` >= Top 20% **VÀ** `popularity_score` >= Top 20%.
3.  **HOT TREND (`hot_trend`):**
    *   Điều kiện: `sold_velocity` >= Top 30% **VÀ** `rating_score` >= Top 20%.
4.  **BÌNH THƯỜNG (`binh_thuong`):**
    *   Các trường hợp còn lại.

---
