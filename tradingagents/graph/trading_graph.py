from typing import Dict, Any, List, Optional

from tradingagents.default_config import DEFAULT_CONFIG
from .setup import GraphSetup
from .propagation import Propagator

DEFAULT_ANALYSTS = ["market", "social", "news", "fundamentals"]


class TradingAgentsGraph:
    """Main class that orchestrates the trading agents framework."""

    def __init__(
        self,
        selected_analysts=None,
        debug=False,
        config: Dict[str, Any] = None,
        callbacks: Optional[List] = None,
    ):
        if selected_analysts is None:
            selected_analysts = DEFAULT_ANALYSTS.copy()

        self.debug = debug
        self.config = config or DEFAULT_CONFIG
        self.callbacks = callbacks or []

        self.graph_setup = GraphSetup(None, None, {}, None)

        self.propagator = Propagator(
            max_recur_limit=self.config.get("max_recur_limit", 100)
        )

        self.workflow = self.graph_setup.setup_graph(selected_analysts)
        self.graph = self.workflow.compile()
