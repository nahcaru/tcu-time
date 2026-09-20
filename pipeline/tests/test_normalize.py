from __future__ import annotations

import pytest

from pipeline.core.normalize import (
    normalize_course_dict,
    normalize_course_name,
    normalize_instructor_name,
    normalize_note,
    normalize_room,
    normalize_target_note,
)


def test_normalize_instructor_name():
    # Fullwidth space
    assert normalize_instructor_name("三宅\u3000弘晃") == "三宅 弘晃"
    # Multiple fullwidth and halfwidth spaces
    assert normalize_instructor_name(" 伊藤 \u3000 和也  ") == "伊藤 和也"
    # Halfwidth space already normalized
    assert normalize_instructor_name("平野 拓一") == "平野 拓一"
    # No space (e.g. foreign teacher single block)
    assert normalize_instructor_name("ボルジロフスカヤアンナ") == "ボルジロフスカヤアンナ"
    # Empty / None
    assert normalize_instructor_name("") == ""
    assert normalize_instructor_name(None) == ""


def test_normalize_course_name():
    # Fullwidth alphabets & fullwidth slash
    assert normalize_course_name("ＰＰＰ／ＰＦＩ特論") == "PPP/PFI特論"
    # Fullwidth parentheses
    assert normalize_course_name("特別講義（基礎Ｉ）") == "特別講義(基礎I)"
    # Halfwidth parentheses preserved
    assert normalize_course_name("特別講義(電気・化学I)") == "特別講義(電気・化学I)"
    # English title with comma missing space
    assert (
        normalize_course_name("Artificial Intelligence,Adv.")
        == "Artificial Intelligence, Adv."
    )
    # X-ray and CAD
    assert normalize_course_name("先端Ｘ線分析特論") == "先端X線分析特論"
    assert normalize_course_name("３次元ＣＡＤ特論") == "3次元CAD特論"
    # Leading / trailing whitespace
    assert normalize_course_name("  量子力学特論I  ") == "量子力学特論I"


def test_normalize_room():
    # Fullwidth parentheses in room
    assert (
        normalize_room("臨床実習室（2号館3階）")
        == "臨床実習室(2号館3階)"
    )
    # Fullwidth alphanumeric in room
    assert normalize_room("１３Ａ") == "13A"
    assert normalize_room(None) == ""


def test_normalize_target_note():
    # Tildes
    assert normalize_target_note("～25VLSI回路設計特論") == "~25VLSI回路設計特論"
    assert normalize_target_note("〜24偏微分方程式論") == "~24偏微分方程式論"
    assert normalize_target_note("~24水圏環境防災特論") == "~24水圏環境防災特論"
    # Parentheses in target note
    assert normalize_target_note("（23以降入学生対象）") == "(23以降入学生対象)"
    assert normalize_target_note(None) == ""


def test_normalize_note():
    assert normalize_note("対開講（月2,火2）") == "対開講(月2,火2)"
    assert normalize_note(" 対開講(月1,木1) ") == "対開講(月1,木1)"


def test_normalize_course_dict():
    raw_course = {
        "code": "smaz080211",
        "name": "ＰＰＰ／ＰＦＩ特論",
        "instructors": ["三宅\u3000弘晃", "伊藤 \u3000 和也"],
        "room": "臨床実習室（2号館3階）",
        "notes": "対開講（月2,火2）",
        "targets": [
            {"target_code": "08", "target_name": "都市", "note": "～25都市特論"},
        ],
    }
    normalized = normalize_course_dict(raw_course)
    assert normalized["name"] == "PPP/PFI特論"
    assert normalized["instructors"] == ["三宅 弘晃", "伊藤 和也"]
    assert normalized["room"] == "臨床実習室(2号館3階)"
    assert normalized["notes"] == "対開講(月2,火2)"
    assert normalized["targets"][0]["note"] == "~25都市特論"
