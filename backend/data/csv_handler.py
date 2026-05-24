from io import BytesIO
import pandas as pd
from database import get_conn


def process_csv_upload(contents: bytes, ticker: str) -> dict:
    df = pd.read_csv(BytesIO(contents))
    required = {"Date", "Open", "High", "Low", "Close", "Volume"}
    if not required.issubset(df.columns):
        return {"error": f"CSV must have columns: {required}"}
    df["ticker"] = ticker.upper()
    conn = get_conn()
    df.to_sql("csv_ohlcv", conn, if_exists="append", index=False)
    conn.close()
    return {"rows_imported": len(df), "ticker": ticker.upper()}
