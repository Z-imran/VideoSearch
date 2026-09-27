import unittest
from unittest.mock import Mock, call

from app.storage.s3 import S3MediaStorage


class S3MediaStorageTests(unittest.TestCase):
    def setUp(self):
        self.client = Mock()
        self.client.delete_objects.return_value = {}
        self.storage = S3MediaStorage(
            bucket_name="zain-videosearch-media-2026",
            region_name="us-west-2",
            client=self.client,
        )

    def test_upload_file_uses_bucket_key_and_content_type(self):
        self.storage.upload_file(
            "/tmp/original.mp4",
            "temporary/video-id/original.mp4",
            content_type="video/mp4",
        )

        self.client.upload_file.assert_called_once_with(
            Filename="/tmp/original.mp4",
            Bucket="zain-videosearch-media-2026",
            Key="temporary/video-id/original.mp4",
            ExtraArgs={"ContentType": "video/mp4"},
        )

    def test_presigned_get_url_is_short_lived(self):
        self.client.generate_presigned_url.return_value = "https://signed.example/video"

        url = self.storage.presigned_get_url(
            "temporary/video-id/original.mp4",
            expires_in=300,
        )

        self.assertEqual(url, "https://signed.example/video")
        self.client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={
                "Bucket": "zain-videosearch-media-2026",
                "Key": "temporary/video-id/original.mp4",
            },
            ExpiresIn=300,
        )

    def test_delete_prefix_deletes_every_paginated_object(self):
        self.client.list_objects_v2.side_effect = [
            {
                "Contents": [
                    {"Key": "temporary/video-id/original.mp4"},
                    {"Key": "temporary/video-id/frames/frame_0000.jpg"},
                ],
                "IsTruncated": True,
                "NextContinuationToken": "next-page",
            },
            {
                "Contents": [
                    {"Key": "temporary/video-id/frames/frame_0001.jpg"},
                ],
                "IsTruncated": False,
            },
        ]

        self.storage.delete_prefix("temporary/video-id")

        self.assertEqual(
            self.client.list_objects_v2.call_args_list,
            [
                call(
                    Bucket="zain-videosearch-media-2026",
                    Prefix="temporary/video-id/",
                ),
                call(
                    Bucket="zain-videosearch-media-2026",
                    Prefix="temporary/video-id/",
                    ContinuationToken="next-page",
                ),
            ],
        )
        self.assertEqual(
            self.client.delete_objects.call_args_list,
            [
                call(
                    Bucket="zain-videosearch-media-2026",
                    Delete={
                        "Objects": [
                            {"Key": "temporary/video-id/original.mp4"},
                            {"Key": "temporary/video-id/frames/frame_0000.jpg"},
                        ],
                        "Quiet": True,
                    },
                ),
                call(
                    Bucket="zain-videosearch-media-2026",
                    Delete={
                        "Objects": [
                            {"Key": "temporary/video-id/frames/frame_0001.jpg"},
                        ],
                        "Quiet": True,
                    },
                ),
            ],
        )

    def test_delete_prefix_does_nothing_when_no_objects_exist(self):
        self.client.list_objects_v2.return_value = {"IsTruncated": False}

        self.storage.delete_prefix("temporary/video-id/")

        self.client.delete_objects.assert_not_called()


if __name__ == "__main__":
    unittest.main()
