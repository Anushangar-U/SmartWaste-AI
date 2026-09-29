"""Deterministic citizen-facing safety and disposal guidance.

This module is deliberately conservative. It does not diagnose injuries or replace
emergency, poison-control, manufacturer, or local-authority instructions.
"""
from __future__ import annotations

from backend.schemas import CitizenGuidance, StructuredIntake


SOURCES = {
    "cea_ewaste": {
        "source_id": "cea-ekunu-2026",
        "title": "Strengthening National E-Waste Management for a Sustainable Future",
        "issuer": "Central Environmental Authority, Sri Lanka",
        "url": "https://cea.lk/web/news-and-events/1854-strengthening-national-e-waste-management-for-a-sustainable-future?lang=en",
    },
    "cdc_tetanus": {
        "source_id": "cdc-tetanus-wound-guidance",
        "title": "Clinical Guidance for Wound Management to Prevent Tetanus",
        "issuer": "U.S. Centers for Disease Control and Prevention",
        "url": "https://www.cdc.gov/tetanus/hcp/clinical-guidance/index.html",
    },
    "who_chemical": {
        "source_id": "who-chemical-release-first-aid",
        "title": "Chemical release: questions and answers",
        "issuer": "World Health Organization",
        "url": "https://www.who.int/news-room/questions-and-answers/item/deliberate-events-chemical-release",
    },
    "who_chemical_manual": {
        "source_id": "who-chemical-incidents-2009",
        "title": "Manual for the Public Health Management of Chemical Incidents",
        "issuer": "World Health Organization",
        "url": None,
    },
    "who_toxic_prevention": {
        "source_id": "who-toxic-exposure-prevention-2004",
        "title": "Guidelines on the prevention of toxic exposures",
        "issuer": "World Health Organization / ILO / UNEP",
        "url": None,
    },
    "who_healthcare_summary": {
        "source_id": "who-healthcare-waste-summary-2017",
        "title": "Safe management of wastes from health-care activities: A summary",
        "issuer": "World Health Organization",
        "url": None,
    },
    "cea_scheduled": {
        "source_id": "lk-cea-scheduled-waste-2009",
        "title": "Guidelines for the Management of Scheduled Waste in Sri Lanka",
        "issuer": "Central Environmental Authority, Sri Lanka",
        "url": None,
    },
    "cea_lead_battery": {
        "source_id": "lk-cea-lead-acid-battery-2005",
        "title": "Technical Guidelines on Management of Used Lead Acid Batteries",
        "issuer": "Central Environmental Authority, Sri Lanka",
        "url": None,
    },
    "cea_ev_battery": {
        "source_id": "lk-cea-ev-lithium-battery",
        "title": "Guideline on Importation and Disposal of Used Lithium-Ion Batteries for Electric Vehicles in Sri Lanka",
        "issuer": "Central Environmental Authority, Sri Lanka",
        "url": None,
    },
    "epa_hhw": {
        "source_id": "epa-household-hazardous-waste",
        "title": "Household Hazardous Waste",
        "issuer": "U.S. Environmental Protection Agency",
        "url": "https://www.epa.gov/hw/household-hazardous-waste-hhw",
    },
    "epa_lithium": {
        "source_id": "epa-lithium-battery-safety",
        "title": "Used Lithium-Ion Batteries",
        "issuer": "U.S. Environmental Protection Agency",
        "url": "https://www.epa.gov/recycle/used-lithium-ion-batteries",
    },
}


def _labels(values):
    return [value.replace("_", " ") for value in values]


def structured_context(intake: dict | StructuredIntake | None) -> str | None:
    if not intake:
        return None
    data = intake if isinstance(intake, StructuredIntake) else StructuredIntake.model_validate(intake)
    return (
        "Reporter structured intake: "
        f"waste types={', '.join(_labels(data.waste_types))}; "
        f"specific items={data.specific_items}; "
        f"problem={data.problem_type.replace('_', ' ')}; "
        f"amount={data.amount.replace('_', ' ')}; "
        f"condition={data.condition.replace('_', ' ')}; "
        f"hazards={', '.join(_labels(data.hazards))}; "
        f"location type={data.location_type.replace('_', ' ')}; "
        f"public landmark={data.area_landmark}; "
        f"nearby={data.nearby_sensitive_place.replace('_', ' ')}; "
        f"placement={data.placement.replace('_', ' ')}; "
        f"duration={data.duration.replace('_', ' ')}; "
        f"recurrence={data.recurrence.replace('_', ' ')}; "
        f"impacts={', '.join(_labels(data.impacts))}; "
        f"reported exposure={data.exposure.replace('_', ' ')}; "
        f"material label={data.material_label}."
    )


