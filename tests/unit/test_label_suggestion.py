from obg.ui.app import _suggest_label


def test_suggest_label_uses_brand():
    assert _suggest_label("TOSHIBA MQ01ABD050") == "TOSHIBA"


def test_suggest_label_lowercase_normalized():
    assert _suggest_label("seagate barracuda") == "SEAGATE"


def test_suggest_label_empty_model():
    assert _suggest_label("") == ""
    assert _suggest_label("   ") == ""


def test_suggest_label_single_word_model():
    assert _suggest_label("WDC") == "WDC"


def test_suggest_label_truncated_to_16_chars():
    long_brand = "A" * 30
    label = _suggest_label(f"{long_brand} extra")
    assert len(label) <= 16
    assert label == "A" * 16


def test_suggest_label_sanitized():
    label = _suggest_label("Hitachi* (R) HDX")
    assert label == "HITACHI"


def test_suggest_label_strips_special_prefix():
    assert _suggest_label("WDC WD5000AAKX") == "WDC"