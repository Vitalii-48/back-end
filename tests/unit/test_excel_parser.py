# tests/unit/test_excel_parser.py
from io import BytesIO
from openpyxl import Workbook

from app.utils.excel_parser import parse_excel_to_quizzes, EXPECTED_HEADERS


def make_excel_bytes(rows: list[tuple]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(EXPECTED_HEADERS)
    for row in rows:
        ws.append(row)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_parse_groups_questions_and_answers():
    content = make_excel_bytes([
        ("Quiz A", "desc", "Q1", "Answer 1", True),
        ("Quiz A", "desc", "Q1", "Answer 2", False),
        ("Quiz A", "desc", "Q2", "Answer 1", False),
        ("Quiz A", "desc", "Q2", "Answer 2", True),
    ])

    quizzes, errors = parse_excel_to_quizzes(content)

    assert errors == []
    assert len(quizzes) == 1
    assert quizzes[0].title == "Quiz A"
    assert len(quizzes[0].questions) == 2
    assert len(quizzes[0].questions[0].answers) == 2


def test_parse_reports_empty_required_field_without_crashing():
    content = make_excel_bytes([
        (None, "desc", "Q1", "Answer 1", True),
    ])

    quizzes, errors = parse_excel_to_quizzes(content)

    assert quizzes == []
    assert len(errors) == 1
    assert "must not be empty" in errors[0].message.lower()