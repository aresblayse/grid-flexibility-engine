import numpy as np, pandas as pd
from grid_flexibility_engine.synthetic import make_grid_dataset
from grid_flexibility_engine.engine import run_scenario
def cfg(): return dict(region="North Metro",horizon=24,weather="Typical",demand_growth=.04,renewable=.45,battery_mwh=80.,flex_mw=45.,peak_hour=18,seed=1)
def test_reproducible():
    a=make_grid_dataset(1); b=make_grid_dataset(1); pd.testing.assert_frame_equal(a,b)
def test_soc_bounds():
    r=run_scenario(make_grid_dataset(1),cfg()); assert (r['table'].battery_soc_mwh>=0).all(); assert (r['table'].battery_soc_mwh<=80).all()
def test_output():
    r=run_scenario(make_grid_dataset(2),cfg()); assert r['table'].shape[0]>0; assert r['kpis']['baseline_peak']>=r['kpis']['intervention_peak']
