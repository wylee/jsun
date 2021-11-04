class DecodeError(ValueError):
    def __init__(self, string, position, message):
        line = string.count("\n", 0, position) + 1
        column = position - string.rfind("\n", 0, position)
        super_message = (
            f"{message} at line {line} column {column} (position {position})"
        )
        super().__init__(super_message)
        self.string = string
        self.message = message
        self.position = position
        self.line = line
        self.column = column


class ExpectedBracketError(DecodeError):
    def __init__(self, string, position, bracket, message=None):
        if message is None:
            message = f"Expected bracket `{bracket}`"
        super().__init__(string, position, message)
        self.bracket = bracket


class ExpectedDelimiterError(DecodeError):
    def __init__(self, string, position, delimiter, message=None):
        if message is None:
            message = f"Expected delimiter `{delimiter}`"
        super().__init__(string, position, message)
        self.delimiter = delimiter


class ExpectedKeyError(DecodeError):
    def __init__(self, string, position, message="Expected key"):
        super().__init__(string, position, message)


class ExpectedValueError(DecodeError):
    def __init__(self, string, position, message="Expected value"):
        super().__init__(string, position, message)


class ExtraneousDataError(DecodeError):
    def __init__(
        self,
        string,
        position,
        message="Extraneous data (likely indicating a malformed JSON document)",
    ):
        super().__init__(string, position, message)


class UnexpectedCharError(DecodeError):
    def __init__(self, string, position, char, message=None):
        if message is None:
            message = f"Unexpected char `{char}`"
        super().__init__(string, position, message)
        self.char = char


class UnknownCharError(DecodeError):
    def __init__(self, string, position, char, message=None):
        if message is None:
            message = f"Unknown char `{char}`"
        super().__init__(string, position, message)
        self.char = char


class UnmatchedBracketError(DecodeError):
    def __init__(self, string, bracket, position, message=None):
        if message is None:
            message = f"Unmatched bracket `{bracket}`"
        super().__init__(string, position, message)
        self.bracket = bracket


class ScanStringError(DecodeError):
    def __init__(self, string, position, message=None):
        if message is None:
            message = "Error scanning string"
        super().__init__(string, position, message)


class INIDecodeError(DecodeError):
    def __init__(self, string, position, message):
        super_message = f"{message} at position {position}"
        super(ValueError, self).__init__(super_message)
        self.string = string
        self.message = message
        self.position = position
