# Deployment Guide

## Overview

This guide covers deploying the Urban Green and Blue Change Monitor to Google Cloud Platform (GCP) with:
- **Backend**: Cloud Run (containerized FastAPI)
- **Frontend**: Firebase Hosting (static React build)
- **Cache**: Cloud Storage (for analysis results)
- **Secrets**: Secret Manager (GEE service account key)
- **CI/CD**: GitHub Actions

---

## Prerequisites

1. **Google Cloud Project** with billing enabled
2. **Firebase Project** (can be same as GCP project)
3. **GitHub Repository** with Actions enabled
4. **GEE Service Account** with access to assets
5. **Domain** (optional, for custom domain)

---

## 1. Google Cloud Setup

### 1.1 Enable APIs

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  storage.googleapis.com \
  firebase.googleapis.com \
  earthengine.googleapis.com
```

### 1.2 Create Service Account for Backend

```bash
# Create service account
gcloud iam service-accounts create ugbcm-backend \
  --display-name="Urban Green Blue Monitor Backend"

# Grant necessary roles
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:ugbcm-backend@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:ugbcm-backend@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```

### 1.3 Store GEE Service Account Key in Secret Manager

```bash
# Assuming you have the key file locally
gcloud secrets create gee-service-account-key \
  --data-file=/path/to/your/gee-service-account.json \
  --replication-policy="automatic"

# Grant access to backend service account
gcloud secrets add-iam-policy-binding gee-service-account-key \
  --member="serviceAccount:ugbcm-backend@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

---

## 2. Firebase Setup

### 2.1 Initialize Firebase

```bash
cd frontend
firebase init hosting
# Select your project
# Public directory: dist
# Single-page app: Yes
# Overwrite index.html: No
```

### 2.2 Configure Firebase for SPA

In `firebase.json`:

```json
{
  "hosting": {
    "public": "dist",
    "ignore": ["firebase.json", "**/.*", "**/node_modules/**"],
    "rewrites": [
      {
        "source": "**",
        "destination": "/index.html"
      }
    ],
    "headers": [
      {
        "source": "**/*.@(js|css|png|jpg|jpeg|gif|svg|ico|woff|woff2)",
        "headers": [
          {
            "key": "Cache-Control",
            "value": "public, max-age=31536000, immutable"
          }
        ]
      }
    ]
  }
}
```

---

## 3. Cloud Storage for Cache

```bash
# Create bucket for analysis cache
gsutil mb -l us-central1 gs://YOUR_PROJECT_ID-ugbcm-cache

# Set lifecycle to auto-delete old files (optional)
cat > lifecycle.json <<EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {"age": 30}
      }
    ]
  }
}
EOF
gsutil lifecycle set lifecycle.json gs://YOUR_PROJECT_ID-ugbcm-cache
```

---

## 4. GitHub Actions Secrets

Add these secrets in GitHub Repository Settings → Secrets → Actions:

| Secret Name | Value |
|-------------|-------|
| `GCP_SERVICE_ACCOUNT_KEY` | Full JSON of a service account with Cloud Run, Cloud Build, Secret Manager, Storage Admin roles |
| `FIREBASE_SERVICE_ACCOUNT` | Firebase service account JSON (from Firebase Console → Project Settings → Service Accounts) |
| `FIREBASE_PROJECT_ID` | Your Firebase project ID |
| `GEE_PROJECT_ID` | `graphic-tide-513321-m3` (or your GEE project) |

### 4.1 Create GitHub Actions Service Account

```bash
gcloud iam service-accounts create github-actions \
  --display-name="GitHub Actions Deployer"

# Grant roles
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:github-actions@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.admin" \
  --role="roles/cloudbuild.builds.builder" \
  --role="roles/secretmanager.secretAccessor" \
  --role="roles/storage.admin" \
  --role="roles/iam.serviceAccountUser"

# Create key
gcloud iam service-accounts keys create github-actions-key.json \
  --iam-account=github-actions@YOUR_PROJECT_ID.iam.gserviceaccount.com

# Copy contents to GCP_SERVICE_ACCOUNT_KEY secret
```

---

## 5. Local Development Deployment

### 5.1 With Docker Compose

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your GEE service account key path
# GEE_SERVICE_ACCOUNT_KEY_PATH=/path/to/your/key.json

# Start services
docker compose up --build

# Frontend: http://localhost:5173
# Backend: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### 5.2 Without Docker (Direct)

```bash
# Backend
cd backend
pip install -r requirements.txt
export GEE_SERVICE_ACCOUNT_KEY_PATH=/path/to/key.json
uvicorn main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

---

## 6. Production Deployment

### 6.1 Deploy Backend to Cloud Run

```bash
# Build and push image
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/ugbcm-backend ./backend

# Deploy
gcloud run deploy ugbcm-backend \
  --image gcr.io/YOUR_PROJECT_ID/ugbcm-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --service-account=ugbcm-backend@YOUR_PROJECT_ID.iam.gserviceaccount.com \
  --set-env-vars GEE_PROJECT_ID=graphic-tide-513321-m3 \
  --set-secrets GEE_SERVICE_ACCOUNT_KEY_JSON=gee-service-account-key:latest \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 0 \
  --max-instances 10 \
  --port 8000 \
  --timeout 300 \
  --concurrency 80
```

### 6.2 Deploy Frontend to Firebase

```bash
cd frontend
npm run build
firebase deploy --only hosting
```

### 6.3 Configure Custom Domain (Optional)

```bash
# Backend custom domain
gcloud run domain-mappings create \
  --service=ugbcm-backend \
  --domain=api.yourdomain.com \
  --region=us-central1

