from __future__ import annotations

from pathlib import Path

import yaml


BLUEPRINT_PATH = Path(__file__).resolve().parents[2] / "render.yaml"
PROVIDER_SERVICES = {
    "tripweaver-hotel-search-mcp",
    "tripweaver-flight-search-mcp",
    "tripweaver-place-search-mcp",
}


def _services_by_name() -> dict[str, dict]:
    blueprint = yaml.safe_load(BLUEPRINT_PATH.read_text(encoding="utf-8"))
    return {service["name"]: service for service in blueprint["services"]}


def _env_by_key(service: dict) -> dict[str, dict]:
    return {item["key"]: item for item in service["envVars"]}


def test_blueprint_uses_dedicated_provider_service_names():
    services = _services_by_name()

    assert PROVIDER_SERVICES <= services.keys()
    assert {
        "tripweaver-hotel-mcp",
        "tripweaver-flight-mcp",
        "tripweaver-location-mcp",
    }.isdisjoint(services)


def test_backend_hosts_reference_blueprint_managed_provider_services():
    services = _services_by_name()
    backend_env = _env_by_key(services["tripweaver-backend"])

    expected_references = {
        "HOTEL_MCP_HOST": "tripweaver-hotel-search-mcp",
        "FLIGHT_MCP_HOST": "tripweaver-flight-search-mcp",
        "LOCATION_MCP_HOST": "tripweaver-place-search-mcp",
    }
    for key, service_name in expected_references.items():
        assert backend_env[key]["fromService"] == {
            "type": "web",
            "name": service_name,
            "envVarKey": "RENDER_EXTERNAL_HOSTNAME",
        }

    assert backend_env["MCP_HEALTH_TIMEOUT_SECONDS"]["value"] == "70"


def test_serpapi_secret_is_owned_by_hotel_and_shared_with_provider_services():
    services = _services_by_name()
    hotel_env = _env_by_key(services["tripweaver-hotel-search-mcp"])

    assert hotel_env["SERPAPI_API_KEY"] == {
        "key": "SERPAPI_API_KEY",
        "sync": False,
    }

    for service_name in {
        "tripweaver-flight-search-mcp",
        "tripweaver-place-search-mcp",
    }:
        service_env = _env_by_key(services[service_name])
        assert service_env["SERPAPI_API_KEY"]["fromService"] == {
            "type": "web",
            "name": "tripweaver-hotel-search-mcp",
            "envVarKey": "SERPAPI_API_KEY",
        }
