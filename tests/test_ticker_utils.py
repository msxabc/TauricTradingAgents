import pytest

from tradingagents.research.ticker_utils import (
    TickerValidationError,
    normalize_research_ticker,
)


@pytest.mark.unit
class TestResearchTickerNormalization:
    def test_strips_spaces_and_leading_dollar(self):
        assert normalize_research_ticker(" $spy ") == "SPY"

    def test_preserves_exchange_suffix(self):
        assert normalize_research_ticker(" cnc.to ") == "CNC.TO"

    def test_rejects_empty_input(self):
        with pytest.raises(TickerValidationError):
            normalize_research_ticker("   ")

    def test_rejects_path_escape_input(self):
        with pytest.raises(TickerValidationError):
            normalize_research_ticker("../../etc/passwd")
