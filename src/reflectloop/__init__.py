"""reflectloop: calibrated benefit-gated reflection for scripted agents.

Reflect only when a benefit model, fit on calibration counterfactuals,
predicts reflection will help. See README.md and PAPER.md.
"""

from .gate import BenefitGate, RawConfidenceGate
from .tasks import FAMILIES, Task, generate_tasks

__version__ = "0.1.0"
__all__ = ["BenefitGate", "RawConfidenceGate", "FAMILIES", "Task",
           "generate_tasks"]
