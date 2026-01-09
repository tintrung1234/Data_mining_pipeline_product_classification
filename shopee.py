from DrissionPage import ChromiumPage
from DrissionPage import ChromiumOptions
import json
import time
import random
import os
import math

# --- HÀM DELAY THÔNG MINH ---
def smart_delay(action_type='normal'):
    """
    Tạo delay ngẫu nhiên giống người dùng thật
    - quick: 1.5-3s (đọc nhanh, cuộn nhẹ)
    - normal: 3-7s (hành động bình thường)
    - careful: 5-12s (sau khi chuyển trang, tránh spam)
    - wait: 10-20s (sau captcha, chờ xử lý)
    """
    delays = {
        'quick': (1.5, 3),
        'normal': (3, 7), 
        'careful': (5, 12),
        'wait': (10, 20)
    }
    
    min_delay, max_delay = delays.get(action_type, (3, 7))
    # Sử dụng phân phối chuẩn để delay tập trung ở giữa, giống người thật
    base_delay = random.uniform(min_delay, max_delay)
    # Thêm micro-delay ngẫu nhiên để tránh pattern
    micro_jitter = random.uniform(-0.3, 0.5)
    final_delay = max(1, base_delay + micro_jitter)
    
    print(f"   ⏱️ Nghỉ {final_delay:.1f}s...")
    time.sleep(final_delay)
    return final_delay

# --- CẤU HÌNH ---
KEYWORD = "Máy ảnh"
TARGET_COUNT = 800
OUTPUT_FILE = "shopee_data_may_anh.json"

# Khởi tạo trình duyệt
co = ChromiumOptions()
co.set_user_agent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
co.set_argument('--disable-blink-features=AutomationControlled')
co.set_argument('--no-sandbox')
co.set_argument('--disable-dev-shm-usage')
co.set_argument('--start-maximized')

# Uncomment để dùng Chrome profile thật
# co.set_user_data_path(r'C:\Users\Admin\AppData\Local\Google\Chrome\User Data')
# co.set_argument('--profile-directory=Default')

try:
    page = ChromiumPage(addr_or_opts=co)
    print("✅ Kết nối trình duyệt thành công!")
except Exception as e:
    print(f"❌ Lỗi khởi tạo trình duyệt: {e}")
    exit()

print("🚀 Đang khởi động trình duyệt...")

# BƯỚC 1: Vào trang chủ Shopee để đăng nhập
print("📦 Đang truy cập trang chủ Shopee...")
try:
    page.get('https://shopee.vn')
    print("✅ Đã vào trang chủ Shopee!")
except Exception as e:
    print(f"❌ Lỗi truy cập Shopee: {e}")
    exit()

# Đợi người dùng xử lý thủ công TRƯỚC
print("\n⚠️ QUAN TRỌNG - HÃY XỬ LÝ TRƯỚC KHI TIẾP TỤC:")
print("   1. Đăng nhập tài khoản Shopee (BẮT BUỘC ĐỂ ÍT BỊ CAPTCHA HƠN!)")
print("   2. Hoàn thành captcha/xác minh nếu có")
print("   3. Chương trình sẽ tự động tiếp tục sau 25 giây...")
print("   (Mẹo: Đăng nhập = Giảm 80% khả năng bị CAPTCHA khi cào)\n")
time.sleep(25)

# BƯỚC 2: BẬT LISTENER TRƯỚC khi vào trang search (QUAN TRỌNG!)
print("🎯 Bắt đầu lắng nghe API 'search_items'...")
page.listen.start('search_items')

# BƯỚC 3: SAU ĐÓ MỚI vào trang search để bắt gói tin
print(f"🔍 Đang truy cập tìm kiếm: {KEYWORD}")
try:
    page.get(f'https://shopee.vn/search?keyword={KEYWORD}')
    print("✅ Đã vào trang tìm kiếm!")
    time.sleep(5)  # Chờ API phản hồi
except Exception as e:
    print(f"❌ Lỗi truy cập trang tìm kiếm: {e}")
    exit()

all_products = []
page_count = 0

print(f"\n🔄 Bắt đầu cào dữ liệu cho từ khóa: {KEYWORD}")
print("💡 Phương pháp: Lắng nghe gói tin search_items")

