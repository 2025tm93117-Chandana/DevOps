# ACEest Fitness & Gym - Kubernetes Deployment Guide

## Overview
This guide explains how to deploy the ACEest Fitness application to Kubernetes using Minikube locally or cloud providers (AWS, Azure, GCP).

## Prerequisites
- Minikube installed and running (`minikube start --driver=docker`)
- kubectl configured (`minikube kubectl -- get nodes`)
- Docker image built and available (`2025tm93117/acefitness:latest`)

## Quick Start - Deploy to Minikube

### 1. Create the Namespace
```bash
kubectl apply -f k8s-namespace.yaml
```

### 2. Deploy the Application (Basic Deployment)
```bash
kubectl apply -f k8s-deployment.yaml
kubectl apply -f k8s-service.yaml
```

### 3. Verify Deployment
```bash
# Check if deployment is ready
kubectl get deployments -n acefitness

# Check if pods are running
kubectl get pods -n acefitness -o wide

# Check service status
kubectl get svc -n acefitness

# Get the application URL for Minikube
minikube service acefitness-service -n acefitness
```

### 4. Access the Application
```bash
# Get Minikube IP
MINIKUBE_IP=$(minikube ip)

# Access via NodePort
curl http://$MINIKUBE_IP:30000/health
curl http://$MINIKUBE_IP:30000/

# Or use port-forward
kubectl port-forward -n acefitness svc/acefitness-service 5000:80
# Then access: http://localhost:5000
```

## Deployment Strategies

### Strategy 1: Blue-Green Deployment (Zero-Downtime Switching)
**Best for:** Switching traffic between two production versions instantly

```bash
# Deploy blue-green setup
kubectl apply -f k8s-blue-green.yaml

# Monitor deployments
kubectl get deployments -n acefitness -l app=acefitness

# Initially, traffic goes to BLUE (slot: blue)
# To switch to GREEN:
kubectl patch service acefitness-bluegreen -n acefitness \
  -p '{"spec":{"selector":{"slot":"green"}}}'

# Access the service
MINIKUBE_IP=$(minikube ip)
curl http://$MINIKUBE_IP:30001/
```

**Rollback:** Just switch the selector back to `blue`
```bash
kubectl patch service acefitness-bluegreen -n acefitness \
  -p '{"spec":{"selector":{"slot":"blue"}}}'
```

### Strategy 2: Canary Deployment (Gradual Rollout)
**Best for:** Testing new versions with real traffic before full rollout

```bash
# Deploy canary setup (90% stable, 10% canary)
kubectl apply -f k8s-canary.yaml

# Monitor the canary pods
kubectl get pods -n acefitness -l version=canary

# If canary is stable, gradually increase replicas
kubectl scale deployment acefitness-canary -n acefitness --replicas=2
kubectl scale deployment acefitness-stable -n acefitness --replicas=8

# Eventually scale down stable and scale up canary
kubectl scale deployment acefitness-canary -n acefitness --replicas=10
kubectl scale deployment acefitness-stable -n acefitness --replicas=0

# Access the service
MINIKUBE_IP=$(minikube ip)
curl http://$MINIKUBE_IP:30002/
```

### Strategy 3: Rolling Update (Default - Zero-Downtime)
**Best for:** Standard deployments with gradual pod replacement

```bash
# Deploy rolling update (included in k8s-deployment.yaml)
kubectl apply -f k8s-rolling-update.yaml

# Update the image (this triggers rolling update)
kubectl set image deployment/acefitness-rolling -n acefitness \
  acefitness=2025tm93117/acefitness:v1.0.0 --record

# Monitor rollout progress
kubectl rollout status deployment/acefitness-rolling -n acefitness

# Access the service
MINIKUBE_IP=$(minikube ip)
curl http://$MINIKUBE_IP:30003/
```

## Rollback Procedures

### View Deployment History
```bash
kubectl rollout history deployment/acefitness-app -n acefitness
kubectl rollout history deployment/acefitness-rolling -n acefitness
```

### Rollback to Previous Version
```bash
# Rollback deployment
kubectl rollout undo deployment/acefitness-app -n acefitness

# Verify status
kubectl rollout status deployment/acefitness-app -n acefitness
```

### Rollback to Specific Revision
```bash
# View all revisions
kubectl rollout history deployment/acefitness-app -n acefitness

# Rollback to revision 2
kubectl rollout undo deployment/acefitness-app -n acefitness --to-revision=2
```

### Pause and Resume Rollout (Canary Testing)
```bash
# Pause the rollout
kubectl rollout pause deployment/acefitness-rolling -n acefitness

# Resume the rollout
kubectl rollout resume deployment/acefitness-rolling -n acefitness
```

## Health Checks & Auto-Healing

The deployment includes:
- **Liveness Probe:** Restarts unhealthy containers
- **Readiness Probe:** Removes unhealthy pods from load balancing
- **Resource Limits:** Prevents resource starvation

```bash
# View probe status
kubectl describe pod <pod-name> -n acefitness

# View pod logs
kubectl logs <pod-name> -n acefitness

# Watch pod status
kubectl get pods -n acefitness -w
```

## Scaling

### Manual Scaling
```bash
# Scale to 5 replicas
kubectl scale deployment acefitness-app -n acefitness --replicas=5

# Scale back to 3
kubectl scale deployment acefitness-app -n acefitness --replicas=3
```

### Horizontal Pod Autoscaling (Optional - requires metrics-server)
```bash
# Create HPA (if metrics-server is installed)
kubectl autoscale deployment acefitness-app -n acefitness --min=2 --max=10 --cpu-percent=80

# Check HPA status
kubectl get hpa -n acefitness
```

## Cleanup

```bash
# Delete the entire namespace (removes all resources)
kubectl delete namespace acefitness

# Or delete specific resources
kubectl delete deployment acefitness-app -n acefitness
kubectl delete service acefitness-service -n acefitness
kubectl delete namespace acefitness
```

## Troubleshooting

### Pods not running
```bash
kubectl describe pod <pod-name> -n acefitness
kubectl logs <pod-name> -n acefitness
```

### Service not accessible
```bash
kubectl get svc -n acefitness
kubectl port-forward svc/acefitness-service 5000:80 -n acefitness
```

### Image pull errors
```bash
# Check image availability
docker images | grep acefitness

# Pull image manually
docker pull 2025tm93117/acefitness:latest
```

## Production Deployment (AWS/Azure/GCP)

For cloud deployment, use the same YAML files with these adjustments:

```yaml
# Change service type for cloud
apiVersion: v1
kind: Service
metadata:
  name: acefitness-service
  namespace: acefitness
spec:
  type: LoadBalancer  # Use LoadBalancer instead of NodePort
  ports:
  - port: 80
    targetPort: 5000
  selector:
    app: acefitness
```

Then deploy to your cloud Kubernetes cluster:
```bash
# AWS EKS
kubectl apply -f k8s-deployment.yaml

# Azure AKS
kubectl apply -f k8s-deployment.yaml

# Google GKE
kubectl apply -f k8s-deployment.yaml
```

## Key Files
- `k8s-namespace.yaml` - Create namespace
- `k8s-deployment.yaml` - Basic deployment with rolling updates
- `k8s-service.yaml` - Service to expose the app
- `k8s-blue-green.yaml` - Blue-Green deployment strategy
- `k8s-canary.yaml` - Canary deployment strategy
- `k8s-rolling-update.yaml` - Rolling update strategy
- `k8s-rollback.yaml` - Rollback procedures and guide
