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
