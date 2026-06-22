import sys
sys.path.insert(0, '.')
from analytics.recruitment_dashboard import get_funnel_metrics, get_funnel_dropoff
metrics = get_funnel_metrics()
print("Metrics:", metrics)
funnel = get_funnel_dropoff(metrics)
print("Funnel:", funnel)
