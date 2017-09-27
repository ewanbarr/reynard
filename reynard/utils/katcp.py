import re
import codecs
import json

"""
This regex is used to resolve escaped characters
in KATCP messages
"""
ESCAPE_SEQUENCE_RE = re.compile(r'''
    ( \\U........      # 8-digit hex escapes
    | \\u....          # 4-digit hex escapes
    | \\x..            # 2-digit hex escapes
    | \\[0-7]{1,3}     # Octal escapes
    | \\N\{[^}]+\}     # Unicode characters by name
    | \\[\\'"abfnrtv]  # Single-character escapes
    )''', re.UNICODE | re.VERBOSE)


def escape_string(s):
    return s.replace(" ", "\_")


def unescape_string(s):
    def decode_match(match):
        return codecs.decode(match.group(0), 'unicode-escape')
    return ESCAPE_SEQUENCE_RE.sub(decode_match, s)


def decode_katcp_message(s):
    """
    @brief      Render a katcp message human readable

    @params s   A string katcp message
    """
    return unescape_string(s).replace("\_", " ")


def pack_dict(x):
    return escape_string(json.dumps(x, separators=(',', ':')))


def unpack_dict(x):
    try:
        return json.loads(decode_katcp_message(x))
    except:
        return json.loads(x.replace("\_"," ").replace("\n","\\n"))