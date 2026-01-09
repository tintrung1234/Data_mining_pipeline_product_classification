import requests
import time
import random
import pandas as pd
from tqdm import tqdm
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import datetime
import logging

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

CATEGORIES = [
    {"name": "Nhà Sách Tiki", "urlKey": "nha-sach-tiki", "category": "8322"},
    {"name": "Nhà Cửa - Đời sống", "urlKey": "nha-cua-doi-song", "category": "1883"},
    {"name": "Điện Thoại - Máy Tính Bảng",
        "urlKey": "dien-thoai-may-tinh-bang", "category": "1789"},
    {"name": "Đồ Chơi - Mẹ & Bé", "urlKey": "do-choi-me-be", "category": "2549"},
    {"name": "Thiết Bị Số - Phụ Kiện Số",
        "urlKey": "thiet-bi-so-phu-kien-so", "category": "1815"},
    {"name": "Điện Gia Dụng", "urlKey": "dien-gia-dung", "category": "20824"},
    {"name": "Làm Đẹp - Sức Khỏe", "urlKey": "lam-dep-suc-khoe", "category": "1520"},
    {"name": "Ô Tô - Xe Máy - Xe Đạp",
        "urlKey": "o-to-xe-may-xe-dap", "category": "21346"},
    {"name": "Thời Trang Nữ", "urlKey": "thoi-trang-nu", "category": "931"},
    {"name": "Bách Hóa Online", "urlKey": "bach-hoa-online", "category": "4384"},
    {"name": "Thể Thao - Dã Ngoại", "urlKey": "the-thao-da-ngoai", "category": "1975"},
    {"name": "Thời Trang Nam", "urlKey": "thoi-trang-nam", "category": "915"},
    {"name": "Laptop - Máy Vi Tính - Linh Kiện",
        "urlKey": "laptop-may-vi-tinh-linh-kien", "category": "1846"},
    {"name": "Giày Dép Nam", "urlKey": "giay-dep-nam", "category": "1686"},
    {"name": "Điện Tử - Điện Lạnh", "urlKey": "dien-tu-dien-lanh", "category": "4221"},
    {"name": "Giày Dép Nữ", "urlKey": "giay-dep-nu", "category": "1703"},
    {"name": "Máy Ảnh - Máy Quay Phim", "urlKey": "may-anh", "category": "1801"},
    {"name": "Phụ kiện thời trang",
        "urlKey": "phu-kien-thoi-trang", "category": "27498"},
    {"name": "Đồng hồ và Trang sức",
        "urlKey": "dong-ho-va-trang-suc", "category": "8371"},
    {"name": "Balo và Vali", "urlKey": "balo-va-vali", "category": "6000"},
    {"name": "Túi thời trang nữ", "urlKey": "tui-thoi-trang-nu", "category": "976"},
    {"name": "Túi thời trang nam", "urlKey": "tui-thoi-trang-nam", "category": "27616"},
    {"name": "Chăm sóc nhà cửa", "urlKey": "cham-soc-nha-cua", "category": "15078"},
]


def get_fresh_cookies():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.get("https://tiki.vn")
        time.sleep(10)
        cookies = {c['name']: c['value'] for c in driver.get_cookies()}
        logging.info("Lấy cookie thành công")
        return cookies
    except Exception as e:
        logging.error(f"Lỗi lấy cookie: {e} - Sử dụng fallback không cookie")
        return {}  # Fallback nếu fail
    finally:
        driver.quit()


def crawl_category(cat, cookies, max_pages=20, retries=2):
    BASE_URL = "https://tiki.vn/api/personalish/v1/blocks/listings"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": f"https://tiki.vn/{cat['urlKey']}/c{cat['category']}",
        "X-Requested-With": "XMLHttpRequest",
    }

    products = []
    params = {
        "limit": 48,
        "sort": "top_seller",
        "urlKey": cat["urlKey"],
        "category": cat["category"],
        "page": 1,
    }

    for page in range(1, max_pages + 1):
        params["page"] = page
        attempt = 0
        success = False
        while attempt < retries and not success:
            try:
                resp = requests.get(BASE_URL, headers=HEADERS,
                                    cookies=cookies, params=params, timeout=20)
                if resp.status_code != 200:
                    logging.warning(
                        f"{cat['name']} trang {page}: HTTP {resp.status_code}")
                    break

                data = resp.json()
                if page == 1:
                    logging.info(
                        f"{cat['name']} - Response keys: {list(data.keys())}")

                listings = data.get("listings") or data.get("data", []) or []
                if not isinstance(listings, list):
                    logging.warning(
                        f"{cat['name']} trang {page}: Listings không phải list")
                    break

                logging.info(
                    f"{cat['name']} - Trang {page}: {len(listings)} sản phẩm")

                for item in listings:
                    if not item or not isinstance(item, dict):
                        continue  # Bỏ qua item None hoặc không phải dict

                    qs = item.get("quantity_sold", {})
                    badges = [b.get("text") for b in item.get(
                        "badges", []) if b.get("text")]
                    seller = item.get("current_seller", {}) or {}

                    product = {
                        "crawl_date": datetime.datetime.now().strftime("%Y-%m-%d"),
                        "platform": "Tiki",
                        "category_name": cat["name"],
                        "id": item.get("id"),
                        "name": item.get("name"),
                        "price": item.get("price"),
                        "original_price": item.get("list_price") or item.get("original_price"),
                        "discount_rate": item.get("discount_rate"),
                        "rating_average": item.get("rating_average"),
                        "review_count": item.get("review_count"),
                        "quantity_sold_value": qs.get("value") if isinstance(qs, dict) else None,
                        "quantity_sold_text": qs.get("text") if isinstance(qs, dict) else None,
                        "brand": item.get("brand", {}).get("name"),
                        "seller_name": seller.get("name"),
                        "thumbnail_url": item.get("thumbnail_url"),
                        "url": f"https://tiki.vn{item.get('url_path', '')}",
                        "badges": ", ".join(badges),
                    }
                    products.append(product)

                success = True
                time.sleep(random.uniform(3, 6))

            except Exception as e:
                attempt += 1
                logging.error(
                    f"{cat['name']} trang {page} (thử {attempt}): {e}")
                time.sleep(5)

        if not success:
            break

    return products


def crawl_all():
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    all_products = []
    cookies = get_fresh_cookies()

    for cat in tqdm(CATEGORIES, desc="Danh mục"):
        prods = crawl_category(cat, cookies, max_pages=20, retries=2)
        all_products.extend(prods)
        time.sleep(random.uniform(8, 15))

    if all_products:
        df = pd.DataFrame(all_products)
        filename = f"tiki_all_{timestamp}.csv"
        df.to_csv(filename, index=False, encoding="utf-8-sig")
        logging.info(
            f"Hoàn thành! Lưu {len(all_products)} sản phẩm vào {filename}")
    else:
        logging.warning("Không có dữ liệu - Kiểm tra cookie/API")


if __name__ == "__main__":
    crawl_all()
