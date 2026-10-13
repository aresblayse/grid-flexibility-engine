import pandas as pd
REQUIRED=["interval","hour","demand_mw","solar_mw","wind_mw","price"]
def validate_grid(df):
    missing=[c for c in REQUIRED if c not in df.columns]
    if missing: raise ValueError("Missing required columns: "+", ".join(missing))
    out=df[REQUIRED].copy()
    if out.isna().any().any(): raise ValueError("Dataset contains missing values.")
    if out.duplicated("interval").any(): raise ValueError("Duplicate interval identifiers detected.")
    for c in REQUIRED[1:]: out[c]=pd.to_numeric(out[c],errors="coerce")
    if out[REQUIRED[1:]].isna().any().any(): raise ValueError("Numeric fields contain non-numeric values.")
    if (out.demand_mw<0).any() or (out.solar_mw<0).any() or (out.wind_mw<0).any() or (out.price<0).any(): raise ValueError("Demand, generation and price must be non-negative.")
    return out
