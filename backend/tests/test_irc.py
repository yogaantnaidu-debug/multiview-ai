"""IRC line parsing, using real-looking Twitch lines."""
from app.irc import parse_line


def test_privmsg():
    line = ":alice!alice@alice.tmi.twitch.tv PRIVMSG #shroud :what a shot\r\n"
    assert parse_line(line) == ("PRIVMSG", "shroud", "alice", "what a shot")


def test_message_text_may_contain_colons():
    line = ":bob!bob@bob.tmi.twitch.tv PRIVMSG #shroud :score: 2:1 :)"
    assert parse_line(line)[3] == "score: 2:1 :)"


def test_channel_is_lowercased():
    assert parse_line(":a!a@a PRIVMSG #ShRoUd :hi")[1] == "shroud"


def test_tagged_line_is_tolerated():
    line = "@badge-info=;color=#FF0000;display-name=Alice :alice!alice@alice.tmi.twitch.tv PRIVMSG #shroud :hi"
    assert parse_line(line) == ("PRIVMSG", "shroud", "alice", "hi")


def test_ping():
    assert parse_line("PING :tmi.twitch.tv") == ("PING", ":tmi.twitch.tv")


def test_other_lines_are_ignored():
    assert parse_line(":tmi.twitch.tv 001 justinfan123 :Welcome, GLHF!") is None
    assert parse_line(":justinfan123!justinfan123@justinfan123.tmi.twitch.tv JOIN #shroud") is None
    assert parse_line("") is None
    assert parse_line("\r\n") is None


def test_privmsg_to_a_user_not_a_channel_is_ignored():
    assert parse_line(":a!a@a PRIVMSG someone :hi") is None
