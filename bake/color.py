import re

try:
    import colorama
except ImportError:
    colorama = None
else:
    from colorama import Fore, Back, Style
    colorama.init()

TokenPattern = re.compile(r'\[!([bcgmryBCGMRY])?\]')
Tokens = {
    'b': Fore.BLUE,
    'c': Fore.CYAN,
    'g': Fore.GREEN,
    'm': Fore.MAGENTA,
    'r': Fore.RED,
    'y': Fore.YELLOW,
}

def _replace_tokens(match):
    token = match.group(1)
    if not token:
        return Style.RESET_ALL

    replacement = Tokens[token.lower()]
    if token.isupper():
        return replacement + Style.BRIGHT
    else:
        return replacement

def ansify(value, colorize=False, reset=True):
    if colorama and colorize:
        value = TokenPattern.sub(_replace_tokens, value)
    else:
        return TokenPattern.sub('', value)
    if reset:
        value = value + Style.RESET_ALL
    return value
