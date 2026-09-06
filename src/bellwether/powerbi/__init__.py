"""Power BI project generation — TMDL and report JSON, never a binary.

Power BI is a **thin consumer**: it reads the star and renders measures generated from
``transform/semantic.py``. No DAX in this package is hand-authored, and a test asserts that
regenerating reproduces the committed files exactly, so a measure edited in the tool fails the
build rather than silently becoming a second definition.

That is a weaker guarantee than the Excel reconciliation and is stated as weaker: it proves the
DAX was generated from the definition, not that it evaluates correctly. See
``docs/phases/phase-05-spec.md`` for why no stronger check is available in CI.
"""

from __future__ import annotations
