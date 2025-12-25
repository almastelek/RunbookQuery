# OOMKilled Troubleshooting

Exit code 137 means the container was killed due to Out of Memory (OOM) conditions.

## Understanding OOMKilled

When a container exceeds its memory limit, the Linux kernel's OOM killer terminates the process. In Kubernetes, this appears as:

- Exit code: 137
- Reason: OOMKilled
- The pod may go into CrashLoopBackOff

## Diagnosis

### Check Pod Status

```bash
kubectl describe pod <pod-name>
```

Look for:
```
Last State:     Terminated
  Reason:       OOMKilled
  Exit Code:    137
```

### Check Resource Limits

```bash
kubectl get pod <pod-name> -o yaml | grep -A10 resources
```

### Monitor Memory Usage

```bash
kubectl top pod <pod-name>
```

## Solutions

### 1. Increase Memory Limits

```yaml
resources:
  requests:
    memory: "256Mi"
  limits:
    memory: "512Mi"  # Increase this
```

### 2. Fix Memory Leaks

Common causes of memory leaks:
- Unbounded caches
- Connection pools not being closed
- Event listeners not being cleaned up
- Large objects not being garbage collected

### 3. Use Memory Profiling

For Java applications:
```bash
java -XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/tmp/heapdump.hprof
```

For Node.js:
```bash
node --inspect app.js
```

### 4. Set Appropriate JVM Heap Size

For Java containers, set heap size relative to container memory:
```yaml
env:
  - name: JAVA_OPTS
    value: "-Xmx400m -Xms400m"
```

## Prevention

1. **Set memory requests = limits** for predictable behavior
2. **Monitor memory trends** before they become critical
3. **Load test** with realistic data volumes
4. **Use vertical pod autoscaling** for automatic right-sizing

## Related Topics

- [Resource Management](/docs/resource-management)
- [Quality of Service](/docs/qos)
- [Monitoring with Prometheus](/docs/prometheus-monitoring)
