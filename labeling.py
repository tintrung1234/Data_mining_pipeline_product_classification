import pandas as pd
import numpy as np
import json
import os
from typing import Dict, Tuple, Optional


class ProductLabeler:
    """
    Labeling Module cho phân vùng sản phẩm (Product Segmentation)

    Target Categories (4 danh mục):
    1. Hot Trend: Sản phẩm đang nổi trào, engagement cao
    2. Best Seller: Sản phẩm bán chạy nhất
    3. Best Deal: Sản phẩm có ưu đãi tốt
    4. Normal: Sản phẩm bình thường
    """

    def __init__(self, df: pd.DataFrame):
        """
        Khởi tạo Product Labeler

        Parameters:
        - df: DataFrame đã được feature engineering
        """
        self.df = df.copy()
        self.label_stats = {}
        self.thresholds = {}

    def create_labels(self) -> pd.DataFrame:
        """
        Tạo labels cho sản phẩm dựa trên features đã được engineering

        Prioritize theo thứ tự:
        1. Best Seller (cao nhất priority)
        2. Best Deal
        3. Hot Trend
        4. Normal (default)
        """

        print("🏷️  BẮT ĐẦU LABELING")
        print("=" * 70)

        # 1. Tính thresholds cho từng feature
        print("\n✓ Bước 1: Tính toán thresholds...")
        self._calculate_thresholds()

        # 2. Tạo labels
        print("✓ Bước 2: Tạo labels cho sản phẩm...")
        self._assign_labels()

        # 3. Thống kê labels
        print("\n" + "=" * 70)
        print(f"✅ HOÀN THÀNH LABELING")
        print(f"   Total products: {len(self.df):,}")

        return self.df

    def _calculate_thresholds(self):
        """
        Tính toán thresholds cho mỗi danh mục

        Best Seller:
        - quantity_sold >= P75
        - rating_average >= 3.8

        Best Deal:
        - discount_intensity_score >= P75
        - value_score >= P60

        Hot Trend:
        - engagement_score >= P75
        - popularity_category in ['Viral', 'Hot']
        """

        # Best Seller thresholds
        q_sold_p75 = self.df['quantity_sold'].quantile(0.75)
        q_sold_p90 = self.df['quantity_sold'].quantile(0.90)
        rating_threshold = 3.8

        # Best Deal thresholds
        discount_score_p75 = self.df['discount_intensity_score'].quantile(0.75)
        value_score_p60 = self.df['value_score'].quantile(0.60)
        value_score_p70 = self.df['value_score'].quantile(0.70)

        # Hot Trend thresholds
        engagement_score_p75 = self.df['engagement_score'].quantile(0.75)
        engagement_score_p85 = self.df['engagement_score'].quantile(0.85)

        self.thresholds = {
            'best_seller': {
                'quantity_sold_p75': q_sold_p75,
                'quantity_sold_p90': q_sold_p90,
                'rating': rating_threshold
            },
            'best_deal': {
                'discount_score_p75': discount_score_p75,
                'value_score_p60': value_score_p60,
                'value_score_p70': value_score_p70
            },
            'hot_trend': {
                'engagement_score_p75': engagement_score_p75,
                'engagement_score_p85': engagement_score_p85
            }
        }

        print(f"   Best Seller - quantity_sold >= {q_sold_p75:,.0f}")
        print(
            f"   Best Deal - discount_score >= {discount_score_p75:.2f} & value_score >= {value_score_p60:.2f}")
        print(
            f"   Hot Trend - engagement_score >= {engagement_score_p75:.2f}")

    def _assign_labels(self):
        """
        Gán label cho mỗi sản phẩm dựa trên features

        Logic:
        1. Best Seller: quantity_sold cao nhất, rating tốt
        2. Best Deal: discount lớn + value_score cao
        3. Hot Trend: engagement cao + popularity cao
        4. Normal: Phần còn lại
        """

        def categorize_product(row):
            # Feature metrics
            quantity_sold = row['quantity_sold']
            rating = row['rating_average']
            discount_score = row['discount_intensity_score']
            value_score = row['value_score']
            engagement_score = row['engagement_score']
            popularity = row['popularity_category']
            lifecycle = row['lifecycle_status']
            discount_intensity = row['discount_intensity']

            # Thresholds
            q_sold_p90 = self.thresholds['best_seller']['quantity_sold_p90']
            q_sold_p75 = self.thresholds['best_seller']['quantity_sold_p75']
            rating_th = self.thresholds['best_seller']['rating']

            discount_score_p75 = self.thresholds['best_deal']['discount_score_p75']
            value_score_p70 = self.thresholds['best_deal']['value_score_p70']
            value_score_p60 = self.thresholds['best_deal']['value_score_p60']

            engagement_p85 = self.thresholds['hot_trend']['engagement_score_p85']
            engagement_p75 = self.thresholds['hot_trend']['engagement_score_p75']

            # Priority 1: Best Seller
            # Sản phẩm bán chạy nhất - quantity cao + rating tốt + lifecycle mature
            if (quantity_sold >= q_sold_p90 and rating >= rating_th):
                return 'Best Seller'
            elif (quantity_sold >= q_sold_p75 and rating >= 4.0 and lifecycle == 'Maturity'):
                return 'Best Seller'

            # Priority 2: Best Deal
            # Sản phẩm có giá trị tốt - discount cao + value_score cao
            if (discount_score >= discount_score_p75 and value_score >= value_score_p70):
                return 'Best Deal'
            elif (discount_intensity in ['Aggressive', 'Heavy'] and value_score >= value_score_p60):
                return 'Best Deal'

            # Priority 3: Hot Trend
            # Sản phẩm nổi trào - engagement cao + popularity cao
            if (engagement_score >= engagement_p85 and popularity in ['Viral', 'Hot']):
                return 'Hot Trend'
            elif (engagement_score >= engagement_p75 and popularity == 'Viral'):
                return 'Hot Trend'

            # Default: Normal
            return 'Normal'

        self.df['label'] = self.df.apply(categorize_product, axis=1)

        # In thống kê
        print(f"\n   Distribution:")
        label_counts = self.df['label'].value_counts()
        self.label_stats = label_counts.to_dict()

        for label, count in label_counts.items():
            percentage = (count / len(self.df)) * 100
            print(f"     - {label}: {count:,} ({percentage:.1f}%)")

    def get_label_statistics(self) -> Dict:
        """Lấy thống kê của labels"""
        return self.label_stats

    def get_thresholds(self) -> Dict:
        """Lấy thresholds được sử dụng"""
        return self.thresholds

    def get_dataframe(self) -> pd.DataFrame:
        """Trả về DataFrame với labels"""
        return self.df


