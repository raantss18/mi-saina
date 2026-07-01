"""Sécurité des origines : anti-CSWSH (WebSocket) et anti-CSRF (HTTP).

Le backend exécute des commandes shell → un site web malveillant ouvert dans un
navigateur local ne doit pas pouvoir l'atteindre. Seules les origines locales et
l'appli desktop (tauri) sont autorisées ; l'absence d'origine (app native / CLI)
est tolérée.
"""
import pytest

from routers.chat import _origin_allowed as ws_allowed
from main import _origin_allowed as http_allowed


@pytest.mark.parametrize("check", [ws_allowed, http_allowed])
class TestOriginAllowed:
    def test_no_origin_allowed(self, check):
        assert check(None) is True
        assert check("") is True

    def test_localhost_allowed(self, check):
        assert check("http://localhost:3001") is True
        assert check("http://127.0.0.1:8000") is True
        assert check("http://localhost") is True

    def test_tauri_app_allowed(self, check):
        assert check("tauri://localhost") is True
        assert check("http://tauri.localhost") is True

    def test_remote_origin_blocked(self, check):
        assert check("https://evil.com") is False
        assert check("http://attacker.example") is False
        # Tentative de contournement par sous-domaine ressemblant
        assert check("http://localhost.evil.com") is False
        assert check("https://127.0.0.1.evil.com") is False


class TestHostAllowed:
    """Anti-DNS-rebinding : une page distante peut faire pointer son domaine sur
    127.0.0.1 et requêter « son » origine SANS header Origin (GET no-cors,
    EventSource) — seul le Host la trahit. Il doit donc être validé."""

    def setup_method(self):
        from security import host_allowed
        self.check = host_allowed

    def test_local_hosts_allowed(self):
        assert self.check("localhost") is True
        assert self.check("localhost:8000") is True
        assert self.check("127.0.0.1:8000") is True
        assert self.check("::1") is True
        assert self.check("[::1]:8000") is True
        assert self.check("tauri.localhost") is True
        assert self.check("LOCALHOST:8000") is True

    def test_rebound_host_blocked(self):
        assert self.check("attacker.com") is False
        assert self.check("attacker.com:8000") is False
        assert self.check("localhost.evil.com") is False
        assert self.check(None) is False
        assert self.check("") is False

    def test_extra_allowed_hosts_setting(self, monkeypatch):
        from config import settings
        monkeypatch.setattr(settings, "EXTRA_ALLOWED_HOSTS", "mon-nas.lan, autre.lan")
        assert self.check("mon-nas.lan:8000") is True
        assert self.check("attacker.com") is False


class TestMiddlewareIntegration:
    """Le middleware HTTP doit appliquer les deux gardes sur toutes les routes."""

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from main import app
        with TestClient(app, base_url="http://localhost") as c:
            yield c

    def test_local_request_passes(self, client):
        assert client.get("/health").status_code == 200

    def test_rebound_host_rejected(self, client):
        r = client.get("/health", headers={"host": "attacker.com"})
        assert r.status_code == 403

    def test_remote_origin_rejected(self, client):
        r = client.get("/health", headers={"origin": "https://evil.com"})
        assert r.status_code == 403

    def test_update_apply_protected_from_rebinding(self, client):
        # /update/apply (GET, EventSource) déclenche une mise à jour logicielle :
        # c'est la cible type d'un DNS rebinding — le Host non local doit bloquer.
        r = client.get("/update/apply", headers={"host": "attacker.com"})
        assert r.status_code == 403
