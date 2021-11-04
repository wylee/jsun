# flake8: noqa

from .exc import DecodeError, DecodeError as JSONDecodeError

# Decode from JSON to Python
from .decoder import (
    decode,
    decode as loads,
    decode_file,
    decode_file as load,
    Decoder,
    Decoder as JSONDecoder,
)

# Encode from Python to JSON
from .encoder import (
    encode,
    encode as dumps,
    encode_to_file,
    encode_to_file as dump,
    Encoder,
    Encoder as JSONEncoder,
)
