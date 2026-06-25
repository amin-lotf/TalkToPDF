from talk_to_pdf.backend.app.core.config import Settings


def test_default_cors_allowed_origins_include_docker_react_port():
    settings = Settings()

    assert "http://localhost:5678" in settings.CORS_ALLOWED_ORIGINS
    assert "http://127.0.0.1:5678" in settings.CORS_ALLOWED_ORIGINS


def test_cors_allowed_origins_accepts_comma_separated_env_value():
    settings = Settings(CORS_ALLOWED_ORIGINS="http://localhost:5678,http://127.0.0.1:5678")

    assert settings.CORS_ALLOWED_ORIGINS == [
        "http://localhost:5678",
        "http://127.0.0.1:5678",
    ]


def test_cors_allowed_origins_accepts_comma_separated_env_var(monkeypatch):
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )

    settings = Settings(_env_file=None)

    assert settings.CORS_ALLOWED_ORIGINS == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
