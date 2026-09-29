import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from fastapi.testclient import TestClient

from backend.config import settings
from backend.database import initialize
from backend.main import app
from backend.repositories import complaints as complaint_repo
from backend.repositories import images as image_repo
from backend.schemas import ImageAnalysisResult
from backend.services import cases, image_storage, vision
from backend.auth import security, users


def image_bytes(fmt="JPEG", *, with_exif=False):
    buffer = io.BytesIO()
    image = Image.new("RGB", (48, 32), "white")
    kwargs = {}
    if with_exif:
        exif = Image.Exif()
        exif[0x010E] = "synthetic metadata"
        kwargs["exif"] = exif
    image.save(buffer, format=fmt, **kwargs)
    return buffer.getvalue()


class PhotoVisionUnitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patches = [
            patch.object(settings, "database_path", str(Path(self.tmp.name) / "photo.sqlite3")),
            patch.object(settings, "upload_dir", str(Path(self.tmp.name) / "uploads")),
            patch.object(settings, "use_mock_agents", True),
            patch.object(settings, "vision_max_image_mb", 5),
            patch.object(settings, "vision_max_dimension", 1800),
        ]
        for item in patches:
            item.start()
            self.addCleanup(item.stop)
        initialize()

    def test_valid_images_are_normalized_and_exif_removed(self):
        for fmt, mime in [("JPEG", "image/jpeg"), ("PNG", "image/png")]:
            sanitized = image_storage.sanitize_image(
                image_bytes(fmt, with_exif=(fmt == "JPEG")),
                mime,
            )
            self.assertEqual(sanitized["mime_type"], "image/jpeg")
            with Image.open(io.BytesIO(sanitized["data"])) as decoded:
                self.assertEqual(decoded.format, "JPEG")
                self.assertEqual(decoded.getexif(), {})

    def test_invalid_fake_svg_and_oversized_files_are_rejected(self):
        with self.assertRaises(image_storage.ImageValidationError):
            image_storage.sanitize_image(b"not an image", "image/jpeg")
        with self.assertRaises(image_storage.ImageValidationError):
            image_storage.sanitize_image(b"<svg></svg>", "image/svg+xml")
        with patch.object(settings, "vision_max_image_mb", 1):
            with self.assertRaises(image_storage.ImageValidationError):
                image_storage.sanitize_image(b"x" * (1024 * 1024 + 1), "image/jpeg")

    def test_storage_uses_random_private_filename(self):
        sanitized = image_storage.sanitize_image(image_bytes("PNG"), "image/png")
        stored = image_storage.persist_image(sanitized)
        path = Path(stored["stored_path"])
        self.assertTrue(path.is_file())
        self.assertEqual(path.parent, Path(settings.upload_dir))
        self.assertEqual(path.suffix, ".jpg")
        self.assertEqual(len(path.stem), 32)
        self.assertNotIn("garbage", path.name.lower())

    def test_text_image_hazard_conflict_requires_review(self):
        observed = ImageAnalysisResult(
            visible_waste_types=["mixed waste"],
            visible_hazards=["syringe-like sharp object"],
            scene_summary="Mixed waste with a possible sharp object.",
            severity_hint="high",
            confidence=0.8,
            analyzed=True,
            provider="fixture",
        )
        reconciled = vision.reconcile(
            observed,
            {"hazards": "none observed"},
            "There are no syringes or medical waste here.",
        )
        self.assertTrue(reconciled.image_text_conflict)
        requirements = vision.review_requirements(reconciled.model_dump())
        self.assertTrue(requirements["requires_human_review"])
        self.assertEqual(requirements["review_urgency"], "urgent")

    def test_photo_submission_persists_analysis_and_enriches_retrieval(self):
        case, created = cases.submit_with_photo(
            "Household garbage has been left beside the road for two days.",
            "Residential street",
            image_bytes("PNG"),
            "image/png",
            "p" * 32,
            {"duration": "two days", "hazards": "unknown"},
            "Library gate",
        )
        self.assertTrue(created)
        self.assertEqual(case["status"], "awaiting_review")
        photo = image_repo.get_for_complaint(case["id"])
        self.assertTrue(photo["analysis"]["analyzed"])
        self.assertIn("Image observations:", case["retrieval"]["query"])
        public = cases.public_status(case)
        self.assertNotIn("photo", public)
        self.assertNotIn("stored_path", str(public))
        self.assertNotIn("analysis_error", str(public))

    def test_image_result_cannot_reduce_text_severity(self):
        fixture = ImageAnalysisResult(
            visible_waste_types=["mixed waste"],
            visible_hazards=["possible sharp object"],
            scene_summary="Waste pile.",
            severity_hint="low",
            confidence=0.9,
            analyzed=True,
            provider="fixture",
        )
        with patch("backend.services.vision.analyze_image", return_value=fixture):
            case, _ = cases.submit_with_photo(
                "Chemical waste and syringes were dumped near the school.",
                "Near a school",
                image_bytes(),
                "image/jpeg",
                "q" * 32,
                {"duration": None, "hazards": "none observed"},
                None,
            )
        self.assertEqual(case["analysis"]["severity"], "high")
        photo = image_repo.get_for_complaint(case["id"])
        self.assertTrue(photo["analysis"]["image_text_conflict"])
        self.assertTrue(case["requires_human_review"])

    def test_vision_failure_keeps_photo_and_complaint(self):
        with patch(
            "backend.services.vision.analyze_image",
            side_effect=vision.VisionProviderError("synthetic failure"),
        ):
            case, _ = cases.submit_with_photo(
                "Household garbage has not been collected for two days.",
                "Residential street",
                image_bytes(),
                "image/jpeg",
                "r" * 32,
                None,
                None,
            )
        self.assertIn(case["status"], {"awaiting_review", "processing_failed"})
        self.assertIsNotNone(complaint_repo.get(case["id"]))
        photo = image_repo.get_for_complaint(case["id"])
        self.assertFalse(photo["analysis"]["analyzed"])
        self.assertEqual(photo["analysis_error"], "vision_unavailable")
        self.assertTrue(case["requires_human_review"])


