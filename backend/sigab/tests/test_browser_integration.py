"""Opt-in real browser/API/PostgreSQL journey; no mutation of the development database."""

import json
import os
import shutil
import socket
import subprocess
import time
from pathlib import Path
from urllib.request import urlopen

import pytest
from django.db import connection

from sigab.models import ServiceBatch, StockBalance, StockLedgerEntry, StockLoan
from sigab.tests.test_requirements_063_070 import _enable_inventory_approval, _quantitative_stock


@pytest.mark.django_db(transaction=True)
@pytest.mark.skipif(
    os.getenv("SIGAB_BROWSER_INTEGRATION") != "1", reason="Ensaio de navegador opt-in."
)
def test_real_browser_quantitative_journey(world, client, live_server):
    assert connection.vendor == "postgresql", "Este ensaio exige PostgreSQL."
    assert shutil.which("bun"), "Bun e Chromium do Playwright precisam estar instalados."
    _enable_inventory_approval(world)
    kind, _ = _quantitative_stock(world, "0")
    kind.name = "Munição integração"
    kind.save()
    client.force_login(world["account"])
    frontend = Path(__file__).resolve().parents[3] / "frontend"
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    origin = f"http://127.0.0.1:{port}"
    env = {
        **os.environ,
        "SIGAB_BACKEND_URL": live_server.url,
        "SIGAB_BROWSER_FIXTURE": json.dumps(
            {
                "origin": origin,
                "username": world["account"].username,
                "password": "Senha-forte-123",
                "person": str(world["person"].id),
                "kind": str(kind.id),
                "unit": str(world["unit"].id),
                "location": str(world["location"].id),
            }
        ),
    }
    server = subprocess.Popen(
        ["bun", "run", "dev", "--host", "127.0.0.1", "--port", str(port), "--strictPort"],
        cwd=frontend,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(100):
            try:
                with urlopen(origin, timeout=1):
                    break
            except OSError:
                assert server.poll() is None, "Vite encerrou antes de iniciar."
                time.sleep(0.1)
        else:
            pytest.fail("Vite não iniciou no prazo.")
        result = subprocess.run(
            ["bun", "integration/stock-journey.mjs"],
            cwd=frontend,
            env=env,
            capture_output=True,
            text=True,
            timeout=90,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert ServiceBatch.objects.count() == 1
        assert StockLoan.objects.get().open_quantity == 20
        assert StockBalance.objects.get().quantity == 70
        assert list(
            StockLedgerEntry.objects.order_by("occurred_at").values_list("entry_type", flat=True)
        ) == ["receipt", "checkout", "return", "consume"]
    finally:
        server.terminate()
        server.wait(timeout=10)
