import pandas as pd
import numpy as np
import json
import os
import pickle
from typing import Dict, List, Tuple, Optional
from sklearn.preprocessing import StandardScaler, LabelEncoder, OneHotEncoder
from sklearn.model_selection import train_test_split


class DataEncoder:
    """
    Encoding Module - Chuyển đổi dữ liệu thành vector số học

    Features được xử lý:
    1. Categorical features: One-hot encoding
    2. Numerical features: Standardization/Normalization
    3. Target label: Label encoding
    """

    def __init__(self, df: pd.DataFrame):
        """
        Khởi tạo Data Encoder

        Parameters:
        - df: DataFrame đã được labeling
        """
        self.df = df.copy()

        # Encoders
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.categorical_encoders = {}

        # Feature information
        self.categorical_features = []
        self.numerical_features = []
        self.feature_mapping = {}
        self.encoding_stats = {}

    def analyze_and_encode(self) -> Tuple[pd.DataFrame, Dict]:
        """
        Phân tích dữ liệu và thực hiện encoding

        Returns:
        - Tuple của (encoded_df, metadata)
        """

        print("🔐 BẮT ĐẦU ENCODING")
        print("=" * 70)

        # 1. Phân loại features
        print("\n✓ Bước 1: Phân loại features...")
        self._identify_features()

        # 2. Encode categorical features
        print("✓ Bước 2: Encoding categorical features (One-hot)...")
        df_encoded = self._encode_categorical()

        # 3. Scale numerical features
        print("✓ Bước 3: Scaling numerical features...")
        df_encoded = self._scale_numerical(df_encoded)

        # 4. Encode target label
        print("✓ Bước 4: Encoding target label...")
        df_encoded = self._encode_target(df_encoded)

        # 5. Tổng kết
        print("\n" + "=" * 70)
        print(f"✅ HOÀN THÀNH ENCODING")
        print(f"   Original shape: {self.df.shape}")
        print(f"   Encoded shape: {df_encoded.shape}")

        return df_encoded, self.get_encoding_info()

    def _identify_features(self):
        """Xác định categorical và numerical features"""

        # Categorical features (từ features engineering)
        categorical = [
            'quality_category', 'popularity_category', 'price_segment',
            'seller_tier', 'brand_strength', 'lifecycle_status',
            'discount_intensity'
        ]

        # Numerical features
        numerical = [
            'rating_average', 'num_reviews', 'quantity_sold',
            'current_price', 'discount_rate', 'engagement_score',
            'value_score', 'discount_intensity_score'
        ]

        # Lọc những features tồn tại trong df
        self.categorical_features = [
            f for f in categorical if f in self.df.columns]
        self.numerical_features = [
            f for f in numerical if f in self.df.columns]

        print(
            f"   Categorical features ({len(self.categorical_features)}): {self.categorical_features}")
        print(
            f"   Numerical features ({len(self.numerical_features)}): {self.numerical_features}")

    def _encode_categorical(self) -> pd.DataFrame:
        """
        One-hot encoding cho categorical features
        """

        df_encoded = self.df.copy()

        for feature in self.categorical_features:
            unique_values = self.df[feature].unique()
            self.categorical_encoders[feature] = unique_values

            print(f"   {feature}: {len(unique_values)} categories")

            # One-hot encoding
            one_hot = pd.get_dummies(
                df_encoded[feature],
                prefix=feature,
                drop_first=False,
                prefix_sep='_'
            )

            # Lưu mapping
            self.feature_mapping[feature] = {
                'type': 'categorical',
                'values': list(unique_values)
            }

            # Drop original column và add one-hot columns
            df_encoded = df_encoded.drop(columns=[feature])
            df_encoded = pd.concat([df_encoded, one_hot], axis=1)

        return df_encoded

    def _scale_numerical(self, df_encoded: pd.DataFrame) -> pd.DataFrame:
        """
        Standardization cho numerical features (mean=0, std=1)
        """

        df_scaled = df_encoded.copy()

        if len(self.numerical_features) > 0:
            # Fit scaler trên training data
            numerical_data = self.df[self.numerical_features].values
            self.scaler.fit(numerical_data)

            # Transform
            scaled_data = self.scaler.transform(numerical_data)

            # Create scaled columns
            for i, feature in enumerate(self.numerical_features):
                df_scaled[f'{feature}_scaled'] = scaled_data[:, i]

                # Lưu mapping
                if self.scaler.mean_ is not None and self.scaler.scale_ is not None:
                    self.feature_mapping[feature] = {
                        'type': 'numerical',
                        'mean': float(self.scaler.mean_[i]),
                        'std': float(self.scaler.scale_[i])
                    }

                    print(
                        f"   {feature}: mean={self.scaler.mean_[i]:.2f}, std={self.scaler.scale_[i]:.2f}")

        return df_scaled

    def _encode_target(self, df_encoded: pd.DataFrame) -> pd.DataFrame:
        """
        Label encoding cho target variable (label)
        """

        if 'label' in df_encoded.columns:
            # Fit encoder
            unique_labels = df_encoded['label'].unique()
            self.label_encoder.fit(unique_labels)

            # Transform
            df_encoded['label_encoded'] = pd.Series(
                self.label_encoder.transform(df_encoded['label']), index=df_encoded.index)

            # Lưu mapping
            encoded_labels = self.label_encoder.transform(self.label_encoder.classes_).tolist() # type: ignore
            self.feature_mapping['label'] = {
                'type': 'target',
                'encoding': dict(zip(self.label_encoder.classes_, encoded_labels))
            }

            print(
                f"   Label encoding: {dict(zip(self.label_encoder.classes_, encoded_labels))}")

        return df_encoded

    def get_feature_columns(self, df_encoded: pd.DataFrame) -> Dict[str, List[str]]:
        """Lấy thông tin columns sau encoding"""

        feature_groups = {
            'original_categorical': self.categorical_features,
            'original_numerical': self.numerical_features,
            'scaled_numerical': [f'{f}_scaled' for f in self.numerical_features],
            'one_hot': [col for col in df_encoded.columns if any(f'{cat}_' in col for cat in self.categorical_features)]
        }

        return feature_groups

    def save_encoders(self, output_dir: str):
        """Lưu encoder objects để sử dụng sau"""

        os.makedirs(output_dir, exist_ok=True)

        # Lưu scaler
        scaler_path = os.path.join(output_dir, 'scaler.pkl')
        with open(scaler_path, 'wb') as f:
            pickle.dump(self.scaler, f)

        # Lưu label encoder
        label_encoder_path = os.path.join(output_dir, 'label_encoder.pkl')
        with open(label_encoder_path, 'wb') as f:
            pickle.dump(self.label_encoder, f)

        # Lưu feature mapping
        mapping_path = os.path.join(output_dir, 'feature_mapping.json')
        with open(mapping_path, 'w', encoding='utf-8') as f:
            json.dump(self.feature_mapping, f, ensure_ascii=False, indent=2)

        print(f"\n💾 Đã lưu encoders:")
        print(f"   - {scaler_path}")
        print(f"   - {label_encoder_path}")
        print(f"   - {mapping_path}")

    def get_encoding_info(self) -> Dict:
        """Lấy thông tin encoding"""
        return {
            'categorical_features': self.categorical_features,
            'numerical_features': self.numerical_features,
            'feature_mapping': self.feature_mapping
        }


