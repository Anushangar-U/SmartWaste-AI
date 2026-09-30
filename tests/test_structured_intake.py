import copy
import unittest

from tests.test_auth_api import AuthApiTests
from backend.repositories import complaints as repo


VALID_INTAKE = {
    "waste_types": ["e_waste", "batteries"],
    "specific_items": "Old laptop with a swollen removable battery",
    "problem_type": "abandoned_electronics",
    "amount": "single_item",
    "condition": "swollen_battery",
    "hazards": ["damaged_battery"],
    "location_type": "residential",
    "area_landmark": "Public library gate",
    "nearby_sensitive_place": "residential_homes",
    "placement": "roadside",
    "duration": "one_to_three_days",
    "recurrence": "first_occurrence",
    "impacts": ["people_children_nearby"],
    "exposure": "none",
    "material_label": "Unknown",
}


class StructuredComplaintApiTests(unittest.TestCase):
    setUp = AuthApiTests.setUp

    def test_missing_structured_fields_are_rejected(self):
        response = self.client.post(
            "/complaints/structured",
            json={"text": "A detailed complaint description long enough to validate.", "intake": {}},
        )
        self.assertEqual(response.status_code, 422)

    def test_inconsistent_hazard_answers_are_rejected(self):
        intake = copy.deepcopy(VALID_INTAKE)
        intake["hazards"] = ["none_observed", "damaged_battery"]
        response = self.client.post(
            "/complaints/structured",
            json={"text": "An abandoned laptop has a visibly swollen battery beside the road.", "intake": intake},
        )
        self.assertEqual(response.status_code, 422)

    def test_structured_submission_persists_inputs_and_returns_specific_guidance(self):
        response = self.client.post(
            "/complaints/structured",
            json={"text": "An abandoned laptop has a visibly swollen battery beside the road.", "intake": VALID_INTAKE},
            headers={"Idempotency-Key": "structured-test-key-0001"},
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertTrue(data["tracking_id"].startswith("WM-"))
        self.assertEqual(data["guidance"]["risk_level"], "high")
        self.assertTrue(any("e-waste" in item.lower() or "battery" in item.lower()
                            for item in data["guidance"]["disposal_steps"]))
        self.assertTrue(any(source["source_id"] == "cea-ekunu-2026"
                            for source in data["guidance"]["sources"]))

        case = repo.track(data["tracking_id"])
        self.assertEqual(case["structured_intake"]["condition"], "swollen_battery")
        self.assertEqual(case["structured_intake"]["area_landmark"], "Public library gate")
        self.assertIsNotNone(case["citizen_guidance"])
        self.assertIn("Reporter structured intake:", case["retrieval"]["query"])

    def test_tracking_returns_guidance_but_not_full_private_case(self):
        created = self.client.post(
            "/complaints/structured",
            json={"text": "An abandoned laptop has a visibly swollen battery beside the road.", "intake": VALID_INTAKE},
        ).json()
        tracked = self.client.get("/complaints/track/" + created["tracking_id"])
        self.assertEqual(tracked.status_code, 200)
        body = tracked.json()
        self.assertIn("guidance", body)
        self.assertNotIn("structured_intake", body)
        self.assertNotIn("text", body)
        self.assertNotIn("citizen_guidance", body)

    def test_rusty_sharp_and_exposure_guidance_is_conservative(self):
        intake = copy.deepcopy(VALID_INTAKE)
        intake.update({
            "waste_types": ["metal_sharp"],
            "specific_items": "Rusty metal sheet with a sharp exposed edge",
            "problem_type": "illegal_dumping",
            "condition": "damaged_broken",
            "hazards": ["rusty_sharp_metal"],
            "exposure": "cut_or_puncture",
            "material_label": "Unknown",
        })
        response = self.client.post(
            "/complaints/structured",
            json={"text": "A person was cut by a sharp rusty metal sheet left near the road.", "intake": intake},
        )
        self.assertEqual(response.status_code, 201)
        guidance = response.json()["guidance"]
        self.assertTrue(any("tetanus" in item.lower() for item in guidance["if_exposed"]))
        self.assertTrue(any(source["source_id"] == "cdc-tetanus-wound-guidance"
                            for source in guidance["sources"]))

    def test_leaking_battery_guidance_covers_exposure_and_cea_handover(self):
        intake = copy.deepcopy(VALID_INTAKE)
        intake.update({
            "waste_types": ["batteries"],
            "specific_items": "Leaking used lead-acid vehicle battery",
            "problem_type": "leaking_spill",
            "condition": "leaking",
            "hazards": ["damaged_battery"],
            "exposure": "skin_contact",
            "material_label": "Lead-acid battery",
        })
        response = self.client.post(
            "/complaints/structured",
            json={"text": "A used lead-acid battery is leaking liquid beside the roadside.", "intake": intake},
        )
        self.assertEqual(response.status_code, 201)
        guidance = response.json()["guidance"]
        self.assertEqual(guidance["risk_level"], "high")
        self.assertTrue(any("registered collector" in item.lower() or "licensed recycler" in item.lower()
                            for item in guidance["immediate_precautions"]))
        self.assertTrue(any("rinse" in item.lower() and "water" in item.lower()
                            for item in guidance["if_exposed"]))
        self.assertTrue(any("do not drain" in item.lower()
                            for item in guidance["disposal_steps"]))
        self.assertTrue(any(source["source_id"] == "lk-cea-lead-acid-battery-2005"
                            for source in guidance["sources"]))

    def test_unknown_chemical_guidance_avoids_guessing(self):
        intake = copy.deepcopy(VALID_INTAKE)
        intake.update({
            "waste_types": ["chemicals"],
            "specific_items": "Unlabelled leaking chemical container",
            "problem_type": "leaking_spill",
            "condition": "leaking",
            "hazards": ["chemical_leak", "strong_fumes"],
            "exposure": "inhalation",
            "material_label": "Unknown",
        })
        response = self.client.post(
            "/complaints/structured",
            json={"text": "An unknown chemical container is leaking and producing strong fumes.", "intake": intake},
        )
        self.assertEqual(response.status_code, 201)
        guidance = response.json()["guidance"]
        self.assertEqual(guidance["risk_level"], "high")
        self.assertTrue(any("do not mix" in item.lower() for item in guidance["do_not"]))
        self.assertTrue(any("unknown chemical" in item.lower() for item in guidance["seek_urgent_help"]))


if __name__ == "__main__":
    unittest.main()
