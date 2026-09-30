import copy
import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from backend.config import settings
from backend.repositories import complaints as complaint_repo
from backend.schemas import ImageAnalysisResult
from backend.services import vision
from tests import test_auth_api


def valid_intake():
    """Return a fresh, valid ordinary-waste structured intake payload."""
    return {
        "waste_types": ["household_mixed"],
        "specific_items": "Several household garbage bags",
        "problem_type": "uncollected",
        "amount": "medium",
        "condition": "mixed",
        "hazards": ["none_observed"],
        "location_type": "residential",
        "area_landmark": "Public library gate",
        "nearby_sensitive_place": "residential_homes",
        "placement": "roadside",
        "duration": "one_to_three_days",
        "recurrence": "first_occurrence",
        "impacts": ["bad_smell"],
        "exposure": "none",
        "material_label": "Unknown",
    }


def image_bytes(fmt="PNG"):
    """Generate a real in-memory image so photo validation is exercised."""
    buf = io.BytesIO()
    Image.new("RGB", (64, 48), "white").save(buf, format=fmt)
    return buf.getvalue()


class PreMergeAcceptanceTests(unittest.TestCase):
    """
    Pre-merge acceptance suite for:
      citizen intake -> agent processing -> human review -> assignment ->
      resolution -> public tracking

    It also covers hazardous guidance, validation, idempotency, photos,
    text/image conflicts, and vision-provider failure fallback.
    """

    def setUp(self):
        # Reuse the repository's own isolated test DB + FastAPI TestClient setup.
        test_auth_api.AuthApiTests.setUp(self)

        # Keep uploaded photos isolated inside the same temporary directory.
        upload_patch = patch.object(
            settings,
            "upload_dir",
            str(Path(self.tmp.name) / "uploads"),
        )
        upload_patch.start()
        self.addCleanup(upload_patch.stop)

        size_patch = patch.object(settings, "vision_max_image_mb", 5)
        size_patch.start()
        self.addCleanup(size_patch.stop)

        dimension_patch = patch.object(settings, "vision_max_dimension", 1800)
        dimension_patch.start()
        self.addCleanup(dimension_patch.stop)

    def submit_structured(self, intake=None, text=None, key=None):
        intake = intake or valid_intake()
        text = text or (
            "Several household garbage bags have not been collected "
            "beside the public library gate for two days."
        )
        headers = {"Idempotency-Key": key} if key else {}
        return self.client.post(
            "/complaints/structured",
            json={"text": text, "intake": intake},
            headers=headers,
        )

    def header(self, username, role):
        """Reuse the repository's existing test token/user helper."""
        return test_auth_api.AuthApiTests.header(self, username, role)

    def staff_header(self, username="premerge_staff"):
        return self.header(username, "staff")

    def find_case(self, tracking_id, headers):
        response = self.client.get("/staff/complaints", headers=headers)
        self.assertEqual(response.status_code, 200, response.text)
        matches = [
            case for case in response.json()
            if case["tracking_id"] == tracking_id
        ]
        self.assertEqual(len(matches), 1)
        return matches[0]

    # ------------------------------------------------------------------
    # 1. Health / readiness
    # ------------------------------------------------------------------

    def test_01_health_and_mock_readiness(self):
        health = self.client.get("/health")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json(), {"status": "ok"})

        ready = self.client.get("/ready")
        self.assertEqual(ready.status_code, 200, ready.text)
        self.assertTrue(ready.json()["ready"])
        self.assertEqual(ready.json()["mode"], "mock_demo")

    # ------------------------------------------------------------------
    # 2. Full citizen -> staff -> tracking lifecycle
    # ------------------------------------------------------------------

    def test_02_full_complaint_lifecycle_and_public_privacy(self):
        created = self.submit_structured()
        self.assertEqual(created.status_code, 201, created.text)

        receipt = created.json()
        tracking_id = receipt["tracking_id"]

        self.assertTrue(tracking_id.startswith("WM-"))
        self.assertEqual(receipt["status"], "awaiting_review")
        self.assertIn("history", receipt)
        self.assertIn("guidance", receipt)

        # Public tracking must work without authentication.
        tracked = self.client.get(f"/complaints/track/{tracking_id}")
        self.assertEqual(tracked.status_code, 200)
        public = tracked.json()

        # Private complaint/staff fields must never leak publicly.
        for forbidden in (
            "text",
            "structured_intake",
            "citizen_guidance",
            "review_reason",
            "resolution_note",
            "assignee",
            "analysis",
            "retrieval",
            "decision",
            "stored_path",
        ):
            self.assertNotIn(forbidden, public)

        headers = self.staff_header()
        case = self.find_case(tracking_id, headers)

        self.assertEqual(case["status"], "awaiting_review")
        self.assertTrue(case["requires_human_review"])

        # Human review / approval.
        reviewed = self.client.post(
            f"/staff/complaints/{case['id']}/review",
            headers=headers,
            json={
                "version": case["version"],
                "decision": "approve",
                "reason": "Pre-merge acceptance: evidence reviewed by staff.",
            },
        )
        self.assertEqual(reviewed.status_code, 200, reviewed.text)
        reviewed_case = reviewed.json()
        self.assertEqual(reviewed_case["status"], "reviewed")

        # Assignment.
        assigned = self.client.post(
            f"/staff/complaints/{case['id']}/assign",
            headers=headers,
            json={
                "version": reviewed_case["version"],
                "assignee": "Collection Team A",
            },
        )
        self.assertEqual(assigned.status_code, 200, assigned.text)
        assigned_case = assigned.json()
        self.assertEqual(assigned_case["status"], "assigned")

        # Resolution.
        resolved = self.client.post(
            f"/staff/complaints/{case['id']}/resolve",
            headers=headers,
            json={
                "version": assigned_case["version"],
                "note": "Waste removed during pre-merge acceptance test.",
            },
        )
        self.assertEqual(resolved.status_code, 200, resolved.text)
        self.assertEqual(resolved.json()["status"], "resolved")

        # Citizen should now see resolved status but not the private resolution note.
        tracked_again = self.client.get(f"/complaints/track/{tracking_id}")
        self.assertEqual(tracked_again.status_code, 200)
        public_after = tracked_again.json()
        self.assertEqual(public_after["status"], "resolved")
        self.assertNotIn("resolution_note", public_after)

        history_statuses = [event["status"] for event in public_after["history"]]
        self.assertIn("submitted", history_statuses)
        self.assertIn("reviewed", history_statuses)
        self.assertIn("assigned", history_statuses)
        self.assertIn("resolved", history_statuses)

    # ------------------------------------------------------------------
    # 3. Hazardous complaint guidance
    # ------------------------------------------------------------------

    def test_03_leaking_lead_acid_battery_guidance(self):
        intake = valid_intake()
        intake.update({
            "waste_types": ["batteries"],
            "specific_items": "Leaking used lead-acid vehicle battery",
            "problem_type": "leaking_spill",
            "amount": "single_item",
            "condition": "leaking",
            "hazards": ["damaged_battery"],
            "exposure": "skin_contact",
            "material_label": "Lead-acid battery",
        })

        response = self.submit_structured(
            intake=intake,
            text=(
                "A used lead-acid vehicle battery is leaking liquid beside "
                "the roadside and someone may have touched the liquid."
            ),
        )
        self.assertEqual(response.status_code, 201, response.text)

        guidance = response.json()["guidance"]
        self.assertEqual(guidance["risk_level"], "high")

        self.assertTrue(any(
            "registered collector" in item.lower()
            or "licensed recycler" in item.lower()
            for item in guidance["immediate_precautions"]
        ))

        self.assertTrue(any(
            "do not drain" in item.lower()
            for item in guidance["disposal_steps"]
        ))

        self.assertTrue(any(
            "rinse" in item.lower() and "water" in item.lower()
            for item in guidance["if_exposed"]
        ))

        source_ids = {source["source_id"] for source in guidance["sources"]}
        self.assertIn("lk-cea-lead-acid-battery-2005", source_ids)

    def test_04_swollen_lithium_battery_guidance(self):
        intake = valid_intake()
        intake.update({
            "waste_types": ["e_waste", "batteries"],
            "specific_items": "Old laptop with a visibly swollen battery",
            "problem_type": "abandoned_electronics",
            "amount": "single_item",
            "condition": "swollen_battery",
            "hazards": ["damaged_battery"],
            "exposure": "none",
            "material_label": "Unknown",
        })

        response = self.submit_structured(
            intake=intake,
            text=(
                "An old laptop with a visibly swollen battery was abandoned "
                "beside a public road."
            ),
        )
        self.assertEqual(response.status_code, 201, response.text)

        guidance = response.json()["guidance"]
        self.assertEqual(guidance["risk_level"], "high")
        self.assertTrue(any(
            "puncture" in item.lower() or "crush" in item.lower()
            for item in guidance["do_not"]
        ))
        self.assertTrue(any(
            "e-waste" in item.lower() or "battery" in item.lower()
            for item in guidance["disposal_steps"]
        ))

    def test_05_unknown_chemical_guidance(self):
        intake = valid_intake()
        intake.update({
            "waste_types": ["chemicals"],
            "specific_items": "Unlabelled leaking chemical container",
            "problem_type": "leaking_spill",
            "amount": "small",
            "condition": "leaking",
            "hazards": ["chemical_leak", "strong_fumes"],
            "nearby_sensitive_place": "school",
            "impacts": ["people_children_nearby"],
            "exposure": "inhalation",
            "material_label": "Unknown",
        })

        response = self.submit_structured(
            intake=intake,
            text=(
                "An unknown chemical container is leaking near a school "
                "and producing strong fumes."
            ),
        )
        self.assertEqual(response.status_code, 201, response.text)

        guidance = response.json()["guidance"]
        self.assertEqual(guidance["risk_level"], "high")
        self.assertTrue(any(
            "do not mix" in item.lower()
            for item in guidance["do_not"]
        ))
        self.assertTrue(any(
            "unknown chemical" in item.lower()
            for item in guidance["seek_urgent_help"]
        ))

    def test_06_sharps_needlestick_guidance(self):
        intake = valid_intake()
        intake.update({
            "waste_types": ["sharps_needles", "medical_waste"],
            "specific_items": "Discarded syringe and needle",
            "problem_type": "illegal_dumping",
            "amount": "very_small",
            "condition": "damaged_broken",
            "hazards": ["sharps_needles", "medical_material"],
            "nearby_sensitive_place": "playground",
            "impacts": ["people_children_nearby"],
            "exposure": "needlestick",
            "material_label": "Unknown",
        })

        response = self.submit_structured(
            intake=intake,
            text=(
                "A discarded syringe was found near a playground and a person "
                "reports a possible needlestick injury."
            ),
        )
        self.assertEqual(response.status_code, 201, response.text)

        guidance = response.json()["guidance"]
        self.assertEqual(guidance["risk_level"], "high")
        self.assertTrue(any(
            "tetanus" in item.lower()
            for item in guidance["if_exposed"]
        ))
        self.assertTrue(any(
            "needlestick" in item.lower()
            for item in guidance["if_exposed"]
        ))

    # ------------------------------------------------------------------
    # 4. Validation / impossible combinations
    # ------------------------------------------------------------------

    def test_07_required_and_consistency_validation(self):
        cases = []

        # Missing all structured fields.
        cases.append({
            "name": "missing structured fields",
            "payload": {
                "text": "A sufficiently long complaint description for validation.",
                "intake": {},
            },
        })

        # Unknown waste cannot coexist with identified waste.
        intake = valid_intake()
        intake["waste_types"] = ["unknown", "plastic"]
        cases.append({
            "name": "unknown plus identified waste",
            "payload": {
                "text": "Mixed waste was found near the public road yesterday.",
                "intake": intake,
            },
        })

        # Swollen battery requires battery/e-waste.
        intake = valid_intake()
        intake.update({
            "waste_types": ["plastic"],
            "condition": "swollen_battery",
            "hazards": ["damaged_battery"],
        })
        cases.append({
            "name": "swollen battery without battery waste",
            "payload": {
                "text": "A suspicious swollen object was found beside the road.",
                "intake": intake,
            },
        })

        # Needlestick exposure requires sharps/medical hazard.
        intake = valid_intake()
        intake.update({
            "waste_types": ["household_mixed"],
            "hazards": ["none_observed"],
            "exposure": "needlestick",
        })
        cases.append({
            "name": "needlestick without sharps hazard",
            "payload": {
                "text": "A person reports an injury around dumped household waste.",
                "intake": intake,
            },
        })

        # No-hazard marker cannot coexist with a specific hazard.
        intake = valid_intake()
        intake["hazards"] = ["none_observed", "broken_glass"]
        cases.append({
            "name": "none observed plus specific hazard",
            "payload": {
                "text": "Broken material is visible in a roadside waste pile.",
                "intake": intake,
            },
        })

        for item in cases:
            with self.subTest(item["name"]):
                response = self.client.post(
                    "/complaints/structured",
                    json=item["payload"],
                )
                self.assertEqual(response.status_code, 422, response.text)

    # ------------------------------------------------------------------
    # 5. Idempotency / duplicate POST protection
    # ------------------------------------------------------------------

    def test_08_idempotency_reuses_tracking_id_and_rejects_changed_input(self):
        key = "premerge-idempotency-key-00000001"
        intake = valid_intake()

        first = self.submit_structured(
            intake=copy.deepcopy(intake),
            key=key,
        )
        self.assertEqual(first.status_code, 201, first.text)

        second = self.submit_structured(
            intake=copy.deepcopy(intake),
            key=key,
        )
        self.assertEqual(second.status_code, 201, second.text)

        self.assertEqual(
            first.json()["tracking_id"],
            second.json()["tracking_id"],
        )

        # The same idempotency key cannot silently represent different input.
        changed = self.submit_structured(
            intake=copy.deepcopy(intake),
            text=(
                "Different complaint text using the same idempotency key "
                "must be rejected by the API."
            ),
            key=key,
        )
        self.assertEqual(changed.status_code, 409, changed.text)

        # Only one persisted complaint should correspond to that tracking ID.
        matches = [
            case for case in complaint_repo.list_cases()
            if case["tracking_id"] == first.json()["tracking_id"]
        ]
        self.assertEqual(len(matches), 1)

    # ------------------------------------------------------------------
    # 6. Photo upload / privacy / image analysis
    # ------------------------------------------------------------------

    def test_09_valid_photo_is_saved_but_remains_staff_only(self):
        intake = valid_intake()

        response = self.client.post(
            "/complaints/structured-with-photo",
            data={
                "text": (
                    "Several household garbage bags have been left beside "
                    "the road for two days."
                ),
                "intake_json": json.dumps(intake),
            },
            files={
                "photo": ("waste.png", image_bytes("PNG"), "image/png"),
            },
        )
        self.assertEqual(response.status_code, 201, response.text)

        tracking_id = response.json()["tracking_id"]

        # Public result contains no raw photo metadata or path.
        public = self.client.get(
            f"/complaints/track/{tracking_id}"
        ).json()
        self.assertNotIn("photo", public)
        self.assertNotIn("stored_path", str(public))

        headers = self.staff_header("photo_staff")
        case = self.find_case(tracking_id, headers)

        # Anonymous user cannot fetch the image.
        no_auth = self.client.get(
            f"/staff/complaints/{case['id']}/photo"
        )
        self.assertEqual(no_auth.status_code, 401)

        # Authorized staff can inspect the normalized JPEG.
        photo = self.client.get(
            f"/staff/complaints/{case['id']}/photo",
            headers=headers,
        )
        self.assertEqual(photo.status_code, 200)
        self.assertEqual(photo.headers["content-type"], "image/jpeg")

        detail = self.client.get(
            f"/staff/complaints/{case['id']}",
            headers=headers,
        )
        self.assertEqual(detail.status_code, 200)
        self.assertIn("photo", detail.json())
        self.assertNotIn("stored_path", str(detail.json()["photo"]))

    def test_10_fake_photo_is_rejected(self):
        response = self.client.post(
            "/complaints/structured-with-photo",
            data={
                "text": (
                    "Several household garbage bags have been left beside "
                    "the road for two days."
                ),
                "intake_json": json.dumps(valid_intake()),
            },
            files={
                "photo": ("fake.jpg", b"this is not an image", "image/jpeg"),
            },
        )
        self.assertEqual(response.status_code, 422, response.text)

    # ------------------------------------------------------------------
    # 7. Text/image conflict must escalate to humans
    # ------------------------------------------------------------------

    def test_11_image_hazard_conflict_forces_urgent_human_review(self):
        intake = valid_intake()
        intake["hazards"] = ["none_observed"]

        observed = ImageAnalysisResult(
            visible_waste_types=["mixed waste"],
            visible_hazards=["syringe-like sharp object"],
            scene_summary="Mixed waste with a possible syringe-like sharp.",
            severity_hint="high",
            confidence=0.90,
            analyzed=True,
            provider="acceptance_fixture",
        )

        with patch(
            "backend.services.vision.analyze_image",
            return_value=observed,
        ):
            response = self.client.post(
                "/complaints/structured-with-photo",
                data={
                    "text": (
                        "Household rubbish is beside the road. "
                        "No medical or sharp hazards were observed."
                    ),
                    "intake_json": json.dumps(intake),
                },
                files={
                    "photo": ("waste.jpg", image_bytes("JPEG"), "image/jpeg"),
                },
            )

        self.assertEqual(response.status_code, 201, response.text)
        tracking_id = response.json()["tracking_id"]

        headers = self.staff_header("conflict_staff")
        case = self.find_case(tracking_id, headers)

        self.assertTrue(case["requires_human_review"])
        self.assertEqual(case["review_urgency"], "urgent")

        detail = self.client.get(
            f"/staff/complaints/{case['id']}",
            headers=headers,
        ).json()

        photo_analysis = detail["photo"]["analysis"]
        self.assertTrue(photo_analysis["image_text_conflict"])
        self.assertTrue(photo_analysis["visible_hazards"])

    # ------------------------------------------------------------------
    # 8. Vision failure must not lose the complaint
    # ------------------------------------------------------------------

    def test_12_vision_failure_keeps_complaint_and_photo_for_staff(self):
        with patch(
            "backend.services.vision.analyze_image",
            side_effect=vision.VisionProviderError("synthetic provider failure"),
        ):
            response = self.client.post(
                "/complaints/structured-with-photo",
                data={
                    "text": (
                        "Several household garbage bags have been left beside "
                        "the road for two days."
                    ),
                    "intake_json": json.dumps(valid_intake()),
                },
                files={
                    "photo": ("waste.png", image_bytes("PNG"), "image/png"),
                },
            )

        self.assertEqual(response.status_code, 201, response.text)
        tracking_id = response.json()["tracking_id"]

        # Complaint remains trackable.
        tracked = self.client.get(f"/complaints/track/{tracking_id}")
        self.assertEqual(tracked.status_code, 200)

        headers = self.staff_header("vision_failure_staff")
        case = self.find_case(tracking_id, headers)

        self.assertTrue(case["requires_human_review"])
        self.assertIn(case["review_urgency"], {"elevated", "urgent"})

        detail = self.client.get(
            f"/staff/complaints/{case['id']}",
            headers=headers,
        ).json()

        self.assertIsNotNone(detail["photo"])
        self.assertFalse(detail["photo"]["analysis"]["analyzed"])

    # ------------------------------------------------------------------
    # 9. Staff endpoints stay protected
    # ------------------------------------------------------------------

    def test_13_staff_endpoints_require_staff_authentication(self):
        created = self.submit_structured()
        self.assertEqual(created.status_code, 201)
        tracking_id = created.json()["tracking_id"]

        # Find the internal ID directly from isolated test storage only.
        case = complaint_repo.track(tracking_id)

        self.assertEqual(
            self.client.get("/staff/complaints").status_code,
            401,
        )
        self.assertEqual(
            self.client.get(
                f"/staff/complaints/{case['id']}"
            ).status_code,
            401,
        )

        citizen_headers = self.header("ordinary_citizen", "user")
        self.assertEqual(
            self.client.get(
                "/staff/complaints",
                headers=citizen_headers,
            ).status_code,
            403,
        )

    # ------------------------------------------------------------------
    # 10. Approved retrieval source manifest integrity
    # ------------------------------------------------------------------

    def test_14_approved_source_manifest_hashes_are_valid(self):
        from retrieval.sources import verify_manifest

        failures = verify_manifest()
        self.assertEqual(
            failures,
            [],
            f"Approved retrieval source manifest failures: {failures}",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
