import math
from dataclasses import dataclass
from typing import Optional

MAX_INPUT_LENGTH = 50


@dataclass
class ValidationResult:
    is_valid: bool
    parsed_values: Optional[list] = None
    error_message: Optional[str] = None
    error_field: Optional[str] = None


@dataclass
class NumberAnalysisResult:
    largest: float
    smallest: float
    middle: float
    inputs: list


def validate_input(raw_inputs: dict) -> ValidationResult:
    """Validates that all three inputs are parseable as finite floats."""
    parsed: list = []
    for field in ["number1", "number2", "number3"]:
        value = raw_inputs.get(field, "")
        if isinstance(value, str):
            value = value.strip()
        else:
            value = str(value)
        if not value:
            return ValidationResult(
                is_valid=False,
                error_message=f"Field '{field}' cannot be empty.",
                error_field=field,
            )
        if len(value) > MAX_INPUT_LENGTH:
            return ValidationResult(
                is_valid=False,
                error_message=f"Field '{field}' exceeds maximum length of {MAX_INPUT_LENGTH}.",
                error_field=field,
            )
        try:
            number = float(value)
        except ValueError:
            return ValidationResult(
                is_valid=False,
                error_message=f"Invalid input: '{value}' is not a valid number.",
                error_field=field,
            )
        if math.isnan(number) or math.isinf(number):
            return ValidationResult(
                is_valid=False,
                error_message=f"Invalid input: '{value}' is not a finite number.",
                error_field=field,
            )
        parsed.append(number)
    return ValidationResult(is_valid=True, parsed_values=parsed)


def find_largest(numbers: list) -> float:
    """Returns the maximum value from a list of exactly 3 floats."""
    if len(numbers) != 3:
        raise ValueError("Exactly 3 numbers are required.")
    return max(numbers)


def find_smallest(numbers: list) -> float:
    """Returns the minimum value from a list of exactly 3 floats."""
    if len(numbers) != 3:
        raise ValueError("Exactly 3 numbers are required.")
    return min(numbers)


def find_min_max_middle(numbers: list) -> NumberAnalysisResult:
    """Returns largest, smallest, and middle (median) from exactly 3 floats."""
    if len(numbers) != 3:
        raise ValueError("Exactly 3 numbers are required.")
    sorted_nums = sorted(numbers)
    return NumberAnalysisResult(
        largest=sorted_nums[2],
        smallest=sorted_nums[0],
        middle=sorted_nums[1],
        inputs=numbers,
    )
