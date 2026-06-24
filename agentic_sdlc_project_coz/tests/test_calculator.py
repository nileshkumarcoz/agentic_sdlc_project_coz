import pytest
from add_two_numbers.calculator import validate_input, calculate_sum


@pytest.mark.parametrize("a,b,expected", [
    ("3", "7", 10.0),
    ("1.5", "2.5", 4.0),
    ("-5", "3", -2.0),
    ("0", "0", 0.0),
    ("1e15", "1e15", 2e15),
    ("10", "0.5", 10.5),
])
def test_calculate_sum(a, b, expected):
    assert calculate_sum(validate_input(a), validate_input(b)) == expected


@pytest.mark.parametrize("bad", ["abc", "", " ", "@"])
def test_validate_input_raises(bad):
    with pytest.raises(ValueError):
        validate_input(bad)
