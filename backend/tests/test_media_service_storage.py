import pathlib
import unittest
from unittest.mock import MagicMock, patch
from uuid import UUID

from app.services import media_service


VIDEO_ID = UUID("12345678-1234-5678-1234-567812345678")
FRAME_ID = UUID("87654321-4321-8765-4321-876543218765")


class MediaServiceStorageTests(unittest.TestCase):
    def test_local_video_resolves_to_an_existing_file(self):
        local_path = pathlib.Path("/app/storage/video/original.mp4")
        video = {
            "id": VIDEO_ID,
            "original_filename": "demo.mp4",
            "storage_backend": "local",
            "storage_key": None,
        }

        with (
            patch.object(media_service.video_repository, "get_video", return_value=video),
            patch.object(media_service, "get_video_file", return_value=local_path),
            patch.object(media_service, "create_s3_storage") as create_s3,
        ):
            result = media_service.resolve_video_media(VIDEO_ID)

        self.assertEqual(result.local_path, local_path)
        self.assertIsNone(result.redirect_url)
        create_s3.assert_not_called()

    def test_s3_video_resolves_to_a_short_lived_signed_url(self):
        storage_key = f"temporary/{VIDEO_ID}/original.mp4"
        video = {
            "id": VIDEO_ID,
            "original_filename": "demo.mp4",
            "storage_backend": "s3",
            "storage_key": storage_key,
        }
        s3_storage = MagicMock()
        s3_storage.presigned_get_url.return_value = "https://signed.example/video"

        with (
            patch.object(media_service.video_repository, "get_video", return_value=video),
            patch.object(media_service, "create_s3_storage", return_value=s3_storage),
            patch.object(media_service.settings, "s3_presigned_url_seconds", 300),
        ):
            result = media_service.resolve_video_media(VIDEO_ID)

        self.assertIsNone(result.local_path)
        self.assertEqual(result.redirect_url, "https://signed.example/video")
        s3_storage.presigned_get_url.assert_called_once_with(storage_key, expires_in=300)

    def test_s3_frame_resolves_using_the_frame_storage_key(self):
        storage_key = f"temporary/{VIDEO_ID}/frames/frame_0000.jpg"
        frame = {
            "id": FRAME_ID,
            "storage_backend": "s3",
            "storage_key": storage_key,
            "thumbnail_path": None,
        }
        s3_storage = MagicMock()
        s3_storage.presigned_get_url.return_value = "https://signed.example/frame"

        with (
            patch.object(media_service.frame_repository, "get_frame", return_value=frame),
            patch.object(media_service, "create_s3_storage", return_value=s3_storage),
        ):
            result = media_service.resolve_frame_media(FRAME_ID)

        self.assertEqual(result.redirect_url, "https://signed.example/frame")
        s3_storage.presigned_get_url.assert_called_once_with(
            storage_key,
            expires_in=media_service.settings.s3_presigned_url_seconds,
        )

    def test_s3_record_without_an_object_key_is_not_servable(self):
        video = {
            "id": VIDEO_ID,
            "storage_backend": "s3",
            "storage_key": None,
        }

        with patch.object(media_service.video_repository, "get_video", return_value=video):
            result = media_service.resolve_video_media(VIDEO_ID)

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
