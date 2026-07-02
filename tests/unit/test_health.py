from unittest.mock import patch, MagicMock
from obg.core.health import read_smart, run_short_test, poll_smart_test

MOCK_SMARTCTL_OUTPUT = """smartctl 7.1 2019-10-24 r5009

=== START OF READ SMART DATA SECTION ===
SMART overall-health self-assessment test result: PASSED
SMART Attributes Data Structure revision number: 16
Vendor Specific SMART Attributes with Thresholds:
ID# ATTRIBUTE_NAME          FLAG     VALUE WORST THRESH TYPE      UPDATED  WHEN_FAILED RAW_VALUE
  5 Reallocated_Sector_Ct   0x0032   100   100   000    Old_age   Always       -       0
  9 Power_On_Hours          0x0032   097   097   000    Old_age   Always       -       12345
 194 Temperature_Celsius     0x0022   040   050   000    Old_age   Always       -       38
 197 Current_Pending_Sector  0x0012   100   100   000    Old_age   Always       -       0
 198 Offline_Uncorrectable   0x0030   100   100   000    Old_age   Offline      -       0
 199 UDMA_CRC_Error_Count    0x0032   200   200   000    Old_age   Always       -       0

SMART Self-test log structure revision number 1
Num  Test_Description    Status                  Remaining  LifeTime(hours)  LBA_of_first_error
# 1  Short offline       Completed without error       00%      12345         -
"""


def test_read_smart_success():
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = MOCK_SMARTCTL_OUTPUT

    with patch("obg.core.health.run", return_value=mock_result):
        sd = read_smart("/dev/sdb")

    assert sd is not None
    assert sd.overall_health == "PASSED"
    assert sd.reallocated_sectors == 0
    assert sd.pending_sectors == 0
    assert sd.uncorrectable_sectors == 0
    assert sd.crc_errors == 0
    assert sd.temperature == 38
    assert sd.power_on_hours == 12345


def test_read_smart_not_supported():
    mock_result = MagicMock()
    mock_result.returncode = 4
    mock_result.stdout = ""

    with patch("obg.core.health.run", return_value=mock_result):
        sd = read_smart("/dev/sdb")

    assert sd is None


def test_read_smart_error():
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""

    with patch("obg.core.health.run", return_value=mock_result):
        sd = read_smart("/dev/sdb")

    assert sd is None


def test_run_short_test_success():
    start_result = MagicMock()
    start_result.returncode = 0
    start_result.stdout = "Test has begun"

    poll_result = MagicMock()
    poll_result.returncode = 0
    poll_result.stdout = "Self-test execution status:      (   0)"

    with patch("obg.core.health.run", side_effect=[start_result, poll_result]):
        with patch("obg.core.health.time.sleep"):
            result = run_short_test("/dev/sdb")

    assert result is True


def test_poll_smart_test_timeout():
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "Self-test execution status:      ( 249)\n 25% of test remaining"

    call_count = 0

    def mock_time_monotonic():
        nonlocal call_count
        call_count += 1
        if call_count > 2:
            return 999999
        return 0

    with patch("obg.core.health.run", return_value=mock_result):
        with patch("obg.core.health.time.sleep"):
            with patch("obg.core.health.time.monotonic", side_effect=mock_time_monotonic):
                result = poll_smart_test("/dev/sdb", timeout_seconds=10, on_output=None)

    assert result is False
