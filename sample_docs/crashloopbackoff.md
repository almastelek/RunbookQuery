# CrashLoopBackOff Troubleshooting

CrashLoopBackOff indicates that a container is repeatedly crashing after starting. The kubelet is continuously trying to restart it.

## Common Causes

### 1. Application Errors

The most common cause is bugs in your application that cause it to exit immediately after starting.

**Diagnosis:**
```bash
kubectl logs <pod-name> --previous
```

This shows logs from the previous container instance before it crashed.

### 2. Readiness Probe Failures

If your readiness probe is misconfigured, the container may be killed before it finishes starting.

**Example configuration issue:**
```yaml
readinessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 5  # May be too short for slow-starting apps
  timeoutSeconds: 1
```

**Solution:** Increase `initialDelaySeconds` or adjust the probe endpoint.

### 3. Liveness Probe Killing Container

Aggressive liveness probes can kill containers that are still starting up.

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 30  # Should be longer than startup time
  periodSeconds: 10
  failureThreshold: 3
```

### 4. OOMKilled (Exit Code 137)

The container is being killed because it exceeded its memory limit.

**Diagnosis:**
```bash
kubectl describe pod <pod-name> | grep -A5 "Last State"
```

Look for `OOMKilled: true` or exit code 137.

**Solution:** Increase memory limits or fix memory leaks in your application.

## Debugging Steps

1. Check pod events:
   ```bash
   kubectl describe pod <pod-name>
   ```

2. Check container logs:
   ```bash
   kubectl logs <pod-name> -c <container-name> --previous
   ```

3. Check resource usage:
   ```bash
   kubectl top pod <pod-name>
   ```

4. Exec into the pod (if it stays up long enough):
   ```bash
   kubectl exec -it <pod-name> -- /bin/sh
   ```

## Related Resources

- [Pod Lifecycle](/docs/pod-lifecycle)
- [Configure Liveness and Readiness Probes](/docs/configure-probes)
- [Resource Management](/docs/resource-management)
