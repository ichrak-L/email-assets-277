#!/usr/bin/env python3
"""BITX email signature generator, version 3 (private-banking style, after RF feedback).

Usage (from the repo root):  python3 tools/generate.py
Writes into the repo root, which GitHub Pages publishes. Options: --base URL, --out DIR, --team CSV.
Reads team.csv (slug,name,title,email,phone,phone_kind,photo) and writes, per person:
  circle-<slug>@2x.png, qr-<slug>@2x.png, signature-<slug>.html, <slug>.html
plus the shared logo-bitx@2x.png and icon-pin@2x.png.
phone_kind: "whatsapp" (wa.me link, WhatsApp icon) or "phone" (tel: link, phone icon).
"""
import argparse, csv, html, math, os, re, urllib.parse
from PIL import Image, ImageDraw, ImageFont
import segno
from segno import helpers as segno_helpers

BASE = "https://ichrak-l.github.io/email-assets-277/"
TEAL, PLUM, CORAL, INK = "#00AFCA", "#7A3B69", "#E65F5C", "#040C17"   # TEAL: icons/links (approved V7); INK: name and title (PLUM unused)
# Brand colours from Figma "BXP Components", Brand section: Purple, Cyan, Green (the logo X gradient)
BRAND_PURPLE, BRAND_CYAN, BRAND_GREEN = "#BB32FF", "#0FD6F5", "#A4FA4D"
# Photo ring: a single colour. Set to None to use the brand gradient again.
RING_COLOR = "#B9BDC4"
LOGO_SVG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "brand", "bitx-logo.svg")
GREY_TEXT, RULE = "#6B7480", "#C9D0D9"
ADDRESS1, ADDRESS2 = "Passeig de Gr&agrave;cia 53, &Aacute;tico", "08007 Barcelona, Spain"
MAPS = "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote("Passeig de Gràcia 53, 08007 Barcelona, Spain")
WEB_URL, WEB_LABEL = "https://www.bitx.es", "www.bitx.es"
FONT = "'Inter',Helvetica,Arial,sans-serif"
# Name font stack for a semibold (600) name; unused while the name is bold (700), which every font in FONT has.
NAME_FONT = "'Inter','Segoe UI',-apple-system,BlinkMacSystemFont,Helvetica,Arial,sans-serif"
BOLD_TTF = "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"

def hexrgb(h): h = h.lstrip("#"); return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

# ---------- images ----------
def circle_photo(src, dst, crop=None, size=180):
    """Photo cropped to a circle with a three-colour ring (teal, plum, coral) and a white gap."""
    S = size * 4
    im = Image.open(src).convert("RGB")
    if crop:
        # A crop box may extend past the photo (e.g. negative top for headroom): the missing area is
        # filled by stretching the photo's edge pixels, which suits plain studio backgrounds.
        import numpy as np
        l, t, r, b = crop; W, H = im.size
        pad = (max(0, -t), max(0, b - H), max(0, -l), max(0, r - W))
        if any(pad):
            a = np.pad(np.asarray(im), ((pad[0], pad[1]), (pad[2], pad[3]), (0, 0)), mode="edge")
            im = Image.fromarray(a); l += pad[2]; r += pad[2]; t += pad[0]; b += pad[0]
        im = im.crop((l, t, r, b))
    w, h = im.size; s = min(w, h)
    im = im.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s))
    ring, gap = 21, 15                            # ring ~3 px, gap ~2 px at display size (108 px circle)
    inner = S - 2 * (ring + gap)
    photo = im.resize((inner, inner), Image.LANCZOS)
    mask = Image.new("L", (inner, inner), 0); ImageDraw.Draw(mask).ellipse((0, 0, inner - 1, inner - 1), fill=255)
    out = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(out)
    d.ellipse((ring, ring, S - ring - 1, S - ring - 1), fill=(255, 255, 255, 255))   # white gap
    # Ring: mirrored sweep through the brand gradient (Purple > Cyan > Green > Cyan > Purple),
    # starting top-left like the gradient on the logo's X.
    import numpy as np
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32) - (S - 1) / 2
    rr = np.hypot(xx, yy); ang = (np.degrees(np.arctan2(yy, xx)) + 135) % 360 / 360
    stops = [hexrgb(c) for c in ((RING_COLOR,) * 5 if RING_COLOR else (BRAND_PURPLE, BRAND_CYAN, BRAND_GREEN, BRAND_CYAN, BRAND_PURPLE))]
    seg = np.minimum((ang * 4).astype(int), 3); t = (ang * 4 - seg)[..., None]
    a = np.array(stops[:4], np.float32)[seg]; b = np.array(stops[1:], np.float32)[seg]
    rgb = a + (b - a) * t
    ring_mask = ((rr <= S / 2) & (rr >= S / 2 - ring)).astype(np.float32)
    ring_img = Image.fromarray(np.dstack([rgb, ring_mask[..., None] * 255]).astype(np.uint8), "RGBA")
    out.alpha_composite(ring_img)
    out.paste(photo, (ring + gap, ring + gap), mask)
    out.resize((size, size), Image.LANCZOS).save(dst)

