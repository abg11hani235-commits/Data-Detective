import ast
import os
from typing import List, Set, Tuple


class SecurityViolation(Exception):
    """Raised when generated code fails static AST security checks."""
    pass


class CodeSecurityChecker(ast.NodeVisitor):
    """
    Hardened static AST security inspector for generated Python analysis code.
    Enforces strict module allowlists, dunder reflection blocks, path traversal prevention,
    and forbidden runtime built-in invocation.
    """

    ALLOWED_MODULES: Set[str] = {
        "pandas", "pd",
        "numpy", "np",
        "plotly", "plotly.express", "plotly.graph_objects", "plotly.subplots", "px", "go",
        "scipy", "scipy.stats",
        "statistics",
        "datetime", "date", "time",
        "math",
        "json",
    }

    FORBIDDEN_CALLS: Set[str] = {
        "eval", "exec", "compile", "__import__",
        "getattr", "setattr", "delattr",
        "globals", "locals", "vars", "dir", "help",
        "breakpoint", "exit", "quit", "input",
        "memoryview", "bytearray",
    }

    FORBIDDEN_ATTRIBUTES: Set[str] = {
        "__subclasses__", "__bases__", "__base__", "__class__",
        "__globals__", "__dict__", "__mro__", "__code__",
        "__closure__", "__func__", "__self__", "__module__",
        "environ", "getenv", "system", "popen", "spawn", "fork",
        "execv", "execve",
    }

    FORBIDDEN_NAMES: Set[str] = {
        "__builtins__", "builtins", "__loader__", "__spec__",
        "pathlib", "os", "sys", "subprocess", "socket", "urllib", "requests", "shutil",
    }

    RESTRICTED_FILE_OPS: Set[str] = {
        "read_csv", "read_table", "read_excel", "read_json", "read_feather", "read_parquet",
        "to_csv", "to_excel", "to_json", "to_parquet", "to_pickle",
    }

    def __init__(self):
        self.violations: List[str] = []
        self.string_constants: dict[str, str] = {}

    def visit_Assign(self, node: ast.Assign):
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            var_name = node.targets[0].id
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                self.string_constants[var_name] = node.value.value
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            base_module = alias.name.split(".")[0]
            if base_module not in self.ALLOWED_MODULES and alias.name not in self.ALLOWED_MODULES:
                self.violations.append(f"Forbidden module import: '{alias.name}'")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            base_module = node.module.split(".")[0]
            if base_module not in self.ALLOWED_MODULES and node.module not in self.ALLOWED_MODULES:
                self.violations.append(f"Forbidden module import: 'from {node.module}'")
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name):
        if node.id in self.FORBIDDEN_NAMES:
            self.violations.append(f"Forbidden variable or identifier reference: '{node.id}'")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        # 1. Direct function call by name (e.g. eval(), open(), getattr())
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name in self.FORBIDDEN_CALLS:
                self.violations.append(f"Forbidden function call: '{func_name}()'")

            elif func_name == "open":
                # Standard open() permitted exclusively for writing to output/results.json
                path_str = None
                if node.args:
                    if isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                        path_str = node.args[0].value
                    elif isinstance(node.args[0], ast.Name) and node.args[0].id in self.string_constants:
                        path_str = self.string_constants[node.args[0].id]

                if path_str is None:
                    self.violations.append("Dynamic, variable, or non-string file path in open()")
                else:
                    norm = os.path.normpath(path_str).replace("\\", "/")
                    if ".." in path_str or norm.startswith("..") or path_str.startswith("/") or ":" in path_str:
                        self.violations.append(f"Path traversal detected in open(): '{path_str}'")
                    elif not norm.startswith("output/") and norm != "output/results.json":
                        self.violations.append(f"File writing restricted strictly to 'output/': '{path_str}'")

        # 2. Method call on an object (e.g. pd.read_csv(), df.to_csv(), os.system())
        elif isinstance(node.func, ast.Attribute):
            method_name = node.func.attr
            if method_name in self.FORBIDDEN_ATTRIBUTES:
                self.violations.append(f"Forbidden method call: '.{method_name}()'")

            # Inspect pandas read_* and to_* for path traversal
            if method_name in self.RESTRICTED_FILE_OPS:
                for arg in node.args:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        val = arg.value
                        if ".." in val or val.startswith("/") or ":" in val or val.startswith("\\"):
                            self.violations.append(f"Path traversal detected in .{method_name}(): '{val}'")
                        norm = os.path.normpath(val).replace("\\", "/")
                        if method_name.startswith("to_") and not norm.startswith("output/"):
                            self.violations.append(f"File outputs via .{method_name}() must write inside 'output/': '{val}'")

        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        if node.attr in self.FORBIDDEN_ATTRIBUTES:
            self.violations.append(f"Forbidden attribute access: '.{node.attr}'")
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript):
        # Detect attempts to access dangerous dunders or builtins via dict lookup: e.g. obj["__subclasses__"]
        if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
            key = node.slice.value
            if key in self.FORBIDDEN_ATTRIBUTES or key in self.FORBIDDEN_NAMES or key in self.FORBIDDEN_CALLS:
                self.violations.append(f"Forbidden dictionary/subscript lookup key: '{key}'")
        self.generic_visit(node)

    @classmethod
    def validate_code(cls, code_str: str) -> Tuple[bool, List[str]]:
        try:
            tree = ast.parse(code_str)
        except SyntaxError as e:
            return False, [f"Python syntax error at line {e.lineno}: {e.msg}"]

        checker = cls()
        checker.visit(tree)
        if checker.violations:
            return False, checker.violations
        return True, []
