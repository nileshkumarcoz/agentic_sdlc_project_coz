import pytest
from src.core.number_analysis import (
    find_largest,
    find_smallest,
    find_min_max_middle,
    validate_input,
)
from src.handlers.number_analysis_handler import handle_number_analysis


@pytest.mark.parametrize("inputs,expected_largest,expected_smallest,expected_middle", [
    ([1.0, 2.0, 3.0], 3.0, 1.0, 2.0),
    ([-5.0, -1.0, -9.0], -1.0, -9.0, -5.0),
    ([-10.0, 0.0, 5.0], 5.0, -10.0, 0.0),
    ([1.1, 2.2, 1.9], 2.2, 1.1, 1.9),
    ([5.0, 5.0, 3.0], 5.0, 3.0, 5.0),
    ([5.0, 2.0, 2.0], 5.0, 2.0, 2.0),
    ([7.0, 7.0, 7.0], 7.0, 7.0, 7.0),
    ([1e308, 1e307, 0.0], 1e308, 0.0, 1e307),
])
def test_find_min_max_middle(inputs, expected_largest, expected_smallest, expected_middle):
    result = find_min_max_middle(inputs)
    assert result.largest == expected_largest
    assert result.smallest == expected_smallest
    assert result.middle == expected_middle
    assert result.inputs == inputs


def test_find_largest_and_smallest_standalone():
    assert find_largest([3.0, 1.0, 2.0]) == 3.0
    assert find_smallest([3.0, 1.0, 2.0]) == 1.0


def test_find_largest_wrong_length():
    with pytest.raises(ValueError, match="Exactly 3 numbers are required"):
        find_largest([1.0, 2.0])


def test_find_smallest_wrong_length():
    with pytest.raises(ValueError, match="Exactly 3 numbers are required"):
        find_smallest([1.0])


def test_find_min_max_middle_wrong_length():
    with pytest.raises(ValueError, match="Exactly 3 numbers are required"):
        find_min_max_middle([1.0, 2.0])


@pytest.mark.parametrize("bad_value,field", [
    ("a", "number1"),
    ("@", "number1"),
    ("nan", "number1"),
    ("inf", "number1"),
    ("", "number1"),
    ("1" * 51, "number1"),
])
def test_validate_input_invalid_number1(bad_value, field):
    raw = {"number1": bad_value, "number2": "2", "number3": "3"}
    result = validate_input(raw)
    assert not result.is_valid
    assert result.error_field == field


def test_validate_input_invalid_third_field():
    raw = {"number1": "1", "number2": "2", "number3": "x"}
    result = validate_input(raw)
    assert not result.is_valid
    assert result.error_field == "number3"


def test_validate_input_valid():
    raw = {"number1": "10", "number2": "42.5", "number3": "-3"}
    result = validate_input(raw)
    assert result.is_valid
    assert result.parsed_values == [10.0, 42.5, -3.0]


def test_handle_number_analysis_success():
    resp = handle_number_analysis({"number1": "10", "number2": "42.5", "number3": "-3"})
    assert resp["status"] == "success"
    assert resp["largest"] == 42.5
    assert resp["smallest"] == -3.0
    assert resp["middle"] == 10.0


def test_handle_number_analysis_error():
    resp = handle_number_analysis({"number1": "abc", "number2": "2", "number3": "3"})
    assert resp["status"] == "error"
    assert resp["field"] == "number1"
    assert "abc" in resp["message"]
