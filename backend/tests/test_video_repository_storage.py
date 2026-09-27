import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import UUID

from app.repositories import video_repository


VIDEO_ID = UUID("12345678-1234-5678-1234-567812345678")


class VideoRepositoryStorageTests(unittest.TestCase):
    def setUp(self):
        self.connection_patch = patch.object(video_repository, "get_connection")
        self.get_connection = self.connection_patch.start()
        self.addCleanup(self.connection_patch.stop)

        self.connection = MagicMock()
        self.cursor = MagicMock()
        self.get_connection.return_value.__enter__.return_value = self.connection
        self.connection.cursor.return_value.__enter__.return_value = self.cursor

    def test_create_temporary_video_records_storage_backend(self):
        expires_at = datetime(2026, 9, 27, tzinfo=timezone.utc)
        created = {
            "id": VIDEO_ID,
            "storage_backend": "s3",
            "storage_key": None,
        }
        self.cursor.fetchone.side_effect = [{"count": 0}, created]

        result = video_repository.create_temporary_video(
            title="Test video",
            source_type="upload",
            original_filename="test.mp4",
            expires_at=expires_at,
            max_temporary_videos=10,
            storage_backend="s3",
        )

        insert_query, insert_values = self.cursor.execute.call_args_list[2].args
        self.assertIn("storage_backend", insert_query)
        self.assertEqual(insert_values["storage_backend"], "s3")
        self.assertEqual(result, created)
        self.connection.commit.assert_called_once_with()

    def test_create_temporary_video_rejects_unknown_storage_backend(self):
        with self.assertRaisesRegex(ValueError, "Unsupported storage backend"):
            video_repository.create_temporary_video(
                title="Test video",
                source_type="upload",
                original_filename="test.mp4",
                expires_at=datetime(2026, 9, 27, tzinfo=timezone.utc),
                max_temporary_videos=10,
                storage_backend="unknown",
            )

        self.get_connection.assert_not_called()

    def test_update_video_storage_saves_the_final_object_key(self):
        updated = {
            "id": VIDEO_ID,
            "storage_backend": "s3",
            "storage_key": f"temporary/{VIDEO_ID}/original.mp4",
        }
        self.cursor.fetchone.return_value = updated

        result = video_repository.update_video_storage(
            VIDEO_ID,
            f"temporary/{VIDEO_ID}/original.mp4",
        )

        query, values = self.cursor.execute.call_args.args
        self.assertIn("storage_key", query)
        self.assertEqual(values["id"], VIDEO_ID)
        self.assertEqual(values["storage_key"], f"temporary/{VIDEO_ID}/original.mp4")
        self.assertEqual(result, updated)
        self.connection.commit.assert_called_once_with()

    def test_expiration_query_includes_the_storage_backend(self):
        self.cursor.fetchall.return_value = []

        result = video_repository.list_expired_videos()

        query = self.cursor.execute.call_args.args[0]
        self.assertIn("storage_backend", query)
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
