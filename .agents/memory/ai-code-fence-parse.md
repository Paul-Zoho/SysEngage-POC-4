---
name: AI response code fence stripping
description: Claude wraps JSON responses in ```json ... ``` fences; bare json.loads() fails without stripping them first.
---

**Rule:** All AI parse helpers that call `json.loads(msg.content[0].text)` must first strip markdown code fences.

**Why:** Claude (claude-sonnet-4-5 and likely all claude-* models) wraps structured JSON responses in ` ```json ... ``` ` fences even when the prompt asks for raw JSON. A bare `json.loads()` on the fenced response raises `JSONDecodeError: Expecting value: line 1 column 1`.

**How to apply:** Add a `_strip_code_fence` helper to any module that parses AI JSON responses:

```python
import re

def _strip_code_fence(text_: str) -> str:
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text_, re.DOTALL)
    return m.group(1).strip() if m else text_.strip()
```

Then call `json.loads(_strip_code_fence(text_))` instead of `json.loads(text_)`.

Already applied in:
- `mechanisms/domain_derivation/stage2_ai_grouping.py` — `_parse_grouping_response`, `_parse_incremental_response`
- `mechanisms/domain_derivation/stage3_structural_validation.py` — `_parse_repair_response`

Any new mechanism that parses AI JSON output needs this pattern from the start.
