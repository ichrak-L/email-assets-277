# BITX email signatures (email-assets-277)

This repo hosts the BITX, S.L. email signatures on GitHub Pages:
https://ichrak-l.github.io/email-assets-277/
Every file in the repo root is public and is loaded by recipients' email clients. Owner: Ichrak.

## How it works

- `tools/team.csv` lists everyone (slug, name, title, email, phone, phone_kind, photo, crop, last_name).
  `last_name` is optional; fill it only for multi-word surnames (e.g. "El May") so the QR contact card splits the name correctly.
- `tools/generate.py` builds, for each person, into the repo root:
  `circle-<slug>@2x.png`, `qr-<slug>@2x.png`, `signature-<slug>.html`, `<slug>.html` (the "copy my signature" page),
  plus the shared `logo-bitx@2x.png` and `icon-pin@2x.png`.
- Shared icons already in the root and NOT generated: `icon-mail@2x.png`, `icon-web@2x.png`,
  `icon-whatsapp@2x.png`, `icon-phone@2x.png`. Do not delete them.
- Image links get `?v=<hash>` automatically, so changed images are never served from cache.

## Running it

```
pip install -r tools/requirements.txt
python3 tools/generate.py
```

Playwright is optional; without it the committed `logo-bitx@2x.png` is reused. Only install it
(`pip install playwright && python -m playwright install chromium`) if `tools/brand/bitx-logo.svg` changes.

## Rules

1. Never edit generated files by hand. Change `tools/team.csv`, `tools/generate.py` or `tools/brand/`, then re-run the generator and commit inputs and outputs together.
2. Work on a branch and open a pull request. Never push to `main` directly; Ichrak reviews and merges. Merging to `main` publishes immediately.
3. In the PR description, list what changed per person and which files changed.
4. File names are case-sensitive and must keep `@2x`.
5. Do not change the disclaimer text (`DISCLAIMER_EN` in `generate.py`) unless the request says Legal has approved the new wording. Formatting changes are fine.
6. The repo is public. Only signature assets go here: no original full-resolution photos, ID documents, or anything private. Source photos in `tools/photos/` are framed squares of at most 800 px.
7. Do not invent personal details. If a name, title, email, phone or photo is missing, ask.

## Adding or changing a person

- New person: add a row to `tools/team.csv` and a front-facing photo in `tools/photos/<slug>.jpg`
  (square, 400 to 800 px; crop it before committing if needed). `phone_kind` is always `whatsapp`
  (WhatsApp icon, wa.me link): every BITX number is a WhatsApp number. `phone` (tel: link) exists but is unused.
- Photo framing: the `crop` column takes `left top right bottom` in source-photo pixels. Negative or
  out-of-range values extend the plain background (used for headroom). Leave empty to use the full square.
- After generating, check the QR code decodes (optional):
  `pip install opencv-python-headless` then decode `qr-<slug>@2x.png` with `cv2.QRCodeDetector`.

## Current design (version 3, awaiting RF approval)

- Fixed one-row desktop layout (no phone stacking for now): circle photo 90 px with a solid #B9BDC4 ring
  (RING_COLOR in generate.py; set to None for the brand gradient Purple #BB32FF, Cyan #0FD6F5, Green #A4FA4D) | name 15 px bold (700), title 10 px (both #040C17), phone, email |
  1 px divider (33 px gap left, 22 px right) | BITX logo 18 px tall, address, www.bitx.es | QR 65 px.
- Contact text 10 px; icons 11 px, teal #00AFCA. Disclaimer English only, 8 px.
- QR contains a vCard with name, BITX S.L., phone and email. Below 65 px it stops scanning reliably.
- Address (signature): Passeig de Gràcia 53, Ático, 08007 Barcelona, Spain. The disclaimer still says "Àtic" (legal text, unchanged).

## Open points (do not resolve on your own)

- RF has not approved version 3. Reinhard's email `reinhard@bitx.es` is unconfirmed.
- Disclaimer wording (legal@bitx.es, English only) needs Legal/Compliance confirmation.
- Old version 2 files `photo-ichrak@2x.png` may be deleted only when Ichrak asks.
