# Prometheus Alerting Rules

This guide covers configuring alerting rules in Prometheus for on-call incident detection.

## Alert Rule Basics

Prometheus alerting rules are defined in YAML:

```yaml
groups:
  - name: kubernetes-alerts
    rules:
      - alert: PodCrashLooping
        expr: rate(kube_pod_container_status_restarts_total[15m]) > 0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Pod {{ $labels.pod }} is crash looping"
          description: "Pod {{ $labels.pod }} in namespace {{ $labels.namespace }} has been restarting"
```

## Key Components

### Expression (expr)

The PromQL expression that triggers the alert:

```promql
# Container restarts
rate(kube_pod_container_status_restarts_total[15m]) > 0

# High error rate
sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) > 0.05

# Pod not ready
kube_pod_status_ready{condition="false"} == 1
```

### Duration (for)

How long the condition must be true before firing:

```yaml
for: 5m  # Wait 5 minutes to avoid flapping
```

### Labels

Used for routing and grouping:

```yaml
labels:
  severity: critical
  team: platform
```

### Annotations

Human-readable information:

```yaml
annotations:
  summary: "High error rate on {{ $labels.service }}"
  runbook_url: "https://runbooks.example.com/high-error-rate"
```

## Common Alert Patterns

### High CPU Usage

```yaml
- alert: HighCPUUsage
  expr: |
    (
      sum(rate(container_cpu_usage_seconds_total[5m])) by (pod, namespace)
      /
      sum(kube_pod_container_resource_limits{resource="cpu"}) by (pod, namespace)
    ) > 0.9
  for: 10m
  labels:
    severity: warning
```

### Memory Pressure

```yaml
- alert: HighMemoryUsage
  expr: |
    (
      sum(container_memory_working_set_bytes) by (pod, namespace)
      /
      sum(kube_pod_container_resource_limits{resource="memory"}) by (pod, namespace)
    ) > 0.9
  for: 5m
  labels:
    severity: warning
```

### Disk Space

```yaml
- alert: DiskSpaceLow
  expr: |
    (
      node_filesystem_avail_bytes{mountpoint="/"}
      /
      node_filesystem_size_bytes{mountpoint="/"}
    ) < 0.1
  for: 5m
  labels:
    severity: critical
```

## Best Practices

1. **Include runbook URLs** in annotations
2. **Use meaningful severity levels** (info, warning, critical)
3. **Set appropriate `for` durations** to avoid alert fatigue
4. **Group related alerts** in the same rules file
5. **Test alerts** before deploying to production

## Related Topics

- [Prometheus Configuration](/docs/prometheus-config)
- [Alertmanager Setup](/docs/alertmanager)
- [Grafana Dashboards](/docs/grafana-dashboards)
