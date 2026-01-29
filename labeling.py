import pandas as pd
import numpy as np
import json
import os
import argparse
from typing import Any, Dict, Tuple, Optional


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
        Hybrid labeling (một mode duy nhất):
        - Rule chỉ gán nhãn cho các case chắc chắn (seed)
        - Model học từ seed để gán nhãn phần còn lại
        - Nếu không đủ seed / thiếu sklearn -> fallback sang rule-based labeling đầy đủ

        Outputs:
        - label: nhãn cuối cùng
        - seed_label: nhãn seed (chỉ có ở case chắc chắn)
        - seed_reason: lý do seed
        - label_source: 'rule_seed' | 'model' | 'rule_full'
        """

        return self.create_labels_with_params()

    def create_labels_hybrid(
        self,
        prob_threshold: float = 0.55,
        min_seed_per_class: int = 50,
        model_type: str = 'random_forest',
        use_model: bool = True
    ) -> pd.DataFrame:
        """Backward-compatible wrapper (deprecated). Use create_labels_with_params()."""
        return self.create_labels_with_params(
            prob_threshold=prob_threshold,
            min_seed_per_class=min_seed_per_class,
            model_type=model_type,
            use_model=use_model
        )

    def create_labels_with_params(
        self,
        prob_threshold: float = 0.55,
        min_seed_per_class: int = 50,
        model_type: str = 'random_forest',
        use_model: bool = True
    ) -> pd.DataFrame:
        """Hybrid labeling (single pipeline) with tunable params."""

        print("🏷️  BẮT ĐẦU LABELING (HYBRID: RULE SEEDS + AI MODEL)")
        print("=" * 70)

        print("\n✓ Bước 1: Tính toán thresholds...")
        self._calculate_thresholds()

        print("✓ Bước 2: Gán seed labels (rule high precision)...")
        self._assign_seed_labels()

        success = False
        if use_model:
            print("✓ Bước 3: Train & Predict bằng model...")
            try:
                success = self._train_and_predict_from_seeds(
                    prob_threshold=prob_threshold,
                    min_seed_per_class=min_seed_per_class,
                    model_type=model_type
                )
            except ImportError as e:
                print(f"\n⚠️  {e}")
                success = False

        if not success:
            print("\n⚠️  Fallback sang rule-based labeling đầy đủ...")
            self._assign_labels()
            self.df['label_source'] = 'rule_full'

        print("\n" + "=" * 70)
        print("✅ HOÀN THÀNH LABELING")
        print(f"   Total products: {len(self.df):,}")

        print("\n   Distribution:")
        label_counts = self.df['label'].value_counts()
        self.label_stats = label_counts.to_dict()
        for label, count in label_counts.items():
            percentage = (count / len(self.df)) * 100
            print(f"     - {label}: {count:,} ({percentage:.1f}%)")

        if 'label_source' in self.df.columns:
            print("\n   Label source:")
            for src, cnt in self.df['label_source'].value_counts().items():
                print(f"     - {src}: {cnt:,} ({cnt/len(self.df)*100:.1f}%)")

        return self.df

    def _calculate_thresholds(self):
        """
        Tính toán thresholds cho mỗi danh mục (đã cân bằng)

        Best Seller:
        - quantity_sold >= P70
        - rating_average >= 3.8

        Best Deal:
        - discount_intensity_score >= P80
        - value_score >= P75

        Hot Trend:
        - engagement_score >= P70
        - popularity_category in ['Viral', 'Hot']
        """

        # Best Seller thresholds (giảm mạnh ngưỡng để tăng số lượng)
        q_sold_p60 = self.df['quantity_sold'].quantile(0.60)
        q_sold_p70 = self.df['quantity_sold'].quantile(0.70)
        q_sold_p85 = self.df['quantity_sold'].quantile(0.85)
        rating_threshold = 3.8

        # Best Deal thresholds (tăng mạnh ngưỡng để giảm số lượng)
        discount_score_p80 = self.df['discount_intensity_score'].quantile(0.80)
        discount_score_p85 = self.df['discount_intensity_score'].quantile(0.85)
        value_score_p75 = self.df['value_score'].quantile(0.75)
        value_score_p80 = self.df['value_score'].quantile(0.80)

        # Hot Trend thresholds (giữ vừa phải)
        engagement_score_p65 = self.df['engagement_score'].quantile(0.65)
        engagement_score_p70 = self.df['engagement_score'].quantile(0.70)
        engagement_score_p75 = self.df['engagement_score'].quantile(0.75)

        self.thresholds = {
            'best_seller': {
                'quantity_sold_p60': q_sold_p60,
                'quantity_sold_p70': q_sold_p70,
                'quantity_sold_p85': q_sold_p85,
                'rating': rating_threshold
            },
            'best_deal': {
                'discount_score_p80': discount_score_p80,
                'discount_score_p85': discount_score_p85,
                'value_score_p75': value_score_p75,
                'value_score_p80': value_score_p80
            },
            'hot_trend': {
                'engagement_score_p65': engagement_score_p65,
                'engagement_score_p70': engagement_score_p70,
                'engagement_score_p75': engagement_score_p75
            }
        }

        print(f"   Best Seller - quantity_sold >= {q_sold_p70:,.0f} (P70)")
        print(
            f"   Best Deal - discount_score >= {discount_score_p80:.2f} (P80) & value_score >= {value_score_p75:.2f} (P75)")
        print(
            f"   Hot Trend - engagement_score >= {engagement_score_p70:.2f} (P70)")

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
            q_sold_p85 = self.thresholds['best_seller']['quantity_sold_p85']
            q_sold_p70 = self.thresholds['best_seller']['quantity_sold_p70']
            q_sold_p60 = self.thresholds['best_seller']['quantity_sold_p60']
            rating_th = self.thresholds['best_seller']['rating']

            discount_score_p80 = self.thresholds['best_deal']['discount_score_p80']
            discount_score_p85 = self.thresholds['best_deal']['discount_score_p85']
            value_score_p75 = self.thresholds['best_deal']['value_score_p75']
            value_score_p80 = self.thresholds['best_deal']['value_score_p80']

            engagement_p65 = self.thresholds['hot_trend']['engagement_score_p65']
            engagement_p70 = self.thresholds['hot_trend']['engagement_score_p70']
            engagement_p75 = self.thresholds['hot_trend']['engagement_score_p75']

            # Priority 1: Hot Trend
            # Sản phẩm nổi trào - engagement cao + popularity cao
            if (engagement_score >= engagement_p75 and popularity in ['Viral', 'Hot']):
                return 'Hot Trend'
            elif (engagement_score >= engagement_p70 and popularity == 'Viral'):
                return 'Hot Trend'
            elif (engagement_score >= engagement_p65 and popularity in ['Viral', 'Hot'] and lifecycle in ['Introduction', 'Growth']):
                return 'Hot Trend'

            # Priority 2: Best Seller (giảm ngưỡng mạnh để tăng số lượng)
            # Sản phẩm bán chạy nhất - quantity cao + rating tốt
            if (quantity_sold >= q_sold_p85 and rating >= 4.0 and lifecycle == 'Maturity'):
                return 'Best Seller'
            elif (quantity_sold >= q_sold_p70 and rating >= 4.2):
                return 'Best Seller'
            elif (quantity_sold >= q_sold_p60 and rating >= 4.5):
                return 'Best Seller'

            # Priority 3: Best Deal (tăng mạnh ngưỡng để giảm số lượng)
            # Sản phẩm có giá trị tốt - discount cao + value_score cao
            if (discount_score >= discount_score_p85 and value_score >= value_score_p80):
                return 'Best Deal'
            elif (discount_intensity in ['Aggressive', 'Heavy'] and value_score >= value_score_p75 and discount_score >= discount_score_p80):
                return 'Best Deal'
            elif (discount_score >= discount_score_p80 and value_score >= value_score_p80):
                return 'Best Deal'

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

    def _assign_seed_labels(self):
        """Gán nhãn seed bằng rule (ưu tiên precision cao).

        Seed labels dùng làm pseudo-ground-truth để train model.
        Các sản phẩm không chắc chắn -> seed_label = NaN.
        """

        q_sold_p85 = self.thresholds['best_seller']['quantity_sold_p85']
        q_sold_p70 = self.thresholds['best_seller']['quantity_sold_p70']
        q_sold_p60 = self.thresholds['best_seller']['quantity_sold_p60']
        rating_th = self.thresholds['best_seller']['rating']

        discount_score_p80 = self.thresholds['best_deal']['discount_score_p80']
        discount_score_p85 = self.thresholds['best_deal']['discount_score_p85']
        value_score_p75 = self.thresholds['best_deal']['value_score_p75']
        value_score_p80 = self.thresholds['best_deal']['value_score_p80']

        engagement_p65 = self.thresholds['hot_trend']['engagement_score_p65']
        engagement_p70 = self.thresholds['hot_trend']['engagement_score_p70']
        engagement_p75 = self.thresholds['hot_trend']['engagement_score_p75']

        def seed_rule(row):
            quantity_sold = row.get('quantity_sold', np.nan)
            rating = row.get('rating_average', np.nan)
            discount_score = row.get('discount_intensity_score', np.nan)
            value_score = row.get('value_score', np.nan)
            engagement_score = row.get('engagement_score', np.nan)
            popularity = row.get('popularity_category', None)
            lifecycle = row.get('lifecycle_status', None)
            discount_intensity = row.get('discount_intensity', None)

            # Seed for Hot Trend (giữ ngưỡng vừa phải)
            if pd.notna(engagement_score):
                if (engagement_score >= engagement_p75 and popularity in ['Viral', 'Hot']):
                    return 'Hot Trend', 'seed: engagement>=p75 & viral/hot'
                if (engagement_score >= engagement_p70 and popularity == 'Viral'):
                    return 'Hot Trend', 'seed: engagement>=p70 & viral'
                if (engagement_score >= engagement_p65 and popularity in ['Viral', 'Hot'] and lifecycle in ['Introduction', 'Growth']):
                    return 'Hot Trend', 'seed: engagement>=p65 & viral/hot & early lifecycle'

            # Seed for Best Seller (giảm ngưỡng để tăng seeds)
            if pd.notna(quantity_sold) and pd.notna(rating):
                if (quantity_sold >= q_sold_p85 and rating >= 4.0 and lifecycle == 'Maturity'):
                    return 'Best Seller', 'seed: sold>=p85 & rating>=4.0 & maturity'
                if (quantity_sold >= q_sold_p70 and rating >= 4.3):
                    return 'Best Seller', 'seed: sold>=p70 & rating>=4.3'
                if (quantity_sold >= q_sold_p60 and rating >= 4.6):
                    return 'Best Seller', 'seed: sold>=p60 & rating>=4.6'

            # Seed for Best Deal (tăng mạnh ngưỡng để giảm seeds)
            if pd.notna(discount_score) and pd.notna(value_score):
                if (discount_score >= discount_score_p85 and value_score >= value_score_p80 and discount_intensity in ['Aggressive', 'Heavy']):
                    return 'Best Deal', 'seed: very high discount_score & value & aggressive/heavy'
                if (discount_intensity == 'Aggressive' and value_score >= value_score_p80 and discount_score >= discount_score_p85):
                    return 'Best Deal', 'seed: aggressive discount & value>=p80 & discount>=p85'
                if (discount_score >= discount_score_p80 and value_score >= value_score_p80):
                    return 'Best Deal', 'seed: discount>=p80 & value>=p80'

            return np.nan, np.nan

        seed = self.df.apply(seed_rule, axis=1, result_type='expand')
        seed.columns = ['seed_label', 'seed_reason']
        self.df[['seed_label', 'seed_reason']] = seed
        self.df['label_source'] = np.where(self.df['seed_label'].notna(), 'rule_seed', 'unlabeled')

        counts = self.df['seed_label'].value_counts(dropna=True)
        print("\n   Seed distribution:")
        if len(counts) == 0:
            print("     (no seed labels)")
        else:
            for label, count in counts.items():
                print(f"     - {label}: {count:,}")

    def _train_and_predict_from_seeds(
        self,
        prob_threshold: float,
        min_seed_per_class: int,
        model_type: str
    ) -> bool:
        """Train model từ seed_label và predict label cho phần còn lại.

        Returns:
            bool: True nếu train/predict thành công.
        """

        try:
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import accuracy_score
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.linear_model import LogisticRegression
        except Exception:
            raise ImportError(
                "Chế độ hybrid cần scikit-learn. Cài bằng: pip install scikit-learn\n"
                "Nếu bạn không muốn cài thêm, hãy dùng mode rule (mặc định)."
            )

        if 'seed_label' not in self.df.columns:
            return False

        seed_df = self.df[self.df['seed_label'].notna()].copy()
        if len(seed_df) == 0:
            return False

        counts = seed_df['seed_label'].value_counts()
        valid_classes = [c for c, n in counts.items() if n >= min_seed_per_class]
        if len(valid_classes) < 2:
            return False

        seed_df = seed_df[seed_df['seed_label'].isin(valid_classes)].copy()

        # Feature selection: ưu tiên các features engineered (tabular)
        default_numeric = [
            'quantity_sold', 'rating_average', 'num_reviews',
            'current_price', 'original_price', 'discount_rate',
            'discount_intensity_score', 'value_score', 'engagement_score'
        ]
        default_categorical = [
            'quality_category', 'popularity_category', 'price_segment',
            'seller_tier', 'brand_strength', 'lifecycle_status', 'discount_intensity'
        ]

        numeric_cols = [c for c in default_numeric if c in self.df.columns]
        cat_cols = [c for c in default_categorical if c in self.df.columns]
        if len(numeric_cols) == 0 and len(cat_cols) == 0:
            # fallback: dùng tất cả numeric trừ cột label
            numeric_cols = [c for c in self.df.select_dtypes(include=[np.number]).columns if c not in ['label']]

        def build_X(df: pd.DataFrame) -> pd.DataFrame:
            X_num = df[numeric_cols].copy() if len(numeric_cols) else pd.DataFrame(index=df.index)
            X_num = X_num.replace([np.inf, -np.inf], np.nan).fillna(0.0)

            X_cat = df[cat_cols].copy() if len(cat_cols) else pd.DataFrame(index=df.index)
            for c in X_cat.columns:
                X_cat[c] = X_cat[c].astype('object').fillna('Unknown')

            if len(X_cat.columns) > 0:
                X_cat = pd.get_dummies(X_cat, columns=list(X_cat.columns), dummy_na=False)

            X = pd.concat([X_num, X_cat], axis=1)
            return X

        X = build_X(seed_df)
        y = seed_df['seed_label'].astype(str)

        # Train/val split
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        model_type = (model_type or '').lower().strip()
        if model_type in ['logreg', 'logistic', 'logistic_regression']:
            model = LogisticRegression(
                max_iter=1000,
                n_jobs=None,
                multi_class='auto'
            )
        else:
            model = RandomForestClassifier(
                n_estimators=400,
                random_state=42,
                class_weight='balanced_subsample',
                n_jobs=-1
            )

        model.fit(X_train, y_train)
        val_pred = model.predict(X_val)
        val_acc = accuracy_score(y_val, val_pred)
        print(f"   Model: {model.__class__.__name__} | seed samples: {len(seed_df):,} | val acc: {val_acc:.3f}")

        # Predict for unlabeled
        unlabeled_idx = self.df[self.df['seed_label'].isna()].index
        if len(unlabeled_idx) == 0:
            # tất cả đã có seed -> label = seed_label
            self.df['label'] = self.df['seed_label']
            self.df['label_source'] = 'rule_seed'
            return True

        X_all = build_X(self.df)
        # align columns
        X_all = X_all.reindex(columns=X.columns, fill_value=0.0)

        if hasattr(model, 'predict_proba'):
            prob = model.predict_proba(X_all.loc[unlabeled_idx])
            classes = list(model.classes_)
            best_idx = prob.argmax(axis=1)
            best_prob = prob.max(axis=1)
            pred_labels = [classes[i] for i in best_idx]
            pred_labels = np.where(best_prob >= prob_threshold, pred_labels, 'Normal')
        else:
            pred_labels = model.predict(X_all.loc[unlabeled_idx])

        # Merge
        self.df['label'] = self.df['seed_label']
        self.df.loc[unlabeled_idx, 'label'] = pred_labels
        self.df['label'] = self.df['label'].fillna('Normal')

        self.df.loc[unlabeled_idx, 'label_source'] = 'model'
        self.df.loc[self.df['seed_label'].notna(), 'label_source'] = 'rule_seed'
        return True

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

    # 2. Labeling (hybrid pipeline)
    labeler = ProductLabeler(df)
    df_labeled = labeler.create_labels_with_params()

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
    parser = argparse.ArgumentParser(description="Product labeling")
    parser.add_argument(
        '--input',
        type=str,
        default=None,
        help='Path tới engineered_features.json / featured_data.json (hoặc encoded_data.json dạng X_train/X_test)'
    )
    parser.add_argument('--output', type=str, default=None, help='Path output labeled_data.json')
    parser.add_argument('--prob-threshold', type=float, default=0.55, help='Ngưỡng xác suất để model gán nhãn (hybrid)')
    parser.add_argument('--min-seed-per-class', type=int, default=50, help='Số seed tối thiểu mỗi nhãn để train (hybrid)')
    parser.add_argument('--model', type=str, default='random_forest', help='random_forest | logistic_regression')
    parser.add_argument('--no-model', action='store_true', help='Chỉ dùng rule-based labeling đầy đủ (không train model)')
    args = parser.parse_args()

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

    # Prefer feature-engineered product records; encoded_data.json is primarily for ML train/test splits.
    input_file = args.input or _resolve_json_path([
        'engineered_features.json',
        'featured_data.json',
        'encoded_data.json',
    ])
    output_file = args.output or os.path.join(script_dir, 'json', 'labeled_data.json')

    if not os.path.exists(input_file):
        raise FileNotFoundError(
            "Không tìm thấy input cho labeling. "
            "Cần file encoded_data.json hoặc featured_data.json trong folder json/. "
            f"Đã thử: {os.path.join(script_dir, 'json', 'encoded_data.json')}, "
            f"{os.path.join(script_dir, 'json', 'featured_data.json')} (và các path tương tự ở thư mục cha)."
        )

    # Single hybrid pipeline entrypoint
    print("\n" + "=" * 70)
    print("🎯 PRODUCT LABELING (HYBRID PIPELINE)")
    print("=" * 70)

    def _load_input_as_dataframe(path: str) -> pd.DataFrame:
        with open(path, 'r', encoding='utf-8') as f:
            payload: Any = json.load(f)

        # Common case: list of product dict records
        if isinstance(payload, list):
            return pd.DataFrame.from_records(payload)

        # encoded_data.json case: dict containing X_train/X_test as list-of-dict records
        if isinstance(payload, dict) and isinstance(payload.get('X_train'), list):
            records = []
            records.extend(payload.get('X_train') or [])
            records.extend(payload.get('X_test') or [])
            if records and isinstance(records[0], dict):
                print(
                    "\nℹ️  Detected encoded_data.json format (X_train/X_test). "
                    "Using combined records for labeling."
                )
                return pd.DataFrame.from_records(records)
            raise ValueError(
                "Input looks like encoded_data.json but X_train/X_test are not list-of-dict records."
            )

        # Fallback: dict-of-columns (only works if all list-like values share the same length)
        if isinstance(payload, dict):
            try:
                return pd.DataFrame(payload)
            except ValueError as e:
                lengths = {
                    k: len(v)
                    for k, v in payload.items()
                    if isinstance(v, list)
                }
                if lengths:
                    min_len = min(lengths.values())
                    max_len = max(lengths.values())
                    mismatch = {k: v for k, v in lengths.items() if v != max_len}
                    raise ValueError(
                        "Không thể tạo DataFrame vì JSON là dict-of-arrays với độ dài khác nhau. "
                        f"min={min_len}, max={max_len}, mismatched={mismatch}. "
                        "Hãy dùng engineered_features.json/featured_data.json (list-of-records), "
                        "hoặc encoded_data.json đúng format X_train/X_test."
                    ) from e
                raise

        raise ValueError(
            "Input JSON root must be a list[dict] (product records) or dict (encoded_data / columns)."
        )

    df = _load_input_as_dataframe(input_file)

    labeler = ProductLabeler(df)
    df_result = labeler.create_labels_with_params(
        prob_threshold=args.prob_threshold,
        min_seed_per_class=args.min_seed_per_class,
        model_type=args.model,
        use_model=(not args.no_model)
    )

    print(f"\n💾 Lưu dữ liệu vào: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(df_result.to_dict('records'), f, ensure_ascii=False, indent=2)

    print(f"✅ Đã lưu {len(df_result):,} records\n")
