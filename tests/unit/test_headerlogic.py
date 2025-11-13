# tests/unit/test_headerlogic.py

from autoheader.headerlogic import header_line_for

def test_header_line_for_no_year():
    """Tests that a template without a year placeholder is unchanged."""
    template = "# {path}"
    result = header_line_for("foo.py", template)
    assert "{year}" not in result

def test_header_line_for_simple_year():
    """Tests that the current year is inserted."""
    from datetime import datetime
    current_year = datetime.now().year
    template = "Copyright (c) {year}"
    result = header_line_for("foo.py", template)
    assert str(current_year) in result
    assert f"-{current_year}" not in result

def test_header_line_for_smart_year_update():
    """Tests that an older year is updated to a range."""
    from datetime import datetime
    current_year = datetime.now().year
    template = "Copyright (c) {year}"
    existing_header = "Copyright (c) 2020"
    result = header_line_for("foo.py", template, existing_header=existing_header)
    assert f"2020-{current_year}" in result

def test_header_line_for_smart_year_no_update_needed():
    """Tests that a current year is not turned into a range."""
    from datetime import datetime
    current_year = datetime.now().year
    template = "Copyright (c) {year}"
    existing_header = f"Copyright (c) {current_year}"
    result = header_line_for("foo.py", template, existing_header=existing_header)
    assert str(current_year) in result
    assert f"-{current_year}" not in result
