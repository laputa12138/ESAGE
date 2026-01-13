import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import json_repair

logger = logging.getLogger(__name__)

def clean_and_parse_json(raw_llm_output: str, context: Optional[str] = None) -> Any:
    """
    Cleans a raw string output from an LLM, attempting to make it valid JSON,
    then parses it. Handles common issues like markdown code blocks and comments.
    Uses json_repair for robustness.

    Args:
        raw_llm_output: The raw string output from the LLM.
        context: Optional context string for logging, e.g., "outline_refinement".

    Returns:
        The parsed JSON data (e.g., dict, list), or None if parsing fails
        after cleaning attempts.
    """
    if not raw_llm_output or not raw_llm_output.strip():
        logger.warning(f"JSON parsing: Empty raw LLM output received. Context: {context or 'N/A'}")
        return None

    cleaned_output = raw_llm_output.strip()

    # 1. Remove Markdown code block fences
    # Matches ```json ... ``` or ``` ... ```
    match = re.match(r"^\s*```(?:[a-zA-Z0-9]+)?\s*(.*?)\s*```\s*$", cleaned_output, re.DOTALL | re.IGNORECASE)
    if match:
        cleaned_output = match.group(1).strip()
        logger.debug(f"JSON parsing: Removed markdown fences. Context: {context or 'N/A'}")

    if not cleaned_output:
        logger.warning(f"JSON parsing: Output became empty after attempting to strip markdown. Context: {context or 'N/A'}")
        return None

    # 2. Parse with json_repair
    # json_repair handles comments, trailing commas, missing quotes, etc.
    try:
        parsed_json = json_repair.loads(cleaned_output)
        logger.debug(f"JSON parsing: Successfully parsed with json_repair. Context: {context or 'N/A'}")
        return parsed_json
    except Exception as e:
        logger.warning(
            f"JSON parsing: Failed with json_repair. Error: {e}. "
            f"Context: {context or 'N/A'}. Raw input: '{cleaned_output[:500]}...'"
        )
        return None

# Example usage (for testing purposes if this file is run directly)
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    test_cases = [
        ('{\n  "key": "value"\n}', {"key": "value"}),
        ('```json\n{\n  "key": "value"//comment\n}\n```', {"key": "value"}),
        ('// Single line comment before json\n{\n  "name": "Test",\n  "version": "1.0", // trailing comment\n  "valid": true,\n}', {"name": "Test", "version": "1.0", "valid": True}),
        ('```\n{\n  "data": [1, 2, 3]\n}\n```', {"data": [1, 2, 3]}),
        ('{\n  "action": "modify_level",//调整层级结构以确保逻辑层次正确\n"id": "ch_1ecb083a",\n"new_level": 2\n}', {"action": "modify_level", "id": "ch_1ecb083a", "new_level": 2}),
        ('[\n  // comment\n  {\n    "action": "delete",\n    "id": "ch_04735923"\n  }\n]', [{"action": "delete", "id": "ch_04735923"}]),
        ('Invalid JSON', None),
        ('{\n  "key": "value",\n  "another_key": "another_value", // comment\n}', {"key": "value", "another_key": "another_value"}),
        # Test case from logs (outline_refinement_agent)
        ('''
[
  // 调整层级结构以确保逻辑层次正确
  {
    "action": "modify_level",
    "id": "ch_1ecb083a",
    "new_level": 2
  },
  {
    "action": "delete",
    "id": "ch_04735923"
  }
]''', [{"action": "modify_level", "id": "ch_1ecb083a", "new_level": 2}, {"action": "delete", "id": "ch_04735923"}]),
        # Test case from logs (chapter_writer_agent for relevance)
        ('''
```json
{
  "is_relevant": false
}
```''', {"is_relevant": False}),
        ('''
```json
{
  "is_relevant": true
}
```''', {"is_relevant": True}),
        ('   ```json\n{\n  "is_relevant": true\n}\n```   ', {"is_relevant": True}),
        ('Empty string test', None),
        ('', None),
        ('   ', None),
        ('// Only comments\n// Line 2', None) # Only comments
    ]

    print(f"json_repair available: {bool(json_repair)}")

    for i, (input_str, expected_output) in enumerate(test_cases):
        context_for_test = f"test_case_{i+1}"
        if input_str == 'Empty string test':
            result = clean_and_parse_json("", context=context_for_test)
        else:
            result = clean_and_parse_json(input_str, context=context_for_test)

        if result == expected_output:
            print(f"Test Case {i+1} PASSED")
        else:
            print(f"Test Case {i+1} FAILED: Input='{input_str[:50]}...', Expected='{expected_output}', Got='{result}'")

    # Test for a case where the JSON is actually malformed beyond repair
    truly_malformed_json = '{\n  "key": "value",\n  "error": \n Oops, no value here \n}'
    result_malformed = clean_and_parse_json(truly_malformed_json, context="truly_malformed_test")
    if result_malformed is None:
        print("Truly Malformed JSON Test PASSED (returned None as expected)")
    else:
        print(f"Truly Malformed JSON Test FAILED: Expected=None, Got='{result_malformed}'")
