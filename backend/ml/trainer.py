import time
import yfinance as yf
import pandas as pd
import joblib
import numpy as np
from pathlib import Path
from xgboost import XGBClassifier
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import roc_auc_score

from data.fetcher import fetch_ohlcv
from ml.features import build_features, build_labels, FEATURE_COLS

MODELS_DIR = Path(__file__).parent / "models"
MODELS_DIR.mkdir(exist_ok=True)

SP500_SAMPLE = [
    "AAPL","MSFT","NVDA","GOOGL","AMZN","META","TSLA","AMD","AVGO","ORCL",
    "CRM","ADBE","QCOM","TXN","INTC","MU","AMAT","LRCX","KLAC","MRVL",
    "JPM","BAC","GS","MS","WFC","C","BLK","SPGI","ICE","CME",
    "JNJ","UNH","PFE","MRK","ABBV","TMO","ABT","BMY","LLY","AMGN",
    "XOM","CVX","COP","SLB","EOG","PXD","MPC","VLO","PSX","HAL",
]

SECTOR_MAP = {
    "Technology": ["NVDA","AMD","MSFT","AAPL","GOOGL","META","AVGO","QCOM","INTC","MU","AMAT","LRCX","KLAC","MRVL","CRM","ADBE","ORCL","TXN","AMZN"],
    "Financials": ["JPM","BAC","GS","MS","WFC","C","BLK","SPGI","ICE","CME"],
    "Healthcare": ["JNJ","UNH","PFE","MRK","ABBV","TMO","ABT","BMY","LLY","AMGN"],
    "Energy": ["XOM","CVX","COP","SLB","EOG","PXD","MPC","VLO","PSX","HAL"],
}


def _collect_data(tickers: list[str]) -> tuple[pd.DataFrame, pd.Series]:
    all_X, all_y = [], []
    for i, t in enumerate(tickers):
        try:
            df = fetch_ohlcv(t, period="2y")
            if len(df) < 250:
                print(f"  [{t}] skipped (only {len(df)} rows)")
                continue
            X = build_features(df)
            y = build_labels(df).reindex(X.index).dropna()
            X = X.reindex(y.index)
            all_X.append(X)
            all_y.append(y)
            print(f"  [{t}] {len(X)} samples")
        except Exception as e:
            print(f"  [{t}] ERROR: {e}")
        if i < len(tickers) - 1:
            time.sleep(1)  # rate limit guard
    if not all_X:
        return pd.DataFrame(), pd.Series(dtype=int)
    return pd.concat(all_X), pd.concat(all_y)


def _train_model(X: pd.DataFrame, y: pd.Series, name: str) -> float:
    if len(X) < 100:
        print(f"  [{name}] skipped — insufficient data ({len(X)} rows)")
        return 0.0
    model = XGBClassifier(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="logloss",
        random_state=42,
    )
    tscv = TimeSeriesSplit(n_splits=3)
    aucs = []
    for train_idx, val_idx in tscv.split(X):
        model.fit(X.iloc[train_idx], y.iloc[train_idx], verbose=False)
        prob = model.predict_proba(X.iloc[val_idx])[:, 1]
        try:
            aucs.append(roc_auc_score(y.iloc[val_idx], prob))
        except Exception:
            aucs.append(0.5)

    model.fit(X, y, verbose=False)
    joblib.dump(model, MODELS_DIR / f"{name}.pkl")
    auc = float(np.mean(aucs))
    print(f"  [{name}] AUC={auc:.3f} | samples={len(X)}")
    return auc


def train_universal():
    print("Training universal model (50 tickers, 2y each)...")
    X, y = _collect_data(SP500_SAMPLE)
    if X.empty:
        print("No data collected — check yfinance connectivity")
        return 0.0
    return _train_model(X, y, "universal")


def train_sector_models():
    for sector, tickers in SECTOR_MAP.items():
        print(f"Training {sector} model...")
        X, y = _collect_data(tickers)
        if not X.empty:
            _train_model(X, y, f"sector_{sector.lower()}")


def train_all():
    train_universal()
    train_sector_models()
    print("All models trained.")


if __name__ == "__main__":
    train_all()
