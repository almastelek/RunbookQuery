# 503 Service Unavailable Errors

Intermittent 503 errors often indicate issues with service routing, upstream connectivity, or resource exhaustion.

## Common Causes

### 1. No Ready Endpoints

The service has no ready pods to receive traffic.

**Diagnosis:**
```bash
kubectl get endpoints <service-name>
```

If ENDPOINTS is empty or `<none>`, no pods are ready.

**Check pod status:**
```bash
kubectl get pods -l app=<your-app>
```

### 2. Readiness Probe Failures

Pods are running but not passing readiness checks.

```bash
kubectl describe pod <pod-name> | grep -A10 Readiness
```

### 3. Connection Pool Exhaustion

The application has exhausted its connection pool to upstream services.

**Symptoms:**
- Sporadic 503s under load
- "upstream connect error" in logs
- Connection timeouts

**Solutions:**
- Increase connection pool size
- Reduce connection timeouts
- Add circuit breakers

### 4. Envoy/Istio Sidecar Issues

If using a service mesh, the sidecar proxy might be having issues.

```bash
kubectl logs <pod-name> -c istio-proxy
```

Look for:
- `upstream connect error or disconnect/reset before headers`
- `no healthy upstream`

## Debugging Steps

1. **Check service endpoints:**
   ```bash
   kubectl get endpoints <service-name> -o wide
   ```

2. **Verify pod readiness:**
   ```bash
   kubectl get pods -o wide | grep <app-name>
   ```

3. **Check service configuration:**
   ```bash
   kubectl describe service <service-name>
   ```

4. **Test connectivity from another pod:**
   ```bash
   kubectl exec -it <debug-pod> -- curl -v http://<service-name>:<port>/health
   ```

5. **Check ingress/gateway logs:**
   ```bash
   kubectl logs -n ingress-nginx <ingress-pod>
   ```

## Load Balancer Configuration

Ensure your load balancer health checks align with your readiness probes:

```yaml
service.beta.kubernetes.io/aws-load-balancer-healthcheck-path: /health
service.beta.kubernetes.io/aws-load-balancer-healthcheck-interval: "30"
```

## Retry Configuration

Add retries for transient 503s:

```yaml
# Istio VirtualService
retries:
  attempts: 3
  perTryTimeout: 2s
  retryOn: 503,reset,connect-failure
```

## Related Topics

- [Service Networking](/docs/service-networking)
- [Debugging Services](/docs/debug-services)
- [Istio Traffic Management](/docs/istio-traffic)
