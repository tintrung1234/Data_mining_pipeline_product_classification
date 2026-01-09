import requests
import time
import random
from tqdm import tqdm
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import re
import pandas as pd
import datetime
import logging
import os

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

LAZADA_CATEGORIES = [
    # ===== ĐIỆN TỬ & CÔNG NGHỆ =====
    {"name": "Điện thoại di động", "path": "dien-thoai-di-dong"},
    {"name": "Máy tính bảng", "path": "may-tinh-bang"},
    {"name": "Laptop", "path": "laptop"},
    {"name": "Pin sạc dự phòng", "path": "pin-sac-du-phong"},
    {"name": "Tai nghe không dây", "path": "shop-wireless-earbuds"},
    {"name": "Máy ảnh máy quay phim", "path": "may-anh-may-quay-phim"},

    # # ===== ĐIỆN GIA DỤNG =====
    {"name": "Tủ lạnh", "path": "tu-lanh"},
    {"name": "Máy giặt", "path": "may-giat"},
    {"name": "Máy lạnh", "path": "may-lanh"},

    # # ===== THỜI TRANG =====
    {"name": "Áo phông & Áo ba lỗ", "path": "shop-t-shirts-&-tanks"},
    {"name": "Quần jeans", "path": "shop-men-jeans"},

    # # ===== LÀM ĐẸP - SỨC KHỎE =====
    {"name": "Dưỡng da & Serum", "path": "duong-da-va-serum"},
    {"name": "Son thỏi", "path": "son-thoi"},

    # # ===== BÁCH HÓA ONLINE =====
    {"name": "Bách hóa online", "path": "bach-hoa-online"},

    # ===== NHÀ CỬA - ĐỜI SỐNG =====
    {"name": "Phụ kiện làm thơm phòng", "path": "do-dung-lam-thom-phong"},
    {"name": "Giường", "path": "giuong"},

    # ===== THỂ THAO & DU LỊCH =====
    {"name": "Bóng đá", "path": "bong-da"},
    {"name": "Máy chạy bộ", "path": "may-chay-bo"},
    {"name": "Bikini", "path": "bikini-2"},

    {"name": "Búp bê cho bé", "path": "bup-be-cho-be"},
    {"name": "Xe máy", "path": "xe-may"},
]


def get_fresh_cookies(path):
    options = Options()
    # options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.get(f"https://www.lazada.vn/{path}")
        time.sleep(10)
        driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight / 2);")
        time.sleep(5)

        cookies = {c['name']: c['value'] for c in driver.get_cookies()}
        logging.info(f"Lấy cookie thành công: {len(cookies)} cookies")
        return cookies
    except Exception as e:
        logging.error(f"Lỗi lấy cookie: {e}")
        return {}
    finally:
        driver.quit()


def crawl_category(cat, max_pages=20, max_retries=2):
    path = cat["path"]
    name = cat["name"]
    BASE_URL = f"https://www.lazada.vn/{path}/"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "vi-VN,vi;q=0.9",
        "Referer": f"https://www.lazada.vn/{path}/",
        "X-Requested-With": "XMLHttpRequest",
    }

    products = []
    page = 1
    cookies = get_fresh_cookies(path)

    if not cookies:
        logging.error(f"Không lấy được cookie cho {name} → bỏ qua")
        return products

    while page <= max_pages:
        params = {"ajax": "true", "page": page}
        retry_count = 0
        success = False

        while retry_count < max_retries and not success:
            try:
                resp = requests.get(BASE_URL, headers=HEADERS,
                                    cookies=cookies, params=params, timeout=20)

                if not resp.text.strip().startswith("{"):
                    logging.warning(
                        f"{name} page {page}: Không phải JSON → refresh cookie (retry {retry_count + 1})")
                    cookies = get_fresh_cookies(path)
                    if not cookies:
                        logging.error(
                            f"Không lấy được cookie mới cho {name} page {page}")
                        break
                    retry_count += 1
                    time.sleep(random.uniform(10, 20))
                    continue

                data = resp.json()
                items = data.get("mods", {}).get("listItems", [])

                if not items:
                    logging.info(f"{name} - Hết dữ liệu ở page {page}")
                    success = True
                    break

                logging.info(f"{name} - Page {page}: {len(items)} sản phẩm")

                for item in items:
                    sold_text = item.get("itemSoldCntShow", "").strip()
                    sold_value = None
                    if sold_text:
                        numbers = re.findall(
                            r'\d+', sold_text.replace(',', ''))
                        if numbers:
                            sold_value = int(numbers[0])
                            if 'k' in sold_text.lower() or 'K' in sold_text:
                                sold_value *= 1000

                    products.append({
                        "crawl_date": datetime.datetime.now().strftime("%Y-%m-%d"),
                        "platform": "Lazada",
                        "category_name": name,
                        "id": item.get("itemId"),
                        "name": item.get("name"),
                        "price": item.get("priceShow") or item.get("price"),
                        "original_price": item.get("originalPriceShow") or item.get("originalPrice"),
                        "discount": item.get("discount"),
                        "rating": item.get("ratingScore"),
                        "review_count": item.get("review"),
                        "sold_value": sold_value,
                        "sold_text": sold_text or None,
                        "brand": item.get("brandName"),
                        "location": item.get("location"),
                        "seller_name": item.get("sellerName"),
                        "url": "https://www.lazada.vn" + item.get("itemUrl") if item.get("itemUrl") else None,
                        "image": item.get("image"),
                    })

                success = True
                page += 1
                time.sleep(random.uniform(3, 7))

            except Exception as e:
                logging.error(
                    f"{name} page {page}: Lỗi {e} → retry {retry_count + 1}")
                retry_count += 1
                time.sleep(random.uniform(10, 20))

        if not success:
            logging.error(f"{name} page {page}: Đạt max retry → bỏ qua page")
            page += 1

    return products


def crawl_all():
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    all_products = []
    # Tạo thư mục lưu file riêng
    os.makedirs("lazada_categories", exist_ok=True)

    for cat in tqdm(LAZADA_CATEGORIES, desc="Danh mục Lazada"):
        cat_name = cat["name"]
        logging.info(f"Bắt đầu crawl: {cat_name}")

        prods = crawl_category(cat, max_pages=20)

        if prods:
            # Lưu file riêng cho từng category
            safe_name = re.sub(r'[<>:"/\\|?*]', '_',
                               cat_name)  # Làm sạch tên file
            # Giới hạn độ dài tên
            cat_filename = f"lazada_categories/lazada_{safe_name[:50]}_{timestamp}.csv"
            df_cat = pd.DataFrame(prods)
            df_cat.to_csv(cat_filename, index=False, encoding="utf-8-sig")
            logging.info(
                f"Đã lưu {len(prods)} sản phẩm của '{cat_name}' vào {cat_filename}")

            all_products.extend(prods)
        else:
            logging.warning(f"Không có dữ liệu cho category: {cat_name}")

        time.sleep(random.uniform(10, 20))

    # Lưu file tổng hợp
    if all_products:
        df_all = pd.DataFrame(all_products)
        total_filename = f"lazada_all_{timestamp}.csv"
        df_all.to_csv(total_filename, index=False, encoding="utf-8-sig")
        logging.info(
            f"HOÀN THÀNH! Lưu tổng cộng {len(all_products)} sản phẩm vào {total_filename}")
    else:
        logging.warning("Không có dữ liệu nào được crawl")


if __name__ == "__main__":
    crawl_all()
