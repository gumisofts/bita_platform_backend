import os

from storages.backends.s3boto3 import S3Boto3Storage


class PublicMinIOStorage(S3Boto3Storage):
    """
    S3Boto3Storage that rewrites presigned URLs from the internal endpoint
    (e.g. http://127.0.0.1:9000) to the public-facing domain
    (e.g. https://mini-io.bita.et).

    Set AWS_S3_ENDPOINT_URL  = internal address boto3 uses to connect/sign
    Set AWS_S3_PUBLIC_URL    = public URL that clients should receive
    """

    def url(self, name, parameters=None, expire=None, http_method=None):
        signed = super().url(
            name, parameters=parameters, expire=expire, http_method=http_method
        )
        internal = os.getenv("AWS_S3_ENDPOINT_URL", "").rstrip("/")
        public = os.getenv("AWS_S3_PUBLIC_URL", "").rstrip("/")
        if internal and public and signed.startswith(internal):
            signed = public + signed[len(internal) :]
        return signed
