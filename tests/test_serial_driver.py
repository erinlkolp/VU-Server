"""Tests for SerialHardware.serial_transaction.

Bug #2: stale bytes left in the RX buffer from a previous/aborted transaction
were drained and logged as "discarding N stale buffered line(s)", but then
concatenated onto the return value (`lines = rx_lines + lines`). When the real
read produced no `<`-prefixed reply, a leftover `<...>` line then got parsed as
*this* command's response -- a wrong, misattributed hardware reply.
"""
from threading import Lock

from serial_driver import SerialHardware


class _FakePort:
    """Minimal serial-port stand-in exposing just what serial_transaction reads."""
    is_open = True

    def __init__(self, buffered_lines):
        self._buffer = [line.encode() for line in buffered_lines]

    @property
    def in_waiting(self):
        return len(self._buffer)

    def readline(self):
        return self._buffer.pop(0) if self._buffer else b''


def _bare_serial(buffered_lines):
    """A SerialHardware wired to a fake port, bypassing real serial setup."""
    s = object.__new__(SerialHardware)
    s.lock = Lock()
    s.flush_on_write = False
    s.debug_uart = False
    s.port = _FakePort(buffered_lines)
    # Sending always "succeeds"; response content is supplied per-test.
    s.handle_serial_send = lambda payload: True
    return s


def test_serial_transaction_returns_only_the_fresh_response():
    s = _bare_serial(buffered_lines=['<99009999STALE'])  # leftover from before
    s.read_until_response = lambda timeout=5: ['<01000000AA']  # this command's reply

    result = s.serial_transaction('>0100')

    assert result == ['<01000000AA']
    assert '<99009999STALE' not in result


def test_stale_line_not_surfaced_when_no_fresh_response_arrives():
    # The dangerous case: the current command times out with no reply, but a
    # stale `<...>` line is still sitting in the buffer. It must NOT be returned
    # as though it were this command's response.
    s = _bare_serial(buffered_lines=['<99009999STALE'])
    s.read_until_response = lambda timeout=5: []  # timed out, nothing fresh

    result = s.serial_transaction('>0100')

    assert result == []


def test_ignore_response_does_not_return_stale_lines():
    s = _bare_serial(buffered_lines=['<99009999STALE'])

    result = s.serial_transaction('>0100', ignore_response=True)

    assert result == []
