# WYGIWYH for Railway: the official image, pinned by version and digest,
# plus a small wrapper (start script, first-boot bootstrap, S3 attachments).
FROM eitchtee/wygiwyh:0.28.0@sha256:d8f08eaa3e19955400746059636da91211335206a77fcce562587c80c435c826

USER root

# django-storages lets attachments live in a Railway Bucket, so the only
# volume in the project is Postgres (Railway's Free plan allows one volume).
RUN pip --python /app/.venv/bin/python install --no-cache-dir \
        "django-storages[s3]==1.14.6" "boto3==1.44.10" \
    && /app/.venv/bin/python -c "import storages, boto3"

# Same class name and module as upstream, so existing migrations
# (storage=PrivateMediaStorage()) still match. Without bucket variables it
# falls back to upstream's local folder.
COPY --chown=app:app storage.py /usr/src/app/apps/transactions/storage.py
COPY --chmod=755 railway-start.sh /railway-start.sh
COPY --chmod=644 railway_bootstrap.py /railway_bootstrap.py

USER app
WORKDIR /usr/src/app

CMD ["/bin/bash", "/railway-start.sh"]
