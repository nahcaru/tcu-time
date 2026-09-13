from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Iterator

from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString

from pipeline.models import PDFMetadata, PDFType, Semester

logger = logging.getLogger(__name__)

GRAD_SECTION_HEADER = "大学院"
GRAD_DEPARTMENT = "総合理工学研究科"
ADVANCE_SECTION_HEADER = "先行履修"


@dataclass
class PdfLink:
    url: str
    label: str


def iter_siblings_until(start: Tag, stop_tags: set[str]) -> Iterator[Tag]:
    for sibling in start.next_siblings:
        if isinstance(sibling, NavigableString):
            continue
        if not isinstance(sibling, Tag):
            continue
        if sibling.name in stop_tags:
            return
        yield sibling


def extract_pdf_links(
    html: str,
    *,
    section_header: str = GRAD_SECTION_HEADER,
    department: str = GRAD_DEPARTMENT,
) -> list[PdfLink]:
    soup = BeautifulSoup(html, "html.parser")
    root = soup.find("div", id="main") or soup

    grad_section: Tag | None = None
    for section in root.find_all("section"):
        h3 = section.find("h3")
        if h3 and section_header in h3.get_text():
            grad_section = section
            break

    if grad_section is None:
        logger.warning("No <section> containing <h3> with '%s' found", section_header)
        return []

    target_h4: Tag | None = None
    for h4 in grad_section.find_all("h4"):
        if department in h4.get_text():
            target_h4 = h4
            break

    if target_h4 is None:
        logger.warning("No <h4> containing '%s' in graduate section", department)
        return []

    seen: set[str] = set()
    links: list[PdfLink] = []
    current_subheading = ""

    for sibling in iter_siblings_until(target_h4, {"h4", "hr"}):
        if sibling.name in {"h5", "h6"} or "■" in sibling.get_text():
            sub_text = sibling.get_text(strip=True)
            if "前期" in sub_text and "後期" not in sub_text:
                current_subheading = "【前期】"
            elif "後期" in sub_text and "前期" not in sub_text:
                current_subheading = "【後期】"
            elif "通年" in sub_text:
                current_subheading = "【通年】"

        anchors = sibling.find_all("a", href=True) if sibling.name != "a" else [sibling]
        for anchor in anchors:
            href = str(anchor["href"])
            text = anchor.get_text(strip=True)
            if not href.lower().endswith(".pdf"):
                continue

            if href.startswith("//"):
                href = "https:" + href
            elif href.startswith("/"):
                href = f"https://www.asc.tcu.ac.jp{href}"

            if href in seen:
                continue
            seen.add(href)

            if current_subheading and "前期" not in text and "後期" not in text:
                label = f"〈{department}〉{current_subheading}{text}"
            else:
                label = f"〈{department}〉{text}"

            links.append(PdfLink(url=href, label=label))

    logger.info(
        "Found %d PDF link(s) for '%s' in '%s' section",
        len(links),
        department,
        section_header,
    )
    return links


def extract_advance_pdf_links(
    html: str,
    *,
    section_header: str = ADVANCE_SECTION_HEADER,
) -> list[PdfLink]:
    soup = BeautifulSoup(html, "html.parser")
    root = soup.find("div", id="main") or soup

    advance_section: Tag | None = None
    for section in root.find_all("section"):
        h3 = section.find("h3")
        if h3 and section_header in h3.get_text():
            advance_section = section
            break

    if advance_section is None:
        logger.debug("No <section> containing <h3> with '%s' found", section_header)
        return []

    seen: set[str] = set()
    links: list[PdfLink] = []
    for anchor in advance_section.find_all("a", href=True):
        href = str(anchor["href"])
        text = anchor.get_text(strip=True)
        if not href.lower().endswith(".pdf"):
            continue
        if href.startswith("//"):
            href = "https:" + href
        elif href.startswith("/"):
            href = f"https://www.asc.tcu.ac.jp{href}"
        if href in seen:
            continue
        seen.add(href)
        links.append(PdfLink(url=href, label=text))

    logger.info("Found %d advance-enrollment PDF link(s) in '%s' section", len(links), section_header)
    return links


def classify_pdf_link(link_text: str, url: str | None = None) -> PDFMetadata:
    text = link_text.strip()

    if "変更一覧" in text or "変更" in text:
        pdf_type = PDFType.CHANGELOG
    elif "先行履修" in text:
        pdf_type = PDFType.ADVANCE_ENROLLMENT
    else:
        pdf_type = PDFType.TIMETABLE

    if pdf_type == PDFType.ADVANCE_ENROLLMENT:
        semester = None
    elif "前期・後期" in text or "通年" in text:
        semester = None
    elif "前期" in text and "後期" not in text:
        semester = Semester.SPRING
    elif "後期" in text and "前期" not in text:
        semester = Semester.FALL
    elif url:
        match = re.search(r"/20\d{2}/(\d{2})/", url)
        if match:
            month = int(match.group(1))
            if month in {8, 9, 10, 11, 12, 1}:
                semester = Semester.FALL
            elif month in {2, 3, 4, 5, 6, 7}:
                semester = Semester.SPRING
            else:
                semester = None
        else:
            semester = None
    else:
        semester = None

    is_tentative = "予定" in text or "（予定）" in text or "仮" in text

    return PDFMetadata(pdf_type=pdf_type, semester=semester, is_tentative=is_tentative)


def extract_academic_year(soup: BeautifulSoup) -> int:
    text = soup.get_text(" ", strip=True)
    match = re.search(r"(20\d{2})年度", text)
    if match:
        return int(match.group(1))
    return 0
