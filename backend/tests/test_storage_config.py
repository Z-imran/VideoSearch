import unittest

from pydantic import ValidationError

from app.config import Settings


class StorageConfigTests(unittest.TestCase):
    def test_local_storage_is_the_default(self):
        settings = Settings(_env_file=None)

        self.assertEqual(settings.storage_backend, "local")
        self.assertIsNone(settings.s3_bucket)
        self.assertEqual(settings.aws_region, "us-west-2")
        self.assertEqual(settings.s3_presigned_url_seconds, 300)

    def test_s3_storage_requires_a_bucket(self):
        with self.assertRaisesRegex(ValidationError, "S3_BUCKET"):
            Settings(
                _env_file=None,
                storage_backend="s3",
                s3_bucket=None,
            )

    def test_s3_storage_accepts_complete_configuration(self):
        settings = Settings(
            _env_file=None,
            storage_backend="s3",
            s3_bucket="zain-videosearch-media-2026",
            aws_region="us-west-2",
            s3_presigned_url_seconds=300,
        )

        self.assertEqual(settings.storage_backend, "s3")
        self.assertEqual(settings.s3_bucket, "zain-videosearch-media-2026")

    def test_unknown_storage_backend_is_rejected(self):
        with self.assertRaises(ValidationError):
            Settings(_env_file=None, storage_backend="ftp")

    def test_presigned_url_lifetime_cannot_exceed_one_hour(self):
        with self.assertRaises(ValidationError):
            Settings(_env_file=None, s3_presigned_url_seconds=3601)


if __name__ == "__main__":
    unittest.main()
