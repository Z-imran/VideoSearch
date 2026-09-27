import unittest
from uuid import UUID

from app.storage.keys import frame_object_key, video_object_key, video_prefix


VIDEO_ID = UUID("12345678-1234-5678-1234-567812345678")


class StorageKeyTests(unittest.TestCase):
    def test_temporary_video_prefix(self):
        self.assertEqual(
            video_prefix(VIDEO_ID, temporary=True),
            "temporary/12345678-1234-5678-1234-567812345678",
        )

    def test_permanent_video_prefix(self):
        self.assertEqual(
            video_prefix(VIDEO_ID, temporary=False),
            "permanent/12345678-1234-5678-1234-567812345678",
        )

    def test_video_key_uses_only_safe_lowercase_extension(self):
        self.assertEqual(
            video_object_key(VIDEO_ID, "../../My Holiday.MOV", temporary=True),
            "temporary/12345678-1234-5678-1234-567812345678/original.mov",
        )

    def test_video_key_defaults_to_mp4_without_an_extension(self):
        self.assertEqual(
            video_object_key(VIDEO_ID, "video", temporary=True),
            "temporary/12345678-1234-5678-1234-567812345678/original.mp4",
        )

    def test_frame_key_uses_only_the_frame_filename(self):
        self.assertEqual(
            frame_object_key(VIDEO_ID, "/tmp/work/frames/frame_0007.jpg", temporary=True),
            "temporary/12345678-1234-5678-1234-567812345678/frames/frame_0007.jpg",
        )


if __name__ == "__main__":
    unittest.main()
