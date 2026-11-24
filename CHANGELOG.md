# Changelog

## 0.28.0 (2026-11-24)

First release of this template.

- WYGIWYH 0.28.0, official image pinned by digest (`sha256:d8f08eaa…c826`). 0.28.0 fixes the high-severity advisories GHSA-hjfv-p3g6-mwch and GHSA-fh52-f8r4-hv6g.
- Services: `WYGIWYH` (web + background worker), Railway `Postgres`, Railway `Bucket` for attachments.
- Admin created on first boot from `ADMIN_EMAIL` and a generated `ADMIN_PASSWORD`; migrations under an advisory lock before the port opens; exits non-zero if the web process or worker stops.
