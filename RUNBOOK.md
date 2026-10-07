# Operations Runbook: Self-Healing Kubernetes Service

This runbook is intended for on-call engineers responsible for maintaining, operating, debugging, and recovering the `self-healing-k8s-service` workloads running across staging and production clusters.

---

## 1. Service Overview & Architecture
- **Namespace**: `self-healing-app`
- **Workload**: `Deployment/self-healing-service` (FastAPI REST service)
- **Port Mapping**:
  - Internal Service: Port `80` (ClusterIP/NodePort) -> Pod port `8000`
  - Ingress NodePort: `30080` (mapped to `localhost:8000` in local Kind)
- **Monitoring**:
  - Prometheus NodePort: `30090` (Prometheus server)
  - Grafana NodePort: `30030` (Golden Signals dashboard, user: `admin`, pass: `admin`)
- **Key Probes**:
  - Liveness: `GET /health` (failure restarts the container after 3 attempts, 15s)
  - Readiness: `GET /ready` (failure unregisters pod from Service endpoints)

---

## 2. Standard Deployment Procedures

### Deploying the Workload
To deploy or update manifests to the active cluster:
```bash
# Check connected cluster
kubectl cluster-info

# Apply all manifests declaratively
kubectl apply -k k8s/

# Monitor rollout status
kubectl rollout status deployment/self-healing-service -n self-healing-app --timeout=60s
```

### Inspecting Deployment Status
```bash
# Verify running pods
kubectl get pods -n self-healing-app -o wide

# Check endpoints registered to service
kubectl get endpoints self-healing-service -n self-healing-app

# Inspect Horizontal Pod Autoscaler
kubectl get hpa -n self-healing-app
```

---

## 3. Rollback Procedures

If an incident or regression occurs immediately following an application rollout:

### Step 1: Check Rollout History
```bash
kubectl rollout history deployment/self-healing-service -n self-healing-app
```

### Step 2: Roll Back to Previous Revision
```bash
kubectl rollout undo deployment/self-healing-service -n self-healing-app
```

### Step 3: Roll Back to a Specific Known Good Revision
```bash
kubectl rollout undo deployment/self-healing-service -n self-healing-app --to-revision=2
```

### Step 4: Verify Health Post-Rollback
```bash
kubectl rollout status deployment/self-healing-service -n self-healing-app
./cli/pinger -url http://localhost:8000/health
```

---

## 4. Triage & Debugging Guide

### Scenario A: Pod in `CrashLoopBackOff` or Repeated Restarts

1. **Check Pod Events & Status**:
   ```bash
   kubectl describe pod -l app=self-healing-service -n self-healing-app
   ```
   *Look for `OOMKilled`, probe timeouts, or failed mounts.*

2. **Inspect Current & Previous Container Logs**:
   ```bash
   # Logs from current container
   kubectl logs -l app=self-healing-service -n self-healing-app --tail=100

   # Logs from crashed previous instance
   kubectl logs <pod-name> -n self-healing-app --previous
   ```

3. **Check Resource Starvation**:
   ```bash
   kubectl top pods -n self-healing-app
   ```
   If memory exceeds `256Mi` (the limit), adjust `limits.memory` in `k8s/deployment.yaml`.

---

### Scenario B: Unhealthy / Degraded Service Probes

1. **Execute Diagnostic Probe via Go CLI**:
   ```bash
   # Text mode
   ./cli/pinger -url http://localhost:8000/health

   # JSON mode for detailed latency breakdown
   ./cli/pinger -url http://localhost:8000/health -json
   ```

2. **Test Endpoints Manually via Port-Forward**:
   ```bash
   kubectl port-forward svc/self-healing-service -n self-healing-app 8000:80
   curl -i http://localhost:8000/health
   curl -i http://localhost:8000/ready
   ```

3. **Recover Manually if Chaos Injected**:
   ```bash
   curl -X POST http://localhost:8000/chaos/recover
   ```

---

## 5. Manual Scaling & Emergency Capacity Overrides

If traffic surges exceed automated HPA reaction times or downstream queue backpressure builds up:

### Temporarily Disable or Override HPA:
```bash
# Manual scale to 6 replicas
kubectl scale deployment/self-healing-service -n self-healing-app --replicas=6

# Verify scale up
kubectl get pods -n self-healing-app -l app=self-healing-service -w
```

### Resume Autoscaling:
```bash
kubectl apply -f k8s/hpa.yaml
```

---

## 6. Incident Escalation Contacts
- **Primary On-Call**: Systems Engineering Intern / SRE Team
- **Slack Alert Channel**: `#alerts-infrastructure`
- **Dashboards**: Grafana (`http://<node-ip>:30030`, UID: `self-healing-golden-signals`)
