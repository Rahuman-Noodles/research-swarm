"""Research Swarm - a tiny multi-agent research orchestrator."""

__version__ = "0.1.0"

from .config import SwarmConfig, ANGLE_PRESETS, DEPTH_PRESETS
from .orchestrator import run_swarm, SwarmResult

__all__ = ["SwarmConfig", "ANGLE_PRESETS", "DEPTH_PRESETS", "run_swarm", "SwarmResult", "__version__"]
