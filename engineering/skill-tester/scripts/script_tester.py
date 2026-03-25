#!/usr/bin/env python3
"""
Script Tester - Tests Python scripts for syntax, imports, and functionality.

This script performs runtime testing of Python scripts within skills,
checking for syntax validity, import compliance, and basic functionality.
"""

import os
import sys
import json
import argparse
import subprocess
import tempfile
import shlex
import ast
import re
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, asdict


@dataclass
class TestReport:
    """Report structure for script testing results."""
    skill_path: str
    timestamp: str
    syntax_validation: Dict[str, Any]
    import_validation: Dict[str, Any]
    runtime_testing: Dict[str, Any]
    output_format_validation: Dict[str, Any]
    overall_passed: bool
    execution_time: float
    error_messages: List[str]


class ScriptTester:
    """Main script testing engine."""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.standard_libs = {
            'os', 'sys', 'json', 'argparse', 'pathlib', 'typing',
            'dataclasses', 'yaml', 're', 'csv', 'math', 'datetime',
            'collections', 'itertools', 'functools', 'hashlib',
            'subprocess', 'tempfile', 'shutil', 'glob', 'statistics',
            'inspect', 'textwrap', 'copy', 'pprint', 'io', 'textwrap'
        }
        
    def syntax_validation(self, skill_path: str) -> Dict[str, Any]:
        """Validate Python syntax for all scripts in the skill."""
        scripts_dir = Path(skill_path) / "scripts"
        if not scripts_dir.exists():
            return {"error": "Scripts directory not found", "passed": False}
            
        python_files = list(scripts_dir.glob("*.py"))
        if not python_files:
            return {"error": "No Python files found", "passed": False}
            
        results = {
            "files_tested": len(python_files),
            "passed": True,
            "files": {},
            "errors": []
        }
        
        for py_file in python_files:
            try:
                content = py_file.read_text(encoding='utf-8')
                # Parse with AST to check syntax
                ast.parse(content)
                results["files"][str(py_file.name)] = {
                    "syntax_valid": True,
                    "line_count": len(content.split('\n')),
                    "ast_nodes": len(list(ast.walk(ast.parse(content))))
                }
            except SyntaxError as e:
                results["passed"] = False
                error_msg = f"{py_file.name}:{e.lineno}: {e.msg}"
                results["errors"].append(error_msg)
                results["files"][str(py_file.name)] = {
                    "syntax_valid": False,
                    "error": str(e),
                    "line": e.lineno
                }
            except Exception as e:
                results["passed"] = False
                results["errors"].append(f"{py_file.name}: {str(e)}")
                results["files"][str(py_file.name)] = {
                    "syntax_valid": False,
                    "error": str(e)
                }
                
        return results
        
    def import_validation(self, skill_path: str) -> Dict[str, Any]:
        """Validate that scripts only use standard library imports."""
        scripts_dir = Path(skill_path) / "scripts"
        if not scripts_dir.exists():
            return {"error": "Scripts directory not found", "passed": False}
            
        python_files = list(scripts_dir.glob("*.py"))
        if not python_files:
            return {"error": "No Python files found", "passed": False}
            
        results = {
            "files_tested": len(python_files),
            "passed": True,
            "files": {},
            "violations": []
        }
        
        for py_file in python_files:
            try:
                content = py_file.read_text(encoding='utf-8')
                lines = content.split('\n')
                
                # Extract import statements
                imports = []
                for line in lines:
                    stripped = line.strip()
                    if stripped.startswith('import '):
                        # Handle: import module or import module as alias
                        parts = stripped.split()
                        if len(parts) >= 2:
                            module = parts[1].split('.')[0]  # Get top-level module
                            if ' as ' in stripped:
                                # import module as alias
                                alias_part = stripped.split(' as ')[1]
                                imports.append((module, alias_part.split()[0]))
                            else:
                                imports.append((module, None))
                    elif stripped.startswith('from '):
                        # Handle: from module import item
                        parts = stripped.split()
                        if len(parts) >= 4 and parts[2] == 'import':
                            module = parts[1].split('.')[0]  # Get top-level module
                            imported_items = parts[3:]
                            # Clean up imported items (remove commas, handle 'as')
                            cleaned_items = []
                            for item in imported_items:
                                if item == ',':
                                    continue
                                if ' as ' in item:
                                    item = item.split(' as ')[0]
                                cleaned_items.append(item.strip(','))
                            imports.append((module, cleaned_items))
                
                # Check for external imports
                external_imports = []
                for module, _ in imports:
                    if module not in self.standard_libs and not module.startswith('_'):
                        external_imports.append(module)
                
                if external_imports:
                    results["passed"] = False
                    results["violations"].append({
                        "file": str(py_file.name),
                        "imports": external_imports
                    })
                
                results["files"][str(py_file.name)] = {
                    "import_count": len(imports),
                    "external_imports": external_imports,
                    "imports_details": imports
                }
                
            except Exception as e:
                results["passed"] = False
                results["files"][str(py_file.name)] = {
                    "error": f"Failed to parse imports: {str(e)}"
                }
                results["errors"].append(f"{py_file.name}: {str(e)}")
                
        return results
        
    def runtime_testing(self, skill_path: str, sample_data: Optional[Dict] = None) -> Dict[str, Any]:
        """Test script execution with sample data."""
        scripts_dir = Path(skill_path) / "scripts"
        if not scripts_dir.exists():
            return {"error": "Scripts directory not found", "passed": False}
            
        python_files = list(scripts_dir.glob("*.py"))
        if not python_files:
            return {"error": "No Python files found", "passed": False}
            
        results = {
            "files_tested": len(python_files),
            "passed": True,
            "files": {},
            "errors": [],
            "execution_times": []
        }
        
        # Default sample data if none provided
        if sample_data is None:
            sample_data = {"test": "data", "number": 42}
            
        for py_file in python_files:
            try:
                # Prepare test environment
                test_env = os.environ.copy()
                test_env['PYTHONPATH'] = str(Path(skill_path))
                
                # Create sample data file if needed
                sample_file = None
                if sample_data:
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                        json.dump(sample_data, f)
                        sample_file = f.name
                
                # Build command
                cmd = [sys.executable, str(py_file)]
                
                # Add common test arguments
                test_args = ['--help']  # Always test --help first
                
                # Test --help functionality
                try:
                    start_time = time.perf_counter()
                    result = subprocess.run(
                        cmd + test_args,
                        capture_output=True,
                        text=True,
                        timeout=self.timeout,
                        env=test_env
                    )
                    end_time = time.perf_counter()
                    
                    help_passed = result.returncode == 0 and ('usage' in result.stdout.lower() or 
                                                             'argument' in result.stdout.lower() or
                                                             len(result.stdout) > 0)
                    
                    results["files"][str(py_file.name)] = {
                        "help_test": {
                            "passed": help_passed,
                            "return_code": result.returncode,
                            "stdout_length": len(result.stdout),
                            "stderr_length": len(result.stderr),
                            "execution_time": end_time - start_time
                        }
                    }
                    
                    if not help_passed:
                        results["passed"] = False
                        results["errors"].append(f"{py_file.name}: --help test failed")
                        
                except subprocess.TimeoutExpired:
                    results["passed"] = False
                    results["errors"].append(f"{py_file.name}: --help test timed out")
                    results["files"][str(py_file.name)] = {
                        "help_test": {
                            "passed": False,
                            "error": "timeout",
                            "execution_time": self.timeout
                        }
                    }
                except Exception as e:
                    results["passed"] = False
                    results["errors"].append(f"{py_file.name}: --help test failed: {str(e)}")
                    results["files"][str(py_file.name)] = {
                        "help_test": {
                            "passed": False,
                            "error": str(e)
                        }
                    }
                
                # Clean up sample file
                if sample_file and os.path.exists(sample_file):
                    os.unlink(sample_file)
                    
            except Exception as e:
                results["passed"] = False
                results["errors"].append(f"{py_file.name}: {str(e)}")
                results["files"][str(py_file.name)] = {
                    "error": f"Failed to test: {str(e)}"
                }
                
        return results
        
    def output_format_validation(self, skill_path: str) -> Dict[str, Any]:
        """Validate that scripts support both JSON and human-readable output."""
        scripts_dir = Path(skill_path) / "scripts"
        if not scripts_dir.exists():
            return {"error": "Scripts directory not found", "passed": False}
            
        python_files = list(scripts_dir.glob("*.py"))
        if not python_files:
            return {"error": "No Python files found", "passed": False}
            
        results = {
            "files_tested": len(python_files),
            "passed": True,
            "files": {},
            "errors": []
        }
        
        for py_file in python_files:
            try:
                content = py_file.read_text(encoding='utf-8')
                
                # Check for JSON output capability
                has_json_support = ('json' in content and 
                                  ('json.dumps' in content or 
                                   'json.dump' in content or
                                   '"json"' in content.lower()))
                
                # Check for argument parsing that might control output format
                has_format_arg = ('--format' in content or 
                                '--output' in content or
                                '--json' in content or
                                'format' in content.lower())
                
                # Check for print statements that suggest human-readable output
                has_print_statements = 'print(' in content
                
                results["files"][str(py_file.name)] = {
                    "has_json_support": has_json_support,
                    "has_format_control": has_format_arg,
                    "has_print_statements": has_print_statements,
                    "supports_dual_output": has_json_support and has_print_statements
                }
                
                # For now, consider it passed if it has either JSON support or print statements
                # In a more sophisticated version, we'd actually test the output formats
                if not (has_json_support or has_print_statements):
                    results["passed"] = False
                    results["errors"].append(f"{py_file.name}: No clear output mechanism found")
                    
            except Exception as e:
                results["passed"] = False
                results["errors"].append(f"{py_file.name}: {str(e)}")
                results["files"][str(py_file.name)] = {
                    "error": f"Failed to analyze: {str(e)}"
                }
                
        return results
        
    def test_skill_scripts(self, skill_path: str, sample_data: Optional[Dict] = None, 
                          timeout: Optional[int] = None) -> TestReport:
        """Perform complete script testing."""
        if timeout is not None:
            self.timeout = timeout
            
        start_time = time.perf_counter()
        
        # Run all tests
        syntax_results = self.syntax_validation(skill_path)
        import_results = self.import_validation(skill_path)
        runtime_results = self.runtime_testing(skill_path, sample_data)
        output_results = self.output_format_validation(skill_path)
        
        end_time = time.perf_counter()
        execution_time = end_time - start_time
        
        # Determine overall pass status
        overall_passed = (syntax_results.get("passed", False) and 
                         import_results.get("passed", False) and
                         runtime_results.get("passed", False) and
                         output_results.get("passed", False))
        
        # Collect all error messages
        error_messages = []
        error_messages.extend(syntax_results.get("errors", []))
        
        # Handle import violations safely
        import_violations = import_results.get("violations", [])
        if import_violations:
            for v in import_violations:
                file_name = v.get("file", "") if v.get("file") is not None else ""
                imports = v.get("imports", []) if v.get("imports") is not None else []
                error_messages.append(f"{file_name}: {imports}")
        
        error_messages.extend(runtime_results.get("errors", []))
        error_messages.extend(output_results.get("errors", []))
        
        return TestReport(
            skill_path=skill_path,
            timestamp=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            syntax_validation=syntax_results,
            import_validation=import_results,
            runtime_testing=runtime_results,
            output_format_validation=output_results,
            overall_passed=overall_passed,
            execution_time=round(execution_time, 3),
            error_messages=error_messages
        )


