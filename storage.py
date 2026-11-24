"""Attachment storage for WYGIWYH on Railway.

Upstream stores transaction and split attachments with a FileSystemStorage
under /usr/src/app/attachments. On Railway that folder would need a second
volume, so when the S3 variables are set (the template wires them to a
Railway Bucket) attachments go to the bucket instead. Downloads still go
through WYGIWYH's own login-protected views; the bucket stays private.
"""

import logging
import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage

logger = logging.getLogger(__name__)

_BUCKET = os.getenv("AWS_STORAGE_BUCKET_NAME", "").strip()
_ENDPOINT = os.getenv("AWS_ENDPOINT_URL", "").strip()

if _BUCKET and _ENDPOINT.startswith("http"):
    from storages.backends.s3 import S3Storage

    class PrivateMediaStorage(S3Storage):
        def __init__(self, *args, **kwargs):
            kwargs.setdefault("bucket_name", _BUCKET)
            kwargs.setdefault("endpoint_url", _ENDPOINT)
            kwargs.setdefault("region_name", os.getenv("AWS_S3_REGION_NAME") or None)
            kwargs.setdefault("access_key", os.getenv("AWS_ACCESS_KEY_ID"))
            kwargs.setdefault("secret_key", os.getenv("AWS_SECRET_ACCESS_KEY"))
            kwargs.setdefault("location", os.getenv("AWS_LOCATION", "attachments"))
            kwargs.setdefault("addressing_style", os.getenv("AWS_S3_ADDRESSING_STYLE", "virtual"))
            kwargs.setdefault("signature_version", "s3v4")
            kwargs.setdefault("default_acl", None)
            kwargs.setdefault("querystring_auth", True)
            kwargs.setdefault("file_overwrite", False)
            super().__init__(*args, **kwargs)

else:
    if _BUCKET or _ENDPOINT:
        logger.warning("Incomplete S3 settings; attachments stay on local disk")

    class PrivateMediaStorage(FileSystemStorage):
        def __init__(self, *args, **kwargs):
            kwargs.setdefault("location", settings.ATTACHMENT_MEDIA_ROOT)
            kwargs.setdefault("base_url", None)
            super().__init__(*args, **kwargs)
