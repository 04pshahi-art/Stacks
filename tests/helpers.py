"""Small builders shared by the tests."""
import zipfile
from io import BytesIO

from PIL import Image


def jpeg_bytes(size=(120, 80), colour=(200, 60, 60)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, colour).save(buffer, "JPEG")
    return buffer.getvalue()


def png_bytes(size=(120, 80)) -> bytes:
    buffer = BytesIO()
    Image.new("RGBA", size, (30, 120, 200, 128)).save(buffer, "PNG")
    return buffer.getvalue()


def zip_bytes(files: dict[str, bytes | str]) -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return buffer.getvalue()


def make_pdf(pages: list[str]) -> bytes:
    """A minimal valid PDF with one line of text per page."""
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b""]
    kids = []
    font_id = 3 + 2 * len(pages)
    for index, text in enumerate(pages):
        page_id = 3 + 2 * index
        kids.append(f"{page_id} 0 R")
        safe = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream = f"BT /F1 12 Tf 72 720 Td ({safe}) Tj ET".encode("latin-1")
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Contents {page_id + 1} 0 R /Resources << /Font << /F1 {font_id} 0 R >> >> >>".encode()
        )
        objects.append(b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream))
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    objects[1] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(pages)} >>".encode()

    out = BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(out.tell())
        out.write(b"%d 0 obj\n%s\nendobj\n" % (number, body))
    xref = out.tell()
    out.write(b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1))
    for offset in offsets:
        out.write(b"%010d 00000 n \n" % offset)
    out.write(b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref))
    return out.getvalue()


def make_epub(chapters: list[tuple[str, str]], images: dict[str, bytes] | None = None) -> bytes:
    """A small EPUB. Each chapter is (title, body html); images maps file name to bytes."""
    images = images or {}
    manifest = "".join(
        f'<item id="c{i}" href="c{i}.xhtml" media-type="application/xhtml+xml"/>'
        for i in range(len(chapters))
    ) + "".join(
        f'<item id="img{i}" href="{name}" media-type="image/jpeg"/>' for i, name in enumerate(images)
    )
    spine = "".join(f'<itemref idref="c{i}"/>' for i in range(len(chapters)))
    files = {
        "mimetype": "application/epub+zip",
        "META-INF/container.xml": (
            '<?xml version="1.0"?><container version="1.0" '
            'xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles>'
            '<rootfile full-path="content.opf" media-type="application/oebps-package+xml"/>'
            "</rootfiles></container>"
        ),
        "content.opf": (
            '<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0">'
            '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Test Book</dc:title>'
            f"<dc:creator>Tester</dc:creator></metadata><manifest>{manifest}</manifest>"
            f"<spine>{spine}</spine></package>"
        ),
    }
    for i, (title, body) in enumerate(chapters):
        files[f"c{i}.xhtml"] = (
            '<html xmlns="http://www.w3.org/1999/xhtml"><body>'
            f"<h1>{title}</h1>{body}</body></html>"
        )
    files.update(images)
    return zip_bytes(files)