# Frontend custom domain (in Firebase Console)
# Hosting → Add custom domain
```

---

## 7. Cost Estimation (Monthly)

| Service | Configuration | Est. Cost |
|---------|---------------|-----------|
| **Cloud Run** | 2 vCPU, 2GB RAM, 0-10 instances, ~100k requests | $5-20 |
| **Firebase Hosting** | Static files, ~10 GB transfer | Free tier |
| **Cloud Storage** | 10 GB cache, 100k operations | $1-5 |
| **Secret Manager** | 1 secret, 10k accesses | $0.06 |
| **Cloud Build** | ~10 builds/month | Free tier |
| **Artifact Registry** | 2 Docker images, ~5 GB | $0.50 |
| **Earth Engine** | Within free tier for research | Free |
| **Total** | | **~$10-30/month** |

### Budget Alert Setup

```bash
# Create budget alert at $50/month
gcloud billing budgets create \
  --billing-account=YOUR_BILLING_ACCOUNT \
  --display-name="UGBM Budget Alert" \
  --budget-amount=50USD \
  --threshold-rule=percent=0.5 \
  --threshold-rule=percent=0.9 \
  --threshold-rule=percent=1.0
```

---

## 8. GEE Quota Considerations

### 8.1 Default Quotas (per project)

| Quota | Limit | Notes |
|-------|-------|-------|
| Compute units | 6,000/min | Enough for ~200 concurrent analyses |
| Export tasks | 3,000/day | Not used (tile-based) |
| Asset storage | 500 GB | District assets are small |
| Batch tasks | 50 concurrent | For background jobs |

### 8.2 Quota Optimization

1. **Caching**: Results cached for 30 days (configurable)
2. **Tile-based maps**: No large exports, just map tiles
3. **Background jobs**: Async processing with progress polling
4. **Rate limiting**: 100 req/min per IP

### 8.3 Requesting Quota Increase

If needed, request via [GCP Console → IAM & Admin → Quotas](https://console.cloud.google.com/iam-admin/quotas)

---

## 9. Monitoring & Logging

### 9.1 Cloud Run Metrics

- Request count, latency, errors
- Instance count, CPU/memory utilization
- Cold start frequency

### 9.2 Log-based Alerts

```bash
# Alert on backend errors > 5/min
gcloud logging write "projects/YOUR_PROJECT_ID/logs/cloudrun" \
  --payload='{"severity":"ERROR","message":"Backend error"}' \
  --severity=ERROR
```

### 9.3 Health Checks

```bash
# Backend health
curl https://api.yourdomain.com/health

# Frontend health (via Firebase)
curl https://yourdomain.com/health
```

---

## 10. Rollback Procedure

### 10.1 Backend Rollback

```bash
# List revisions
gcloud run revisions list --service=ugbcm-backend --region=us-central1

# Rollback to previous revision
gcloud run services update-traffic ugbcm-backend \
  --to-revisions=PREVIOUS_REVISION=100 \
  --region=us-central1
```

### 10.2 Frontend Rollback

```bash
# In Firebase Console: Hosting → Release history → Rollback
# Or CLI:
firebase hosting:clone SOURCE_SITE:SOURCE_CHANNEL TARGET_SITE:live
```

---

## 11. Security Checklist

- [ ] No secrets in repository (use Secret Manager)
- [ ] CORS restricted to frontend domain
- [ ] Rate limiting enabled (100 req/min/IP)
- [ ] Upload size limited (10 MB max)
- [ ] File type validation (GeoJSON, Shapefile only)
- [ ] No PII collected
- [ ] HTTPS enforced (Cloud Run + Firebase provide this)
- [ ] Service accounts follow least privilege
- [ ] Secret scanning in CI/CD (TruffleHog)
- [ ] Dependency auditing in CI/CD (pip-audit, npm audit)

---

## 12. Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| GEE auth fails | Wrong service account | Verify key in Secret Manager, check IAM roles |
| Cloud Run timeout | Analysis too slow | Increase timeout, optimize GEE queries |
| CORS errors | Wrong origin in CORS_ORIGINS | Update env var with exact frontend URL |
| Map tiles don't load | Tile URL expired | Tiles auto-refresh; check network tab |
| 2018 data missing | Sentinel-2 coverage | Expected; UI shows quality warning |

### Debug Commands

```bash
# Check Cloud Run logs
gcloud run services logs read ugbcm-backend --region=us-central1 --limit=50

# Test GEE locally
cd backend && python -c "import ee; ee.Initialize(project='graphic-tide-513321-m3'); print('OK')"

# Test API directly
curl -X POST http://localhost:8000/api/analysis \
  -H "Content-Type: application/json" \
  -d '{"district_id":"bengaluru_urban","years":[2018,2025]}'
```

---

## 13. Maintenance

### Monthly Tasks

- [ ] Review Cloud Run metrics and costs
- [ ] Check cache hit rate (aim > 80%)
- [ ] Verify GEE quota usage < 50%
- [ ] Update dependencies (security patches)
- [ ] Review error logs for patterns

### Quarterly Tasks

- [ ] Review and update GEE service account permissions
- [ ] Test disaster recovery (backup/restore)
- [ ] Update documentation for any API changes
- [ ] Performance profiling of slow endpoints

---

## 14. GEE Project Registration Type

**Important**: Verify your GEE project registration type permits your use case:

| Registration Type | Commercial Use | Research/Education | Notes |
|-------------------|----------------|-------------------|-------|
| **Research** | ❌ | ✅ | Free, non-commercial only |
| **Commercial** | ✅ | ✅ | Requires paid agreement |
| **Evaluation** | ❌ | ✅ | Time-limited trial |

Check in [GEE Code Editor → Settings → Project Info](https://code.earthengine.google.com/)

If your use case is commercial (e.g., selling reports, consulting), you need a **Commercial** registration.

---

*Last updated: 2024 | For questions, see GitHub Issues or contact maintainers*