"""Record map only (no predicates or quantities needed for this contract)."""

# Record map (spec 6.4): the scorer's combined_score for a construction whose ratio_squared equals v.
maps = {"score_from_ratio_squared": lambda v: (1.0 / v) / (1 / 12.889266112)}
