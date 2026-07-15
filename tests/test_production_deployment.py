from pathlib import Path

import yaml


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
COMPOSE_PATH = REPOSITORY_ROOT / "deploy" / "production" / "docker-compose.yml"


def _compose() -> dict:
    return yaml.safe_load(COMPOSE_PATH.read_text(encoding="utf-8"))


def test_frontend_runtime_image_contains_public_assets():
    dockerfile = (REPOSITORY_ROOT / "frontend" / "Dockerfile").read_text(
        encoding="utf-8"
    )

    assert "COPY --from=builder /app/public ./public" in dockerfile


def test_production_stack_keeps_internal_services_private_and_data_durable():
    services = _compose()["services"]
    expected = {
        "frontend",
        "backend",
        "hotel-mcp",
        "flight-mcp",
        "itinerary-mcp",
        "weather-mcp",
        "currency-mcp",
        "location-mcp",
        "caddy",
    }

    assert set(services) == expected
    assert services["caddy"]["ports"] == ["80:80", "443:443", "443:443/udp"]
    assert all("ports" not in config for name, config in services.items() if name != "caddy")
    assert "backend_data:/data" in services["backend"]["volumes"]
    assert services["backend"]["environment"]["TRIPWEAVER_DB_PATH"] == "/data/tripweaver.sqlite3"


def test_production_stack_scopes_provider_secrets():
    services = _compose()["services"]

    assert "OPENAI_API_KEY" in services["backend"]["environment"]
    for name in ("hotel-mcp", "flight-mcp", "location-mcp"):
        assert "SERPAPI_API_KEY" in services[name]["environment"]
    for name in ("backend", "frontend", "itinerary-mcp", "weather-mcp", "currency-mcp"):
        assert "SERPAPI_API_KEY" not in services[name]["environment"]
    assert services["frontend"]["environment"]["BACKEND_URL"] == "http://backend:8000"


def test_production_stack_checks_frontend_health():
    frontend = _compose()["services"]["frontend"]

    assert frontend["depends_on"]["backend"] == {"condition": "service_healthy"}
    assert frontend["healthcheck"]["interval"] == "20s"
    assert "http://localhost:3000/api/health" in " ".join(frontend["healthcheck"]["test"])
