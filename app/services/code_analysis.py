import ast
from dataclasses import dataclass


@dataclass(frozen=True)
class CodeAnalysisResult:
    code_bytes: int
    physical_lines: int
    effective_lines: int
    max_nesting_depth: int | None
    analysis_error: str | None


NESTING_NODES = (
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.With,
    ast.AsyncWith,
    ast.Try,
    ast.ExceptHandler,
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.ClassDef,
    ast.Match,
)


def analyze_python_code(source_code: str) -> CodeAnalysisResult:
    lines = source_code.splitlines()
    effective_lines = sum(
        1 for line in lines if line.strip() and not line.strip().startswith("#")
    )

    try:
        tree = ast.parse(source_code)
    except SyntaxError as exc:
        return CodeAnalysisResult(
            code_bytes=len(source_code.encode("utf-8")),
            physical_lines=len(lines),
            effective_lines=effective_lines,
            max_nesting_depth=None,
            analysis_error=str(exc),
        )

    return CodeAnalysisResult(
        code_bytes=len(source_code.encode("utf-8")),
        physical_lines=len(lines),
        effective_lines=effective_lines,
        max_nesting_depth=_max_nesting_depth(tree),
        analysis_error=None,
    )


def analyze_code(language: str, source_code: str) -> CodeAnalysisResult:
    if language != "python3":
        lines = source_code.splitlines()
        return CodeAnalysisResult(
            code_bytes=len(source_code.encode("utf-8")),
            physical_lines=len(lines),
            effective_lines=sum(
                1 for line in lines if line.strip() and not line.strip().startswith("#")
            ),
            max_nesting_depth=None,
            analysis_error="static analysis is only available for python3",
        )
    return analyze_python_code(source_code)


def _max_nesting_depth(tree: ast.AST) -> int:
    def visit(node: ast.AST, current_depth: int) -> int:
        next_depth = (
            current_depth + 1 if isinstance(node, NESTING_NODES) else current_depth
        )
        child_depths = [
            visit(child, next_depth) for child in ast.iter_child_nodes(node)
        ]
        return max([next_depth, *child_depths])

    return visit(tree, 0)
