"""`consilience stress`: check scoring code before you optimise against it.

Needs numpy: ``pip install consilience[stress]``. See docs/stress.md and the product spec.
"""
from .contract import Contract, ContractError, load_contract  # noqa: F401
from .checks import StressResult  # noqa: F401,E402
from .receipt import SCHEMA as STRESS_RECEIPT_SCHEMA, stress, steps_from_receipt, verify_stress  # noqa: F401,E402
