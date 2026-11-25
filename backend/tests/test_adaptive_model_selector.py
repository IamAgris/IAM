"""Tests for hardware-aware adaptive model selection (OD-39 / OD-41)."""

from app.core.config import settings
from app.services.adaptive_model_selector import AdaptiveModelSelector, ResourceSnapshot

ALL = {
    settings.adaptive_tiny_model,
    settings.adaptive_small_model,
    settings.adaptive_standard_model,
    settings.adaptive_large_model,
}


def snapshot(available_mb: int) -> ResourceSnapshot:
    return ResourceSnapshot(
        total_ram_mb=available_mb,
        available_ram_mb=available_mb,
        cpu_count=4,
        has_gpu=False,
        source="test",
    )


def test_simple_text_uses_smallest_capable_model():
    decision = AdaptiveModelSelector(snapshot(1000)).select(1, ALL)
    assert decision["tier"] == "0.5b"
    assert decision["delegate"] is False
    assert decision["context_tokens"] == 1024


def test_light_coding_uses_1_5b():
    decision = AdaptiveModelSelector(snapshot(3000)).select(2, ALL)
    assert decision["tier"] == "1.5b"
    assert decision["context_tokens"] == 2048


def test_regular_coding_uses_locked_3b_baseline():
    decision = AdaptiveModelSelector(snapshot(6000)).select(3, ALL)
    assert decision["tier"] == "3b"
    assert decision["model"] == "local-qwen-3b"
    assert decision["max_concurrent"] == 1


def test_complex_coding_uses_7b_when_ram_allows():
    decision = AdaptiveModelSelector(snapshot(9000)).select(4, ALL)
    assert decision["tier"] == "7b"


def test_complexity_beyond_local_delegates():
    decision = AdaptiveModelSelector(snapshot(16000)).select(5, ALL)
    assert decision["delegate"] is True
    assert decision["model"] == settings.adaptive_delegate_model
    assert "capability" in decision["reason"]


def test_low_ram_delegates_instead_of_loading_3b():
    decision = AdaptiveModelSelector(snapshot(1000)).select(
        3, {settings.adaptive_standard_model}
    )
    assert decision["delegate"] is True
    assert "RAM" in decision["reason"]


def test_core_services_reserve_is_protected():
    # 2000 MB available minus 1500 MB reserve = 500 MB usable: 3B must not load.
    selector = AdaptiveModelSelector(snapshot(2000))
    assert selector.usable_ram_mb == 500
    decision = selector.select(3, {settings.adaptive_standard_model})
    assert decision["delegate"] is True


def test_unavailable_alias_never_selected():
    decision = AdaptiveModelSelector(snapshot(9000)).select(
        3, {settings.adaptive_tiny_model}
    )
    # Tiny cannot handle complexity 3, so delegation is required.
    assert decision["delegate"] is True