def logo(dst, height=36):
    """Official BITX wordmark (Figma "BITX Website", node 3822:986), rendered to PNG with a headless browser."""
    from playwright.sync_api import sync_playwright  # optional dependency
    svg = open(LOGO_SVG, encoding="utf-8").read()
    vb = [float(v) for v in re.search(r'viewBox="([^"]+)"', svg).group(1).split()]
    width = round(height * vb[2] / vb[3])
    svg = re.sub(r'width="[^"]+" height="[^"]+"', f'width="{width}" height="{height}"', svg, count=1)
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": width, "height": height})
        pg.set_content(f'<html><body style="margin:0;background:transparent">{svg}</body></html>')
        pg.locator("svg").screenshot(path=dst, omit_background=True); b.close()
    return Image.open(dst).size

def pin_icon(dst, size=28):
    k = 8; S = size * k; out = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(out)
    c = hexrgb(TEAL) + (255,); r = int(S * 0.34); cx, cy = S // 2, int(S * 0.38)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=c)
    d.polygon([(cx - int(r * 0.86), cy + int(r * 0.5)), (cx + int(r * 0.86), cy + int(r * 0.5)), (cx, int(S * 0.96))], fill=c)
    h = int(r * 0.42); d.ellipse((cx - h, cy - h, cx + h, cy + h), fill=(0, 0, 0, 0))
    out.resize((size, size), Image.LANCZOS).save(dst)