def create_labeling(input_file: str, output_file: Optional[str] = None) -> pd.DataFrame:
    """
    Hàm main cho labeling

    Parameters:
    - input_file: đường dẫn file engineered features (JSON)
    - output_file: đường dẫn file output (default: data/transformation/labeled_data.json)

    Returns:
    - DataFrame với labels
    """

    print("\n" + "=" * 70)
    print("🎯 PRODUCT LABELING - PHÂN VÀO 4 DANH MỤC")
    print("=" * 70)

    # 1. Đọc dữ liệu
    print("\n📂 Bước 0: Đọc dữ liệu...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    df = pd.DataFrame(data)
    print(f"✓ Đã load {len(df):,} records")

    # 2. Labeling
    labeler = ProductLabeler(df)
    df_labeled = labeler.create_labels()

    # 3. Lưu dữ liệu
    if output_file is None:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_dir = os.path.join(base, 'data/transformation')
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, 'labeled_data.json')

    print(f"\n💾 Lưu dữ liệu vào: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(df_labeled.to_dict('records'),
                  f, ensure_ascii=False, indent=2)

    print(f"✅ Đã lưu {len(df_labeled):,} records\n")

    # 4. Thống kê chi tiết
    print("=" * 70)
    print("📊 CHI TIẾT PHÂN LOẠI")
    print("=" * 70)

    print("\n🏆 Thống kê theo Label:")
    for label in ['Best Seller', 'Best Deal', 'Hot Trend', 'Normal']:
        count = len(df_labeled[df_labeled['label'] == label])
        if count > 0:
            percentage = (count / len(df_labeled)) * 100
            print(f"\n{label}:")
            print(f"  Số lượng: {count:,} ({percentage:.1f}%)")

            # Chi tiết thống kê cho mỗi label
            label_data = df_labeled[df_labeled['label'] == label]

            if label == 'Best Seller':
                print(
                    f"  Avg quantity_sold: {label_data['quantity_sold'].mean():,.0f}")
                print(
                    f"  Avg rating: {label_data['rating_average'].mean():.2f}")
                print(
                    f"  Avg engagement_score: {label_data['engagement_score'].mean():.2f}")

            elif label == 'Best Deal':
                print(
                    f"  Avg discount_score: {label_data['discount_intensity_score'].mean():.2f}")
                print(
                    f"  Avg value_score: {label_data['value_score'].mean():.2f}")
                print(
                    f"  Discount intensity: {label_data['discount_intensity'].value_counts().to_dict()}")

            elif label == 'Hot Trend':
                print(
                    f"  Avg engagement_score: {label_data['engagement_score'].mean():.2f}")
                print(
                    f"  Popularity distribution: {label_data['popularity_category'].value_counts().to_dict()}")
                print(
                    f"  Avg quantity_sold: {label_data['quantity_sold'].mean():,.0f}")

    print("\n" + "=" * 70)
    print("✅ HOÀN THÀNH LABELING\n")

    return df_labeled

if __name__ == "__main__":
    # Resolve paths relative to this script (workspace `code/`) and fallback to parent.
    script_dir = os.path.dirname(os.path.abspath(__file__))

    def _resolve_json_path(filenames):
        candidates = []
        for filename in filenames:
            candidates.extend([
                os.path.join(script_dir, 'json', filename),
                os.path.join(os.path.dirname(script_dir), 'json', filename),
            ])
        for path in candidates:
            if os.path.exists(path):
                return path
        return candidates[0] if candidates else os.path.join(script_dir, 'json', 'featured_data.json')

    # Support both naming conventions.
    input_file = _resolve_json_path(['engineered_features.json', 'featured_data.json'])
    output_file = os.path.join(script_dir, 'json', 'labeled_data.json')

    if not os.path.exists(input_file):
        raise FileNotFoundError(
            "Không tìm thấy input cho labeling. "
            "Cần file engineered_features.json hoặc featured_data.json trong folder json/. "
            f"Đã thử: {os.path.join(script_dir, 'json', 'engineered_features.json')}, "
            f"{os.path.join(script_dir, 'json', 'featured_data.json')} (và các path tương tự ở thư mục cha)."
        )

    df_result = create_labeling(input_file, output_file)
