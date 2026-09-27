import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch
from uuid import UUID

from app.services import video_service


VIDEO_ID = UUID("12345678-1234-5678-1234-567812345678")


class VideoServiceStorageTests(unittest.TestCase):
    def test_upload_row_records_the_configured_storage_backend(self):
        upload = SimpleNamespace(filename="demo.mp4")
        created = {"id": VIDEO_ID}

        with (
            patch.object(video_service.settings, "storage_backend", "s3"),
            patch.object(
                video_service.video_repository,
                "create_temporary_video",
                return_value=created,
            ) as create_video,
            patch.object(video_service, "save_upload", return_value="/tmp/demo.mp4"),
            patch.object(video_service, "get_duration_seconds", return_value=12.0),
            patch.object(
                video_service.video_repository,
                "update_video_duration",
                return_value=created,
            ),
        ):
            result, video_path = video_service.create_video_from_upload(upload, "Demo")

        self.assertEqual(result, created)
        self.assertEqual(video_path, "/tmp/demo.mp4")
        self.assertEqual(create_video.call_args.kwargs["storage_backend"], "s3")

    def test_s3_processing_publishes_media_and_saves_object_keys(self):
        video_path = f"/app/storage/{VIDEO_ID}/original.mp4"
        frame_path = f"/app/storage/{VIDEO_ID}/frames/frame_0000.jpg"
        video_key = f"temporary/{VIDEO_ID}/original.mp4"
        frame_key = f"temporary/{VIDEO_ID}/frames/frame_0000.jpg"
        vector = [0.1, 0.2, 0.3]
        s3_storage = MagicMock()

        with (
            patch.object(video_service, "create_s3_storage", return_value=s3_storage),
            patch.object(video_service, "extract_keyframes", return_value=[(0.0, frame_path)]),
            patch.object(video_service.embedder, "embed_image", return_value=vector),
            patch.object(video_service.video_repository, "update_video_status") as update_status,
            patch.object(video_service.video_repository, "update_video_storage") as update_storage,
            patch.object(video_service.frame_repository, "create_frame") as create_frame,
            patch.object(video_service.frame_repository, "update_frame_embedding") as update_embedding,
            patch.object(video_service, "delete_video_files") as delete_local_files,
        ):
            video_service.process_video(str(VIDEO_ID), video_path)

        self.assertEqual(
            s3_storage.upload_file.call_args_list,
            [
                call(video_path, video_key, content_type="video/mp4"),
                call(frame_path, frame_key, content_type="image/jpeg"),
            ],
        )
        update_storage.assert_called_once_with(str(VIDEO_ID), video_key)
        create_frame.assert_called_once_with(
            str(VIDEO_ID),
            0.0,
            storage_key=frame_key,
            embedding=vector,
        )
        update_embedding.assert_not_called()
        self.assertEqual(
            update_status.call_args_list,
            [call(str(VIDEO_ID), "processing"), call(str(VIDEO_ID), "ready")],
        )
        delete_local_files.assert_called_once_with(str(VIDEO_ID))

    def test_local_processing_keeps_existing_file_based_behavior(self):
        video_path = f"/app/storage/{VIDEO_ID}/original.mp4"
        frame_path = f"/app/storage/{VIDEO_ID}/frames/frame_0000.jpg"
        vector = [0.1, 0.2, 0.3]
        created_frame = {"id": "frame-id"}

        with (
            patch.object(video_service, "create_s3_storage", return_value=None),
            patch.object(video_service, "extract_keyframes", return_value=[(0.0, frame_path)]),
            patch.object(video_service.embedder, "embed_image", return_value=vector),
            patch.object(video_service.video_repository, "update_video_status"),
            patch.object(video_service.video_repository, "update_video_storage") as update_storage,
            patch.object(
                video_service.frame_repository,
                "create_frame",
                return_value=created_frame,
            ) as create_frame,
            patch.object(video_service.frame_repository, "update_frame_embedding") as update_embedding,
            patch.object(video_service, "delete_video_files") as delete_local_files,
        ):
            video_service.process_video(str(VIDEO_ID), video_path)

        create_frame.assert_called_once_with(str(VIDEO_ID), 0.0, frame_path)
        update_embedding.assert_called_once_with("frame-id", vector)
        update_storage.assert_not_called()
        delete_local_files.assert_not_called()

    def test_failed_s3_processing_removes_partial_objects_and_local_staging(self):
        video_path = f"/app/storage/{VIDEO_ID}/original.mp4"
        frame_path = f"/app/storage/{VIDEO_ID}/frames/frame_0000.jpg"
        s3_storage = MagicMock()
        s3_storage.upload_file.side_effect = [None, RuntimeError("upload failed")]

        with (
            patch.object(video_service, "create_s3_storage", return_value=s3_storage),
            patch.object(video_service, "extract_keyframes", return_value=[(0.0, frame_path)]),
            patch.object(video_service.embedder, "embed_image", return_value=[0.1, 0.2]),
            patch.object(video_service.video_repository, "update_video_status"),
            patch.object(video_service.video_repository, "update_video_storage"),
            patch.object(video_service.video_repository, "mark_video_failed") as mark_failed,
            patch.object(video_service.frame_repository, "create_frame"),
            patch.object(video_service, "delete_video_files") as delete_local_files,
        ):
            with self.assertRaisesRegex(RuntimeError, "upload failed"):
                video_service.process_video(str(VIDEO_ID), video_path)

        mark_failed.assert_called_once_with(str(VIDEO_ID))
        s3_storage.delete_prefix.assert_called_once_with(f"temporary/{VIDEO_ID}")
        delete_local_files.assert_called_once_with(str(VIDEO_ID))

    def test_expiration_cleanup_removes_local_and_s3_media_before_database_rows(self):
        local_id = UUID("11111111-1111-1111-1111-111111111111")
        s3_id = UUID("22222222-2222-2222-2222-222222222222")
        expired = [
            {"id": local_id, "storage_backend": "local"},
            {"id": s3_id, "storage_backend": "s3"},
        ]
        s3_storage = MagicMock()

        with (
            patch.object(video_service.video_repository, "list_expired_videos", return_value=expired),
            patch.object(video_service.video_repository, "delete_video") as delete_video,
            patch.object(video_service, "create_s3_storage", return_value=s3_storage),
            patch.object(video_service, "delete_video_files") as delete_local_files,
        ):
            video_service.cleanup_expired_videos()

        self.assertEqual(
            delete_local_files.call_args_list,
            [call(local_id), call(s3_id)],
        )
        s3_storage.delete_prefix.assert_called_once_with(f"temporary/{s3_id}")
        self.assertEqual(
            delete_video.call_args_list,
            [call(local_id), call(s3_id)],
        )


if __name__ == "__main__":
    unittest.main()
