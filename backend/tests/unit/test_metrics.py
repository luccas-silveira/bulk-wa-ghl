# backend/tests/unit/test_metrics.py
"""Unit tests for business Prometheus metrics (ANA-09)."""
from prometheus_client import Counter, Gauge


class TestBusinessMetrics:
    def test_messages_sent_total_is_counter(self):
        from src.metrics import messages_sent_total
        assert isinstance(messages_sent_total, Counter)

    def test_messages_sent_total_has_status_label(self):
        from src.metrics import messages_sent_total
        sample = messages_sent_total.labels(status='sent')
        assert sample is not None

    def test_campaigns_active_gauge_is_gauge(self):
        from src.metrics import campaigns_active_gauge
        assert isinstance(campaigns_active_gauge, Gauge)


class TestExecutorCounterIncrement:
    def test_counter_import_available_in_executor_module(self):
        """messages_sent_total must be importable from executor (verifies wiring)."""
        import src.services.campaign_executor_service as mod
        assert hasattr(mod, 'messages_sent_total')
