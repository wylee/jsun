# jsun

This is an alternative JSON decoder/encoder that supports some extra
features. It takes a *lot* of inspiration from the `json` module in the
standard library and exposes the same high level API: `load`, `loads`,
`dump`, `dumps`, `JSONDecoder`, and `JSONEncoder`.

In many cases, `jsun` can be swapped in by installing the package then
simply updating imports to use `jsun` instead of `json`.

## Extra decoding features

- Trailing commas
 
- Line comments starting with //
 
- All valid Python ints and floats:
  - Binary, octal, hex
  - Underscore separators
  - Unary plus operator

- Math constants:
  - inf, nan, E, π, PI, τ, TAU
  - Infinity, NaN

- Literal (unquoted) dates and times:
  - 2021-06
  - 2021-06-23
  - 2021-06-23T12:00
  - 2021-06-23T12:00Z
  - 2021-06-23T12:00-07:00
  - 12:00 (today's date at noon)

- Decoding an empty string will produce `None` rather than an exception
  (an exception will be raised if extras are disabled)

- *All* parsing methods can be overridden if some additional
  customization is required. In particular, the object and array
  parsers can be overridden

- A pre-parse method can be provided to handle values before the regular
  JSON parsers are applied

- A fallback parsing method can be provided to handle additional types
  of values if none of the default parsers are suitable

- When errors are encountered, specific exceptions are raised (all
  derived from the built-in `ValueError`)

## Extra encoding features

The `jsun` encoder is very similar to the standard library encoder (and
is in fact a subclass of `json.JSONEncoder`). Currently, it supports
only a couple of extra features:

- Date objects are converted to ISO format by default
- Datetime objects are converted to ISO format by default

NOTE: There is some asymmetry here. E.g., date and datetime objects
should be converted to literals instead of quoted strings.

## Disabling the extra features

*All* the extra features can be turned off with a flag:

    >>> from jsun import decode
    >>> decode("[1, 2, 3,]")
    [1, 2, 3]
    >>> decode("[1, 2, 3,]", enable_extras=False)
    <exception traceback>

## Differences between jsun and standard library json

- An empty string input is converted to `None` rather than raising an
  exception (only if extras are enabled).

- When decoding, instead of `object_hook` and `object_hook_pairs`,
  there's just a single `object_converter` argument. It's essentially
  the same as `object_hook`. `object_hook_pairs` seems unnecessary
  nowadays since `dict`s are ordered.

- The default object type is `jsun.obj.JSONObject` instead of `dict`. A
  `JSONObject` is a bucket of properties that can be accessed via dotted
  or bracket notation. Pass `object_converter=None` to get back
  `dict`s instead.

## Config files

A bonus feature is that configuration can be loaded from INI files
where the keys are split on dots to create sub-objects and the values
are encoded as JSON.

This is quite similar to TOML and some of the features of `jsun`, like
literal dates, are inspired by TOML.

This feature was originally developed in 2014 as part of the
`django-local-settings` project, about a year and half after TOML was
first released but before I'd heard of it.

### Differences with TOML

- Parentheses are used instead of quotes to avoid splitting on dots
- Objects created using `{}` syntax (AKA "inline tables" in TOML) can
  span multiple lines
- There are no arrays of tables
- Others I'm not thinking of at the moment...

## About the name

My first choice was `jsonish` but that's already taken. My second choice
was `jsonesque` but it's also taken, and it's hard to type. `jsun` is
nice because it's easy to type and easy to swap in for `json` by just
changing a single letter.

## Testing

There's a suite of unit tests, which also tests against the JSON checker
files at https://json.org/JSON_checker/. Coverage is currently at 82%.
