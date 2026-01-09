# ==========================================
# Khang - Visualization (Code)
# CRISP-DM Data Mining Project
# ==========================================

import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

sns.set(style="whitegrid")
OUTPUT_DIR = "figures"


def load_data(filename="labeled_data.json"):
    print("[INFO] Loading labeled data...")
 
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, filename)

    print("[INFO] Looking for file at:", file_path)

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    df = pd.read_json(file_path)
    print("[INFO] Data loaded successfully")
    return df


def ensure_output_dir():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)


# -------- Data Understanding --------
def plot_label_distribution(df):
    plt.figure(figsize=(8, 5))
    sns.countplot(data=df, x="label")
    plt.title("Phân bố nhãn sản phẩm")
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/label_distribution.png", dpi=300)
    plt.close()


def plot_price_distribution(df):
    plt.figure(figsize=(8, 5))
    sns.histplot(df["current_price"], bins=30, kde=True)
    plt.title("Phân bố giá sản phẩm")
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/price_distribution.png", dpi=300)
    plt.close()


# -------- Data Preparation --------
def plot_price_by_label(df):
    plt.figure(figsize=(8, 5))
    sns.boxplot(data=df, x="label", y="current_price")
    plt.title("So sánh giá theo nhãn")
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/price_by_label.png", dpi=300)


def plot_rating_by_label(df):
    plt.figure(figsize=(8, 5))
    sns.boxplot(data=df, x="label", y="rating_score")
    plt.title("So sánh rating theo nhãn")
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/rating_by_label.png", dpi=300)
    plt.close()


# -------- Modeling Support --------
def plot_avg_sold_by_label(df):
    plt.figure(figsize=(8, 5))
    sns.barplot(data=df, x="label", y="sold", estimator="mean")
    plt.title("Số bán trung bình theo nhãn")
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/avg_sold_by_label.png", dpi=300)
    plt.close()


def plot_price_vs_sold(df):
    plt.figure(figsize=(8, 5))
    sns.scatterplot(data=df, x="current_price", y="sold", hue="label")
    plt.title("Quan hệ Giá và Số bán")
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/price_vs_sold.png", dpi=300)
    plt.close()


# -------- Evaluation --------
def plot_top_products(df):
    top_df = df.sort_values("sold", ascending=False).groupby("label").head(3)

    plt.figure(figsize=(10, 6))
    sns.barplot(data=top_df, x="sold", y="product_name", hue="label")
    plt.title("Top sản phẩm theo từng nhãn")
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/top_products.png", dpi=300)
    plt.close()


def main():
    print("[INFO] Visualization script started")
    ensure_output_dir()

    df = load_data()

    plot_label_distribution(df)
    plot_price_distribution(df)

    plot_price_by_label(df)
    plot_rating_by_label(df)

    plot_avg_sold_by_label(df)
    plot_price_vs_sold(df)

    plot_top_products(df)

    print("[DONE] All visualizations saved to 'figures/' folder")


if __name__ == "__main__":
    main()
