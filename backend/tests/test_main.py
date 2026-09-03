"""Test main endpoints."""


def test_root(client):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "pookie-employer-backend"
    assert "version" in data


def test_health(client):
    """Test health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_protected_route_rejects_missing_authorization(client):
    """Protected routes return a safe structured error without credentials."""
    response = client.get("/api/protected")

    assert response.status_code == 401
    assert response.json()["detail"] == {
        "code": "authentication_required",
        "message": "Authentication required.",
    }


def test_protected_route_rejects_invalid_secret(client):
    """Protected routes reject an invalid shared secret."""
    response = client.get(
        "/api/protected", headers={"Authorization": "Bearer wrong-secret"}
    )

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "invalid_credentials"


def test_protected_route_accepts_configured_secret(client):
    """Protected routes accept the configured shared secret."""
    response = client.get(
        "/api/protected", headers={"Authorization": "Bearer test-api-secret"}
    )

    assert response.status_code == 200
    assert response.json() == {"status": "authorized"}


def test_cors_allows_configured_origin_and_blocks_other_origins(client):
    """CORS only grants access to the configured local origins."""
    allowed = client.options(
        "/api/protected",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    blocked = client.options(
        "/api/protected",
        headers={
            "Origin": "https://malicious.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "access-control-allow-origin" not in blocked.headers


def test_request_id_is_generated_and_incoming_id_is_propagated(client):
    """Every response has a request ID, preserving a caller-supplied one."""
    generated = client.get("/health")
    propagated = client.get("/health", headers={"X-Request-ID": "client-request-123"})

    assert generated.headers["x-request-id"]
    assert propagated.headers["x-request-id"] == "client-request-123"


def test_request_id_rejects_unsafe_client_value(client):
    """An unsafe client-supplied request ID is replaced, not echoed back."""
    response = client.get(
        "/health", headers={"X-Request-ID": "bad\r\nX-Injected: evil"}
    )

    assert response.headers["x-request-id"] != "bad\r\nX-Injected: evil"
    assert "x-injected" not in response.headers


def test_unhandled_exception_fallback_response_still_gets_cors_headers(client):
    """The request-id middleware's manual 500 fallback must still pass through
    CORSMiddleware, or the browser blocks a cross-origin error as a CORS
    failure instead of surfacing the real 500 to the frontend."""
    from pookie_backend.main import app
    from pookie_backend.security import require_api_secret

    def boom() -> None:
        raise RuntimeError("boom")

    app.dependency_overrides[require_api_secret] = boom
    try:
        response = client.get(
            "/api/protected",
            headers={
                "Authorization": "Bearer test-api-secret",
                "Origin": "http://localhost:3000",
            },
        )
    finally:
        app.dependency_overrides.pop(require_api_secret, None)

    assert response.status_code == 500
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
