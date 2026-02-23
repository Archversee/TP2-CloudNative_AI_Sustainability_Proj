# TP2-CloudNative_AI_Sustainability_Proj
## Prerequisites
### Required
-  Docker Desktop installed
-  `.env` file in project root:
### For Kubernetes
-  Enable Kubernetes in Docker Desktop

## Deployment Commands
### Make Script Executable 
chmod +x deployment.sh

## Kubernetes (Production)
### Start (REBUILDS images & deploys pods LARGE CONTEXT - 30 MINUTES)
./deployment.sh start k8s
### Start (Deploys pods ONLY - 2 Minutes)
./deployment.sh start k8s --skip-build
**Access (with NodePort):**
- Frontend: http://localhost:30300
- API: http://localhost:30800
### Stop (Keeps namespace & secrets)
./deployment.sh stop k8s
### Stop & Cleanup (Removes everything)
./deployment.sh stop k8s --cleanup
### View Available Pods
./deployment.sh logs k8s
### Check Status (Shows pods, services, secrets)
./deployment.sh status k8s

##  Rebuild Commands
### Rebuild All Images
./deployment.sh rebuild all
### Rebuild Frontend Only (Rebuilds for K8 port 30800)
./deployment.sh rebuild frontend
**Use this when:**
- Updating frontend code

### Kubernetes (NodePort)
- Frontend: http://localhost:30300
- API: http://localhost:30800
- API Docs: http://localhost:30800/docs


## Docker Compose (LEGACY, faster for Development)
### Start (Builds images & starts containers)
./deployment.sh start compose
**Access:**
- Frontend: http://localhost:3000
- API: http://localhost:8000
### Stop (Keeps data)
./deployment.sh stop compose
### Stop & Cleanup (Removes all data)
./deployment.sh stop compose --cleanup
### View Log
./deployment.sh logs compose
### Check Status
./deployment.sh status compose
### Rebuild Frontend Only (Rebuilds for Compose port 3000)
cd infrastructure/docker
docker-compose up --build frontend

## Access URLs
### Docker Compose
- Frontend: http://localhost:3000
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
