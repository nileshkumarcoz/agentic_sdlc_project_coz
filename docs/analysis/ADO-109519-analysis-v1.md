# Requirement Analysis

## Story ID: 109519 — Factorial Calculator

---

## 1. Restated Problem

Users need a reliable, input-validated factorial calculation feature within the application. Currently there is no dedicated utility to compute factorials, forcing users to rely on external tools or manual computation. The feature must accept a non-negative integer, validate it, compute the factorial, and surface either the correct result or a clear error message.

---

## 2. Business Goal

Provide an in-application mathematical utility that increases self-service capability for users solving mathematical problems, improving user satisfaction and reducing dependency on external calculators.

---

## 3. Stakeholders

| Stakeholder | Role / Interest |
|---|---|
| End User | Enters numbers and expects correct factorial results |
| Product Owner | Wants a correct, well-validated feature delivered per acceptance criteria |
| Developer | Implements the logic, validation, and UI integration |
| QA Engineer | Validates correctness, edge cases, and error handling |
| DevOps / CI | Ensures the feature builds and tests pass in the pipeline |

---

## 4. Functional Requirements

| ID | Requirement |
|---|---|
| FR-01 | The application SHALL provide an input mechanism for the user to enter a non-negative integer. |
| FR-02 | The application SHALL validate that the input is a non-negative integer (0, 1, 2, …). |
| FR-03 | The application SHALL reject negative integers and display a descriptive error message. |
| FR-04 | The application SHALL reject non-integer input (e.g., decimals, alphabetic characters, empty string) and display a descriptive error message. |
| FR-05 | The application SHALL compute and display the correct factorial value for valid input (0! = 1, 1! = 1, n! = n × (n-1)! for n > 1). |
| FR-06 | The application SHALL display the result clearly alongside the original input for context. |

---

## 5. Non-Functional Requirements

| ID | Requirement |
|---|---|
| NFR-01 | **Correctness**: The factorial algorithm must be mathematically accurate for all valid inputs within the supported range. |
| NFR-02 | **Performance**: Factorial computation for inputs up to n=1000 must complete within 200 ms. |
| NFR-03 | **Usability**: Error messages must be human-readable and actionable. |
| NFR-04 | **Maintainability**: Business logic (computation + validation) must be decoupled from the UI layer and covered by unit tests. |
| NFR-05 | **Scalability**: The implementation must handle arbitrarily large integers without overflow (use big-integer arithmetic). |
| NFR-06 | **Reliability**: The feature must not crash the application for any user-supplied input. |

---

## 6. In-Scope

- Input field / UI component for entering a non-negative integer.
- Client-side and/or server-side input validation.
- Factorial computation logic (iterative or recursive with memoisation).
- Result display component.
- Error message display for invalid inputs.
- Unit and integration tests for the above.

---

## 7. Out of Scope

- Gamma function / factorial for non-integer or floating-point numbers.
- Batch/bulk factorial calculations.
- Persisting calculation history to a database.
- User authentication or session management.
- Internationalisation (i18n) of error messages (first iteration).

---

## 8. Assumptions

- The project (`agentic_sdlc_project_coz`) is a Python-based application (web or CLI) given it is in the agentic SDLC project repository.
- Big-integer support is natively available (Python's `int` is arbitrary precision).
- A maximum input cap of n = 10,000 is acceptable to prevent excessive computation time on the server/client.
- The UI layer already has a pattern for displaying success and error states that this feature will follow.

---

## 9. Identified Gaps & Open Questions

| ID | Gap / Question | Owner | Priority |
|---|---|---|---|
| GAP-01 | What is the maximum integer value the application should accept? (Assumed 10,000 — needs PO confirmation.) | Product Owner | High |
| GAP-02 | Is this a web API endpoint, a web UI page, or a CLI command? The story does not specify the interface type. | Product Owner / Tech Lead | High |
| GAP-03 | Should results for large n be truncated/summarised in the UI (e.g., scientific notation for n > 100)? | UX / Product Owner | Medium |
| GAP-04 | Is server-side validation alone sufficient, or is client-side (JS) validation also required? | Tech Lead | Medium |
| GAP-05 | Are there accessibility (WCAG) requirements for the input and error message components? | UX | Low |

---

## 10. Risks

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R-01 | Very large inputs (n > 10,000) cause slow response or memory spikes. | Medium | High | Enforce an upper-bound limit with a validation rule. |
| R-02 | Integer overflow if language/runtime does not support big integers natively. | Low (Python handles it) | High | Confirm runtime; add an integration test for n=1000. |
| R-03 | Ambiguous error messages confuse users. | Low | Medium | Define standard error message strings in a constants file. |
| R-04 | Requirement gaps (GAP-01, GAP-02) delay implementation. | Medium | Medium | Schedule a quick refinement session before sprint start. |
