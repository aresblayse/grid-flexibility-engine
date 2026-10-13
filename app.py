import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))
import time, json
from pathlib import Path
import pandas as pd, streamlit as st
from grid_flexibility_engine.synthetic import make_grid_dataset
from grid_flexibility_engine.engine import run_scenario
from grid_flexibility_engine.persistence import ScenarioStore
from grid_flexibility_engine.validation import validate_grid

st.set_page_config(page_title="Grid Flexibility Control Room", layout="wide")

@st.cache_data(show_spinner=False)
def cached_data(seed:int, scale:str, scenario:str): return make_grid_dataset(seed, scale, scenario)

def main():
    st.title("Grid Flexibility Control Room")
    st.caption("Forecast → flexibility envelope → constraint-aware intervention → counterfactual operations")
    with st.sidebar:
        st.header("Scenario controls")
        region=st.selectbox("Region", ["North Metro","Coastal Industrial","Renewables Corridor"])
        horizon=st.slider("Forecast horizon (hours)", 12, 72, 24)
        weather=st.selectbox("Weather", ["Typical","Hot / low wind","Cool / high wind"])
        demand_growth=st.slider("Demand growth", -0.05, 0.20, 0.04, 0.01)
        renewable=st.slider("Renewable penetration", 0.10, 0.90, 0.45, 0.05)
        battery_mwh=st.slider("Battery capacity (MWh)", 10.0, 250.0, 80.0, 10.0)
        flex_mw=st.slider("Flexible load (MW)", 0.0, 150.0, 45.0, 5.0)
        peak_hour=st.slider("Peak event hour", 0, horizon-1, min(18,horizon-1))
        seed=st.number_input("Scenario seed", 0, 999999, 31415)
        upload=st.file_uploader("Upload compatible CSV", type=["csv"])
        run=st.button("Run control-room analysis", type="primary", use_container_width=True)
    if run or "grid_result" not in st.session_state:
        t=time.perf_counter(); df=(validate_grid(pd.read_csv(upload)) if upload else cached_data(seed, "medium", region)); df=df.head(horizon).copy()
        cfg=dict(region=region,horizon=horizon,weather=weather,demand_growth=demand_growth,renewable=renewable,battery_mwh=battery_mwh,flex_mw=flex_mw,peak_hour=peak_hour,seed=seed)
        result=run_scenario(df,cfg); result["runtime_ms"]=(time.perf_counter()-t)*1000; result["source"]="uploaded_csv" if upload else "synthetic"
        st.session_state.grid_result=result
    r=st.session_state.grid_result
    k=r["kpis"]; cols=st.columns(6)
    for c,(label,val) in zip(cols,[("Peak baseline",f"{k['baseline_peak']:.1f} MW"),("Peak intervention",f"{k['intervention_peak']:.1f} MW"),("Peak reduction",f"{k['peak_reduction']:.1f} MW"),("Flex available",f"{k['flex_available']:.1f} MW"),("Curtailment",f"{k['curtailment']:.1f} MWh"),("Op. cost",f"${k['cost']:.0f}")]): c.metric(label,val)
    tab1,tab2,tab3,tab4,tab5=st.tabs(["Control room","Flexibility envelope","Decision trace","Scenario snapshots","Diagnostics"])
    with tab1:
        st.plotly_chart(r["figure"], use_container_width=True)
        st.subheader("Baseline vs intervention")
        st.dataframe(r["table"], use_container_width=True, hide_index=True)
        st.download_button("Download results JSON", json.dumps(r["export"],indent=2), "grid_run.json", "application/json")
        st.download_button("Download interval CSV", r["table"].to_csv(index=False), "grid_intervals.csv", "text/csv")
    with tab2:
        st.plotly_chart(r["envelope_figure"], use_container_width=True)
        idx=st.slider("Inspect interval",0,len(r["table"])-1,0)
        st.json(r["envelope"][idx])
    with tab3:
        for e in r["trace"]:
            with st.expander(f"{e['stage']} · {e['duration_ms']:.1f} ms"):
                st.json(e)
    with tab4:
        store=ScenarioStore(Path("data/grid_scenarios.db"))
        name=st.text_input("Snapshot name", "Peak Summer / High Flex")
        if st.button("Save current scenario"):
            store.save(name,r["config"]); st.success("Scenario saved")
        st.dataframe(pd.DataFrame(store.list()), use_container_width=True, hide_index=True)
    with tab5:
        st.json({"python_target":"3.14.8","records_processed":len(r["table"]),"runtime_ms":r["runtime_ms"],"cache":"cached synthetic dataset" if r.get("source")=="synthetic" else "upload validation","source":r.get("source"),"seed":r["config"]["seed"]})

if __name__ == "__main__": main()
