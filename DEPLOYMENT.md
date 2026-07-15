# TripWeaver deployment

The lowest-cost durable deployment for the current eight-process architecture
is one Linux VM running Docker Compose. This keeps the six MCP services private,
preserves account history on a named volume, and exposes only Caddy on ports 80
and 443.

## Recommended free host

Use one Oracle Cloud Always Free Ampere A1 VM. Select Ubuntu 24.04, the largest
Always Free A1 shape your tenancy currently permits, and an Always Free boot
volume. Capacity and allowance can vary by account and home region, so confirm
that the console labels every selected resource `Always Free` before creating
it.

This is suitable for a personal demonstration deployment, not a service-level
agreement. OpenAI and SerpApi usage are separately billed or quota-limited even
when the VM itself is free.

## VM preparation

Open inbound TCP 22, 80, and 443 in the OCI network security list. Then connect
to the VM and install Git and Docker:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"
newgrp docker
docker version
docker compose version
```

Clone the repository and check out the reviewed branch after its pull request
has been merged:

```bash
git clone https://github.com/AmiruMallawarachchi/multi-agent-travel-planner.git
cd multi-agent-travel-planner
git switch dev
```

## Private configuration

Create the ignored deployment environment file from the example:

```bash
cd deploy/production
cp .env.example .env
nano .env
```

Set `OPENAI_API_KEY`, `SERPAPI_API_KEY`, and a long random
`TRIPWEAVER_API_KEY`. Keep `SITE_ADDRESS=:80` for an initial IP-only HTTP
deployment. For HTTPS, point a domain's A record at the VM and set
`SITE_ADDRESS` to that domain; Caddy then provisions and renews TLS
automatically. Set `PUBLIC_ORIGIN` to the full public origin, including
`http://` or `https://`.

## Build and launch

```bash
docker compose build
docker compose up -d
docker compose ps
docker compose logs --tail=100 backend frontend caddy
```

Open the VM's public IP or configured domain. The backend and MCP ports are not
published; the Next.js server reaches the backend over the private Compose
network.

## Updates and backup

Deploy a reviewed update with:

```bash
git pull --ff-only origin dev
cd deploy/production
docker compose build
docker compose up -d
```

Back up account history before infrastructure changes:

```bash
docker compose exec backend python -c "import shutil; shutil.copy2('/data/tripweaver.sqlite3', '/data/tripweaver-backup.sqlite3')"
docker run --rm -v tripweaver-production_backend_data:/data -v "$PWD":/backup alpine cp /data/tripweaver-backup.sqlite3 /backup/
```

The VM boot volume and Docker volume are durable across container rebuilds, but
they are not a substitute for an off-VM encrypted backup.
