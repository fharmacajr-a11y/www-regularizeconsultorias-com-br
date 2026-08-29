from pathlib import Path

from test_rodapes_globais import public_html_paths


ROOT = Path(__file__).parents[1]
ADS_LINE = b"google.com, pub-2993532924249779, DIRECT, f08c47fec0942fa0\n"
PUBLISHER_ID = "ca-pub-2993532924249779"


def test_ads_txt_has_the_exact_authorized_record_without_bom():
    assert (ROOT / "ads.txt").read_bytes() == ADS_LINE


def test_ads_txt_publisher_matches_the_existing_adsense_code():
    """ads.txt must match the publisher ID already present on the site."""
    ads_bytes = (ROOT / "ads.txt").read_bytes()
    ads_publisher = "pub-2993532924249779"

    assert ads_bytes == ADS_LINE
    assert ads_publisher.encode("ascii") in ads_bytes
    assert not ads_bytes.startswith(b"\xef\xbb\xbf")

    pages_with_publisher_id = [
        path
        for path in public_html_paths()
        if PUBLISHER_ID in path.read_text(encoding="utf-8")
    ]
    assert pages_with_publisher_id
    assert PUBLISHER_ID.endswith(ads_publisher)
