"""JSONish Decoder

In addition to standard JSON, the JSONish decoder also supports/handles
the following:

- Trailing commas

- Line comments starting with //

- Any valid Python int or float:
  - Literal binary, octal, and hex values
  - Underscore separators in numbers
  - Unary plus operator

- Math constants:
  - inf, nan, E, π, PI, τ, TAU
  - Infinity, NaN

- Empty input strings will be converted to ``None`` rather than raising
  an exception.

- Literal (unquoted) dates & times:
  - 2021-06
  - 2021-06-23
  - 2021-06-23T12:00
  - 2021-06-23T12:00Z
  - 2021-06-23T12:00-07:00
  - 12:00 (today's date at noon)

.. note:: For dates and times, when a time zone isn't specified, the
    local time zone will be used.

- An object converter can be specified to convert JSON objects into a
  custom type (or types). By default, JSON objects will be converted to
  :class:`scanner.JSONObject`s, which allows properties to be accessed
  with either dotted or bracket notation.

- Loading config from INI files with values encoded as JSON.

- *All* scanning methods can be overridden if some additional
  customization is required.

- A prescan method can be provided to handle values before the JSON
  scanners are applied.

- A fallback scanner method can be provided to handle additional types
  of values if none of the default scanners are suitable.

.. note:: See details below in :func:`decode` for using prescan or a
    fallback scanner.

Examples::

    >>> decode("+1")
    1
    >>> decode("1_000")
    1000
    >>> decode("[0b11]")
    [3]
    >>> d = decode("2021-06-24")
    >>> d.timetuple()[:5]
    (2021, 6, 24, 0, 0)
    >>> d.tzinfo
    tzlocal()
    >>> decode(" [1, 2 ,  3  ,   ] ")
    [1, 2, 3]
    >>> decode("[[]]")
    [[]]

"""
from configparser import ConfigParser, ExtendedInterpolation
from pathlib import Path
from typing import Any, Callable, Optional, TextIO, Tuple, Union

from . import scanner
from .exc import INIDecodeError
from .obj import JSONObject
from .scanner import Scanner, Scanner as Decoder


__all__ = ["decode", "decode_file", "Decoder"]


# Signature for prescanner and fallback scanner functions
AltScannerFunc = Callable[[Scanner, Callable, str, int], Tuple[Any, int]]


def decode(
    string: str,
    *,
    strict: bool = True,
    prescan: Optional[AltScannerFunc] = None,
    scan_object: Callable = scanner.scan_object,
    object_converter: Callable = JSONObject,
    scan_array: Callable = scanner.scan_array,
    scan_string: Callable = scanner.scan_string,
    scan_date: Callable = scanner.scan_date,
    scan_number: Callable = scanner.scan_number,
    fallback_scanner: Optional[AltScannerFunc] = None,
    enable_extras: bool = True,
    ignore_extra_data: bool = False,
    ini=False,
) -> Union[Any, Tuple[Any, int]]:
    """Scan JSONish string and return a Python object.

    - JSON object -> Python object (see below)
    - JSON array -> Python list
    - JSON string -> Python string
    - Literal date string (no quotes) -> Python datetime
    - JSON number -> Python number (int or float)
    - Empty string -> None

    By default, JSON objects are converted to simple Python namespace
    objects that allow attributes to be accessed via dotted or bracket
    notation. These objects can be converted to plain dicts with
    ``dict(obj)`` or you can use ``object_converter=None`` to get back
    plain dicts.

    A different ``object_converter`` can be passed to customize object
    creation, perhaps based on a type field::

        def converter(obj):
            if "__type__" in obj:
                # Convert to type based on __type__
                T = types[obj["__type__"]]
                return T(**obj)
            # Don't convert since no type was specified
            return obj

    When errors are encountered, various kinds of exceptions are
    thrown. These all derive from :class:`DecodeError`, which in turn
    derives from the builtin :class:`ValueError`.

    Examples::

        >>> import arrow, math

        >>> decode("") is None
        True

        >>> d = decode("2021-06-23")
        >>> d.timetuple()[:5]
        (2021, 6, 23, 0, 0)

        >>> t = arrow.now()
        >>> d = decode("12:00")
        >>> d.timetuple()[:5] == (t.year, t.month, t.day, 12, 0)
        True

        >>> d = decode("2021-06-23T12:00")
        >>> d.timetuple()[:6]
        (2021, 6, 23, 12, 0, 0)

        >>> decode("[inf, nan]")
        [inf, nan]

        >>> decode("E") == math.e
        True
        >>> (decode("π"), decode("PI")) == (math.pi, math.pi)
        True
        >>> (decode("τ"), decode("TAU")) == (math.tau, math.tau)
        True

        >>> decode("0"), decode("+0"), decode("-0"), decode("000")
        (0, 0, 0, 0)
        >>> decode("1"), decode("+1"), decode("-1")
        (1, 1, -1)

        >>> decode("1.0"), decode("+1.0"), decode("-1.0")
        (1.0, 1.0, -1.0)

        >>> decode("0b11"), decode("0o11"), decode("0x11")
        (3, 9, 17)

        >>> decode("{}", object_converter=None), decode("[]")
        ({}, [])

        >>> decode("[0b11, 11, 0x11]")
        [3, 11, 17]

    When the ``ignore_extra_data`` flag is set, a tuple will be returned
    containing 1) a Python object representing the part of the JSON
    string that was successfully parsed and 2) the index in the JSON
    string where the extra data starts. In most cases, extra data
    indicates an error, but this flag can be used to intentionally
    include extra data:

        >>> decode('{} # ignored', object_converter=None, ignore_extra_data=True)
        ({}, 3)

    There are a couple of advanced/esoteric/low level features for use
    where additional customization of parsing is required:

    - The prescanner. This is a callable that takes the scanner
      instance, the primary scan function, the JSON input string, and
      the current position; it can either return a value and the next
      position or ``None``. Returning ``None`` indicates that the
      prescanner didn't handle the string and that the regular scanners
      should be tried.

    - The fallback scanner. This is a callable that takes a scanner
      instance, the primary scan function, the JSON input string, and
      the current position; it must return a Python value along with
      the next position.

    """
    instance = scanner.Scanner(
        strict=strict,
        prescan=prescan,
        scan_object=scan_object,
        object_converter=object_converter,
        scan_array=scan_array,
        scan_string=scan_string,
        scan_date=scan_date,
        scan_number=scan_number,
        enable_extras=enable_extras,
        fallback_scanner=fallback_scanner,
    )
    if ini:
        return decode_ini(string, instance)
    return instance.decode(string, ignore_extra_data=ignore_extra_data)


