"""`consilience stress`: check scoring code before you optimise against it.

Needs numpy: ``pip install consilience[stress]``. See docs/stress.md and the product spec.
"""
from .contract import Contract, ContractError, load_contract  # noqa: F401
