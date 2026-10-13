from __future__ import annotations
from dataclasses import dataclass
import time, numpy as np, pandas as pd, plotly.graph_objects as go

@dataclass(frozen=True)
class Battery:
    capacity_mwh: float; max_power_mw: float; efficiency: float=0.92

def ewma_forecast(x:np.ndarray, span:int=8)->np.ndarray:
    s=pd.Series(x).ewm(span=span, adjust=False).mean().to_numpy(); return s

def run_scenario(df:pd.DataFrame,cfg:dict)->dict:
    trace=[]
    def stage(name,fn):
        t=time.perf_counter(); out=fn(); trace.append({"stage":name,"duration_ms":(time.perf_counter()-t)*1000,"status":"success"}); return out
    base=stage("baseline forecast",lambda: _baseline(df,cfg))
    forecast=base["forecast"]; renewable=base["renewable"]
    net=forecast-renewable
    flex=stage("flexibility envelope",lambda:_flexibility(len(df),cfg,net))
    intervention=stage("constraint-aware dispatch",lambda:_dispatch(net,df["price"].to_numpy(),cfg,flex))
    table=pd.DataFrame({"interval":df.interval,"hour":df.hour,"baseline_mw":net,"intervention_mw":intervention["net"],"battery_soc_mwh":intervention["soc"],"up_flex_mw":flex["up"],"down_flex_mw":flex["down"],"price":df.price})
    peak0=float(net.max()); peak1=float(intervention["net"].max());
    kpis={"baseline_peak":peak0,"intervention_peak":peak1,"peak_reduction":max(0,peak0-peak1),"flex_available":float(np.mean(flex["up"]+flex["down"])),"curtailment":float(intervention["curtailment"]),"cost":float(np.sum(intervention["net"]*df.price/1000))}
    fig=go.Figure(); fig.add_scatter(x=table.hour,y=table.baseline_mw,name="Baseline net load"); fig.add_scatter(x=table.hour,y=table.intervention_mw,name="Intervention net load"); fig.update_layout(title="Net-load counterfactual",xaxis_title="Hour",yaxis_title="MW")
    env= pd.DataFrame({"hour":df.hour,"forecast":forecast,"lower":forecast-base["sigma"]*1.96,"upper":forecast+base["sigma"]*1.96,"up_flex":flex["up"],"down_flex":flex["down"]})
    envfig=go.Figure(); envfig.add_scatter(x=env.hour,y=env.upper,name="Forecast upper",line=dict(width=0)); envfig.add_scatter(x=env.hour,y=env.lower,name="Forecast lower",fill="tonexty"); envfig.add_scatter(x=env.hour,y=env.forecast,name="Forecast"); envfig.add_scatter(x=env.hour,y=env.forecast+env.up_flex,name="Upward flexibility",line=dict(dash="dot")); envfig.add_scatter(x=env.hour,y=env.forecast-env.down_flex,name="Downward flexibility",line=dict(dash="dot")); envfig.update_layout(title="Flexibility envelope")
    export={"config":cfg,"kpis":kpis,"intervals":table.to_dict("records"),"trace":trace}
    return {"config":cfg,"kpis":kpis,"table":table,"figure":fig,"envelope_figure":envfig,"envelope":flex["details"],"trace":trace,"export":export,"runtime_ms":0}

def _baseline(df,cfg):
    demand=df.demand_mw.to_numpy()*(1+cfg["demand_growth"]); solar=df.solar_mw.to_numpy()*cfg["renewable"]/0.45; wind=df.wind_mw.to_numpy()*cfg["renewable"]/0.45
    if cfg["weather"]=="Hot / low wind": demand*=1.08; wind*=0.75
    if cfg["weather"]=="Cool / high wind": demand*=0.95; wind*=1.2
    f=ewma_forecast(demand); sigma=pd.Series(demand-f).rolling(12,min_periods=3).std().bfill().fillna(3).to_numpy()
    return {"forecast":f,"renewable":solar+wind,"sigma":sigma}

def _flexibility(n,cfg,net):
    battery=cfg["battery_mwh"]; power=min(battery/2,80); up=np.full(n,min(power,cfg["flex_mw"]*0.5)); down=np.full(n,min(power,cfg["flex_mw"]*0.5)); details=[]
    for i in range(n): details.append({"interval":i,"up_mw":float(up[i]),"down_mw":float(down[i]),"duration_hours":2.0,"recovery_mwh":float(0.15*battery),"confidence":0.9})
    return {"up":up,"down":down,"details":details}

def _dispatch(net,price,cfg,flex):
    n=len(net); soc=np.full(n,cfg["battery_mwh"]*0.5); out=net.copy(); curtail=0.0
    peak=np.percentile(net,85);
    for i in range(1,n):
        soc[i]=soc[i-1];
        if net[i]>peak and soc[i]>0:
            discharge=min(flex["up"][i],soc[i]*0.92); out[i]-=discharge; soc[i]-=discharge
        elif price[i]<np.percentile(price,35) and soc[i]<cfg["battery_mwh"] and net[i] < peak*0.80:
            charge=min(flex["down"][i],cfg["battery_mwh"]-soc[i], max(0,(peak-net[i])*0.92)); out[i]+=charge/0.92; soc[i]+=charge
        elif net[i]<0:
            curtail+=-net[i]; out[i]=0
    return {"net":out,"soc":soc,"curtailment":curtail}
