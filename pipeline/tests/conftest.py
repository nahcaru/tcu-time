from pathlib import Path

import pytest


@pytest.fixture
def reference_pdf_path() -> Path:
    return Path(__file__).resolve().parents[2] / "References" / "grad_timetable_front.pdf"
