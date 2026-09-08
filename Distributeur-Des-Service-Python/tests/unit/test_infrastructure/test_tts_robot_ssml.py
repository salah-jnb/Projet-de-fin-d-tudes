from src.infrastructure.tts_robot_ssml import build_robot_ssml, escape_ssml_text, locale_from_voice_name


def test_escape_ssml_text():
    assert escape_ssml_text("a & b <c>") == "a &amp; b &lt;c&gt;"


def test_locale_from_voice_name():
    assert locale_from_voice_name("ar-SA-HamedNeural") == "ar-SA"
    assert locale_from_voice_name("fr-FR-HenriNeural") == "fr-FR"


def test_build_robot_ssml_contains_prosody():
    ssml = build_robot_ssml("مرحبا", "ar-SA-HamedNeural", pitch="+30%", rate="1.15")
    assert 'pitch="+30%"' in ssml
    assert 'rate="1.15"' in ssml
    assert "ar-SA-HamedNeural" in ssml
    assert "مرحبا" in ssml
