import time
from datetime import datetime

from mandate.mandate import is_active, load_mandate, revoke, save_mandate


def test_FR_MAN_7_status_transitions_to_revoked(tmp_path):
    m = load_mandate()
    assert m["status"] == "active"
    assert is_active(m)

    m = revoke(m)
    assert m["status"] == "revoked"
    assert not is_active(m)


def test_FR_MAN_8_revoked_at_is_set_when_revoked(tmp_path):
    m = load_mandate()
    assert m["revoked_at"] is None

    m = revoke(m)
    ts = m["revoked_at"]
    assert ts is not None
    datetime.fromisoformat(ts)


def test_FR_MAN_9_mandate_is_re_read_from_disk(tmp_path):
    path = tmp_path / "mandate.yaml"
    original = load_mandate()
    save_mandate(original, path)

    reloaded = load_mandate(path)
    assert reloaded["status"] == "active"

    revoked = revoke(reloaded)
    save_mandate(revoked, path)

    reloaded_again = load_mandate(path)
    assert reloaded_again["status"] == "revoked"
    assert reloaded_again["revoked_at"] is not None