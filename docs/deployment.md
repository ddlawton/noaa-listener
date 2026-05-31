# Deployment Guide

## Docker Compose (Recommended)

The simplest deployment method for personal use.

### Setup

```bash
# Configure
cp .env.example .env
nano .env  # Set POSTGRES_PASSWORD, NOAA_CDO_API_TOKEN, and location coordinates

# Start services
docker-compose up -d

# View logs
docker-compose logs -f noaa_listener

# Stop services
docker-compose down
```

### Using Pre-built Image

Instead of building locally, use the GitHub Container Registry image:

Edit `docker-compose.yaml`:
```yaml
services:
  noaa_listener:
    image: ghcr.io/ddlawton/noaa-listener:latest
    # Remove 'build: .' line
```

Then:
```bash
docker-compose pull
docker-compose up -d
```

## TrueNAS Scale

TrueNAS Scale uses Kubernetes (k3s). Two options:

### Option 1: Docker Compose (via Custom App)

1. Install Docker Compose plugin in TrueNAS Scale
2. Copy project to TrueNAS: `/mnt/pool/apps/noaa-listener`
3. Configure `.env` and `config.yaml`
4. Run `docker-compose up -d`

### Option 2: Kubernetes (Native)

Create a deployment manifest:

**`k8s/deployment.yaml`**:
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: noaa-listener
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: noaa-config
  namespace: noaa-listener
data:
  config.yaml: |
    fetching:
      forecast_update_interval: 60
    # ... rest of config (location is in secrets)
---
apiVersion: v1
kind: Secret
metadata:
  name: noaa-secrets
  namespace: noaa-listener
type: Opaque
stringData:
  POSTGRES_HOST: "192.168.50.134"
  POSTGRES_PORT: "5432"
  POSTGRES_DB: "noaa_weather"
  POSTGRES_USER: "postgres"
  POSTGRES_PASSWORD: "your_password"
  NOAA_CDO_API_TOKEN: "your_token"
  LOCATION_LATITUDE: "37.7749"
  LOCATION_LONGITUDE: "-122.4194"
  LOCATION_NAME: "San Francisco, CA"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: noaa-listener
  namespace: noaa-listener
spec:
  replicas: 1
  selector:
    matchLabels:
      app: noaa-listener
  template:
    metadata:
      labels:
        app: noaa-listener
    spec:
      containers:
      - name: noaa-listener
        image: ghcr.io/ddlawton/noaa-listener:latest
        envFrom:
        - secretRef:
            name: noaa-secrets
        volumeMounts:
        - name: config
          mountPath: /app/config.yaml
          subPath: config.yaml
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
      volumes:
      - name: config
        configMap:
          name: noaa-config
---
```

Apply:
```bash
kubectl apply -f k8s/deployment.yaml
kubectl logs -n noaa-listener -l app=noaa-listener -f
```

## External PostgreSQL

The application connects to an external PostgreSQL server (not in the container). Ensure:

1. PostgreSQL allows connections from Docker network
2. Firewall allows port 5432
3. `pg_hba.conf` permits host connections

Test connection:
```bash
psql -h 192.168.50.134 -U postgres -d noaa_weather -c "SELECT 1"
```

## Environment Variables

Required:
- `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `NOAA_CDO_API_TOKEN`

Optional:
- `LOG_LEVEL`: DEBUG, INFO, WARNING, ERROR

## Health Checks

The application doesn't expose an HTTP endpoint. Monitor via:

**Logs**:
```bash
docker-compose logs -f noaa_listener
```

**Database**:
```sql
SELECT * FROM data_fetch_log ORDER BY fetch_time DESC LIMIT 1;
```

If `fetch_time` is older than 2 hours, something is wrong.

## Troubleshooting

**Container exits immediately**:
```bash
docker-compose logs noaa_listener
# Check for config errors
```

**No data in database**:
```bash
# Check logs for API errors
docker-compose logs noaa_listener | grep ERROR

# Verify location coordinates
docker-compose exec noaa_listener python -c "import os; print(f'Lat: {os.getenv(\"LOCATION_LATITUDE\")}, Lon: {os.getenv(\"LOCATION_LONGITUDE\")}')"
```

**Database connection refused**:
```bash
# Test from container
docker-compose exec noaa_listener psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT 1"
```

## Updates

**Docker Compose**:
```bash
docker-compose pull
docker-compose up -d
```

**Kubernetes**:
```bash
kubectl rollout restart deployment/noaa-listener -n noaa-listener
```

## Backup

**Database**:
```bash
pg_dump -h 192.168.50.134 -U postgres noaa_weather > backup.sql
```

**Configuration**:
```bash
tar -czf noaa-listener-config.tar.gz .env config.yaml docker-compose.yaml
```

## Monitoring

Consider adding:
- Prometheus for metrics
- Grafana for dashboards
- Alertmanager for notifications

Example metrics to track:
- Fetch success rate (from `data_fetch_log`)
- Database write latency
- API response times
