# GCP setup for F05 — AlloyDB + Auth Proxy + Vertex AI

Hands-on steps to stand up the only cloud component. **Every command here is a Tier C
(critical) action — run them yourself, never ask the agent to.** Rough timeline: 15–40 min,
most of it waiting for the cluster to be ready.

---

## 0. Prereqs

- A GCP account with billing enabled (free trial works) and one project.
- `gcloud` CLI installed and authenticated:

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

> **Cost:** the cluster is the main cost driver (smallest primary instance ≈ a few $/day).
> Keep it small, and **delete it when you're not demoing** (§6).

## 1. Enable APIs

```bash
gcloud services enable \
  alloydb.googleapis.com \
  aiplatform.googleapis.com \
  servicenetworking.googleapis.com \
  compute.googleapis.com
```

## 2. Prepare the VPC (required prerequisite for any AlloyDB cluster)

```bash
# reserve a /16 for Google-managed services (private services access)
gcloud compute addresses create google-managed-services-default \
  --global \
  --purpose=VPC_PEERING \
  --prefix-length=16 \
  --description="peering range for Google services" \
  --network=default

# peer the range to servicenetworking
gcloud services vpc-peerings connect \
  --service=servicenetworking.googleapis.com \
  --ranges=google-managed-services-default \
  --network=default
```

## 3. Create the cluster + primary instance (small, public IP for dev)

```bash
REGION=us-central1

# cluster (takes 10–30 min to provision)
gcloud alloydb clusters create catalog-cluster \
  --region=$REGION \
  --network=default \
  --database-version=POSTGRES_15 \
  --password=YOUR_POSTGRES_PASSWORD

# primary instance, 2 vCPU, public IP so the laptop can connect via the Auth Proxy
gcloud alloydb instances create catalog-primary \
  --cluster=catalog-cluster \
  --region=$REGION \
  --cpu-count=2 \
  --assign-public-ip
```

> If a flag name differs in your gcloud version, check `gcloud alloydb instances create --help`.

## 4. Let AlloyDB call Vertex AI (for `embedding()` in SQL)

```bash
PROJECT_NUMBER=$(gcloud projects describe YOUR_PROJECT_ID --format="value(projectNumber)")

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-alloydb.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

## 5. Run the Auth Proxy (a single binary, no Docker)

```bash
# download (one time)
curl -o alloydb-auth-proxy https://storage.googleapis.com/alloydb-auth-proxy/v1/alloydb-auth-proxy-linux-amd64 \
  && chmod +x alloydb-auth-proxy

# keep this terminal running
./alloydb-auth-proxy \
  "projects/YOUR_PROJECT_ID/locations/us-central1/clusters/catalog-cluster/instances/catalog-primary" \
  --public-ip --port 5432
```

Expected: `{"severity":"INFO","message":"server listening on 127.0.0.1:5432"}`.

## 6. Create the `catalog` database

In a second terminal, through the proxy:

```bash
psql "postgresql://postgres:YOUR_POSTGRES_PASSWORD@127.0.0.1:5432/postgres" \
  -c "CREATE DATABASE catalog;"
```

(No `psql`? Use `.venv/bin/python` + `psycopg` to run the same `CREATE DATABASE`.)

## 7. Fill `.env`

```
ENABLE_CLOUD=true
GCP_PROJECT=YOUR_PROJECT_ID
GCP_REGION=us-central1
PGHOST=127.0.0.1
PGPORT=5432
PGUSER=postgres
PGPASSWORD=YOUR_POSTGRES_PASSWORD
PGDATABASE=catalog
GEMINI_MODEL=gemini-2.5-flash
EMBEDDING_MODEL=text-embedding-005
LLM_MAX_ROWS_PER_RUN=500
```

## 8. Run the pipeline (🔴 agent approval required)

```bash
make data && make ingest && make quality && make gold   # local, already works
make db        # create extensions + schema + indexes (Tier C — approve with the agent)
make load      # upsert 197 gold rows + embeddings    (Tier C — approve)
```

Verification:
```sql
select count(*) from products;                                   -- expect 197
select count(*) from products where embedding is null;           -- expect 0
select count(*) from products where tsv is null;                 -- expect 0
```

## 9. Cleanup (when the demo is over)

```bash
gcloud alloydb clusters delete catalog-cluster --region=us-central1 --force
```

AlloyDB instances cannot be paused — they bill per hour while the cluster exists. Delete it
when not presenting.
