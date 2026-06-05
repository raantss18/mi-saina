"""
Tests de l'adaptation de num_ctx à la VRAM libre (#79).
sysinfo.recommended_num_ctx + llm.num_ctx (toggle NUM_CTX_AUTO).
"""
import pytest

from services import sysinfo, llm
from config import settings


@pytest.mark.parametrize("free, ceiling, expected", [
    (6000, 8192, 8192),   # VRAM large → plafond
    (4000, 8192, 8192),   # >=3500 → min(ceiling, 8192)
    (4000, 4096, 4096),   # plafond plus bas respecté
    (3000, 8192, 4096),   # >=2200
    (2000, 8192, 2048),   # >=1300
    (800,  8192, 1024),   # très faible → plancher
])
def test_recommended_num_ctx_mapping(monkeypatch, free, ceiling, expected):
    monkeypatch.setattr(sysinfo, "free_vram_mb", lambda *a, **k: free)
    assert sysinfo.recommended_num_ctx(ceiling) == expected


def test_unknown_vram_keeps_ceiling(monkeypatch):
    monkeypatch.setattr(sysinfo, "free_vram_mb", lambda *a, **k: None)
    assert sysinfo.recommended_num_ctx(8192) == 8192


def test_never_below_floor(monkeypatch):
    monkeypatch.setattr(sysinfo, "free_vram_mb", lambda *a, **k: 100)
    assert sysinfo.recommended_num_ctx(8192, floor=1024) == 1024


class TestLlmNumCtx:
    def test_fixed_when_auto_off(self, monkeypatch):
        monkeypatch.setattr(settings, "NUM_CTX_AUTO", False)
        monkeypatch.setattr(settings, "NUM_CTX", 6000)
        assert llm.num_ctx() == 6000

    def test_uses_recommended_when_auto_on(self, monkeypatch):
        monkeypatch.setattr(settings, "NUM_CTX_AUTO", True)
        monkeypatch.setattr(settings, "NUM_CTX", 8192)
        # VRAM faible → réduit sous le plafond
        monkeypatch.setattr(llm, "recommended_num_ctx", lambda ceiling: min(ceiling, 2048))
        assert llm.num_ctx() == 2048


def test_free_vram_is_cached(monkeypatch):
    """free_vram_mb met en cache (n'appelle pas la sonde à chaque token)."""
    calls = {"n": 0}
    def fake_query():
        calls["n"] += 1
        return 4242
    monkeypatch.setattr(sysinfo, "_query_free_vram_mb", fake_query)
    sysinfo._vram_cache.update(t=0.0, mb=None)   # invalider le cache
    a = sysinfo.free_vram_mb()
    b = sysinfo.free_vram_mb()
    assert a == b == 4242
    assert calls["n"] == 1     # 2e appel servi par le cache
