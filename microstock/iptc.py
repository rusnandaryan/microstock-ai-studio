"""Lossless Adobe XMP & IPTC Metadata Injector for Microstock JPEG assets.

Embeds Title, Description, Keywords, and Category directly into JPEG stream (APP1)
without re-encoding pixel data. Adobe Stock Contributor, Shutterstock Contributor,
and Freepik automatically read this metadata upon direct upload.
"""
from __future__ import annotations

import io
import xml.sax.saxutils
from typing import List, Optional
from PIL import Image


def escape_xml(text: str) -> str:
    """Escape XML special characters safely."""
    return xml.sax.saxutils.escape(str(text or "").strip())


def build_adobe_xmp_packet(
    title: str,
    description: str,
    keywords: List[str],
    adobe_category: Optional[str] = None,
) -> bytes:
    """Construct a fully compliant Adobe XMP metadata packet (Dublin Core + Photoshop schemas)."""
    esc_title = escape_xml(title)
    esc_desc = escape_xml(description)
    kw_items = "\n".join(f"      <rdf:li>{escape_xml(kw)}</rdf:li>" for kw in keywords if str(kw).strip())
    cat_tag = f"\n   <photoshop:Category>{escape_xml(str(adobe_category))}</photoshop:Category>" if adobe_category else ""

    packet = f"""<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="Microstock AI Studio Engine">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about=""
    xmlns:dc="http://purl.org/dc/elements/1.1/"
    xmlns:photoshop="http://ns.adobe.com/photoshop/1.0/"
    xmlns:xmp="http://ns.adobe.com/xap/1.0/">
   <dc:title>
    <rdf:Alt>
     <rdf:li xml:lang="x-default">{esc_title}</rdf:li>
    </rdf:Alt>
   </dc:title>
   <dc:description>
    <rdf:Alt>
     <rdf:li xml:lang="x-default">{esc_desc}</rdf:li>
    </rdf:Alt>
   </dc:description>
   <dc:subject>
    <rdf:Bag>
{kw_items}
    </rdf:Bag>
   </dc:subject>{cat_tag}
   <photoshop:Credit>Microstock AI Studio</photoshop:Credit>
  </rdf:Description>
 </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>"""
    return packet.encode("utf-8")


def inject_xmp_into_jpeg(
    jpeg_bytes: bytes,
    title: str,
    description: str,
    keywords: List[str],
    adobe_category: Optional[str] = None,
) -> bytes:
    """Inject Adobe XMP metadata segment into a JPEG byte stream losslessly.
    
    If an existing XMP APP1 segment is present, it is cleanly replaced.
    No pixel decoding or compression occurs during this operation.
    """
    if not jpeg_bytes.startswith(b"\xff\xd8"):
        return jpeg_bytes

    xmp_packet = build_adobe_xmp_packet(title, description, keywords, adobe_category)
    header_magic = b"http://ns.adobe.com/xap/1.0/\x00"
    payload = header_magic + xmp_packet
    seg_len = len(payload) + 2
    app1_seg = b"\xff\xe1" + seg_len.to_bytes(2, "big") + payload

    pos = 2
    out = bytearray(b"\xff\xd8")
    inserted = False

    while pos < len(jpeg_bytes):
        if jpeg_bytes[pos] != 0xFF:
            out.extend(jpeg_bytes[pos:])
            break
        marker = jpeg_bytes[pos + 1]
        if marker in (0xD9, 0xDA):  # EOI or SOS
            if not inserted:
                out.extend(app1_seg)
                inserted = True
            out.extend(jpeg_bytes[pos:])
            break
        if marker == 0x00:
            out.extend(jpeg_bytes[pos : pos + 2])
            pos += 2
            continue

        seg_size = int.from_bytes(jpeg_bytes[pos + 2 : pos + 4], "big")
        seg_data = jpeg_bytes[pos + 4 : pos + 2 + seg_size]

        # Skip existing XMP segment
        if marker == 0xE1 and seg_data.startswith(header_magic):
            pos += 2 + seg_size
            continue

        out.extend(jpeg_bytes[pos : pos + 2 + seg_size])
        pos += 2 + seg_size

        # Insert new XMP after APP0 or at the first marker
        if not inserted and (marker == 0xE0 or marker in (0xDB, 0xC0, 0xC2)):
            out.extend(app1_seg)
            inserted = True

    if not inserted:
        out = b"\xff\xd8" + app1_seg + out[2:]

    return bytes(out)