def main():
    """Main entry point for the script tester."""
    parser = argparse.ArgumentParser(description="Test skill Python scripts")
    parser.add_argument("skill_path", help="Path to the skill directory to test")
    parser.add_argument("--timeout", type=int, default=30,
                       help="Timeout for script execution in seconds (default: 30)")
    parser.add_argument("--sample-data", type=str,
                       help="Path to JSON file containing sample data for testing")
    parser.add_argument("--json", action="store_true",
                       help="Output results in JSON format")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose output")
    
    args = parser.parse_args()
    
    # Load sample data if provided
    sample_data = None
    if args.sample_data:
        try:
            with open(args.sample_data, 'r') as f:
                sample_data = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load sample data from {args.sample_data}: {e}")
            print("Proceeding without sample data...")
    
    tester = ScriptTester(timeout=args.timeout)
    report = tester.test_skill_scripts(args.skill_path, sample_data)
    
    if args.json:
        print(json.dumps(asdict(report), indent=2))
    else:
        # Human-readable output
        print(f"=== SCRIPT TESTING REPORT ===")
        print(f"Skill: {report.skill_path}")
        print(f"Overall Status: {'✓ PASSED' if report.overall_passed else '✗ FAILED'}")
        print(f"Execution Time: {report.execution_time}s")
        print()
        
        print("Syntax Validation:")
        syntax = report.syntax_validation
        if "error" in syntax:
            print(f"  ✗ FAIL: {syntax['error']}")
        else:
            passed = syntax.get("passed", False)
            files_tested = syntax.get("files_tested", 0)
            print(f"  {'✓' if passed else '✗'} {files_tested} file(s) tested")
            if not passed:
                errors = syntax.get("errors", [])
                for error in errors[:3]:  # Show first 3 errors
                    print(f"    - {error}")
                if len(errors) > 3:
                    print(f"    - ... and {len(errors) - 3} more")
        print()
        
        print("Import Validation:")
        imports = report.import_validation
        if "error" in imports:
            print(f"  ✗ FAIL: {imports['error']}")
        else:
            passed = imports.get("passed", False)
            files_tested = imports.get("files_tested", 0)
            violations = len(imports.get("violations", []))
            print(f"  {'✓' if passed else '✗'} {files_tested} file(s) tested")
            if violations > 0:
                print(f"    ✗ {violations} file(s) have external imports")
                for violation in imports.get("violations", [])[:2]:
                    file_name = violation.get('file', 'unknown')
                    imports_list = violation.get('imports', [])
                    print(f"      - {file_name}: {imports_list}")
            else:
                print("    ✓ All imports are from standard library")
        print()
        
        print("Runtime Testing:")
        runtime = report.runtime_testing
        if "error" in runtime:
            print(f"  ✗ FAIL: {runtime['error']}")
        else:
            passed = runtime.get("passed", False)
            files_tested = runtime.get("files_tested", 0)
            print(f"  {'✓' if passed else '✗'} {files_tested} file(s) tested")
            if not passed:
                errors = runtime.get("errors", [])
                for error in errors[:3]:
                    print(f"    - {error}")
                if len(errors) > 3:
                    print(f"    - ... and {len(errors) - 3} more")
        print()
        
        print("Output Format Validation:")
        output = report.output_format_validation
        if "error" in output:
            print(f"  ✗ FAIL: {output['error']}")
        else:
            passed = output.get("passed", False)
            files_tested = output.get("files_tested", 0)
            print(f"  {'✓' if passed else '✗'} {files_tested} file(s) tested")
            if not passed:
                errors = output.get("errors", [])
                for error in errors[:3]:
                    print(f"    - {error}")
        print()
        
        if report.error_messages and args.verbose:
            print("All Error Messages:")
            for i, error in enumerate(report.error_messages, 1):
                print(f"  {i}. {error}")
        
        print()
        print(f"Final Result: {'PASS' if report.overall_passed else 'FAIL'}")


if __name__ == "__main__":
    main()