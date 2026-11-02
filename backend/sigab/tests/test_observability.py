import json
import logging
import sys

import pytest

from sigab.observability import CorrelationIdFilter, JsonFormatter, redact

SYNTHETIC_CPF = "52998224725"


def _format(record):
    CorrelationIdFilter().filter(record)
    return json.loads(JsonFormatter().format(record))


def _record(message, *args, exc_info=None, **extra):
    record = logging.LogRecord("sigab.test", logging.INFO, __file__, 1, message, args, exc_info)
    for key, value in extra.items():
        setattr(record, key, value)
    return record


@pytest.mark.parametrize(
    "text",
    [SYNTHETIC_CPF, "529.982.247-25", "cpf=52998224725&x=1"],
)
def test_redact_removes_cpf(text):
    assert "52998224725" not in redact(text)
    assert "529.982.247-25" not in redact(text)


@pytest.mark.parametrize(
    "text",
    ["password=Senha-forte-123", '{"password": "Senha-forte-123"}', "token: Senha-forte-123"],
)
def test_redact_removes_secrets(text):
    assert "Senha-forte-123" not in redact(text)


def test_formatter_keeps_only_allowed_fields():
    entry = _format(
        _record("request", method="POST", path="/api/v1/items/", request=object(), body="x")
    )
    assert entry["message"] == "request"
    assert entry["method"] == "POST"
    assert entry["path"] == "/api/v1/items/"
    assert "request" not in entry
    assert "body" not in entry
    assert {"timestamp", "level", "logger", "correlation_id"} <= entry.keys()


def test_formatter_redacts_traceback():
    try:
        raise ValueError(f"cpf {SYNTHETIC_CPF}")
    except ValueError:
        entry = _format(_record("falhou", exc_info=sys.exc_info()))
    assert entry["error_type"] == "ValueError"
    assert SYNTHETIC_CPF not in entry["traceback"]


@pytest.mark.django_db
def test_request_is_logged_with_correlation_and_without_query(client, api_world, caplog):
    client.force_login(api_world["account"])
    with caplog.at_level(logging.INFO, logger="sigab.request"):
        response = client.get("/api/v1/items/?q=segredo", headers={"X-Request-ID": "req-1"})
    assert response["X-Request-ID"] == "req-1"
    record = next(r for r in caplog.records if r.name == "sigab.request")
    entry = _format(record)
    assert entry["correlation_id"] == "req-1"
    assert entry["path"] == "/api/v1/items/"
    assert entry["status"] == 200
    assert entry["account_id"] == str(api_world["account"].id)
    assert "segredo" not in json.dumps(entry)


@pytest.mark.parametrize("header", ["a" * 65, "linha\nnova", "com espaço"])
@pytest.mark.django_db
def test_unsafe_request_id_is_replaced(client, header):
    response = client.get("/api/v1/session/", headers={"X-Request-ID": header})
    assert response["X-Request-ID"] != header
    assert len(response["X-Request-ID"]) == 36


@pytest.mark.django_db
def test_login_does_not_log_password(client, api_world, caplog):
    with caplog.at_level(logging.DEBUG):
        client.post("/entrar/", {"username": "operador-api", "password": "Senha-errada-999"})
    rendered = "\n".join(JsonFormatter().format(record) for record in caplog.records)
    assert "Senha-errada-999" not in rendered


@pytest.mark.parametrize("name", ["", "django", "django.request", "django.security.csrf"])
def test_every_django_log_line_is_json(name):
    logger = logging.getLogger(name)
    while logger and not logger.handlers:
        logger = logger.parent if logger.propagate else None
    assert logger is not None
    # pytest adds its own capture handlers; check only the ones configured in settings.
    configured = [h for h in logger.handlers if type(h).__module__ == "logging"]
    assert configured
    for handler in configured:
        assert isinstance(handler.formatter, JsonFormatter)
