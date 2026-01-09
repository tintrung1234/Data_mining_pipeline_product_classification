# Quy trình Khai phá Dữ liệu (Data Mining Pipeline)

Tài liệu này mô tả chi tiết quy trình xử lý dữ liệu thương mại điện tử từ bước thu thập đến phân tích và gán nhãn.

**Quy trình tổng quan:**
1. Thu thập dữ liệu (Data Crawling)
2. Làm sạch dữ liệu (Data Cleaning)
3. Trích xuất đặc trưng (Feature Engineering)
4. Gán nhãn dữ liệu (Data Labeling)
5. Trực quan hóa (Data Visualization)

---

## Cài đặt & Chạy (Installation & Run)

1.  **Cài đặt thư viện:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Chạy các script (ví dụ):**
    ```bash
    python lazada_auto_crawl.py
    python clean.py
    python feature.py
    python labeling.py
    python visualize.py
    ```

---

## 1. Thu thập dữ liệu (Data Crawling)

Các script thu thập dữ liệu từ ba sàn thương mại điện tử lớn: Lazada, Tiki, và Shopee.

### Lazada (`lazada_auto_crawl.py`)
*   **Phương thức:** Sử dụng Selenium để lấy cookie thực và `requests` để gọi API nội bộ của Lazada.
*   **Quy trình:**
    *   Duyệt qua danh sách các danh mục định sẵn (Điện tử, Gia dụng, Thời trang...).
    *   Tự động cuộn trang để tải dữ liệu và lách các cơ chế chặn.
    *   Lưu dữ liệu thô vào folder `lazada_categories/` và file tổng hợp `lazada_all_[date].csv`.

### Tiki (`tiki_auto_crawl.py`)
*   **Phương thức:** Sử dụng API public `https://tiki.vn/api/personalish/v1/blocks/listings`.
*   **Quy trình:**
    *   Dùng Selenium để lấy cookie hợp lệ ban đầu.
    *   Gửi request API để lấy danh sách sản phẩm theo danh mục và trang.
    *   Lấy các thông tin chi tiết như giá, discount, badge, thông tin nhà bán.
    *   Lưu kết quả vào file `tiki_all_[date].csv`.

### Shopee (`shopee.py`)
*   **Phương thức:** Sử dụng thư viện `DrissionPage` để điều khiển trình duyệt và lắng nghe gói tin mạng (Network Packet Sniffing).
*   **Quy trình:**
    *   Yêu cầu người dùng đăng nhập thủ công để giảm thiểu CAPTCHA.
    *   Lắng nghe API `search_items` trong khi cuộn trang mô phỏng hành vi người dùng.
    *   Tự động xử lý phân trang và lưu dữ liệu JSON realtime.
    *   **Lưu ý:** Script này chạy ở chế độ tương tác bán tự động (Semi-automatic).

---

## 2. Làm sạch dữ liệu (`clean.py`)

**Mục đích:**
Chuẩn hóa dữ liệu thô từ nhiều nguồn khác nhau về một định dạng thống nhất để phục vụ cho các bước phân tích tiếp theo.

*   **Input:** File `.json` hoặc `.csv` thô từ bước crawl (ví dụ: `ecommerce_all_platforms.json`).
*   **Output:** File đã làm sạch (suffix `_cleaned.csv`).

**Các bước xử lý chính:**
1.  **Chuẩn hóa tên cột:** Ánh xạ các tên cột khác nhau (ví dụ: `price_sale`, `price`, `sales`) về tên chuẩn (`current_price`, `quantity_sold_value`...).
2.  **Xử lý kiểu dữ liệu:**
    *   Chuyển đổi giá tiền, phần trăm giảm giá sang số.
    *   Chuyển đổi số lượng đã bán (ví dụ: "1.2k" -> 1200).
3.  **Xử lý giá trị thiếu (Missing Values):** Điền giá trị mặc định cho giá, rating (0.0), review count (0).
4.  **Xóa trùng lặp:**
    *   Ưu tiên xóa trùng theo URL sản phẩm.
    *   Dự phòng xóa trùng theo bộ (`product_name`, `price`, `seller`).

---

## 3. Trích xuất đặc trưng (`feature.py`)

**Mục đích:**
Tạo ra các đặc trưng mới (new features) từ dữ liệu gốc để đo lường độ phổ biến, tốc độ bán và chất lượng sản phẩm một cách định lượng.

*   **Input:** `merged_cleaned.json` (File đã gộp và làm sạch).
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

## 4. Gán nhãn dữ liệu (`labeling.py`)

**Mục đích:**
Phân loại sản phẩm vào các nhóm nhãn (`label`) cụ thể dựa trên các ngưỡng thống kê (percentile) của các đặc trưng đã tạo.

*   **Input:** `featured_data.json`
*   **Output:** `labeled_data.json`

**Logic gán nhãn:**
Sử dụng các phân vị (percentile) 70%, 80%, 85% của toàn bộ tập dữ liệu để làm ngưỡng.

1.  **ƯU ĐÃI (`uu_dai`):**
    *   `discount_percent` >= Top 15% cao nhất.
2.  **BÁN CHẠY (`ban_chay`):**
    *   `sold_velocity` >= Top 20% **VÀ** `popularity_score` >= Top 20%.
3.  **HOT TREND (`hot_trend`):**
    *   `sold_velocity` >= Top 30% **VÀ** `rating_score` >= Top 20%.
4.  **BÌNH THƯỜNG (`binh_thuong`):**
    *   Các trường hợp còn lại.

---

## 5. Trực quan hóa (`visualize.py`)

**Mục đích:**
Vẽ các biểu đồ để phân tích sự phân bố của dữ liệu và nhãn dán, giúp kiểm tra chất lượng bộ dữ liệu.

*   **Input:** `labeled_data.json`
*   **Output:** Các file ảnh `.png` trong thư mục `figures/`.

**Các biểu đồ chính:**
*   `label_distribution.png`: Tỷ lệ các nhãn sản phẩm.
*   `price_distribution.png`: Phân bố giá sản phẩm.
*   `price_vs_sold.png`: Tương quan giữa giá và số lượng bán (Scatter plot).
*   `rating_by_label.png`: So sánh điểm đánh giá giữa các nhãn.
*   `top_products.png`: Top sản phẩm bán chạy nhất theo từng nhãn.
