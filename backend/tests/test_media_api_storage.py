import unittest
from unittest.mock import patch
from uuid import UUID

from fastapi.responses import RedirectResponse

from app.api import media
from app.services.media_service import MediaLocation


VIDEO_ID = UUID("12345678-1234-5678-1234-567812345678")


class MediaApiStorageTests(unittest.TestCase):
    def test_s3_video_endpoint_redirects_to_the_signed_url(self):
        location = MediaLocation(redirect_url="https://signed.example/video")

        with patch.object(media.media_service, "resolve_video_media", return_value=location):
            response = media.serve_video(VIDEO_ID)

        self.assertIsInstance(response, RedirectResponse)
        self.assertEqual(response.status_code, 307)
        self.assertEqual(response.headers["location"], "https://signed.example/video")


if __name__ == "__main__":
    unittest.main()
