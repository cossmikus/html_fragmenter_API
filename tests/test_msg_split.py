# tests/test_msg_split.py

import pytest
from msg_split import split_message, SplitMessageError

def test_basic_split():
    html = """
    <p>First paragraph</p>
    <p>Second paragraph with <b>bold text</b></p>
    """ * 20
    fragments = list(split_message(html, max_len=200))
    assert len(fragments) > 1
    for fragment in fragments:
        assert len(fragment) <= 200
        # Basic check for matching tag counts:
        assert fragment.count('<p>') == fragment.count('</p>')
        assert fragment.count('<b>') == fragment.count('</b>')

def test_cannot_split():
    # A single block that is longer than max_len, with no internal block to split:
    long_text = "A" * 300
    # This <p> block alone is 313 chars => won't be splittable if max_len=200
    html = f"<p>Some block that is too long: {long_text}</p>"
    with pytest.raises(SplitMessageError, match="Unable to split HTML"):
        list(split_message(html, max_len=200))

def test_nested_tags():
    html = """
    <div>
        <span>Some content <b>with <i>nested</i></b></span>
    </div>
    """ * 10
    fragments = list(split_message(html, max_len=150))
    assert len(fragments) > 1
    for fragment in fragments:
        assert len(fragment) <= 150
        # Check matching tags
        assert fragment.count('<div>') == fragment.count('</div>')
        assert fragment.count('<span>') == fragment.count('</span>')
        assert fragment.count('<b>') == fragment.count('</b>')
        assert fragment.count('<i>') == fragment.count('</i>')
