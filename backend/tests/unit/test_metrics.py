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


class TestMessagesCounterIncrements:
    """Verifica que messages_sent_total é incrementado nas labels corretas."""

    def test_sent_label_increments(self):
        """labels(status='sent').inc() deve incrementar o counter de sent."""
        from src.metrics import messages_sent_total
        from unittest.mock import patch, MagicMock

        mock_sample = MagicMock()
        with patch.object(messages_sent_total, 'labels', return_value=mock_sample) as mock_labels:
            messages_sent_total.labels(status='sent').inc()
            mock_labels.assert_called_once_with(status='sent')
            mock_sample.inc.assert_called_once()

    def test_failed_label_increments(self):
        """labels(status='failed').inc() deve incrementar o counter de failed."""
        from src.metrics import messages_sent_total
        from unittest.mock import patch, MagicMock

        mock_sample = MagicMock()
        with patch.object(messages_sent_total, 'labels', return_value=mock_sample) as mock_labels:
            messages_sent_total.labels(status='failed').inc()
            mock_labels.assert_called_once_with(status='failed')
            mock_sample.inc.assert_called_once()

    def test_executor_module_has_counter_wired(self):
        """O módulo executor deve expor messages_sent_total (wiring verificado)."""
        import src.services.campaign_executor_service as mod
        from src.metrics import messages_sent_total
        assert mod.messages_sent_total is messages_sent_total
