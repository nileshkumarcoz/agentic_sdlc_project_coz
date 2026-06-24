from add_two_numbers.calculator import validate_input, calculate_sum
from add_two_numbers import audit_logger


def main() -> None:
    print("=== Add Two Numbers ===")
    raw1 = input("Enter the first number: ")
    raw2 = input("Enter the second number: ")
    try:
        num1 = validate_input(raw1)
        num2 = validate_input(raw2)
        result = calculate_sum(num1, num2)
        print(f"Result: {num1} + {num2} = {result}")
        audit_logger.log_success(raw1, raw2, result)
    except ValueError as e:
        print(f"Error: {e}")
        audit_logger.log_failure(raw1, raw2, str(e))


if __name__ == "__main__":
    main()
