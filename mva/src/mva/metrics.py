import numpy as np
from .models import Cycle, CycleMetrics

def cycle_time_statistics(cycles: list[Cycle]) -> CycleMetrics:
    values=np.array([c.duration for c in cycles if c.complete and c.duration is not None],dtype=float)
    if not len(values): return CycleMetrics(n=0,mean=None,median=None,min=None,max=None,std=None,p90=None,p95=None,cv=None)
    mean=float(np.mean(values)); std=float(np.std(values,ddof=0))
    return CycleMetrics(n=len(values),mean=mean,median=float(np.median(values)),min=float(np.min(values)),max=float(np.max(values)),std=std,p90=float(np.percentile(values,90)),p95=float(np.percentile(values,95)),cv=(std/mean if mean else None))

def classify_cycle_time(ct: float, takt: float, near_fraction: float=.05, severe_ratio: float=1.20) -> dict:
    ratio=ct/takt
    if ratio<1-near_fraction: label="below"
    elif ratio<=1+near_fraction: label="near"
    elif ratio>severe_ratio: label="severely_above"
    else: label="above"
    return {"cycle_time":ct,"takt_time":takt,"deviation_seconds":ct-takt,"ratio":ratio,"classification":label}
