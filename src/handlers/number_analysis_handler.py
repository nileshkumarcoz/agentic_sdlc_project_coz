import logging
from src.core.number_analysis import validate_input, find_min_max_middle

logger = logging.getLogger(__name__)


def handle_number_analysis(raw_inputs: dict) -> dict:
    """Orchestrates validation, computation, and response formatting."""
    logger.debug("number_analysis request received: inputs=%s", raw_inputs)

    validation = validate_input(raw_inputs)
    if not validation.is_valid:
        logger.warning(
            "Validation failed: field=%s, reason=%s",
            validation.error_field,
            validation.error_message,
        )
        return {
            "status": "error",
            "message": validation.error_message,
            "field": validation.error_field,
        }

    result = find_min_max_middle(validation.parsed_values)
    logger.info(
        "number_analysis result: largest=%s, smallest=%s, middle=%s",
        result.largest, result.smallest, result.middle,
    )
    return {
        "status": "success",
        "largest": result.largest,
        "smallest": result.smallest,
        "middle": result.middle,
        "inputs": result.inputs,
    }
