from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)


@dataclass
class SyllabusFields:
    category: str | None = None
    credits: float | None = None


def find_label_value(rows: list[Tag], label_substr: str) -> str | None:
    for tr in rows:
        label_td = tr.find("td", class_="label_kougi")
        if label_td and label_substr in label_td.get_text():
            value_td = tr.find("td", class_="kougi")
            if value_td:
                return value_td.get_text(strip=True).replace("\xa0", "")
    return None


_GRAD_CATEGORY_RE = re.compile(r"■(.+?)■")
_UNDERGRAD_CATEGORY_RE = re.compile(r"\[(.+?)・(.+?)\]")


def parse_syllabus_html(html: str) -> SyllabusFields:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="syllabus_detail")
    if table is None:
        logger.warning("No syllabus_detail table found in HTML")
        return SyllabusFields()

    rows = table.find_all("tr")  # type: ignore[union-attr]
    fields = SyllabusFields()

    credits_text = find_label_value(rows, "単位数")
    if credits_text:
        try:
            fields.credits = float(credits_text)
        except ValueError:
            logger.warning("Could not parse credits: %r", credits_text)

    category_text = find_label_value(rows, "分野系列")
    if category_text:
        grad_match = _GRAD_CATEGORY_RE.search(category_text)
        if grad_match:
            fields.category = grad_match.group(1)
        else:
            undergrad_match = _UNDERGRAD_CATEGORY_RE.search(category_text)
            if undergrad_match:
                fields.category = undergrad_match.group(1)
            else:
                fields.category = category_text if category_text else None

    return fields
