def validate_input(value: str) -> float:
    if not value.strip():
        raise ValueError("Input must not be empty.")
    try:
        return float(value.strip())
    except ValueError:
        raise ValueError(f"'{value.strip()}' is not a valid numeric value.")


def calculate_sum(a: float, b: float) -> float:
    return a + b
