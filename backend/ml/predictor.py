import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from ml.features import build_features, FEATURE_COLS

MODELS_DIR = Path(__file__).parent / "models"

_cache: dict = {}


def _load(name: str):
    if name not in _cache:
        path = MODELS_DIR / f"{name}.pkl"
        if path.exists():
            _cache[name] = joblib.load(path)
        else:
            return None
    return _cache[name]


def predict_breakout_prob(df: pd.DataFrame, sector: str = "Unknown") -> float:
    """Returns probability 0-1 that this ticker will break out in next 10 sessions."""
    features = build_features(df)
    if features.empty:
        return 0.0

    row = features.iloc[[-1]]
    sector_key = f"sector_{sector.lower()}"
    model = _load(sector_key) or _load("universal")

    if model is None:
        return 0.0

    prob = float(model.predict_proba(row)[0, 1])
    return round(prob, 3)
