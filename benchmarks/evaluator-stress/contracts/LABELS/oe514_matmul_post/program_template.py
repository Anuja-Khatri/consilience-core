# Adapter template written for this contract (not vendored code). The scorer calls run() and unpacks
# (decomposition, n, m, p, loss, rank) with decomposition = (U, V, W); the stress harness generates a
# flat loader, _consilience_flat(), between the markers below, returning the contract's `returns`
# fields in order. run() regroups them; it does nothing else.
# EVOLVE-BLOCK-START
# EVOLVE-BLOCK-END


def run():
    U, V, W, n, m, p, loss, rank = _consilience_flat()
    return (U, V, W), n, m, p, loss, rank
