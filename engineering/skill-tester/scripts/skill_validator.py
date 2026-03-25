#!/usr/bin/env python3
"""
Skill Validator - Validates skill structure and documentation compliance.

This script performs structural validation of skills, checking for required
directories, files, and documentation standards compliance.
"""

import os
import sys
import json
import argparse
import yaml
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict


@dataclass
class ValidationReport:
    """Report structure for skill validation results."""
    skill_path: str
    tier: str
    timestamp: str
    structure_compliance: Dict[str, Any]
    documentation_compliance: Dict[str, Any]
    overall_score: float
    letter_grade: str
    tier_recommendation: str
    improvement_suggestions: List[str]


class SkillValidator:
    """Main skill validation engine."""
    
    def __init__(self):
        self.required_dirs = ['scripts', 'references', 'assets', 'expected_outputs']
        self.required_files = ['SKILL.md', 'README.md']
        self.sections_required = [
            'Description', 'Features', 'Usage', 'Core Approach',
            'Implementation Details', 'Usage Scenarios'
        ]
        
    def validate_skill_structure(self, skill_path: str) -> Dict[str, Any]:
        """Validate the directory structure of a skill."""
        skill_dir = Path(skill_path)
        if not skill_dir.exists():
            return {"error": f"Skill directory {skill_path} does not exist"}
             
        results = {
            "skill_md_exists": False,
            "readme_exists": False,
            "scripts_directory": False,
            "references_directory": False,
            "assets_directory": False,
            "expected_outputs_directory": False,
            "missing_items": [],
            "present_items": []
        }
         
        # Check required files
        for req_file in self.required_files:
            if (skill_dir / req_file).exists():
                results[f"{req_file.lower().replace('.', '_')}_exists"] = True
                results["present_items"].append(req_file)
            else:
                results["missing_items"].append(req_file)
                 
        # Check required directories
        for req_dir in self.required_dirs:
            if (skill_dir / req_dir).exists() and (skill_dir / req_dir).is_dir():
                results[f"{req_dir}_directory"] = True
                results["present_items"].append(req_dir)
            else:
                results["missing_items"].append(req_dir)
                 
        return results
         
    def check_skill_md_compliance(self, skill_path: str) -> Dict[str, Any]:
        """Check SKILL.md for compliance with standards."""
        skill_md_path = Path(skill_path) / "SKILL.md"
        if not skill_md_path.exists():
            return {"error": "SKILL.md not found"}
             
        try:
            content = skill_md_path.read_text(encoding='utf-8')
            lines = content.split('\n')
            line_count = len(lines)
             
            # Check frontmatter
            frontmatter_valid = False
            frontmatter_data = {}
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    try:
                        frontmatter_data = yaml.safe_load(parts[1])
                        frontmatter_valid = True
                    except yaml.YAMLError:
                        pass
             
            # Check required sections
            sections_found = []
            for section in self.sections_required:
                # Look for section headers (## Section Name or # Section Name)
                pattern = rf'^#+\s*{re.escape(section)}'
                if any(re.match(pattern, line, re.IGNORECASE) for line in lines):
                    sections_found.append(section)
                     
            # Check for code examples
            has_code_examples = '```' in content
             
            return {
                "line_count": line_count,
                "frontmatter_valid": frontmatter_valid,
                "frontmatter_data": frontmatter_data,
                "sections_found": sections_found,
                "sections_missing": [s for s in self.sections_required if s not in sections_found],
                "has_code_examples": has_code_examples,
                "min_line_count_met": line_count >= 100  # BASIC tier minimum
            }
        except Exception as e:
            return {"error": f"Failed to read SKILL.md: {str(e)}"}
             
    def validate_python_scripts(self, skill_path: str) -> Dict[str, Any]:
        """Validate Python scripts for syntax and basic requirements."""
        scripts_dir = Path(skill_path) / "scripts"
        if not scripts_dir.exists():
            return {"error": "Scripts directory not found"}
             
        python_files = list(scripts_dir.glob("*.py"))
        if not python_files:
            return {"error": "No Python files found in scripts directory"}
             
        results = {
            "python_files_found": len(python_files),
            "files": {},
            "total_lines": 0,
            "syntax_errors": [],
            "import_violations": []
        }
         
        for py_file in python_files:
            try:
                content = py_file.read_text(encoding='utf-8')
                lines = content.split('\n')
                line_count = len(lines)
                 
                # Basic syntax check
                try:
                    compile(content, str(py_file), 'exec')
                    syntax_valid = True
                except SyntaxError as e:
                    syntax_valid = False
                    results["syntax_errors"].append({
                        "file": str(py_file.relative_to(Path(skill_path))),
                        "error": str(e),
                        "line": e.lineno
                    })
                 
                # Check for external imports (basic check)
                import_lines = [line.strip() for line in lines 
                              if line.strip().startswith(('import ', 'from '))]
                external_imports = []
                standard_libs = {
                    'os', 'sys', 'json', 'argparse', 'pathlib', 'typing',
                    'dataclasses', 'yaml', 're', 'csv', 'math', 'datetime',
                    'collections', 'itertools', 'functools', 'hashlib',
                    'subprocess', 'tempfile', 'shutil', 'glob', 'statistics'
                }
                 
                for imp in import_lines:
                    if imp.startswith('import '):
                        module = imp.split()[1].split('.')[0]
                    elif imp.startswith('from '):
                        module = imp.split()[1].split('.')[0]
                    else:
                        continue
                         
                    if module not in standard_libs and not module.startswith('_'):
                        external_imports.append(module)
                         
                if external_imports:
                    results["import_violations"].append({
                        "file": str(py_file.relative_to(Path(skill_path))),
                        "imports": external_imports
                    })
                 
                results["files"][str(py_file.name)] = {
                    "line_count": line_count,
                    "syntax_valid": syntax_valid,
                    "import_count": len(import_lines),
                    "has_main_guard": "if __name__ == '__main__'" in content,
                    "has_argparse": "argparse" in content or "ArgumentParser" in content
                }
                 
                results["total_lines"] += line_count
                 
            except Exception as e:
                results["files"][str(py_file.name)] = {
                    "error": f"Failed to process file: {str(e)}"
                }
                 
        return results
         
    def calculate_compliance_score(self, structure_results: Dict, 
                                 doc_results: Dict, 
                                 script_results: Dict) -> Tuple[float, str]:
        """Calculate overall compliance score and letter grade."""
        score = 0.0
        max_score = 100.0
         
        # Structure compliance (40 points)
        structure_score = 0
        if not structure_results.get("error"):
            structure_checks = [
                structure_results.get("skill_md_exists", False),
                structure_results.get("readme_exists", False),
                structure_results.get("scripts_directory", False),
                structure_results.get("references_directory", False)
            ]
            structure_score = (sum(structure_checks) / len(structure_checks)) * 40
        score += structure_score
         
        # Documentation compliance (30 points)
        doc_score = 0
        if not doc_results.get("error"):
            line_count = doc_results.get("line_count", 0)
            frontmatter_valid = doc_results.get("frontmatter_valid", False)
            sections_found = len(doc_results.get("sections_found", []))
            sections_total = len(self.sections_required)
             
            # Line count scoring (up to 10 points)
            line_score = min(10, (line_count / 300) * 10)  # POWERFUL tier is 300+
             
            # Frontmatter scoring (up to 5 points)
            frontmatter_score = 5 if frontmatter_valid else 0
             
            # Sections scoring (up to 15 points)
            section_score = (sections_found / sections_total) * 15 if sections_total > 0 else 0
             
            doc_score = line_score + frontmatter_score + section_score
        score += doc_score
         
        # Script compliance (30 points)
        script_score = 0
        if not script_results.get("error"):
            syntax_valid_count = sum(1 for f in script_results.get("files", {}).values() 
                                   if isinstance(f, dict) and f.get("syntax_valid", False))
            total_files = len(script_results.get("files", {}))
             
            if total_files > 0:
                syntax_score = (syntax_valid_count / total_files) * 15  # Half for syntax
                 
                # Import compliance (half for no external deps)
                import_violations = len(script_results.get("import_violations", []))
                import_score = 15 if import_violations == 0 else max(0, 15 - (import_violations * 5))
                 
                script_score = syntax_score + import_score
        score += script_score
         
        # Determine letter grade
        if score >= 90:
            letter_grade = "A"
        elif score >= 80:
            letter_grade = "B"
        elif score >= 70:
            letter_grade = "C"
        elif score >= 60:
            letter_grade = "D"
        else:
            letter_grade = "F"
             
        return score, letter_grade
         
    def get_tier_recommendation(self, line_count: int, script_results: Dict) -> str:
        """Recommend appropriate tier based on skill complexity."""
        total_lines = script_results.get("total_lines", 0) or 0
        python_files = script_results.get("python_files_found", 0) or 0
         
        if line_count >= 300 and total_lines >= 1000 and python_files >= 2:
            return "POWERFUL"
        elif line_count >= 200 and total_lines >= 600 and python_files >= 1:
            return "STANDARD"
        else:
            return "BASIC"
         
    def generate_improvement_suggestions(self, structure_results: Dict,
                                       doc_results: Dict,
                                       script_results: Dict) -> List[str]:
        """Generate improvement suggestions based on validation results."""
        suggestions = []
         
        # Structure suggestions
        if structure_results.get("missing_items"):
            missing = structure_results["missing_items"]
            suggestions.append(f"Add missing items: {', '.join(missing)}")
             
        # Documentation suggestions
        if not doc_results.get("error"):
            line_count = doc_results.get("line_count", 0) or 0
            if line_count < 100:
                suggestions.append("Increase SKILL.md length (minimum 100 lines for BASIC tier)")
            if not doc_results.get("frontmatter_valid", False):
                suggestions.append("Add valid YAML frontmatter to SKILL.md")
            missing_sections = doc_results.get("sections_missing", [])
            if missing_sections:
                suggestions.append(f"Add missing sections: {', '.join(missing_sections)}")
            if not doc_results.get("has_code_examples", False):
                suggestions.append("Add code examples to SKILL.md using markdown code blocks")
                 
        # Script suggestions
        if not script_results.get("error"):
            syntax_errors = script_results.get("syntax_errors", [])
            if syntax_errors:
                suggestions.append(f"Fix syntax errors in {len(syntax_errors)} Python file(s)")
                 
            import_violations = script_results.get("import_violations", [])
            if import_violations:
                suggestions.append("Use only standard library imports (remove external dependencies)")
                 
            files = script_results.get("files", {})
            no_argparse = []
            for fname, fdata in files.items():
                if isinstance(fdata, dict) and not fdata.get("has_argparse", False):
                    no_argparse.append(fname)
            if no_argparse and len(files) > 0:
                suggestions.append("Add argparse implementation to Python scripts for CLI support")
                 
        return suggestions
         
    def validate_skill(self, skill_path: str, target_tier: Optional[str] = None) -> ValidationReport:
        """Perform complete skill validation."""
         
        # Validate structure
        structure_results = self.validate_skill_structure(skill_path)
         
        # Validate documentation
        doc_results = self.check_skill_md_compliance(skill_path)
         
        # Validate scripts
        script_results = self.validate_python_scripts(skill_path)
         
        # Calculate scores
        overall_score, letter_grade = self.calculate_compliance_score(
            structure_results, doc_results, script_results)
             
        # Get tier recommendation
        line_count = doc_results.get("line_count", 0) if not doc_results.get("error") else 0
        tier_recommendation = self.get_tier_recommendation(line_count, script_results)
         
        # Override with target tier if specified
        if target_tier:
            tier_recommendation = target_tier
             
        # Generate suggestions
        improvement_suggestions = self.generate_improvement_suggestions(
            structure_results, doc_results, script_results)
             
        return ValidationReport(
            skill_path=skill_path,
            tier=tier_recommendation,
            timestamp=datetime.now().isoformat(),
            structure_compliance=structure_results,
            documentation_compliance=doc_results,
            overall_score=round(overall_score, 2),
            letter_grade=letter_grade,
            tier_recommendation=tier_recommendation,
            improvement_suggestions=improvement_suggestions
        )


