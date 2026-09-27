from pathlib import Path
from typing import Any


class S3MediaStorage:
    def __init__(
        self,
        bucket_name: str,
        region_name: str,
        client: Any | None = None,
    ) -> None:
        self.bucket_name = bucket_name
        if client is None:
            import boto3

            client = boto3.client("s3", region_name=region_name)
        self.client = client

    def upload_file(self, local_path: str | Path, key: str, *, content_type: str) -> None:
        self.client.upload_file(
            Filename=str(local_path),
            Bucket=self.bucket_name,
            Key=key,
            ExtraArgs={"ContentType": content_type},
        )

    def presigned_get_url(self, key: str, *, expires_in: int) -> str:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket_name, "Key": key},
            ExpiresIn=expires_in,
        )

    def delete_prefix(self, prefix: str) -> None:
        normalized_prefix = f"{prefix.rstrip('/')}/"
        continuation_token = None

        while True:
            request = {
                "Bucket": self.bucket_name,
                "Prefix": normalized_prefix,
            }
            if continuation_token:
                request["ContinuationToken"] = continuation_token

            page = self.client.list_objects_v2(**request)
            objects = [{"Key": item["Key"]} for item in page.get("Contents", [])]
            if objects:
                response = self.client.delete_objects(
                    Bucket=self.bucket_name,
                    Delete={"Objects": objects, "Quiet": True},
                )
                if response.get("Errors"):
                    raise RuntimeError("S3 could not delete every object under the video prefix")

            if not page.get("IsTruncated", False):
                return

            continuation_token = page.get("NextContinuationToken")
            if not continuation_token:
                raise RuntimeError("S3 returned a truncated listing without a continuation token")