def decode_ini(string, scanner):
    """Decode INI file with JSONish values.

    INI section and setting names are split on dots to create sub-dicts.
    For example::

        [section.one]
        a.b = 1

    will result in the following dict::

        {"section": "one": {"a": {"b": 1}}}

    To disable splitting a name, wrap it in parentheses. For example::

        [(section.one)]
        (a.b) = 1

    will result in the following dict::

        {"section.one": {"a.b": 1}}

    """
    result = {}
    parser = ConfigParser(interpolation=ExtendedInterpolation())
    parser.optionxform = lambda option: option
    parser.read_string(string)

    for section_name in parser.sections():
        obj = result
        section_path = parse_ini_name(section_name)
        for segment in section_path[:-1]:
            if segment not in obj:
                obj[segment] = {}
            obj = obj[segment]
        obj[section_path[-1]] = section_config = {}

        section_items = parser[section_name]
        for raw_name, raw_value in section_items.items():
            obj = section_config
            path = parse_ini_name(raw_name)
            for segment in path[:-1]:
                if segment not in obj:
                    obj[segment] = {}
                obj = obj[segment]
            value, _ = scanner.scan(raw_value)
            obj[path[-1]] = value

    return result


def parse_ini_name(name):
    """Parse section and setting names from INI file."""
    # NOTE: Groups can't be nested, so this is simplistic

    if "(" not in name and ")" not in name:
        return name.split(".")

    j = 0
    segments = []
    last_right_paren = 0

    while True:
        i = name.find("(", j)
        if i == -1:
            break

        unmatched_i = name.find(")", j)
        if -1 < unmatched_i < i:
            raise INIDecodeError(name, unmatched_i, f"Unmatched ) in name '{name}'")

        before = name[j:i]
        if before:
            if not before.endswith("."):
                raise INIDecodeError(name, i - 1, f"Expected dot in name '{name}'")
            segments.append(before[:-1])

        j = name.find(")", i + 1)
        if j == -1:
            raise INIDecodeError(name, i, f"Unmatched ( in name '{name}'")
        last_right_paren = j

        nested_i = name.find("(", i + 1)
        if -1 < nested_i < j:
            raise INIDecodeError(name, nested_i, f"Nested ( in name '{name}'")

        part = name[i + 1 : j]
        segments.append(part)

    unmatched_i = name.find(")", last_right_paren + 1)
    if unmatched_i != -1:
        raise INIDecodeError(name, unmatched_i, f"Unmatched ) in name '{name}'")

    after = name[j + 1 :]
    if after:
        if not after.startswith("."):
            raise INIDecodeError(name, j + 1, f"Expected dot in name '{name}'")
        segments.append(after[1:])

    return segments


def decode_file(
    file: Union[str, Path, TextIO],
    *,
    strict: bool = True,
    prescan: Optional[AltScannerFunc] = None,
    scan_object: Callable = scanner.scan_object,
    object_converter: Callable = JSONObject,
    scan_array: Callable = scanner.scan_array,
    scan_string: Callable = scanner.scan_string,
    scan_date: Callable = scanner.scan_date,
    scan_number: Callable = scanner.scan_number,
    fallback_scanner: Optional[AltScannerFunc] = None,
    enable_extras: bool = True,
    ignore_extra_data: bool = False,
    ini=None,
) -> Union[Any, Tuple[Any, int]]:
    """Read file, scan JSONish string, and return a Python object.

    This reads the file into a string, then calls :func:`decode`; see
    its docstring for details.

    TODO: This reads the whole file all at once. Maybe find a way to
          stream the file contents, although this would add a bit of
          complexity to the scanner in order to make it generically
          handle iterables of chars.

    """
    if isinstance(file, str):
        path = Path(file)
        with path.open() as fp:
            string = fp.read()
    elif isinstance(file, Path):
        path = file
        with file.open() as fp:
            string = fp.read()
    else:
        path = None
        string = file.read()
    if ini is None:
        if path is not None and path.suffix in (".cfg", ".ini", ".inijson"):
            ini = True
        else:
            ini = False
    return decode(
        string,
        strict=strict,
        prescan=prescan,
        scan_object=scan_object,
        object_converter=object_converter,
        scan_array=scan_array,
        scan_string=scan_string,
        scan_date=scan_date,
        scan_number=scan_number,
        fallback_scanner=fallback_scanner,
        enable_extras=enable_extras,
        ignore_extra_data=ignore_extra_data,
        ini=ini,
    )
