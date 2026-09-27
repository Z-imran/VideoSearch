import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.storage import factory


class StorageFactoryTests(unittest.TestCase):
    @patch("app.storage.factory.S3MediaStorage")
    def test_local_mode_does_not_create_an_s3_client(self, s3_storage_class):
        config = SimpleNamespace(storage_backend="local")

        storage = factory.create_s3_storage(config)

        self.assertIsNone(storage)
        s3_storage_class.assert_not_called()

    @patch("app.storage.factory.S3MediaStorage")
    def test_s3_mode_creates_storage_for_the_configured_bucket(self, s3_storage_class):
        expected_storage = object()
        s3_storage_class.return_value = expected_storage
        config = SimpleNamespace(
            storage_backend="s3",
            s3_bucket="zain-videosearch-media-2026",
            aws_region="us-west-2",
        )

        storage = factory.create_s3_storage(config)

        self.assertIs(storage, expected_storage)
        s3_storage_class.assert_called_once_with(
            bucket_name="zain-videosearch-media-2026",
            region_name="us-west-2",
        )


if __name__ == "__main__":
    unittest.main()
