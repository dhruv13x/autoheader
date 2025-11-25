
import os
from unittest.mock import patch
from autoheader.banner import print_logo, lerp, blend

def test_print_logo_with_env_var():
    with patch.dict(os.environ, {"CREATE_DUMP_PALETTE": "1"}):
        print_logo()

def test_print_logo_procedural():
    with patch.dict(os.environ, {}, clear=True):
        print_logo()

def test_print_logo_with_invalid_env_var():
    with patch.dict(os.environ, {"CREATE_DUMP_PALETTE": "invalid"}):
        print_logo()

def test_print_logo_with_out_of_bounds_env_var():
    with patch.dict(os.environ, {"CREATE_DUMP_PALETTE": "100"}):
        print_logo()

def test_lerp():
    assert lerp(0, 10, 0.5) == 5

def test_blend():
    c1 = (0, 0, 0)
    c2 = (255, 255, 255)
    assert blend(c1, c2, 0.5) == "#5e5e5e"
