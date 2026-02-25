"""Tests to validate docker-compose.yml structure and configuration."""

from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).parent.parent.parent
COMPOSE_FILE = PROJECT_ROOT / "docker-compose.yml"


def _load_compose() -> dict:  # type: ignore[type-arg]
    """Load and parse docker-compose.yml."""
    assert COMPOSE_FILE.exists(), f"docker-compose.yml not found at {COMPOSE_FILE}"
    with open(COMPOSE_FILE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)
    return data


# -- Service inventory --


EXPECTED_SERVICES = [
    "config-server",
    "discovery-server",
    "customers-service",
    "visits-service",
    "vets-service",
    "genai-service",
    "api-gateway",
    "admin-server",
    "tracing-server",
    "grafana-server",
    "prometheus-server",
]


def test_all_11_services_defined() -> None:
    data = _load_compose()
    services = data.get("services", {})
    for name in EXPECTED_SERVICES:
        assert name in services, f"Missing service: {name}"
    assert len(services) == 11


# -- Port mappings --


EXPECTED_PORTS: dict[str, str] = {
    "config-server": "18888:8888",
    "discovery-server": "18761:8761",
    "customers-service": "8081:8081",
    "visits-service": "8082:8082",
    "vets-service": "8083:8083",
    "genai-service": "8084:8084",
    "api-gateway": "8080:8080",
    "admin-server": "9090:9090",
    "tracing-server": "19411:9411",
    "grafana-server": "13030:3000",
    "prometheus-server": "19091:9090",
}


def test_port_mappings() -> None:
    data = _load_compose()
    services = data["services"]
    for svc_name, expected_port in EXPECTED_PORTS.items():
        svc = services[svc_name]
        ports = [str(p) for p in svc.get("ports", [])]
        assert expected_port in ports, f"{svc_name} should map {expected_port}, got {ports}"


# -- Memory limits --


def test_memory_limits() -> None:
    data = _load_compose()
    services = data["services"]

    app_services = [
        "config-server",
        "discovery-server",
        "customers-service",
        "visits-service",
        "vets-service",
        "genai-service",
        "api-gateway",
        "admin-server",
        "tracing-server",
    ]
    infra_services = ["grafana-server", "prometheus-server"]

    for name in app_services:
        limit = services[name]["deploy"]["resources"]["limits"]["memory"]
        assert limit == "512M", f"{name} should have 512M limit, got {limit}"

    for name in infra_services:
        limit = services[name]["deploy"]["resources"]["limits"]["memory"]
        assert limit == "256M", f"{name} should have 256M limit, got {limit}"


# -- Startup dependency chain --


def test_config_server_has_healthcheck() -> None:
    data = _load_compose()
    svc = data["services"]["config-server"]
    hc = svc.get("healthcheck", {})
    assert hc.get("test") is not None, "config-server must have a healthcheck"
    assert hc.get("interval") is not None
    assert hc.get("retries") is not None


def test_discovery_server_depends_on_config_server_healthy() -> None:
    data = _load_compose()
    svc = data["services"]["discovery-server"]
    deps = svc.get("depends_on", {})
    assert "config-server" in deps
    assert deps["config-server"].get("condition") == "service_healthy"


def test_discovery_server_has_healthcheck() -> None:
    data = _load_compose()
    svc = data["services"]["discovery-server"]
    hc = svc.get("healthcheck", {})
    assert hc.get("test") is not None, "discovery-server must have a healthcheck"


def test_business_services_depend_on_config_and_discovery_healthy() -> None:
    data = _load_compose()
    business_services = [
        "customers-service",
        "visits-service",
        "vets-service",
        "genai-service",
        "api-gateway",
        "admin-server",
    ]
    for name in business_services:
        svc = data["services"][name]
        deps = svc.get("depends_on", {})
        assert "config-server" in deps, f"{name} should depend on config-server"
        assert deps["config-server"].get("condition") == "service_healthy"
        assert "discovery-server" in deps, f"{name} should depend on discovery-server"
        assert deps["discovery-server"].get("condition") == "service_healthy"


def test_infra_services_have_no_depends_on() -> None:
    """Tracing, Grafana, Prometheus are independent."""
    data = _load_compose()
    for name in ["tracing-server", "grafana-server", "prometheus-server"]:
        svc = data["services"][name]
        assert not svc.get("depends_on"), f"{name} should have no depends_on"


# -- Build configuration for application services --


APPLICATION_SERVICES = {
    "config-server": ("config_server", "8888"),
    "discovery-server": ("discovery_server", "8761"),
    "customers-service": ("customers_service", "8081"),
    "visits-service": ("visits_service", "8082"),
    "vets-service": ("vets_service", "8083"),
    "genai-service": ("genai_service", "8084"),
    "api-gateway": ("api_gateway", "8080"),
    "admin-server": ("admin_server", "9090"),
}


def test_application_services_use_shared_dockerfile() -> None:
    data = _load_compose()
    services = data["services"]
    for svc_name, (service_module, port) in APPLICATION_SERVICES.items():
        svc = services[svc_name]
        build = svc.get("build", {})
        assert build.get("dockerfile") == "docker/Dockerfile", f"{svc_name} should use docker/Dockerfile"
        args = build.get("args", {})
        assert args.get("SERVICE_NAME") == service_module, f"{svc_name} SERVICE_NAME should be {service_module}"
        assert str(args.get("EXPOSED_PORT")) == port, f"{svc_name} EXPOSED_PORT should be {port}"


# -- GenAI environment variables --


def test_genai_service_has_openai_env_vars() -> None:
    data = _load_compose()
    svc = data["services"]["genai-service"]
    env = svc.get("environment", [])
    # Environment can be a list of "KEY=VALUE" or a dict
    if isinstance(env, list):
        env_keys = [e.split("=")[0] for e in env]
    else:
        env_keys = list(env.keys())
    assert "OPENAI_API_KEY" in env_keys


# -- Infrastructure services use standard images --


def test_tracing_server_uses_zipkin_image() -> None:
    data = _load_compose()
    svc = data["services"]["tracing-server"]
    assert "openzipkin/zipkin" in svc.get("image", "")


def test_grafana_server_uses_grafana_image() -> None:
    data = _load_compose()
    svc = data["services"]["grafana-server"]
    assert "grafana/grafana" in svc.get("image", "")


def test_prometheus_server_uses_prometheus_image() -> None:
    data = _load_compose()
    svc = data["services"]["prometheus-server"]
    assert "prom/prometheus" in svc.get("image", "")


# -- Container names match service names --


def test_container_names() -> None:
    data = _load_compose()
    services = data["services"]
    for name in EXPECTED_SERVICES:
        svc = services[name]
        assert svc.get("container_name") == name, f"{name} container_name should be {name}"