def _add_unique(target, *items):
    for item in items:
        if item and item not in target:
            target.append(item)


def build_guidance(intake: dict | StructuredIntake) -> CitizenGuidance:
    data = intake if isinstance(intake, StructuredIntake) else StructuredIntake.model_validate(intake)
    waste = set(data.waste_types)
    hazards = set(data.hazards)

    precautions = []
    disposal = []
    exposed = []
    urgent = []
    do_not = []
    source_keys = []
    reasons = []
    risk = "routine"

    dangerous = bool(
        waste & {
            "medical_waste", "sharps_needles", "chemicals", "pesticides",
            "paint_solvent_oil_fuel", "batteries", "e_waste",
        }
        or hazards & {
            "sharps_needles", "rusty_sharp_metal", "medical_material",
            "chemical_container", "chemical_leak", "damaged_battery",
            "smoke_fire", "strong_fumes",
        }
        or data.condition in {"burning_smoking", "swollen_battery"}
    )
    if dangerous:
        risk = "high"
        _add_unique(precautions, "Keep people, children and pets away from the waste.")
        reasons.append("The report includes a potentially hazardous waste type, condition or visible hazard.")

    if waste & {"sharps_needles", "medical_waste"} or hazards & {
        "sharps_needles", "medical_material", "rusty_sharp_metal", "broken_glass"
    }:
        risk = "high"
        _add_unique(
            precautions,
            "Do not pick up exposed needles, sharps, broken glass or sharp metal with bare hands.",
            "Keep the area isolated until trained staff or an appropriate collection service can handle it.",
        )
        _add_unique(
            disposal,
            "Do not place exposed sharps loosely into an ordinary rubbish bag.",
            "Use an approved sharps or hazardous-waste collection route where available.",
        )
        _add_unique(
            do_not,
            "Do not bend, break or recap discarded needles.",
            "Do not deliberately handle rusty or contaminated sharp objects to inspect them.",
        )
        _add_unique(
            exposed,
            "If a cut or puncture occurred, clean the wound with running water and soap and remove visible dirt if this can be done safely.",
            "For a needlestick or contaminated sharp injury, seek prompt medical assessment because blood-borne infection and tetanus prevention may need to be considered.",
        )
        _add_unique(
            urgent,
            "Seek urgent medical care for severe or uncontrolled bleeding, a deep wound, an embedded object, loss of sensation or movement, or rapidly worsening symptoms.",
        )
        source_keys.extend(["who_healthcare_summary", "cdc_tetanus"])
        reasons.append("Sharp or medical waste can cause puncture, contamination and infection risks.")

    if waste & {"chemicals", "pesticides", "paint_solvent_oil_fuel"} or hazards & {
        "chemical_container", "chemical_leak", "strong_fumes"
    }:
        risk = "high"
        _add_unique(
            precautions,
            "Move away from leaking chemicals or strong fumes and keep other people away.",
            "If a product label or Safety Data Sheet is available without approaching the hazard, follow its emergency instructions.",
        )
        _add_unique(
            disposal,
            "Keep hazardous household chemicals in their original labelled containers when possible.",
            "Use an authorized hazardous-waste collection or disposal route rather than ordinary household rubbish.",
        )
        _add_unique(
            do_not,
            "Do not mix chemicals together.",
            "Do not pour unknown chemicals, solvents, pesticides, fuels or oils into drains, soil or waterways.",
            "Do not deliberately smell, taste or touch an unknown chemical to identify it.",
            "Do not attempt to neutralize an unknown spill unless qualified guidance specifically instructs you to do so.",
        )
        _add_unique(
            exposed,
            "Move away from the chemical source and avoid further contact.",
            "If skin or clothing is contaminated, remove contaminated clothing when it is safe to do so and rinse exposed skin with plenty of water.",
            "If eyes are exposed or irritated, rinse with clean water and seek medical advice.",
            "For inhalation, ingestion, significant skin/eye exposure, or an unknown chemical, contact emergency or medical services for chemical-specific advice.",
        )
        _add_unique(
            urgent,
            "Seek emergency help for breathing difficulty, collapse, severe burns, persistent eye pain, confusion, seizures, or significant exposure to an unknown chemical.",
        )
        source_keys.extend(["cea_scheduled", "who_chemical_manual", "who_toxic_prevention", "who_chemical", "epa_hhw"])
        reasons.append("Chemical exposure and disposal instructions can be substance-specific.")

    if waste & {"e_waste", "batteries"} or hazards & {"damaged_battery"} or data.condition == "swollen_battery":
        if risk == "routine":
            risk = "elevated"
        _add_unique(
            precautions,
            "Keep damaged, swollen or hot batteries away from heat, flames and combustible materials.",
            "Handle damaged batteries as little as possible and keep them separate from ordinary household waste.",
        )
        _add_unique(
            disposal,
            "Use a recognized e-waste or battery collection route instead of normal household rubbish.",
            "For intact removable batteries, keep terminals from contacting metal objects; use non-conductive tape or separate containment when appropriate.",
            "In Sri Lanka, use CEA-supported or other authorized e-waste collection channels.",
        )
        _add_unique(
            do_not,
            "Do not puncture, crush, dismantle, burn or intentionally short-circuit a battery.",
            "Do not put lithium-ion batteries in ordinary household rubbish or normal recycling bins.",
        )
        if data.condition == "swollen_battery" or "damaged_battery" in hazards:
            _add_unique(
                urgent,
                "If a battery is smoking, very hot, hissing or on fire, move away and contact emergency services rather than attempting to handle it.",
            )
        source_keys.extend(["cea_lead_battery", "cea_ev_battery", "epa_lithium", "cea_ewaste"])
        reasons.append("Electronic waste and batteries can contain hazardous materials and damaged lithium batteries can create fire risk.")

    if "smoke_fire" in hazards or data.condition == "burning_smoking" or data.problem_type == "burning":
        risk = "high"
        _add_unique(
            precautions,
            "Move away from smoke and keep others away from the burning waste.",
        )
        _add_unique(
            do_not,
            "Do not enter smoke or approach burning waste to identify the material.",
            "Do not burn waste as a disposal method.",
        )
        _add_unique(
            urgent,
            "Contact emergency services if there is an active uncontrolled fire, spreading smoke, explosions or immediate danger to people or buildings.",
        )
        reasons.append("Burning waste can expose people to heat, smoke and unknown combustion products.")

    if not dangerous:
        if data.nearby_sensitive_place in {"school", "hospital", "playground", "waterway", "storm_drain"}:
            risk = "elevated"
            _add_unique(
                precautions,
                "Keep the waste contained and away from children, drains and waterways where this can be done without handling hazardous material.",
            )
            reasons.append("The waste is reported near a sensitive place.")
        _add_unique(
            disposal,
            "Keep ordinary waste securely contained until the responsible collection service can remove it.",
            "Separate clearly recyclable or compostable material only when it is safe, clean and permitted by the local collection system.",
        )
        _add_unique(do_not, "Do not burn or dump waste into drains, waterways or public land.")

    if data.exposure not in {"none", "unknown"} and not exposed:
        _add_unique(
            exposed,
            "Stop further contact with the waste and seek appropriate medical advice if symptoms, injury or contamination occurred.",
        )
    if data.exposure not in {"none", "unknown"}:
        risk = "high"
        reasons.append("The reporter indicated that an exposure or injury may already have occurred.")

    source_records = [SOURCES[key] for key in dict.fromkeys(source_keys)]
    return CitizenGuidance(
        risk_level=risk,
        waste_summary=f"{', '.join(_labels(data.waste_types))}: {data.specific_items}",
        immediate_precautions=precautions,
        disposal_steps=disposal,
        if_exposed=exposed,
        seek_urgent_help=urgent,
        do_not=do_not,
        reason=" ".join(dict.fromkeys(reasons)) or "Guidance is based on the structured complaint details.",
        sources=source_records,
    )
