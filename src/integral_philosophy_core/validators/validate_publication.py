#!/usr/bin/env python3
"""
Integration script for validation system with Integral Philosophy publishing pipeline.
Demonstrates end-to-end validation of publication outputs.
"""

import sys
import os
import tempfile
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from validators import (
    HTML5Validator,
    CSSValidator,
    JavaScriptValidator,
    LaTeXValidator,
    ContentIntegrityValidator,
    QualityReportGenerator,
)


def validate_publication_outputs():
    """Validate typical publication outputs from the Integral Philosophy system."""

    print("🔍 Validating Integral Philosophy Publication Outputs...\n")

    # Define output directories to validate
    output_dirs = {
        "html": Path("out/html"),
        "pdf": Path("out/pdf"),
        "epub": Path("out/epub"),
        "docx": Path("out/docx"),
    }

    validators = {
        "html": HTML5Validator(),
        "css": CSSValidator(),
        "js": JavaScriptValidator(),
        "latex": LaTeXValidator(),
    }

    results = {}

    # Validate HTML outputs
    if output_dirs["html"].exists():
        print("📄 Validating HTML outputs...")
        html_files = list(output_dirs["html"].glob("**/*.html"))
        css_files = list(output_dirs["html"].glob("**/*.css"))
        js_files = list(output_dirs["html"].glob("**/*.js"))

        html_results = []
        for html_file in html_files:
            result = validators["html"].validate(html_file)
            html_results.append(result)
            print(
                f"  ✓ {html_file.name}: {result.error_count} errors, {result.warning_count} warnings"
            )

        css_results = []
        for css_file in css_files:
            result = validators["css"].validate(css_file)
            css_results.append(result)
            print(
                f"  ✓ {css_file.name}: {result.error_count} errors, {result.warning_count} warnings"
            )

        js_results = []
        for js_file in js_files:
            result = validators["js"].validate(js_file)
            js_results.append(result)
            print(
                f"  ✓ {js_file.name}: {result.error_count} errors, {result.warning_count} warnings"
            )

        results["html"] = html_results
        results["css"] = css_results
        results["js"] = js_results

    # Validate LaTeX sources
    tex_files = list(Path(".").glob("**/*.tex"))
    if tex_files:
        print("\n📝 Validating LaTeX sources...")
        latex_results = []
        for tex_file in tex_files:
            if not any(skip in str(tex_file) for skip in ["tmp/", "out/"]):
                result = validators["latex"].validate(tex_file)
                latex_results.append(result)
                print(
                    f"  ✓ {tex_file.name}: {result.error_count} errors, {result.warning_count} warnings"
                )

        results["latex"] = latex_results

    # Content integrity validation
    integrity_formats = {}
    integrity_result = None

    # Always collect files for integrity checking if available
    if output_dirs["html"].exists():
        html_files = list(output_dirs["html"].glob("**/*.html"))
        if html_files:
            integrity_formats["html"] = html_files[0]  # Use first HTML file

    # Add source LaTeX if available
    if Path("main.tex").exists():
        integrity_formats["latex"] = Path("main.tex")

    # Run integrity validation if we have at least 2 formats
    if len(integrity_formats) >= 2:
        print("\n🔗 Validating content integrity across formats...")

        integrity_validator = ContentIntegrityValidator()
        integrity_result = integrity_validator.validate_integrity_across_formats(
            integrity_formats
        )
        results["integrity"] = [integrity_result]
        print(
            f"  ✓ Content integrity: {integrity_result.error_count} errors, {integrity_result.warning_count} warnings"
        )
        print(
            f"  ✓ Similarity scores: {integrity_result.stats.get('similarity_scores', {})}"
        )
    else:
        # Create a dummy integrity result if we don't have enough formats
        if len(integrity_formats) == 1:
            print(
                f"\n🔗 Content integrity check skipped: only 1 format available ({list(integrity_formats.keys())[0]})"
            )

    # Generate quality report
    print("\n📊 Generating quality report...")

    # Flatten all results for report generation
    all_validation_results = {}
    for format_name, format_results in results.items():
        if format_results:
            if format_name == "integrity":
                all_validation_results[format_name] = format_results[0]
            else:
                # Take worst result for each format as representative
                worst_result = max(
                    format_results, key=lambda r: r.error_count + r.warning_count
                )
                all_validation_results[format_name] = worst_result

    if all_validation_results:
        generator = QualityReportGenerator()
        report = generator.generate_report(
            source_files=[Path("main.tex")],
            output_formats=integrity_formats,
            validation_results=all_validation_results,
            processing_time=5.0,
        )

        # Only try to access integrity_result if it exists
        if len(integrity_formats) >= 2:
            integrity_result = all_validation_results.get("integrity")
            if integrity_result:
                error_count = len(
                    [e for e in integrity_result.errors if e.severity == "error"]
                )
                warning_count = len(
                    [e for e in integrity_result.errors if e.severity == "warning"]
                )
                stats = integrity_result.stats or {}
                print(
                    f"  ✓ Content integrity: {error_count} errors, {warning_count} warnings"
                )
                print(f"  ✓ Similarity scores: {stats.get('similarity_scores', {})}")

    # Generate quality report
    print("\n📊 Generating quality report...")

    # Flatten all results for report generation
    all_validation_results = {}
    for format_name, format_results in results.items():
        if format_results:
            if format_name == "integrity":
                all_validation_results[format_name] = format_results[0]
            else:
                # Take the worst result for each format as representative
                worst_result = max(
                    format_results, key=lambda r: r.error_count + r.warning_count
                )
                all_validation_results[format_name] = worst_result

    if all_validation_results:
        generator = QualityReportGenerator()
        report = generator.generate_report(
            source_files=[Path("main.tex")],
            output_formats={
                k: v
                for k, v in integrity_formats.items()
                if k in all_validation_results
            },
            validation_results=all_validation_results,
            processing_time=5.0,
        )

        print(
            f"  ✓ Overall quality score: {report.quality_metrics.overall_score:.1f}/100"
        )
        print(f"  ✓ Format scores: {report.quality_metrics.format_scores}")
        print(f"  ✓ Integrity score: {report.quality_metrics.integrity_score:.1f}")
        print(
            f"  ✓ Accessibility score: {report.quality_metrics.accessibility_score:.1f}"
        )
        print(
            f"  ✓ Standards compliance: {report.quality_metrics.standards_compliance:.1f}"
        )
        print(f"  ✓ Recommendations: {len(report.recommendations)}")

        # Save reports
        report_dir = Path("out/validation_reports")
        report_dir.mkdir(parents=True, exist_ok=True)

        json_report = report_dir / "quality_report.json"
        html_report = report_dir / "quality_report.html"
        markdown_report = report_dir / "quality_report.md"

        generator.save_report(report, json_report, "json")
        generator.save_report(report, html_report, "html")
        generator.save_report(report, markdown_report, "markdown")

        print(f"  ✓ Reports saved to: {report_dir}")

        # Summary of key recommendations
        if report.recommendations:
            print(f"\n🎯 Key Recommendations:")
            for rec in report.recommendations[:5]:  # Show top 5
                print(f"    • {rec}")

    return True


def main():
    """Run publication validation."""
    print("🚀 Integral Philosophy Publication Validation\n")

    try:
        success = validate_publication_outputs()

        print("\n" + "=" * 60)
        print("✅ Publication validation completed successfully")
        print("📈 Quality reports are available in out/validation_reports/")

        return 0

    except Exception as e:
        print(f"\n❌ Publication validation failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
