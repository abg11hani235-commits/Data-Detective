import pytest
from app.sandbox.security import CodeSecurityChecker


def test_allowed_imports_pass():
    code = """
import pandas as pd
import numpy as np
import plotly.express as px
import json
import math
from datetime import datetime

mean_val = np.mean([1, 2, 3])
"""
    is_safe, violations = CodeSecurityChecker.validate_code(code)
    assert is_safe is True
    assert len(violations) == 0


def test_blocks_os_subprocess_socket():
    dangerous_snippets = [
        "import os\nos.system('dir')",
        "import subprocess\nsubprocess.run(['dir'])",
        "import socket\ns = socket.socket()",
        "import urllib.request\nurllib.request.urlopen('http://evil.com')",
        "import requests\nrequests.get('http://evil.com')",
        "from os import environ\nx = environ['GEMINI_API_KEY']",
    ]
    for snippet in dangerous_snippets:
        is_safe, violations = CodeSecurityChecker.validate_code(snippet)
        assert is_safe is False, f"Expected violation for: {snippet}"
        assert len(violations) > 0


def test_blocks_eval_exec_and_subclasses():
    dangerous_snippets = [
        "eval('1 + 1')",
        "exec('print(1)')",
        "__import__('os').system('dir')",
        "().__class__.__bases__[0].__subclasses__()",
        "x = ().__class__.__base__",
        "m = ().__class__.__mro__",
        "d = ().__dict__",
    ]
    for snippet in dangerous_snippets:
        is_safe, violations = CodeSecurityChecker.validate_code(snippet)
        assert is_safe is False, f"Expected violation for: {snippet}"


def test_blocks_dynamic_reflection_getattr_globals():
    dangerous_snippets = [
        "getattr(__builtins__, 'ev' + 'al')('print(1)')",
        "setattr(pd, 'read_csv', None)",
        "g = globals()",
        "l = locals()",
        "v = vars()",
        "d = dir()",
    ]
    for snippet in dangerous_snippets:
        is_safe, violations = CodeSecurityChecker.validate_code(snippet)
        assert is_safe is False, f"Expected violation for: {snippet}"
        assert any(term in str(violations) for term in ["Forbidden function call", "Forbidden variable"])


def test_blocks_path_traversal_in_open_and_pandas():
    dangerous_snippets = [
        "with open('/etc/passwd', 'w') as f: f.write('bad')",
        "with open('output/../../.env', 'w') as f: f.write('bad')",
        "with open('..\\\\secret.txt', 'w') as f: f.write('bad')",
        "df2 = pd.read_csv('../../.env')",
        "df2 = pd.read_csv('..\\\\..\\\\.env')",
        "df.to_csv('../../escaped.csv')",
        "df.to_json('/tmp/evil.json')",
    ]
    for snippet in dangerous_snippets:
        is_safe, violations = CodeSecurityChecker.validate_code(snippet)
        assert is_safe is False, f"Expected violation for: {snippet}"
        assert any(
            "path traversal" in v.lower() or "restricted" in v.lower()
            for v in violations
        ), f"Expected traversal message in {violations}"


def test_blocks_pathlib_reference():
    dangerous_snippets = [
        "import pathlib",
        "from pathlib import Path",
        "p = pathlib.Path('/tmp')",
    ]
    for snippet in dangerous_snippets:
        is_safe, violations = CodeSecurityChecker.validate_code(snippet)
        assert is_safe is False, f"Expected violation for: {snippet}"


def test_allows_output_results_file():
    code = """
import json
with open('output/results.json', 'w') as f:
    json.dump({'status': 'success'}, f)
"""
    is_safe, violations = CodeSecurityChecker.validate_code(code)
    assert is_safe is True
    assert len(violations) == 0
