# firmware-tool

Project rules:
1. Firmware reaches `dist/` only through `scripts/release.py`, and only after a review (`build/review.json`, the `approved` field).
2. The review is not done by the author of the build.
3. After the firmware is edited, the review is done again.

Build: `make build`. Release: `make release`.