while len(all_products) < TARGET_COUNT:
    page_count += 1
    print(f"\n--- Đang xử lý Trang {page_count} (Đã lấy: {len(all_products)}) ---")
    
    # 1. Kiểm tra nếu bị chặn
    if page.ele('text:Trang không khả dụng', timeout=1) or page.ele('text:Traffic Error', timeout=1):
        print("🛑 BỊ CHẶN! Hãy xử lý captcha hoặc đổi mạng.")
        page.listen.stop()
        input("👉 Nhấn Enter sau khi xử lý để tiếp tục...")
        page.listen.start('search_items')
        page.refresh()
        time.sleep(5)
    
    # 2. Cuộn trang giả lập hành vi người dùng
    print("-> Đang cuộn trang giả lập hành vi...")
    page.scroll.to_bottom()
    smart_delay('quick')  # Delay ngắn sau khi cuộn
    
    # 3. Thu thập gói tin API với TIMEOUT (QUAN TRỌNG!)
    print("-> Đang bắt gói tin API...")
    items_in_page = 0
    found_packet = False
    
    try:
        # Sử dụng timeout=8 để đợi gói tin nếu mạng chậm hoặc có CAPTCHA
        for packet in page.listen.steps(timeout=8):
            print(f"   📡 Bắt được: {packet.url[:60]}...")
            found_packet = True
            
            try:
                body = packet.response.body
                if not isinstance(body, dict):
                    continue
                
                # Lấy danh sách items
                items = None
                if 'items' in body:
                    items = body['items']
                elif 'data' in body and isinstance(body['data'], dict):
                    items = body['data'].get('items')
                
                if not items:
                    continue
                
                print(f"   ✅ Tìm thấy {len(items)} sản phẩm trong gói tin")
                
                for item in items:
                    basic = item.get('item_basic', item)
                    itemid = basic.get('itemid') or basic.get('item_id')
                    shopid = basic.get('shopid') or basic.get('shop_id')
                    
                    if not itemid or not shopid:
                        continue
                    
                    # Chuẩn hóa rating_star: lấy 1 chữ số thập phân (truncate, không làm tròn)
                    raw_rating = basic.get('item_rating', {}).get('rating_star', 0)
                    try:
                        r = float(raw_rating) if raw_rating is not None else 0.0
                        rating_star_val = math.floor(r * 10) / 10
                    except Exception:
                        rating_star_val = raw_rating

                    product = {
                        'itemid': str(itemid),
                        'shopid': str(shopid),
                        'name': basic.get('name', 'N/A'),
                        'price': round((basic.get('price', 0) or 0) / 100000, 2),
                        'historical_sold': basic.get('historical_sold', 0),
                        'liked_count': basic.get('liked_count', 0),
                        'rating_star': rating_star_val,
                        'discount': basic.get('discount', ''),
                        'location': basic.get('shop_location', 'N/A'),
                        'image': f"https://down-vn.img.susercontent.com/file/{basic.get('image')}" if basic.get('image') else '',
                        'url': f"https://shopee.vn/product/{shopid}/{itemid}"
                    }
                    
                    if not any(p['itemid'] == product['itemid'] for p in all_products):
                        all_products.append(product)
                        items_in_page += 1
                        
            except Exception as e:
                print(f"   ⚠️ Lỗi đọc gói tin: {e}")
                continue
    
    except Exception as e:
        print(f"   ❌ Lỗi listener: {e}")
    
    # --- XỬ LÝ CAPTCHA HOẶC KHÔNG CÓ DỮ LIỆU ---
    if items_in_page == 0:
        print("\n🛑 CẢNH BÁO: KHÔNG TÌM THẤY SẢN PHẨM MỚI!")
        print("👉 Có thể Shopee đang hiện CAPTCHA trên màn hình.")
        print("👉 HÃY KIỂM TRA TRÌNH DUYỆT VÀ GIẢI CAPTCHA BẰNG TAY NGAY.")
        print("👉 Hoặc có thể đã hết trang sản phẩm.\n")
        
        # Dừng chương trình chờ user giải captcha
        input("👉 SAU KHI GIẢI XONG CAPTCHA (hoặc kiểm tra xong), BẤM [ENTER] ĐỂ TIẾP TỤC...")
        
        print("🔄 Đang thử tải lại trang hiện tại...")
        page.refresh()  # Tải lại trang để lấy lại dữ liệu
        smart_delay('normal')  # Delay sau refresh
        page_count -= 1  # Lùi lại biến đếm để cào lại trang này
        continue  # Quay lại đầu vòng lặp
    
    print(f"-> Tìm thấy {items_in_page} sản phẩm mới. Tổng: {len(all_products)}")
    
    # 4. Lưu dữ liệu tạm thời
    if items_in_page > 0:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_products, f, ensure_ascii=False, indent=2)
        print(f"-> Đã lưu tạm vào {OUTPUT_FILE}")
    
    # 5. Kiểm tra điều kiện dừng
    if len(all_products) >= TARGET_COUNT:
        print("✅ Đã đạt đủ số lượng mục tiêu!")
        break
    
    if items_in_page == 0:
        print("⚠️ Cảnh báo: Trang này không lấy được sản phẩm nào.")
        smart_delay('wait')  # Delay dài khi không lấy được sản phẩm
    
    # 6. Chuyển sang trang tiếp theo
    try:
        btn_next = None
        next_selectors = [
            'xpath://button[contains(@class, "next") and not(contains(@class, "disabled"))]',
            'xpath://button[@aria-label="Next page"]',
            'css:.shopee-icon-button--right:not(.shopee-button-disabled)'
        ]
        
        for selector in next_selectors:
            try:
                btn_next = page.ele(selector, timeout=2)
                if btn_next:
                    break
            except:
                continue
        
        if btn_next:
            is_disabled = 'disabled' in (btn_next.attr('class') or '').lower()
            
            if not is_disabled:
                print("-> Bấm Next sang trang sau...")
                btn_next.click()
                
                # Không cần clear listener, steps() tự đọc tiếp gói mới
                smart_delay('careful')  # Delay dài hơn sau khi chuyển trang
            else:
                print("🛑 Nút Next bị disabled. Có thể hết trang.")
                print("👉 Kiểm tra trình duyệt xem còn trang nào không?")
                input("👉 Nhấn [ENTER] để thử lại hoặc Ctrl+C để thoát...")
                if len(all_products) < TARGET_COUNT:
                    page.refresh()
                    smart_delay('normal')  # Delay sau refresh khi next bị disabled
                    page_count -= 1
                    continue
                else:
                    break
        else:
            print("🛑 Không tìm thấy nút Next.")
            print("👉 Có thể có CAPTCHA hoặc lỗi tải trang.")
            input("👉 Kiểm tra trình duyệt, nhấn [ENTER] để thử lại hoặc Ctrl+C để thoát...")
            page.refresh()
            smart_delay('normal')  # Delay sau refresh khi không tìm thấy next
            page_count -= 1
            continue
            
    except Exception as e:
        print(f"🛑 Lỗi khi chuyển trang: {e}")
        break

print(f"\n🎉 HOÀN TẤT! Tổng cộng: {len(all_products)} sản phẩm.")
print(f"File dữ liệu nằm tại: {os.path.abspath(OUTPUT_FILE)}")