def create_encoding(input_file: str, output_file: Optional[str] = None,
                    encoder_dir: Optional[str] = None, test_size: float = 0.2) -> Tuple[pd.DataFrame, Optional[pd.DataFrame], Optional[pd.Series], Optional[pd.Series], Dict]:
    """
    Hàm main cho encoding + train/test split

    Parameters:
    - input_file: đường dẫn file labeled data (JSON)
    - output_file: đường dẫn file output (default: data/transformation/encoded_data.json)
    - encoder_dir: đường dẫn lưu encoders (default: data/transformation/encoders/)
    - test_size: tỷ lệ test split (default: 0.2)

    Returns:
    - Tuple của (X_train, X_test, y_train, y_test, metadata)
    """

    print("\n" + "=" * 70)
    print("🎯 DATA ENCODING & TRAIN/TEST SPLIT")
    print("=" * 70)

    # 1. Đọc dữ liệu
    print("\n📂 Bước 0: Đọc dữ liệu...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    df = pd.DataFrame(data)
    print(f"✓ Đã load {len(df):,} records")

    # 2. Encoding
    encoder = DataEncoder(df)
    df_encoded, encoding_info = encoder.analyze_and_encode()

    # 3. Lưu encoders
    if encoder_dir is None:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        encoder_dir = os.path.join(base, 'data/transformation/encoders')

    encoder.save_encoders(encoder_dir)

    # 4. Train/Test Split
    print("\n" + "=" * 70)
    print("📊 TRAIN/TEST SPLIT")
    print("=" * 70)

    if 'label_encoded' in df_encoded.columns:
        X = df_encoded.drop(columns=['label', 'label_encoded'])
        y = df_encoded['label_encoded']
    else:
        X = df_encoded
        y = None

    print(f"\n✓ Total samples: {len(df_encoded):,}")
    print(f"✓ Features: {X.shape[1]}")

    if y is not None:
        # Stratified split requires each class to have at least 2 samples,
        # and test/train sizes large enough to contain all classes.
        label_counts = y.value_counts()
        n_classes = int(label_counts.shape[0])
        n_samples = int(len(y))
        n_test = int(round(n_samples * test_size))
        n_train = n_samples - n_test

        can_stratify = True
        if label_counts.min() < 2:
            can_stratify = False
        if n_test < n_classes or n_train < n_classes:
            can_stratify = False

        if not can_stratify:
            print("\n⚠️  Không thể stratify train/test split vì có lớp quá ít mẫu hoặc tập test/train quá nhỏ.")
            print("   → Sẽ split KHÔNG stratify để tránh lỗi.")
            print(f"   Label counts: {label_counts.to_dict()}")
            stratify_arg = None
        else:
            stratify_arg = y

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=stratify_arg
        )

        print(f"\nTrain set: {len(X_train):,} ({(1-test_size)*100:.0f}%)")
        print(f"Test set: {len(X_test):,} ({test_size*100:.0f}%)")

        # Thống kê labels
        print(f"\nLabel distribution (Train):")
        for label_id, count in y_train.value_counts().items():
            label_name = encoder.label_encoder.inverse_transform([label_id])[0]
            print(f"  {label_name}: {count:,} ({count/len(y_train)*100:.1f}%)")

        print(f"\nLabel distribution (Test):")
        for label_id, count in y_test.value_counts().items():
            label_name = encoder.label_encoder.inverse_transform([label_id])[0]
            print(f"  {label_name}: {count:,} ({count/len(y_test)*100:.1f}%)")
    else:
        X_train = X
        y_train = None
        X_test = None
        y_test = None

    # 5. Lưu dữ liệu
    if output_file is None:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_dir = os.path.join(base, 'data/transformation')
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, 'encoded_data.json')

    print(f"\n💾 Lưu dữ liệu vào: {output_file}")

    # Lưu encoded data
    output_data = {
        'X_train': X_train.to_dict('records'),
        'y_train': y_train.tolist() if y_train is not None else None,
        'X_test': X_test.to_dict('records') if X_test is not None else None,
        'y_test': y_test.tolist() if y_test is not None else None,
        'feature_names': X.columns.tolist(),
        'feature_info': encoder.get_encoding_info()
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"✅ Đã lưu {len(X_train):,} train records\n")

    # 6. Thống kê tóm tắt
    print("=" * 70)
    print("📊 THỐNG KÊ ENCODING")
    print("=" * 70)

    feature_groups = encoder.get_feature_columns(df_encoded)
    print(f"\n✨ Feature Groups:")
    print(
        f"  - Categorical features: {len(feature_groups['original_categorical'])}")
    print(
        f"  - Numerical features: {len(feature_groups['original_numerical'])}")
    print(f"  - One-hot columns: {len(feature_groups['one_hot'])}")
    print(f"  - Scaled numerical: {len(feature_groups['scaled_numerical'])}")
    print(f"  - Total input features: {X.shape[1]}")

    print(f"\n✨ Feature Names (first 10):")
    for i, col in enumerate(X.columns[:10]):
        print(f"  {i+1}. {col}")
    if X.shape[1] > 10:
        print(f"  ... và {X.shape[1] - 10} features khác")

    print("\n" + "=" * 70)
    print("✅ HOÀN THÀNH ENCODING\n")

    return X_train, X_test, y_train, y_test, encoder.get_encoding_info()


if __name__ == "__main__":
    # Default: resolve paths relative to this script's folder (workspace `code/`).
    script_dir = os.path.dirname(os.path.abspath(__file__))

    def _resolve_json_path(filename: str) -> str:
        """Try common locations for the json folder."""
        candidates = [
            os.path.join(script_dir, 'json', filename),
            os.path.join(os.path.dirname(script_dir), 'json', filename),
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        return candidates[0]

    input_file = _resolve_json_path('engineered_features.json')
    output_file = os.path.join(script_dir, 'json', 'encoded_data.json')
    encoder_dir = os.path.join(script_dir, 'json', 'encoders')

    if not os.path.exists(input_file):
        raise FileNotFoundError(
            "Không tìm thấy file labeled_data.json. "
            f"Đã thử: {os.path.join(script_dir, 'json', 'labeled_data.json')} và "
            f"{os.path.join(os.path.dirname(script_dir), 'json', 'labeled_data.json')}. "
            "Hãy kiểm tra lại folder json/ trong workspace."
        )

    X_train, X_test, y_train, y_test, info = create_encoding(
        input_file, output_file, encoder_dir, test_size=0.2
    )
