"""Regression tests for a batch of bug fixes.

Covered defects:
  #1 Device_Set_Image `force` flag was dead (string arg compared with `is True`).
  #2 DialSerialDriver.dial_set_backlight crashed (KeyError) on an unknown dial.
  #3 dial_multiple_set_percent passed the value into set_dial's UID slot and
     never recorded it in the dial cache.
  #5 DialsDB.api_update_master never committed the master-key row.
"""
import sqlite3
import types

import pytest

from server import BaseHandler
from dial_driver import DialSerialDriver
from database import DialsDB


# -- #1: force flag argument parsing -----------------------------------------

@pytest.mark.parametrize("value,expected", [
    ("true", True),
    ("True", True),
    ("1", True),
    ("yes", True),
    ("on", True),
    (True, True),
    ("false", False),
    ("0", False),
    ("", False),
    ("no", False),
    (False, False),
])
def test_arg_is_true_parses_query_string_values(value, expected):
    # get_argument returns a *string* when the param is present, or the
    # supplied default otherwise. Neither is ever the `True` singleton, so the
    # old `get_force is True` check could never fire.
    assert BaseHandler._arg_is_true(value) is expected


# -- #2: dial_set_backlight on an unknown dial -------------------------------

def _bare_driver():
    """A DialSerialDriver with no serial port, for pure-logic tests."""
    driver = object.__new__(DialSerialDriver)
    driver.dials = {}
    return driver


def test_dial_set_backlight_unknown_dial_returns_false_without_crashing():
    driver = _bare_driver()
    # Previously this resolved to None via _verify_device and then blew up on
    # self.dials[None]['rgbw'] with a KeyError.
    assert driver.dial_set_backlight('DOESNOTEXIST', 1, 2, 3, 4) is False


# -- #3: dial_multiple_set_percent records values in the cache ----------------

def test_dial_multiple_set_percent_caches_values():
    driver = _bare_driver()
    driver.dials = {
        0: {'index': '0', 'uid': 'AAA', 'value': 0},
        1: {'index': '1', 'uid': 'BBB', 'value': 0},
    }
    driver.commands = types.SimpleNamespace(COMM_CMD_SET_DIAL_PERC_MULTIPLE=0)
    driver.data_type = types.SimpleNamespace(COMM_DATA_KEY_VALUE_PAIR=0)
    sent = {}

    def fake_send(*args, **kwargs):  # pragma: no cover - trivial stub
        sent['called'] = True
        return True

    driver._sendCommand = fake_send

    driver.dial_multiple_set_percent([0, 1], [42, 77])

    assert driver.dials[0]['value'] == 42
    assert driver.dials[1]['value'] == 77
    assert sent.get('called') is True


# -- #5: api_update_master commits -------------------------------------------

def test_api_update_master_is_committed(tmp_path):
    db_file = str(tmp_path / "commit_test.db")
    db = DialsDB(database_file=db_file, init_if_missing=True)

    db.api_update_master('MASTERKEY123')

    # A brand new connection only sees committed rows.
    verify = sqlite3.connect(db_file)
    verify.row_factory = sqlite3.Row
    row = verify.execute(
        "SELECT key_uid FROM api_keys WHERE key_name='MASTER_KEY'"
    ).fetchone()
    verify.close()

    assert row is not None
    assert row['key_uid'] == 'MASTERKEY123'
