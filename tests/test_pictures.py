import pytest
from helpers import jpeg_bytes, png_bytes
from PIL import Image
from io import BytesIO

from app.services.importing.types import UploadRejected
from app.services.pictures import reencode

FORMATS = {"JPEG", "PNG", "WEBP", "GIF"}


def test_png_with_transparency_becomes_a_jpeg():
    out = reencode(png_bytes(), max_size=(1600, 1600), formats=FORMATS, label="picture")
    assert out.data[:3] == b"\xff\xd8\xff"


def test_large_pictures_are_shrunk():
    buffer = BytesIO()
    Image.new("RGB", (4000, 2000)).save(buffer, "PNG")
    out = reencode(buffer.getvalue(), max_size=(1600, 1600), formats=FORMATS, label="picture")
    assert (out.width, out.height) == (1600, 800)


@pytest.mark.parametrize("data", [b"<svg><script>alert(1)</script></svg>", b"GIF89a-not-really", b""])
def test_things_that_are_not_pictures_are_refused(data):
    with pytest.raises(UploadRejected):
        reencode(data, max_size=(1600, 1600), formats=FORMATS, label="picture")


def test_a_format_that_is_not_allowed_is_refused():
    with pytest.raises(UploadRejected):
        reencode(jpeg_bytes(), max_size=(600, 900), formats={"PNG"}, label="cover image")