def qr(p, dst, size=130):
    parts = p["name"].replace("Dr ", "").rsplit(" ", 1); first, last = (parts + [""])[:2] if len(parts) == 2 else (parts[0], "")
    # Compact vCard (LF line endings, no TYPE params) keeps the code at a low version so it scans small.
    data = "\n".join(["BEGIN:VCARD", "VERSION:3.0", f"N:{last};{first}", f"FN:{p['name']}", "ORG:BITX S.L.",
                      f"TEL:{digits(p['phone'], plus=True)}", f"EMAIL:{p['email']}",
                      "END:VCARD"])   # title and website left out: both are printed beside the code; a shorter card keeps it scannable at 96 px
    q = segno.make(data, error="l", micro=False)
    n = q.symbol_size(scale=1, border=1)[0]
    sc = max(1, size // n)                  # whole pixels per module; pad to exact size so modules stay crisp
    q.save(dst, scale=sc, border=1, dark=INK, light="#FFFFFF")
    im = Image.open(dst).convert("RGB"); canvas = Image.new("RGB", (size, size), "white")
    canvas.paste(im, ((size - im.width) // 2, (size - im.height) // 2)); canvas.save(dst)
    return q

def digits(phone, plus=False):
    d = re.sub(r"\D", "", phone); return ("+" + d) if plus else d

# ---------- html ----------
def icon_row(icon, alt, href, label, base, color=INK, underline=False, top=0):
    deco = "underline" if underline else "none"
    return (f'<tr><td valign="top" style="padding:{top + 2}px 8px 0 0;width:11px;">'
            f'<img src="{base}{icon}" width="11" height="11" alt="{alt}" style="display:block;width:11px;height:11px;border:0;"></td>'
            f'<td valign="top" style="padding-top:{top}px;font-family:{FONT};font-size:10px;line-height:15px;color:{color};white-space:nowrap;">'
            f'<a href="{href}" style="color:{color};text-decoration:{deco};">{label}</a></td></tr>')

DISCLAIMER_EN = [
    "The information contained in this message and/or any attached files, sent from BITX, S.L., is confidential and/or legally privileged and is intended solely for the use of the individual(s) to whom it is addressed. Please note that your personal data has been incorporated into the processing systems of BITX, S.L., and that, provided the legal requirements are met, you may exercise your rights of access, rectification, restriction of processing, erasure (right to be forgotten), data portability, objection, and withdrawal by sending a written request to {addr}, &Agrave;tic, 08007 Barcelona (Spain), or by email to {mail}.",
    "If you have received this message in error, are not the intended recipient, the employee, or the agent responsible for delivering it, please be advised that any use, disclosure, distribution, or reproduction of this communication is strictly prohibited and may be unlawful. We kindly ask you to notify us immediately and delete the message, as well as destroy any copies you may have. Thank you.",
]
DISCLAIMER_ES = [
    "La informaci&oacute;n contenida en este mensaje y/o en los archivos adjuntos, enviada desde BITX, S.L., es confidencial y/o est&aacute; legalmente protegida, y est&aacute; destinada a ser le&iacute;da s&oacute;lo por la(s) persona(s) a la(s) que va dirigida. Le recordamos que sus datos personales han sido incorporados a los sistemas de tratamiento de BITX, S.L., y que, siempre que se cumplan los requisitos establecidos en la normativa vigente, podr&aacute; ejercer sus derechos de acceso, rectificaci&oacute;n, limitaci&oacute;n del tratamiento, supresi&oacute;n (derecho al olvido), portabilidad, oposici&oacute;n y revocaci&oacute;n, dirigiendo su solicitud por escrito a la direcci&oacute;n postal {addr}, &Agrave;tic, 08007 Barcelona (Espa&ntilde;a), o mediante correo electr&oacute;nico a {mail}.",
    "Si usted ha recibido este mensaje por error, no es su destinatario se&ntilde;alado, la persona trabajadora o el agente responsable de entregar el mensaje al destinatario, le informamos de que est&aacute; prohibida &mdash;y puede ser ilegal&mdash; cualquier utilizaci&oacute;n, divulgaci&oacute;n, distribuci&oacute;n o reproducci&oacute;n del mismo. Le rogamos que nos lo notifique de inmediato y proceda a eliminarlo, as&iacute; como a destruir cualquier copia que pudiera obrar en su poder. Gracias por su colaboraci&oacute;n.",
]

def disclaimer_html():
    link = f"color:{GREY_TEXT};text-decoration:underline;"
    addr = f'<a href="{MAPS}" style="{link}">Passeig de Gr&agrave;cia 53</a>'
    mail = f'<a href="mailto:legal@bitx.es" style="{link}">legal@bitx.es</a>'
    p = f"margin:0 0 4px 0;font-family:Helvetica,Arial,sans-serif;font-size:8px;line-height:11px;color:{GREY_TEXT};"
    hd = f"margin:0 0 2px 0;font-family:Helvetica,Arial,sans-serif;font-size:8px;line-height:11px;font-weight:bold;letter-spacing:0.4px;color:{INK};"
    out = [f'<p style="{hd}">DISCLAIMER</p>'] + [f'<p style="{p}">{t.format(addr=addr, mail=mail)}</p>' for t in DISCLAIMER_EN]
    # Spanish notice (DISCLAIMER_ES) removed from the signature on request; text kept above for reference.
    return "".join(out)

def signature_html(p, base, logo_w):
    """Fixed desktop layout (one table row, does not stack on phones):
    [photo | name, title, phone, email]  |  [logo, address, web]  [QR]"""
    name, title = html.escape(p["name"]), html.escape(p["title"])
    if p["phone_kind"] == "whatsapp":
        ph_icon, ph_alt, ph_href = "icon-whatsapp@2x.png", "WhatsApp", "https://wa.me/" + digits(p["phone"])
    else:
        ph_icon, ph_alt, ph_href = "icon-phone@2x.png", "Phone", "tel:" + digits(p["phone"], plus=True)
    text = (f'<div style="font-family:{FONT};font-size:15px;line-height:18px;font-weight:700;letter-spacing:-0.1px;color:{INK};white-space:nowrap;">{name}</div>'
            f'<div style="font-family:{FONT};font-size:10px;line-height:13px;color:{INK};padding-top:2px;white-space:nowrap;">{title}</div>'
            f'<table cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;margin-top:10px;">'
            + icon_row(ph_icon, ph_alt, ph_href, html.escape(p["phone"]), base)
            + icon_row("icon-mail@2x.png", "Email", "mailto:" + p["email"], html.escape(p["email"]), base, top=4)
            + "</table>")
    info = (f'<img src="{base}logo-bitx@2x.png" width="{logo_w}" height="18" alt="BITX" style="display:block;width:{logo_w}px;height:18px;border:0;">'
            f'<table cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;margin-top:12px;">'
            + icon_row("icon-pin@2x.png", "Address", MAPS, f"{ADDRESS1}<br>{ADDRESS2}", base)
            + icon_row("icon-web@2x.png", "Website", WEB_URL, WEB_LABEL, base, color=TEAL, underline=True, top=6)
            + "</table>")
    return (f'<table cellpadding="0" cellspacing="0" border="0" bgcolor="#FFFFFF" style="border-collapse:collapse;background-color:#FFFFFF;font-family:{FONT};"><tr><td style="padding:8px 0 4px 0;">'
            f'<table cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;"><tr>'
            f'<td valign="middle" style="width:90px;padding-right:13px;"><img src="{base}circle-{p["slug"]}@2x.png" width="90" height="90" alt="{name}" style="display:block;width:90px;height:90px;border:0;"></td>'
            f'<td valign="middle" style="padding-right:33px;">{text}</td>'
            f'<td valign="middle" style="width:1px;font-size:0;line-height:0;"><div style="width:1px;height:96px;background-color:{RULE};font-size:0;line-height:96px;">&nbsp;</div></td>'
            f'<td valign="middle" style="padding-left:22px;padding-right:20px;">{info}</td>'
            f'<td valign="middle" style="width:65px;"><img src="{base}qr-{p["slug"]}@2x.png" width="65" height="65" alt="Scan to save contact" style="display:block;width:65px;height:65px;border:0;"></td>'
            f'</tr></table>'
            f'<div style="height:1px;line-height:1px;font-size:0;background-color:{RULE};margin:12px 0 9px 0;">&nbsp;</div>'
            f'<div style="max-width:560px;">{disclaimer_html()}</div>'
            f'</td></tr></table>')

def copy_page(p, sig):
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(p['name'])} - Email signature</title>
<style>body{{margin:0;background:#F2F4F7;font-family:Helvetica,Arial,sans-serif;color:#040C17}}
.w{{max-width:760px;margin:0 auto;padding:36px 20px}}h1{{font-size:22px;margin:0 0 6px}}p{{color:#39424F;line-height:1.5}}
.box{{background:#fff;border:1px solid #E4E8EE;border-radius:10px;padding:10px;margin:18px 0;overflow-x:auto}}
.box p{{line-height:inherit}}
button{{background:#00AFCA;color:#fff;border:0;border-radius:8px;padding:12px 22px;font-size:15px;font-weight:700;cursor:pointer}}
#ok{{display:none;color:#1a7f4b;font-weight:700;margin-left:12px}}ol{{color:#39424F;line-height:1.7}}</style></head><body><div class="w">
<h1>{html.escape(p['name'])}</h1><p>Your BITX email signature. Click the button, then paste it into Gmail.</p>
<div class="box" id="sig">{sig}</div>
<button id="b">Copy signature</button><span id="ok">Copied</span>
<ol><li>Click <b>Copy signature</b>.</li><li>In Gmail: gear icon, <b>See all settings</b>, <b>General</b> tab, <b>Signature</b>, <b>Create new</b> (or replace the old one).</li>
<li>Click in the box and paste (Ctrl/Cmd + V).</li><li>Choose it under <b>Signature defaults</b>, then scroll down and click <b>Save Changes</b>.</li></ol></div>
<script>document.getElementById('b').onclick=function(){{var e=document.getElementById('sig'),r=document.createRange();r.selectNodeContents(e);
var s=getSelection();s.removeAllRanges();s.addRange(r);try{{document.execCommand('copy');document.getElementById('ok').style.display='inline'}}catch(x){{}}}};</script></body></html>"""

def bust_cache(sig, out_dir):
    """Append ?v=<content hash> to links of images built in this run, so a changed image gets a new URL
    and Gmail, browsers and GitHub Pages cannot keep showing an old copy."""
    import hashlib
    def rep(m):
        name = m.group(2); path = os.path.join(out_dir, name)
        if not os.path.exists(path): return m.group(0)
        h = hashlib.md5(open(path, "rb").read()).hexdigest()[:8]
        return f'{m.group(1)}{name}?v={h}"'
    return re.sub(r'(src="[^"]*/)([^"/?]+\.png)"', rep, sig)

def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(); ap.add_argument("--base", default=BASE)
    ap.add_argument("--out", default=os.path.dirname(here)); ap.add_argument("--team", default=os.path.join(here, "team.csv"))
    a = ap.parse_args(); os.chdir(here)              # photo paths in team.csv are relative to tools/
    os.makedirs(a.out, exist_ok=True)
    logo_png = os.path.join(a.out, "logo-bitx@2x.png")
    try:
        lw, _ = logo(logo_png)
    except ImportError:                               # Playwright not installed: reuse the committed logo
        if not os.path.exists(logo_png): raise SystemExit("logo-bitx@2x.png missing and Playwright not installed")
        lw = Image.open(logo_png).size[0]
    logo_w = round(lw / 2)
    pin_icon(os.path.join(a.out, "icon-pin@2x.png"))
    for p in csv.DictReader(open(a.team, encoding="utf-8")):
        crop = tuple(int(v) for v in p["crop"].split()) if p.get("crop") else None
        circle_photo(p["photo"], os.path.join(a.out, f"circle-{p['slug']}@2x.png"), crop)
        qr(p, os.path.join(a.out, f"qr-{p['slug']}@2x.png"))
        sig = bust_cache(signature_html(p, a.base, logo_w), a.out)
        open(os.path.join(a.out, f"signature-{p['slug']}.html"), "w", encoding="utf-8").write(sig)
        open(os.path.join(a.out, f"{p['slug']}.html"), "w", encoding="utf-8").write(copy_page(p, sig))
        print("built", p["slug"])

if __name__ == "__main__":
    main()
