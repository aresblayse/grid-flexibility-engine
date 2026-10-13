from __future__ import annotations
import numpy as np, pandas as pd

def make_grid_dataset(seed:int=31415, scale:str="medium", scenario:str="North Metro") -> pd.DataFrame:
    n={"small":48,"medium":288,"large":1440}.get(scale,288)
    rng=np.random.default_rng(seed)
    t=np.arange(n); hour=t%24
    daily=18*np.sin((hour-7)/24*2*np.pi)+8*np.sin((hour-17)/24*4*np.pi)
    weekly=3*np.sin(t/(24*7)*2*np.pi)
    demand=220+daily+weekly+rng.normal(0,3,n)
    solar=np.maximum(0,70*np.sin((hour-6)/12*np.pi))+rng.normal(0,1.5,n)
    wind=35+8*np.sin(t/(24*3)*2*np.pi)+rng.normal(0,2,n)
    price=55+25*((hour>=17)&(hour<=21))+rng.normal(0,4,n)
    return pd.DataFrame({"interval":t,"hour":hour,"demand_mw":demand.clip(120),"solar_mw":solar.clip(0),"wind_mw":wind.clip(0),"price":price.clip(10)})