def main():
    """Main entry point for the skill validator."""
    parser = argparse.ArgumentParser(description="Validate skill structure and documentation")
    parser.add_argument("skill_path", help="Path to the skill directory to validate")
    parser.add_argument("--tier", choices=["BASIC", "STANDARD", "POWERFUL"], 
                       help="Target tier for validation (optional)")
    parser.add_argument("--json", action="store_true", 
                       help="Output results in JSON format")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose output")
     
    args = parser.parse_args()
     
    validator = SkillValidator()
    report = validator.validate_skill(args.skill_path, args.tier)
     
    if args.json:
        print(json.dumps(asdict(report), indent=2))
    else:
        # Human-readable output
        print(f"=== SKILL VALIDATION REPORT ===")
        print(f"Skill: {report.skill_path}")
        print(f"Tier: {report.tier}")
        print(f"Overall Score: {report.overall_score}/100 ({report.letter_grade})")
        print()
         
        print("Structure Validation:")
        struct = report.structure_compliance
        if "error" in struct:
            print(f"  ✗ FAIL: {struct['error']}")
        else:
            skill_md = "✓" if struct.get("skill_md_exists") else "✗"
            readme = "✓" if struct.get("readme_exists") else "✗"
            scripts = "✓" if struct.get("scripts_directory") else "✗"
            refs = "✓" if struct.get("references_directory") else "✗"
            skill_md_exists = struct.get('skill_md_exists', False)
            print(f"  ├─ SKILL.md: {skill_md} EXISTS ({skill_md_exists})")
            print(f"  ├─ README.md: {readme} EXISTS")
            print(f"  ├─ scripts/: {scripts} EXISTS")
            refs_exists = struct.get('references_directory', False)
            refs_status = 'EXISTS' if refs_exists else 'MISSING (recommended)'
            print(f"  └─ references/: {refs} {refs_status}")
        print()
         
        print("Documentation Quality:")
        doc = report.documentation_compliance
        if "error" in doc:
            print(f"  ✗ FAIL: {doc['error']}")
        else:
            line_count = doc.get("line_count", 0)
            frontmatter = "✓" if doc.get("frontmatter_valid") else "✗"
            sections_found = len(doc.get("sections_found", []))
            sections_total = len(validator.sections_required)
            line_count_adequate = line_count >= 100
            print(f"  ├─ Lines: {line_count} ({'✓' if line_count_adequate else '✗'} minimum 100)")
            print(f"  ├─ Frontmatter: {frontmatter} VALID")
            print(f"  ├─ Sections: {sections_found}/{sections_total} FOUND")
            if doc.get("sections_missing"):
                missing_str = ', '.join(doc['sections_missing'])
                print(f"  └─ Missing: {missing_str}")
        print()
         
        print("Improvement Recommendations:")
        if report.improvement_suggestions:
            for i, suggestion in enumerate(report.improvement_suggestions, 1):
                print(f"  {i}. {suggestion}")
        else:
            print("  No improvements needed - skill meets all requirements!")
        print()
         
        assessment = 'PASS' if report.letter_grade in ['A', 'B', 'C'] else 'NEEDS IMPROVEMENT'
        print(f"Overall Assessment: {report.letter_grade} ({assessment})")


if __name__ == "__main__":
    main()