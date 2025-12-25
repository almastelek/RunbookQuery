# Grafana Dashboard Best Practices

Effective dashboards help on-call engineers quickly identify and resolve issues.

## Dashboard Structure

### Overview Dashboards

Start with high-level metrics:
- Request rate
- Error rate  
- Latency percentiles
- Active alerts

Use the RED method:
- **R**ate: Requests per second
- **E**rrors: Error rate percentage
- **D**uration: Latency distribution

### Drill-Down Dashboards

Link to detailed views:
- Per-service metrics
- Per-instance metrics
- Log exploration

## Useful Panels

### Error Rate Panel

```promql
# 5xx error rate percentage
sum(rate(http_requests_total{status=~"5.."}[5m])) by (service)
/
sum(rate(http_requests_total[5m])) by (service)
* 100
```

### Latency Heatmap

```promql
# P95 latency
histogram_quantile(0.95, 
  sum(rate(http_request_duration_seconds_bucket[5m])) by (le, service)
)
```

### Pod Status

```promql
# Count of pods by status
sum(kube_pod_status_phase) by (phase)
```

## Alert Integration

### Annotations

Add alert annotations to show when issues started:

1. Go to Dashboard Settings
2. Add annotation query:
   ```promql
   ALERTS{alertstate="firing", severity="critical"}
   ```

### Thresholds

Set visual thresholds matching your alerts:

```json
{
  "thresholds": [
    { "color": "green", "value": null },
    { "color": "yellow", "value": 0.01 },
    { "color": "red", "value": 0.05 }
  ]
}
```

## Variables

Use template variables for flexibility:

```promql
label_values(kube_pod_info, namespace)
label_values(kube_pod_info{namespace="$namespace"}, pod)
```

## Links

Add useful links:
- Logs (to Loki/Elasticsearch)
- Traces (to Jaeger/Tempo)  
- Runbooks (to wiki/docs)

## Related Topics

- [Prometheus Queries](/docs/prometheus-queries)
- [Grafana Alerting](/docs/grafana-alerting)
- [Log Aggregation](/docs/logging)
