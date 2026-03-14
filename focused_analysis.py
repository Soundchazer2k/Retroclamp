#!/usr/bin/env python3
"""
Focused Analysis for Key Retroclamp Components
Provides deep analysis of CHDMAN integration, plugin system, and GUI architecture.

Usage: python focused_analysis.py [component] [project_path]
Components: chdman, plugins, gui, all
"""

import argparse
import ast
import json
import logging
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class ComponentAnalysis:
    """Analysis results for a specific component"""

    component: str
    files_analyzed: List[str]
    issues: List[str]
    recommendations: List[str]
    metrics: Dict[str, Any]
    patterns: Dict[str, List[str]]


class FocusedAnalyzer:
    """Focused analyzer for specific Retroclamp components"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root).resolve()
        self.python_files = self._discover_files()

    def _discover_files(self) -> List[Path]:
        """Discover Python files in the project"""
        exclude_patterns = {"__pycache__", ".git", "venv", "env"}
        python_files = []

        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [d for d in dirs if d not in exclude_patterns]
            for file in files:
                if file.endswith(".py"):
                    python_files.append(Path(root) / file)

        return python_files

    def analyze_chdman_integration(self) -> ComponentAnalysis:
        """Deep analysis of CHDMAN integration"""

        print("🔍 Analyzing CHDMAN Integration...")

        relevant_files = []
        from typing import Any, Dict, List

        issues: List[str] = []
        recommendations: List[str] = []
        patterns: Dict[str, List[Any]] = {
            "subprocess_usage": [],
            "error_handling": [],
            "security_issues": [],
            "performance_concerns": [],
            "path_handling": [],
        }
        metrics = {
            "subprocess_calls": 0,
            "error_handlers": 0,
            "shell_usage": 0,
            "timeout_usage": 0,
        }

        # Find files that likely handle CHDMAN operations
        chdman_files = []
        for file_path in self.python_files:
            try:
                with open(file_path, encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                if any(
                    term in content.lower()
                    for term in ["chdman", "subprocess", "popen"]
                ):
                    chdman_files.append(file_path)
                    relevant_files.append(str(file_path.relative_to(self.project_root)))
            except Exception as e:
                logging.warning(f'Exception in metrics["gui_files"] loop: {e}')
                continue

        for file_path in chdman_files:
            self._analyze_chdman_file(file_path, issues, patterns, metrics)

        # Generate recommendations based on findings
        if metrics["shell_usage"] > 0:
            recommendations.append(
                "CRITICAL: Replace shell=True with safer subprocess calls"
            )
            issues.append(
                f"Found {metrics['shell_usage']} subprocess calls with shell=True"
            )

        if metrics["timeout_usage"] == 0 and metrics["subprocess_calls"] > 0:
            recommendations.append(
                "Add timeout parameters to subprocess calls to prevent hanging"
            )

        if metrics["error_handlers"] < metrics["subprocess_calls"]:
            recommendations.append(
                "Add comprehensive error handling for all CHDMAN operations"
            )

        if patterns["path_handling"]:
            recommendations.append("Use pathlib for cross-platform path handling")

        recommendations.extend(
            [
                "Implement progress reporting for long-running CHDMAN operations",
                "Add input validation before calling CHDMAN",
                "Consider using async subprocess for better GUI responsiveness",
                "Log CHDMAN commands and outputs for debugging",
                "Implement retry logic for transient failures",
            ]
        )

        return ComponentAnalysis(
            component="CHDMAN Integration",
            files_analyzed=relevant_files,
            issues=issues,
            recommendations=recommendations,
            metrics=metrics,
            patterns=patterns,
        )

    def _analyze_chdman_file(
        self,
        file_path: Path,
        issues: List[str],
        patterns: Dict[str, List[str]],
        metrics: Dict[str, Any],
    ):
        """Analyze a single file for CHDMAN patterns"""
        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                content = f.read()

            rel_path = str(file_path.relative_to(self.project_root))

            # Parse AST for deeper analysis
            try:
                tree = ast.parse(content)
            except SyntaxError:
                issues.append(f"Syntax error in {rel_path}")
                return

            # Analyze subprocess usage
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute):
                        if (
                            isinstance(node.func.value, ast.Name)
                            and node.func.value.id == "subprocess"
                        ):
                            metrics["subprocess_calls"] += 1
                            patterns["subprocess_usage"].append(
                                f"{rel_path}:{node.lineno}"
                            )

                            # Check for shell=True
                            for keyword in node.keywords:
                                if keyword.arg == "shell" and isinstance(
                                    keyword.value, ast.Constant
                                ):
                                    if keyword.value.value is True:
                                        metrics["shell_usage"] += 1
                                        patterns["security_issues"].append(
                                            f"{rel_path}:{node.lineno} - "
                                            "shell=True usage"
                                        )
                                elif keyword.arg == "timeout":
                                    metrics["timeout_usage"] += 1

            # Check error handling patterns
            try_blocks = [node for node in ast.walk(tree) if isinstance(node, ast.Try)]
            for try_block in try_blocks:
                if any("subprocess" in ast.dump(child) for child in try_block.body):
                    metrics["error_handlers"] += 1
                    patterns["error_handling"].append(
                        f"{rel_path} - try/except around subprocess"
                    )

            # Look for path handling issues
            if re.search(r'["\'][C-Z]:\\|["\']/', content):
                patterns["path_handling"].append(
                    f"{rel_path} - potential hardcoded paths"
                )

            # Check for performance concerns
            if "time.sleep" in content:
                patterns["performance_concerns"].append(f"{rel_path} - uses time.sleep")

            if re.search(r"while.*running|while.*True", content):
                patterns["performance_concerns"].append(
                    f"{rel_path} - potential blocking loop"
                )

        except Exception as e:
            issues.append(f"Error analyzing {file_path}: {e}")

    def analyze_plugin_system(self) -> ComponentAnalysis:
        """Deep analysis of the plugin system"""

        print("🔍 Analyzing Plugin System...")

        relevant_files = []
        issues: List[str] = []  # Line 342
        recommendations = []
        patterns: Dict[str, List[str]] = {  # Line 344
            "plugin_files": [],
            "plugin_metadata": [],
            "registration_methods": [],
            "error_handling": [],
            "api_consistency": [],
        }
        metrics = {
            "total_plugins": 0,
            "plugins_with_metadata": 0,
            "plugins_with_registration": 0,
            "api_violations": 0,
        }

        # Find plugin-related files
        plugin_files = []
        tools_dir = self.project_root / "tools"

        if tools_dir.exists():
            for file_path in tools_dir.glob("*.py"):
                if file_path.name != "__init__.py":
                    plugin_files.append(file_path)
                    relevant_files.append(str(file_path.relative_to(self.project_root)))
                    metrics["total_plugins"] += 1

        # Analyze plugin manager/loader
        init_file = tools_dir / "__init__.py" if tools_dir.exists() else None
        if init_file and init_file.exists():
            relevant_files.append(str(init_file.relative_to(self.project_root)))

        # Analyze each plugin
        required_metadata = [
            "PLUGIN_NAME",
            "PLUGIN_DESCRIPTION",
            "PLUGIN_VERSION",
            "PLUGIN_AUTHOR",
        ]

        for plugin_path in plugin_files:
            self._analyze_plugin_file(
                plugin_path, required_metadata, issues, patterns, metrics
            )

        # Analyze plugin loader if it exists
        if init_file and init_file.exists():
            self._analyze_plugin_loader(init_file, issues, patterns)

        # Generate recommendations
        if metrics["plugins_with_metadata"] < metrics["total_plugins"]:
            missing = metrics["total_plugins"] - metrics["plugins_with_metadata"]
            recommendations.append(f"Add required metadata to {missing} plugin(s)")

        if metrics["plugins_with_registration"] < metrics["total_plugins"]:
            missing = metrics["total_plugins"] - metrics["plugins_with_registration"]
            recommendations.append(
                f"Add register_panel function to {missing} plugin(s)"
            )

        recommendations.extend(
            [
                "Implement plugin dependency management",
                "Add plugin configuration validation",
                "Create plugin API documentation",
                "Implement plugin error isolation",
                "Add plugin versioning and compatibility checks",
                "Create plugin development template",
                "Add plugin testing framework",
            ]
        )

        return ComponentAnalysis(
            component="Plugin System",
            files_analyzed=relevant_files,
            issues=issues,
            recommendations=recommendations,
            metrics=metrics,
            patterns=patterns,
        )

    def _analyze_plugin_file(
        self,
        plugin_path: Path,
        required_metadata: List[str],
        issues: List[str],
        patterns: Dict[str, List[str]],
        metrics: Dict[str, Any],
    ):
        """Analyze a single plugin file"""
        try:
            with open(plugin_path, encoding="utf-8", errors="ignore") as f:
                content = f.read()

            rel_path = str(plugin_path.relative_to(self.project_root))
            patterns["plugin_files"].append(rel_path)

            # Check for required metadata
            metadata_found = []
            for metadata in required_metadata:
                if f"{metadata} =" in content:
                    metadata_found.append(metadata)
                    patterns["plugin_metadata"].append(f"{rel_path} - {metadata}")

            if len(metadata_found) == len(required_metadata):
                metrics["plugins_with_metadata"] += 1
            else:
                missing = set(required_metadata) - set(metadata_found)
                issues.append(f"{rel_path} missing metadata: {', '.join(missing)}")

            # Check for registration function
            if "def register_panel" in content:
                metrics["plugins_with_registration"] += 1
                patterns["registration_methods"].append(rel_path)
            else:
                issues.append(f"{rel_path} missing register_panel function")

            # Parse AST for deeper analysis
            try:
                tree = ast.parse(content)

                # Check function signatures
                for node in ast.walk(tree):
                    if (
                        isinstance(node, ast.FunctionDef)
                        and node.name == "register_panel"
                    ):
                        if len(node.args.args) != 1:  # Should take tools_view
                            issues.append(
                                f"{rel_path} register_panel has incorrect signature"
                            )
                            metrics["api_violations"] += 1

            except SyntaxError:
                issues.append(f"Syntax error in plugin {rel_path}")

        except Exception as e:
            issues.append(f"Error analyzing plugin {plugin_path}: {e}")

    def _analyze_plugin_loader(
        self, init_file: Path, issues: List[str], patterns: Dict[str, List[str]]
    ):
        """Analyze the plugin loader/manager"""
        try:
            with open(init_file, encoding="utf-8", errors="ignore") as f:
                content = f.read()

            rel_path = str(init_file.relative_to(self.project_root))

            # Look for plugin loading patterns
            if "importlib" in content:
                patterns["registration_methods"].append(f"{rel_path} - uses importlib")

            if "try:" in content and "import" in content:
                patterns["error_handling"].append(
                    f"{rel_path} - error handling for imports"
                )
            else:
                issues.append(f"{rel_path} lacks error handling for plugin imports")

        except Exception as e:
            issues.append(f"Error analyzing plugin loader: {e}")

    def analyze_gui_architecture(self) -> ComponentAnalysis:
        """Deep analysis of GUI architecture"""

        print("🔍 Analyzing GUI Architecture...")

        relevant_files = []
        issues: List[str] = []
        recommendations = []
        patterns: Dict[str, List[str]] = {
            "gui_files": [],
            "threading_usage": [],
            "signal_connections": [],
            "ui_components": [],
            "theme_handling": [],
        }
        metrics = {
            "gui_files": 0,
            "threaded_operations": 0,
            "signal_slots": 0,
            "ui_classes": 0,
            "theme_files": 0,
        }

        # Find GUI-related files
        gui_files = []
        gui_dir = self.project_root / "gui"

        if gui_dir.exists():
            for file_path in gui_dir.glob("*.py"):
                gui_files.append(file_path)
                relevant_files.append(str(file_path.relative_to(self.project_root)))
                metrics["gui_files"] += 1

        # Also check main.py and other potential GUI files
        for file_path in self.python_files:
            if file_path.name in ["main.py", "app.py", "window.py"]:
                try:
                    with open(file_path, encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    if any(
                        term in content
                        for term in ["PySide6", "PyQt", "QWidget", "QMainWindow"]
                    ):
                        gui_files.append(file_path)
                        relevant_files.append(
                            str(file_path.relative_to(self.project_root))
                        )
                        if file_path not in [
                            f for f in gui_files if f.parent.name == "gui"
                        ]:
                            metrics["gui_files"] += 1
                except Exception as e:
                    logging.warning(f"Exception in relevant_files loop: {e}")
                    continue

        # Analyze each GUI file
        for gui_file in gui_files:
            self._analyze_gui_file(gui_file, issues, patterns, metrics)

        # Check theme system
        theme_files = list(self.project_root.glob("**/*theme*.json")) + list(
            self.project_root.glob("**/theme*.py")
        )

        for theme_file in theme_files:
            relevant_files.append(str(theme_file.relative_to(self.project_root)))
            metrics["theme_files"] += 1
            patterns["theme_handling"].append(
                str(theme_file.relative_to(self.project_root))
            )

        # Generate recommendations
        if metrics["threaded_operations"] == 0:
            recommendations.append("Consider using QThread for long-running operations")

        if patterns["signal_connections"]:
            recommendations.append(
                "Ensure proper signal/slot disconnection to prevent memory leaks"
            )

        recommendations.extend(
            [
                "Implement proper error handling in GUI components",
                "Add input validation for user inputs",
                "Ensure GUI responsiveness during operations",
                "Implement proper window state management",
                "Add accessibility features (keyboard navigation, "
                "screen reader support)",
                "Optimize GUI performance for large datasets",
                "Implement proper resource cleanup",
            ]
        )

        return ComponentAnalysis(
            component="GUI Architecture",
            files_analyzed=relevant_files,
            issues=issues,
            recommendations=recommendations,
            metrics=metrics,
            patterns=patterns,
        )

    def _analyze_gui_file(
        self,
        gui_file: Path,
        issues: List[str],
        patterns: Dict[str, List[str]],
        metrics: Dict[str, Any],
    ):
        """Analyze a single GUI file"""
        try:
            with open(gui_file, encoding="utf-8", errors="ignore") as f:
                content = f.read()

            rel_path = str(gui_file.relative_to(self.project_root))
            patterns["gui_files"].append(rel_path)

            # Check for threading
            threading_indicators = ["QThread", "threading.Thread", "QRunnable"]
            for indicator in threading_indicators:
                if indicator in content:
                    metrics["threaded_operations"] += 1
                    patterns["threading_usage"].append(f"{rel_path} - {indicator}")

            # Check for signal/slot usage
            signal_indicators = [".connect(", ".emit(", "pyqtSignal", "Signal("]
            for indicator in signal_indicators:
                if indicator in content:
                    metrics["signal_slots"] += content.count(indicator)
                    patterns["signal_connections"].append(f"{rel_path} - {indicator}")

            # Parse AST for class analysis
            try:
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        # Check if it's a UI class
                        ui_indicators = ["Widget", "Window", "Dialog", "Tab"]
                        if any(indicator in node.name for indicator in ui_indicators):
                            metrics["ui_classes"] += 1
                            patterns["ui_components"].append(
                                f"{rel_path} - {node.name}"
                            )

                        # Check for proper __init__ method
                        init_methods = [
                            n
                            for n in node.body
                            if isinstance(n, ast.FunctionDef) and n.name == "__init__"
                        ]
                        if not init_methods:
                            issues.append(
                                f"{rel_path} class {node.name} missing __init__"
                            )

            except SyntaxError:
                issues.append(f"Syntax error in GUI file {rel_path}")

            # Check for potential GUI blocking operations
            blocking_patterns = ["time.sleep", "subprocess.run", "requests.get"]
            for pattern in blocking_patterns:
                if pattern in content:
                    issues.append(
                        f"{rel_path} contains potentially blocking operation: {pattern}"
                    )

        except Exception as e:
            issues.append(f"Error analyzing GUI file {gui_file}: {e}")

    def run_focused_analysis(
        self, component: str = "all"
    ) -> Dict[str, ComponentAnalysis]:
        """Run focused analysis on specified component(s)"""
        results = {}

        if component in ["chdman", "all"]:
            results["chdman"] = self.analyze_chdman_integration()

        if component in ["plugins", "all"]:
            results["plugins"] = self.analyze_plugin_system()

        if component in ["gui", "all"]:
            results["gui"] = self.analyze_gui_architecture()

        return results

    def print_analysis_report(self, results: Dict[str, ComponentAnalysis]):
        """Print detailed analysis report"""
        print("\n" + "=" * 80)
        print("🎯 FOCUSED RETROCLAMP COMPONENT ANALYSIS")
        print("=" * 80)

        for _, analysis in results.items():
            print(f"\n{'=' * 60}")
            print(f"📊 {analysis.component.upper()} ANALYSIS")
            print(f"{'=' * 60}")

            # Files analyzed
            print(f"\n📁 Files Analyzed ({len(analysis.files_analyzed)}):")
            for file in analysis.files_analyzed[:10]:  # Show first 10
                print(f"  • {file}")
            if len(analysis.files_analyzed) > 10:
                print(f"  ... and {len(analysis.files_analyzed) - 10} more")

            # Metrics
            print("\n📈 Metrics:")
            for metric, value in analysis.metrics.items():
                print(f"  • {metric.replace('_', ' ').title()}: {value}")

            # Issues
            if analysis.issues:
                print(f"\n⚠️  Issues Found ({len(analysis.issues)}):")
                for issue in analysis.issues[:8]:  # Show first 8
                    print(f"  • {issue}")
                if len(analysis.issues) > 8:
                    print(f"  ... and {len(analysis.issues) - 8} more issues")

            # Patterns
            print("\n🔍 Patterns Found:")
            for pattern_type, pattern_list in analysis.patterns.items():
                if pattern_list:
                    print(
                        f"  • {pattern_type.replace('_', ' ').title()}: "
                        f"{len(pattern_list)}"
                    )
                    for pattern in pattern_list[:3]:  # Show first 3
                        print(f"    - {pattern}")
                    if len(pattern_list) > 3:
                        print(f"    ... and {len(pattern_list) - 3} more")

            # Recommendations
            print("\n💡 Recommendations:")
            for i, rec in enumerate(analysis.recommendations[:10], 1):
                priority = "🔴" if i <= 3 else "🟡" if i <= 6 else "🟢"
                print(f"  {priority} {i}. {rec}")

            if len(analysis.recommendations) > 10:
                print(
                    f"  ... and {len(analysis.recommendations) - 10} "
                    "more recommendations"
                )

        # Overall summary
        total_issues = sum(len(a.issues) for a in results.values())
        total_files = sum(len(a.files_analyzed) for a in results.values())

        print("\n" + "=" * 60)
        print("📋 OVERALL SUMMARY")
        print("=" * 60)
        print(f"• Components analyzed: {len(results)}")
        print(f"• Total files analyzed: {total_files}")
        print(f"• Total issues found: {total_issues}")

        if total_issues == 0:
            print("✅ No critical issues found!")
        elif total_issues < 10:
            print("🟡 Few issues found - good overall health")
        elif total_issues < 25:
            print("🟠 Moderate number of issues - address high priority items")
        else:
            print("🔴 Many issues found - prioritize critical fixes")


def main():
    parser = argparse.ArgumentParser(
        description="Focused analysis of Retroclamp components"
    )
    parser.add_argument(
        "component",
        nargs="?",
        default="all",
        choices=["chdman", "plugins", "gui", "all"],
        help="Component to analyze (default: all)",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to Retroclamp project (default: current directory)",
    )
    parser.add_argument("--output", "-o", help="Output JSON report to file")
    parser.add_argument(
        "--detailed",
        "-d",
        action="store_true",
        help="Show detailed patterns and issues",
    )

    args = parser.parse_args()

    if not Path(args.path).exists():
        print(f"❌ Path does not exist: {args.path}")
        sys.exit(1)

    analyzer = FocusedAnalyzer(args.path)

    try:
        print(f"🔍 Running focused analysis on: {args.component}")
        results = analyzer.run_focused_analysis(args.component)

        if not results:
            print("❌ No analysis results generated")
            sys.exit(1)

        analyzer.print_analysis_report(results)

        if args.output:
            # Convert ComponentAnalysis objects to dictionaries for JSON serialization
            json_results = {}
            for comp_name, analysis in results.items():
                json_results[comp_name] = {
                    "component": analysis.component,
                    "files_analyzed": analysis.files_analyzed,
                    "issues": analysis.issues,
                    "recommendations": analysis.recommendations,
                    "metrics": analysis.metrics,
                    "patterns": analysis.patterns,
                }

            with open(args.output, "w") as f:
                json.dump(json_results, f, indent=2)
            print(f"\n💾 Detailed report saved to: {args.output}")

    except KeyboardInterrupt:
        print("\n❌ Analysis interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Analysis failed: {e}")
        if args.detailed:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
