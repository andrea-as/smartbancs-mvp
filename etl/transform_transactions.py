from pathlib import Path
import pandas as pd

BASE = Path(__file__).parent
INPUT = BASE / "data" / "raw_transactions.csv"
OUTPUT = BASE / "data" / "clean_transactions.csv"

def main():
    df = pd.read_csv(INPUT, dtype=str)
    original_count = len(df)

    df.columns = [c.strip().lower() for c in df.columns]
    for col in ["transaction_id", "account_id", "currency", "status"]:
        df[col] = df[col].astype("string").str.strip()

    df["currency"] = df["currency"].str.upper()
    df["status"] = df["status"].str.upper()
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df["event_time"] = pd.to_datetime(df["event_time"], errors="coerce", utc=True)

    df["quality_amount_ok"] = df["amount"].notna() & (df["amount"] > 0)
    df["quality_date_ok"] = df["event_time"].notna()
    df["quality_id_ok"] = df["transaction_id"].notna() & df["account_id"].notna()

    df = df[
        df["quality_amount_ok"] &
        df["quality_date_ok"] &
        df["quality_id_ok"]
    ].drop_duplicates("transaction_id", keep="first")

    df["event_date"] = df["event_time"].dt.date.astype("string")
    df["amount"] = df["amount"].round(2)

    columns = [
        "transaction_id", "account_id", "amount", "currency", "event_time",
        "event_date", "status", "quality_amount_ok", "quality_date_ok",
        "quality_id_ok"
    ]
    df[columns].to_csv(OUTPUT, index=False)

    print(f"Filas procesadas: {original_count}")
    print(f"Filas válidas: {len(df)}")
    print(f"Filas rechazadas: {original_count - len(df)}")
    print(f"Salida: {OUTPUT}")

if __name__ == "__main__":
    main()
