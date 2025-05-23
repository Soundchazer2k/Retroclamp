# This file does not execute subprocesses, only scans for related patterns in code.
# nosec B404
#!/usr/bin/env python3
"""
Comprehensive Retroclamp Code Analyzer
Analyzes your Retroclamp project for code quality, architecture, and potential issues.

Usage: python retroclamp_analyzer.py [project_path] [--output filename.json]
"""

import argparse
import ast
import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class FileMetrics:
    """Metrics for a single file"""

    path: str
    lines_of_code: int = 0
    comment_lines: int = 0
    blank_lines: int = 0
    functions: int = 0
    classes: int = 0
    complexity: int = 0
    imports: List[str] = field(default_factory=list)
    docstring_coverage: float = 0.0
    issues: List[str] = field(default_factory=list)

    def __post_init__(self):
        if self.imports is None:
            self.imports = []
        if self.issues is None:
            self.issues = []


@dataclass
class ProjectMetrics:
    """Overall project metrics"""

    total_files: int = 0
    total_loc: int = 0
    total_functions: int = 0
    total_classes: int = 0
    comment_ratio: float = 0.0
    docstring_coverage: float = 0.0
    average_complexity: float = 0.0


class RetroclamptAnalyzer:
    """Main analyzer for Retroclamp project"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root).resolve()
        self.python_files: List[Path] = []
        self.file_metrics: Dict[str, FileMetrics] = {}
        self.project_metrics = ProjectMetrics()

    def discover_files(self) -> List[Path]:
        """Find all Python files in the project"""
        exclude_patterns = {
            "__pycache__",
            ".git",
            "venv",
            "env",
            ".env",
            "node_modules",
            "build",
            "dist",
            ".pytest_cache",
        }

        python_files = []
        for root, dirs, files in os.walk(self.project_root):
            # Remove excluded directories
            dirs[:] = [d for d in dirs if d not in exclude_patterns]

            for file in files:
                if file.endswith(".py"):
                    python_files.append(Path(root) / file)

        self.python_files = python_files
        print(f"Found {len(python_files)} Python files")
        return python_files

    def analyze_file(self, file_path: Path) -> FileMetrics:
        """Analyze a single Python file"""
        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception as e:
            return FileMetrics(
                path=str(file_path.relative_to(self.project_root)),
                issues=[f"Could not read file: {e}"],
            )

        # Basic line counting
        lines = content.split("\n")
        total_lines = len(lines)
        comment_lines = sum(1 for line in lines if line.strip().startswith("#"))
        blank_lines = sum(1 for line in lines if not line.strip())
        code_lines = total_lines - comment_lines - blank_lines

        # Parse AST for deeper analysis
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            return FileMetrics(
                path=str(file_path.relative_to(self.project_root)),
                lines_of_code=code_lines,
                comment_lines=comment_lines,
                blank_lines=blank_lines,
                issues=[f"Syntax error: {e}"],
            )

        # Count functions, classes, and imports
        functions = []
        classes = []
        imports = []
        complexity = 1  # Base complexity

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(node)
            elif isinstance(node, ast.ClassDef):
                classes.append(node)
            elif isinstance(node, ast.Import):
                imports.extend([alias.name for alias in node.names])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

            # Complexity calculation
            if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(node, ast.ExceptHandler):
                complexity += 1
            elif isinstance(node, (ast.And, ast.Or)):
                complexity += 1

        # Calculate docstring coverage
        documented_items = 0
        total_items = len(functions) + len(classes)

        if ast.get_docstring(tree):  # Module docstring
            documented_items += 1
            total_items += 1

        for func in functions:
            if ast.get_docstring(func):
                documented_items += 1

        for cls in classes:
            if ast.get_docstring(cls):
                documented_items += 1

        docstring_coverage = (documented_items / max(total_items, 1)) * 100

        # Identify issues
        issues = []

        # Long functions (>50 lines)
        for func in functions:
            if hasattr(func, "end_lineno") and func.end_lineno:
                func_length = func.end_lineno - func.lineno
                if func_length > 50:
                    issues.append(f"Long function '{func.name}': {func_length} lines")

        # High complexity functions
        for func in functions:
            func_complexity = self._calculate_function_complexity(func)
            if func_complexity > 10:
                issues.append(
                    f"High complexity function '{func.name}': {func_complexity}"
                )

        # Security issues
        if "shell=True" in content:
            issues.append("Security risk: uses shell=True in subprocess")

        # Check for TODO/FIXME comments
        if re.search(r"TODO|FIXME|HACK", content, re.IGNORECASE):
            issues.append("Contains TODO/FIXME/HACK comments")

        return FileMetrics(
            path=str(file_path.relative_to(self.project_root)),
            lines_of_code=code_lines,
            comment_lines=comment_lines,
            blank_lines=blank_lines,
            functions=len(functions),
            classes=len(classes),
            complexity=complexity,
            imports=list(set(imports)),
            docstring_coverage=docstring_coverage,
            issues=issues,
        )

    def _calculate_function_complexity(self, func_node) -> int:
        """Calculate cyclomatic complexity for a function"""
        complexity = 1
        for node in ast.walk(func_node):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(node, ast.ExceptHandler):
                complexity += 1
            elif isinstance(node, (ast.And, ast.Or)):
                complexity += 1
        return complexity

    def analyze_architecture(self) -> Dict[str, Any]:
        """Analyze project architecture"""
        structure: Dict[str, List[str]] = {
            "core_modules": [],
            "gui_modules": [],
            "tools_modules": [],
            "test_modules": [],
            "other_modules": [],
        }

        for file_path in self.python_files:
            rel_path = str(file_path.relative_to(self.project_root))

            if rel_path.startswith("core/"):
                structure["core_modules"].append(rel_path)
            elif rel_path.startswith("gui/"):
                structure["gui_modules"].append(rel_path)
            elif rel_path.startswith("tools/"):
                structure["tools_modules"].append(rel_path)
            elif "test" in rel_path.lower():
                structure["test_modules"].append(rel_path)
            else:
                structure["other_modules"].append(rel_path)

        return structure

    def analyze_dependencies(self) -> Dict[str, Any]:
        from collections import Counter

        """Analyze project dependencies"""
        all_imports: Counter = Counter()
        external_deps = set()
        stdlib_modules = {
            "os",
            "sys",
            "json",
            "pathlib",
            "typing",
            "collections",
            "dataclasses",
            "argparse",
            "subprocess",
            "re",
            "ast",
            "threading",
            "queue",
            "time",
            "datetime",
            "math",
            "random",
        }

        for metrics in self.file_metrics.values():
            for imp in metrics.imports:
                all_imports[imp] += 1
                base_module = imp.split(".")[0]
                if base_module not in stdlib_modules and not imp.startswith(
                    ("core.", "gui.", "tools.", "modules.")
                ):
                    external_deps.add(base_module)

        return {
            "all_imports": dict(all_imports.most_common(20)),
            "external_dependencies": sorted(external_deps),
        }

    def check_retroclamp_patterns(self) -> Dict[str, List[str]]:
        """Check for Retroclamp-specific patterns"""
        patterns: Dict[str, List[str]] = {
            "chdman_usage": [],
            "gui_threading": [],
            "plugin_implementations": [],
            "security_issues": [],
        }

        for file_path in self.python_files:
            try:
                with open(file_path, encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                rel_path = str(file_path.relative_to(self.project_root))

                # Check CHDMAN usage
                if "chdman" in content.lower() or "subprocess" in content:
                    patterns["chdman_usage"].append(rel_path)

                # Check GUI threading
                if any(term in content for term in ["QThread", "threading.Thread"]):
                    patterns["gui_threading"].append(rel_path)

                # Check plugin patterns
                if "PLUGIN_NAME" in content or "register_tab" in content:
                    patterns["plugin_implementations"].append(rel_path)

                # Security issues
                if "shell=True" in content:
                    patterns["security_issues"].append(f"{rel_path}: shell=True usage")

            except Exception:
                continue  # nosec B404

        return patterns

    def generate_project_metrics(self) -> ProjectMetrics:
        """Generate overall project metrics"""
        total_files = len(self.file_metrics)
        total_loc = sum(m.lines_of_code for m in self.file_metrics.values())
        total_functions = sum(m.functions for m in self.file_metrics.values())
        total_classes = sum(m.classes for m in self.file_metrics.values())
        total_comments = sum(m.comment_lines for m in self.file_metrics.values())

        comment_ratio = (total_comments / max(total_loc, 1)) * 100

        # Average docstring coverage
        coverages = [
            m.docstring_coverage
            for m in self.file_metrics.values()
            if m.docstring_coverage > 0
        ]
        avg_docstring_coverage = sum(coverages) / len(coverages) if coverages else 0

        # Average complexity
        complexities = [m.complexity for m in self.file_metrics.values()]
        avg_complexity = sum(complexities) / len(complexities) if complexities else 0

        return ProjectMetrics(
            total_files=total_files,
            total_loc=total_loc,
            total_functions=total_functions,
            total_classes=total_classes,
            comment_ratio=comment_ratio,
            docstring_coverage=avg_docstring_coverage,
            average_complexity=avg_complexity,
        )

    def run_analysis(self) -> Dict[str, Any]:
        """Run complete analysis"""
        print("Starting Retroclamp Analysis...")

        # Discover files
        self.discover_files()

        # Analyze each file
        print("Analyzing individual files...")
        for i, file_path in enumerate(self.python_files, 1):
            if i % 10 == 0:
                print(f"  Analyzed {i}/{len(self.python_files)} files...")
            metrics = self.analyze_file(file_path)
            self.file_metrics[metrics.path] = metrics

        # Generate project metrics
        self.project_metrics = self.generate_project_metrics()

        # Analyze architecture
        architecture = self.analyze_architecture()

        # Analyze dependencies
        dependencies = self.analyze_dependencies()

        # Check Retroclamp patterns
        retroclamp_patterns = self.check_retroclamp_patterns()

        return {
            "project_metrics": asdict(self.project_metrics),
            "file_metrics": {
                path: asdict(metrics) for path, metrics in self.file_metrics.items()
            },
            "architecture": architecture,
            "dependencies": dependencies,
            "retroclamp_patterns": retroclamp_patterns,
            "summary": self._generate_summary(),
        }

    def _generate_summary(self) -> Dict[str, Any]:
        """Generate analysis summary"""
        all_issues = []
        for metrics in self.file_metrics.values():
            all_issues.extend(metrics.issues)

        health_score = self._calculate_health_score()

        return {
            "total_issues": len(all_issues),
            "top_issues": all_issues[:10],
            "health_score": health_score,
            "recommendations": self._generate_recommendations(),
        }

    def _calculate_health_score(self) -> float:
        """Calculate overall project health score (0-100)"""
        score = 100.0

        if self.project_metrics.comment_ratio < 15:
            score -= 15
        if self.project_metrics.docstring_coverage < 50:
            score -= 20
        if self.project_metrics.average_complexity > 10:
            score -= 15

        total_issues = sum(len(m.issues) for m in self.file_metrics.values())
        if total_issues > 50:
            score -= 25
        elif total_issues > 20:
            score -= 15

        return max(0.0, score)

    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations"""
        recommendations = []

        if self.project_metrics.comment_ratio < 15:
            recommendations.append(
                f"Increase code comments (currently "
                f"{self.project_metrics.comment_ratio:.1f}%)"
            )

        if self.project_metrics.docstring_coverage < 50:
            recommendations.append(
                f"Add docstrings to functions and classes "
                f"(currently {self.project_metrics.docstring_coverage:.1f}%)"
            )

        if self.project_metrics.average_complexity > 10:
            recommendations.append(
                f"Reduce function complexity "
                f"(currently {self.project_metrics.average_complexity:.1f} average)"
            )

        test_files = [f for f in self.file_metrics.keys() if "test" in f.lower()]
        if not test_files:
            recommendations.append("Add unit tests - no test files found")

        recommendations.extend(
            [
                "Set up CI/CD pipeline with automated quality checks",
                "Consider adding type hints for better code maintainability",
                "Review security issues, especially subprocess usage",
            ]
        )

        return recommendations

    def print_report(self, analysis_results: Dict[str, Any]):
        """Print formatted analysis report"""
        print("\n" + "=" * 80)
        print("RETROCLAMP CODE ANALYSIS REPORT")
        print("=" * 80)

        # Project Summary
        metrics = analysis_results["project_metrics"]
        summary = analysis_results["summary"]

        print("\nPROJECT OVERVIEW:")
        print(f"  Files analyzed: {metrics['total_files']}")
        print(f"  Lines of code: {metrics['total_loc']:,}")
        print(f"  Functions: {metrics['total_functions']}")
        print(f"  Classes: {metrics['total_classes']}")
        print(f"  Comment ratio: {metrics['comment_ratio']:.1f}%")
        print(f"  Docstring coverage: {metrics['docstring_coverage']:.1f}%")
        print(f"  Average complexity: {metrics['average_complexity']:.1f}")
        print(f"  Health score: {summary['health_score']:.1f}/100")

        # Architecture
        arch = analysis_results["architecture"]
        print("\nARCHITECTURE:")
        print(f"  Core modules: {len(arch['core_modules'])}")
        print(f"  GUI modules: {len(arch['gui_modules'])}")
        print(f"  Tool plugins: {len(arch['tools_modules'])}")
        print(f"  Test modules: {len(arch['test_modules'])}")

        # Retroclamp patterns
        patterns = analysis_results["retroclamp_patterns"]
        print("\nRETROCLAMP-SPECIFIC ANALYSIS:")
        for category, items in patterns.items():
            if items:
                print(f"  {category.replace('_', ' ').title()}: {len(items)}")

        # Issues
        print("\nISSUES FOUND:")
        print(f"  Total issues: {summary['total_issues']}")
        if summary["top_issues"]:
            print("  Top issues:")
            for issue in summary["top_issues"][:5]:
                print(f"    - {issue}")

        # Recommendations
        print("\nRECOMMENDATIONS:")
        for i, rec in enumerate(summary["recommendations"][:5], 1):
            print(f"  {i}. {rec}")

        print(f"\nAnalysis complete! Health score: {summary['health_score']:.1f}/100")


def main():
    parser = argparse.ArgumentParser(description="Analyze Retroclamp codebase")
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to project (default: current directory)",
    )
    parser.add_argument("--output", "-o", help="Output JSON report to file")

    args = parser.parse_args()

    if not Path(args.path).exists():
        print(f"Error: Path does not exist: {args.path}")
        sys.exit(1)

    analyzer = RetroclamptAnalyzer(args.path)

    try:
        results = analyzer.run_analysis()
        analyzer.print_report(results)

        if args.output:
            with open(args.output, "w") as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\nDetailed report saved to: {args.output}")

    except KeyboardInterrupt:
        print("\nAnalysis interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nAnalysis failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
