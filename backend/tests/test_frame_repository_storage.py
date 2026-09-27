import unittest
from unittest.mock import MagicMock, patch
from uuid import UUID

from app.repositories import frame_repository


VIDEO_ID = UUID("12345678-1234-5678-1234-567812345678")
FRAME_ID = UUID("87654321-4321-8765-4321-876543218765")


class FrameRepositoryStorageTests(unittest.TestCase):
    def setUp(self):
        self.connection_patch = patch.object(frame_repository, "get_connection")
        self.get_connection = self.connection_patch.start()
        self.addCleanup(self.connection_patch.stop)

        self.connection = MagicMock()
        self.cursor = MagicMock()
        self.get_connection.return_value.__enter__.return_value = self.connection
        self.connection.cursor.return_value.__enter__.return_value = self.cursor

    def test_create_local_frame_preserves_thumbnail_path(self):
        created = {"id": FRAME_ID, "thumbnail_path": "storage/video/frame.jpg"}
        self.cursor.fetchone.return_value = created

        result = frame_repository.create_frame(
            VIDEO_ID,
            3.0,
            thumbnail_path="storage/video/frame.jpg",
        )

        query, values = self.cursor.execute.call_args.args
        self.assertIn("storage_key", query)
        self.assertEqual(values["thumbnail_path"], "storage/video/frame.jpg")
        self.assertIsNone(values["storage_key"])
        self.assertIsNone(values["embedding"])
        self.assertEqual(result, created)
        self.connection.commit.assert_called_once_with()

    def test_create_s3_frame_stores_key_and_embedding_together(self):
        embedding = [0.1, 0.2, 0.3]
        storage_key = f"temporary/{VIDEO_ID}/frames/frame_0001.jpg"
        created = {
            "id": FRAME_ID,
            "thumbnail_path": None,
            "storage_key": storage_key,
            "embedding": embedding,
        }
        self.cursor.fetchone.return_value = created

        result = frame_repository.create_frame(
            VIDEO_ID,
            6.0,
            storage_key=storage_key,
            embedding=embedding,
        )

        _, values = self.cursor.execute.call_args.args
        self.assertIsNone(values["thumbnail_path"])
        self.assertEqual(values["storage_key"], storage_key)
        self.assertEqual(values["embedding"], embedding)
        self.assertEqual(result, created)
        self.connection.commit.assert_called_once_with()

    def test_create_frame_requires_a_media_location(self):
        with self.assertRaisesRegex(ValueError, "media location"):
            frame_repository.create_frame(VIDEO_ID, 9.0)

        self.get_connection.assert_not_called()

    def test_get_frame_includes_parent_storage_backend(self):
        stored = {
            "id": FRAME_ID,
            "storage_key": "temporary/video-id/frames/frame.jpg",
            "storage_backend": "s3",
        }
        self.cursor.fetchone.return_value = stored

        result = frame_repository.get_frame(FRAME_ID)

        query, values = self.cursor.execute.call_args.args
        self.assertIn("videos.storage_backend", query)
        self.assertEqual(values["id"], FRAME_ID)
        self.assertEqual(result, stored)


if __name__ == "__main__":
    unittest.main()
