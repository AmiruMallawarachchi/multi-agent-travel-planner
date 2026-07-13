from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SERVICE_CONTEXTS = (
    "backend",
    "frontend",
    "mcp_servers/flight_mcp",
    "mcp_servers/hotel_mcp",
)
REQUIRED_PATTERNS = {".env", ".env.*", "!.env.example"}


def test_service_docker_contexts_exclude_local_environment_files():
    failures: list[str] = []

    for relative_context in SERVICE_CONTEXTS:
        dockerignore = REPOSITORY_ROOT / relative_context / ".dockerignore"
        if not dockerignore.is_file():
            failures.append(f"{relative_context}: missing .dockerignore")
            continue

        patterns = {
            line.strip()
            for line in dockerignore.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
        missing = REQUIRED_PATTERNS - patterns
        if missing:
            failures.append(f"{relative_context}: missing patterns {sorted(missing)}")

    assert not failures, "\n".join(failures)
