"""Contract tests for manifest, services, and translations."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "gif"


def test_manifest_public_contract() -> None:
    """HACS install path, domain, and ownership must stay stable."""
    manifest = json.loads((INTEGRATION / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["domain"] == "gif"
    assert manifest["name"] == "GIF"
    assert manifest["integration_type"] == "service"
    assert manifest["iot_class"] == "calculated"
    assert manifest["config_flow"] is True
    assert manifest["single_config_entry"] is True
    assert manifest["codeowners"] == ["@Helvio88"]
    assert manifest["version"] == "0.3.1"


def test_hacs_json_keeps_custom_repo_install() -> None:
    """Do not switch HACS to a zip-release layout."""
    hacs = json.loads((ROOT / "hacs.json").read_text(encoding="utf-8"))
    assert hacs["name"] == "GIF"
    assert "zip_release" not in hacs
    assert "filename" not in hacs
    assert hacs.get("content_in_root") is not True


def test_services_yaml_has_selectors_and_original_fields() -> None:
    """Keep gif.create_gif fields and add UI selectors."""
    text = (INTEGRATION / "services.yaml").read_text(encoding="utf-8")
    assert text.strip().startswith("create_gif:")
    for field in (
        "images:",
        "camera:",
        "count:",
        "interval:",
        "fps:",
        "output_path:",
        "loop:",
    ):
        assert field in text
    assert "selector:" in text
    assert "multiple: true" in text
    assert "boolean:" in text
    assert "domain: camera" in text
    assert "min: 1" in text
    assert "max: 60" in text
    assert "unit_of_measurement: seconds" in text
    assert "required: true" not in text
    assert "Defaults to /config/www/gif/" in text


def test_translations_cover_config_services_and_exceptions() -> None:
    """English translations must match the config flow and service."""
    translations = json.loads(
        (INTEGRATION / "translations" / "en.json").read_text(encoding="utf-8")
    )
    assert "options" not in translations
    assert "single_instance_allowed" in translations["config"]["abort"]
    fields = translations["services"]["create_gif"]["fields"]
    assert set(fields) == {
        "images",
        "camera",
        "count",
        "interval",
        "fps",
        "output_path",
        "loop",
    }
    exceptions = translations["exceptions"]
    assert "not_setup" in exceptions
    assert "source_exclusive" in exceptions
    assert "source_required" in exceptions
    assert "camera_not_found" in exceptions
    assert "camera_unavailable" in exceptions
