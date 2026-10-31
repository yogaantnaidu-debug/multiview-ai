"""Server-side channel validation (the browser's input is never trusted)."""
from app.channels import MAX_STREAMS, clean_channels


def test_valid_names_are_lowercased_and_kept_in_order():
    assert clean_channels(["Shroud", " pokimane ", "summit1g"]) == ["shroud", "pokimane", "summit1g"]


def test_length_limits():
    assert clean_channels(["abc"]) == []           # 3 chars: too short
    assert clean_channels(["abcd"]) == ["abcd"]    # 4: ok
    assert clean_channels(["a" * 25]) == ["a" * 25]
    assert clean_channels(["a" * 26]) == []        # 26: too long


def test_bad_characters_are_rejected():
    assert clean_channels(["bad name", "bad!", "x;DROP", "name\nnext", "#shroud"]) == []


def test_duplicates_removed_case_insensitively():
    assert clean_channels(["shroud", "SHROUD"]) == ["shroud"]


def test_capped_at_max_streams():
    names = [f"chan{i:02d}" for i in range(10)]
    assert len(clean_channels(names)) == MAX_STREAMS


def test_non_list_input_is_safe():
    assert clean_channels("shroud") == []
    assert clean_channels(None) == []
    assert clean_channels({"a": 1}) == []
    # Non-strings are dropped. (A bug found by this test: str(None) == "none" passed validation.)
    assert clean_channels([123456, None, True]) == []
