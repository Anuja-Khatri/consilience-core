"""From the source records' strings to IRIs.

The ledger and the cross-theory demo store axes, conditions, units, techniques, theories
and positions as snake_case strings. A nanopublication carries IRIs instead, so that the
same condition or axis can be queried across records. Every table here is closed: a
string with no IRI is refused with a named reason, never guessed. The choice of each
IRI (reused vocabulary or a minted ``cv`` term) is documented in ``docs/VOCABULARY.md``.
"""

from __future__ import annotations

from rdflib import URIRef

from .vocab import CV, OBO, UNIT, WD


class MappingError(ValueError):
    """A source string has no IRI in the closed tables. The message names it."""


def iri(table: dict, key, what: str) -> URIRef:
    try:
        v = table[key]
    except (KeyError, TypeError):
        v = None
    if v is None:
        raise MappingError(f"no_iri_for_{what}: {key!r}")
    return v


# --- consilience-ledger (electrocatalysis) ---------------------------------------------

AXES = {
    "operational_stability_duration": CV.OperationalStabilityDuration,
    "hours_to_threshold": CV.HoursToThreshold,
    "overpotential_at_current_density": CV.OverpotentialAtCurrentDensity,
    "cell_voltage_at_current_density": CV.CellVoltageAtCurrentDensity,
    "mass_activity": CV.MassActivity,
}

CONDITIONS = {
    "current_density": CV.CurrentDensity,
    "electrolyte": CV.Electrolyte,
    "temperature": CV.Temperature,
    "ir_correction": CV.IRCorrection,
    "prior_operation_duration": CV.PriorOperationDuration,
    "anneal_temperature": CV.AnnealTemperature,
    "loading": CV.CatalystLoading,
    "ph": CV.PH,
    "protocol_tier": CV.ProtocolTier,
    "substrate": CV.Substrate,
}

# Units as the ledger writes them (after its own spelling normalisation).
UNITS = {
    "h": UNIT.HR,
    "V": UNIT.V,
    "mV": UNIT.MilliV,
    "A/g": UNIT["A-PER-GM"],
    "A/cm^2": UNIT["A-PER-CentiM2"],
    "mA/cm^2": CV["MilliA-PER-CentiM2"],   # QUDT has no mA/cm²; see vocab/cv.ttl
    "mol/L": UNIT["MOL-PER-L"],
    "degC": UNIT.DEG_C,
}

BOUNDS = {
    "exact": CV.ExactValue,
    "approx": CV.ApproximateValue,
    "lower": CV.LowerBound,
    "upper": CV.UpperBound,
}

CLAIM_KINDS = {"performance_value": CV.PerformanceValue, "stability_value": CV.StabilityValue}

MEASURABILITY = {"measurable_now": CV.MeasurableNow}

TECHNIQUES = {
    "cp_chronopotentiometry": OBO.CHMO_0000017,   # CHMO "chrono-potentiometry"
    "polarization_curve": CV.PolarizationCurve,
    "cv_or_lsv": CV.CVOrLSV,
    "rde_mass_activity": CV.RDEMassActivity,
}

# Electrolyte identities, matched without case. Only identities checked against ChEBI are
# listed; any other electrolyte is refused until it is added here.
ELECTROLYTES = {"hclo4": OBO.CHEBI_29221}   # ChEBI "perchloric acid"

NORMALIZATIONS = {"geometric": CV.GeometricArea}

IR_CORRECTION = {False: CV.NotIRCorrected, True: CV.IRCorrected}

# --- the cross-theory demo (consciousness science) -------------------------------------

THEORIES = {
    "IIT": WD.Q6042884,                     # Wikidata "integrated information theory"
    "GNWT": CV.GlobalNeuronalWorkspaceTheory,
}

DIMENSIONS = {
    "locus": CV.Locus,
    "temporal_profile": CV.TemporalProfile,
    "connectivity": CV.Connectivity,
}

POSITIONS = {
    "single_maximal_complex": CV.SingleMaximalComplex,
    "maximal_irreducible_complex": CV.MaximalIrreducibleComplex,
    "intrinsic_not_broadcast": CV.IntrinsicNotBroadcast,
    "posterior_hot_zone": CV.PosteriorHotZone,
    "prefrontal_parietal_cortical_network": CV.PrefrontalParietalCorticalNetwork,
    "sustained_maintenance": CV.SustainedMaintenance,
    "late_onset_threshold": CV.LateOnsetThreshold,
    "gradual_buildup": CV.GradualBuildup,
    "serial_all_or_none": CV.SerialAllOrNone,
    "heterogeneous_connectivity_required": CV.HeterogeneousConnectivityRequired,
    "global_workspace_connectivity_required": CV.GlobalWorkspaceConnectivityRequired,
}

OBSERVABLES = {
    "regional_decoding": CV.RegionalDecoding,
    "connectivity_metrics": CV.ConnectivityMetrics,
    "ignition_signature": CV.IgnitionSignature,
    "temporal_generalization": CV.TemporalGeneralization,
}

POLARITY = {"asserts": CV.Asserts, "denies": CV.Denies}


def quantity_conditions(name: str, value) -> list[tuple[str, object]]:
    """Split one ledger condition into the nodes a claim card states.

    Returns a list of ``("quantity", (condition_iri, number, unit_iri))`` and
    ``("categorical", (condition_iri, value_iri))`` items. Anything not covered raises
    ``MappingError``.
    """
    cond = iri(CONDITIONS, name, "condition")
    out: list[tuple[str, object]] = []

    def qty(c, v, what):
        if not isinstance(v, dict) or set(v) != {"unit", "value"}:
            raise MappingError(f"unsupported_condition_value: {what}={v!r}")
        num = v["value"]
        if isinstance(num, bool) or not isinstance(num, (int, float)):
            raise MappingError(f"non_numeric_condition_value: {what}={num!r}")
        return ("quantity", (c, num, iri(UNITS, v["unit"], "unit")))

    if name == "current_density":
        if not isinstance(value, dict) or set(value) != {"normalization", "unit", "value"}:
            raise MappingError(f"unsupported_condition_value: {name}={value!r}")
        out.append(qty(cond, {"unit": value["unit"], "value": value["value"]}, name))
        out.append(("categorical", (CV.CurrentDensityNormalization,
                                    iri(NORMALIZATIONS, value["normalization"], "normalization"))))
    elif name == "electrolyte":
        if not isinstance(value, dict) or "identity" not in value or set(value) - {"identity", "concentration"}:
            raise MappingError(f"unsupported_condition_value: {name}={value!r}")
        ident = str(value["identity"]).lower()
        out.append(("categorical", (cond, iri(ELECTROLYTES, ident, "electrolyte"))))
        if value.get("concentration") is not None:
            out.append(qty(CV.ElectrolyteConcentration, value["concentration"], "electrolyte.concentration"))
    elif name == "ir_correction":
        if not isinstance(value, bool):
            raise MappingError(f"unsupported_condition_value: {name}={value!r}")
        out.append(("categorical", (cond, IR_CORRECTION[value])))
    else:
        out.append(qty(cond, value, name))
    return out