class PhotoApiTests(unittest.TestCase):
    def setUp(self):
        from backend.middleware import resources

        resources._requests.clear()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patches = [
            patch.object(settings, "database_path", str(Path(self.tmp.name) / "api.sqlite3")),
            patch.object(settings, "upload_dir", str(Path(self.tmp.name) / "uploads")),
            patch.object(settings, "use_mock_agents", True),
            patch.object(settings, "admin_password", ""),
        ]
        for item in patches:
            item.start()
            self.addCleanup(item.stop)
        self.client = TestClient(app)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def staff_header(self):
        users.create_user("photo_staff", "synthetic-password", "staff")
        return {
            "Authorization": "Bearer "
            + security.create_access_token("photo_staff", "staff")
        }

    def test_invalid_photo_is_rejected_and_valid_photo_is_staff_only(self):
        bad = self.client.post(
            "/complaints/with-photo",
            data={"text": "Household garbage has been left beside the road."},
            files={"photo": ("fake.jpg", b"not an image", "image/jpeg")},
        )
        self.assertEqual(bad.status_code, 422)

        good = self.client.post(
            "/complaints/with-photo",
            data={
                "text": "Household garbage has been left beside the road.",
                "hazards": "unknown",
            },
            files={"photo": ("garbage.png", image_bytes("PNG"), "image/png")},
        )
        self.assertEqual(good.status_code, 201)
        tracking = good.json()["tracking_id"]
        case = complaint_repo.track(tracking)

        self.assertEqual(
            self.client.get(f"/staff/complaints/{case['id']}/photo").status_code,
            401,
        )
        response = self.client.get(
            f"/staff/complaints/{case['id']}/photo",
            headers=self.staff_header(),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "image/jpeg")
        detail = self.client.get(
            f"/staff/complaints/{case['id']}",
            headers=self.staff_header(),
        ).json()
        self.assertIn("photo", detail)
        self.assertNotIn("stored_path", str(detail["photo"]))


if __name__ == "__main__":
    unittest.main()
