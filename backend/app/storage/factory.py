from app.config import Settings, settings
from app.storage.s3 import S3MediaStorage


def create_s3_storage(config: Settings = settings) -> S3MediaStorage | None:
    if config.storage_backend == "local":
        return None

    if not config.s3_bucket:
        raise ValueError("S3_BUCKET is required when STORAGE_BACKEND=s3")

    return S3MediaStorage(
        bucket_name=config.s3_bucket,
        region_name=config.aws_region,
    )
