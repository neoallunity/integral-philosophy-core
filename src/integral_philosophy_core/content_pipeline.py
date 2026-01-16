#!/usr/bin/env python3
"""
Master Content Pipeline Controller
Orchestrates the complete conversion pipeline:
Website → HTML → TEI → Multiple Formats (HTML, LaTeX, PDF, EPUB, DOCX)
With UML visualization and isomorphism testing
"""

import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
import logging

# Import pipeline components
try:
    from web_scraper import WebScraper
    from markdowntex_parser import MarkdownTeXParser
    from ast_to_uml import ASTToUMLTransformer
    from tei_generator import TEIGenerator
    from xslt_transformer import XSLTTransformer
    from html_tei_converter import HTMLTEIConverter
except ImportError:
    from scripts.web_scraper import WebScraper
    from scripts.markdowntex_parser import MarkdownTeXParser
    from scripts.ast_to_uml import ASTToUMLTransformer
    from scripts.tei_generator import TEIGenerator
    from scripts.xslt_transformer import XSLTTransformer
    from scripts.html_tei_converter import HTMLTEIConverter

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("pipeline.log"), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


class ContentPipeline:
    """Master content transformation pipeline"""

    def __init__(self, work_dir: Path = Path("content_pipeline")):
        self.work_dir = work_dir
        self.work_dir.mkdir(exist_ok=True)

        # Create subdirectories
        self.dirs = {
            "scraped": self.work_dir / "01_scraped",
            "parsed": self.work_dir / "02_parsed",
            "uml": self.work_dir / "03_uml",
            "tei": self.work_dir / "04_tei",
            "transformed": self.work_dir / "05_transformed",
            "validation": self.work_dir / "06_validation",
            "reports": self.work_dir / "reports",
        }

        for dir_path in self.dirs.values():
            dir_path.mkdir(exist_ok=True)

        # Initialize pipeline components
        self.scraper = None
        self.parser = MarkdownTeXParser()
        self.uml_transformer = ASTToUMLTransformer()
        self.tei_generator = TEIGenerator()
        self.xslt_transformer = XSLTTransformer()
        self.html_tei_converter = HTMLTEIConverter()

        # Pipeline results
        self.results = {
            "start_time": None,
            "end_time": None,
            "duration": None,
            "stages": {},
            "success": False,
        }

    async def process_website(self, url: str, max_pages: int = 100) -> bool:
        """Process complete website through the pipeline"""
        logger.info(f"Starting pipeline for: {url}")
        self.results["start_time"] = time.time()

        try:
            # Stage 1: Web Scraping
            if not await self._stage_1_scrape_website(url, max_pages):
                return False

            # Stage 2: Content Parsing
            if not await self._stage_2_parse_content():
                return False

            # Stage 3: UML Generation
            if not await self._stage_3_generate_uml():
                return False

            # Stage 4: TEI Generation
            if not await self._stage_4_generate_tei():
                return False

            # Stage 5: Multi-format Transformation
            if not await self._stage_5_transform_formats():
                return False

            # Stage 6: Validation & Testing
            if not await self._stage_6_validate_pipeline():
                return False

            # Complete pipeline
            self.results["end_time"] = time.time()
            self.results["duration"] = (
                self.results["end_time"] - self.results["start_time"]
            )
            self.results["success"] = True

            logger.info(
                f"Pipeline completed successfully in {self.results['duration']:.2f} seconds"
            )
            return True

        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            self.results["error"] = str(e)
            self.results["end_time"] = time.time()
            self.results["duration"] = (
                self.results["end_time"] - self.results["start_time"]
            )
            return False

    async def _stage_1_scrape_website(self, url: str, max_pages: int) -> bool:
        """Stage 1: Scrape website content"""
        logger.info("=== Stage 1: Web Scraping ===")

        try:
            self.scraper = WebScraper(url, str(self.dirs["scraped"]))
            self.scraper.recursive_scrape(max_pages=max_pages)

            # Check results
            site_ast_file = self.dirs["scraped"] / "site_ast.json"
            if not site_ast_file.exists():
                logger.error("Site AST not generated")
                return False

            # Load and store results
            with open(site_ast_file, "r", encoding="utf-8") as f:
                site_ast = json.load(f)

            self.results["stages"]["scraping"] = {
                "success": True,
                "pages_downloaded": site_ast["metadata"]["total_pages"],
                "failed_pages": site_ast["metadata"].get("failed_pages", 0),
                "scraped_at": site_ast["metadata"]["scraped_at"],
            }

            logger.info(f"Scraped {site_ast['metadata']['total_pages']} pages")
            return True

        except Exception as e:
            logger.error(f"Scraping failed: {e}")
            self.results["stages"]["scraping"] = {"success": False, "error": str(e)}
            return False

    async def _stage_2_parse_content(self) -> bool:
        """Stage 2: Parse MarkdownTeX content to AST"""
        logger.info("=== Stage 2: Content Parsing ===")

        try:
            pages_dir = self.dirs["scraped"] / "pages"
            parsed_pages = {}
            total_files = 0
            successful_parses = 0

            for md_file in pages_dir.glob("*.md"):
                total_files += 1

                try:
                    # Read markdown content
                    with open(md_file, "r", encoding="utf-8") as f:
                        content = f.read()

                    # Parse to AST
                    ast = self.parser.parse(content)

                    # Save AST
                    ast_file = self.dirs["parsed"] / f"{md_file.stem}.ast.json"
                    self.parser.save_ast(ast, ast_file)

                    # Extract metadata
                    metadata_file = pages_dir / f"{md_file.stem}.json"
                    if metadata_file.exists():
                        with open(metadata_file, "r", encoding="utf-8") as f:
                            metadata = json.load(f)
                    else:
                        metadata = {}

                    parsed_pages[str(md_file.relative_to(pages_dir))] = {
                        "ast_file": str(ast_file.relative_to(self.work_dir)),
                        "metadata": metadata,
                        "content_length": len(content),
                    }

                    successful_parses += 1

                except Exception as e:
                    logger.warning(f"Failed to parse {md_file}: {e}")

            # Save parsed content summary
            summary_file = self.dirs["parsed"] / "parsed_summary.json"
            with open(summary_file, "w", encoding="utf-8") as f:
                json.dump(parsed_pages, f, indent=2, ensure_ascii=False)

            self.results["stages"]["parsing"] = {
                "success": True,
                "total_files": total_files,
                "successful_parses": successful_parses,
                "parse_rate": successful_parses / total_files if total_files > 0 else 0,
            }

            logger.info(f"Parsed {successful_parses}/{total_files} files successfully")
            return True

        except Exception as e:
            logger.error(f"Parsing failed: {e}")
            self.results["stages"]["parsing"] = {"success": False, "error": str(e)}
            return False

    async def _stage_3_generate_uml(self) -> bool:
        """Stage 3: Generate UML diagrams from site structure"""
        logger.info("=== Stage 3: UML Generation ===")

        try:
            # Load site AST
            site_ast_file = self.dirs["scraped"] / "site_ast.json"
            with open(site_ast_file, "r", encoding="utf-8") as f:
                site_ast = json.load(f)

            # Transform to UML
            uml_data = self.uml_transformer.transform_site_ast(site_ast)

            # Generate all UML formats
            self.uml_transformer.generate_all_formats(uml_data, self.dirs["uml"])

            # Save UML data
            uml_data_file = self.dirs["uml"] / "uml_data.json"
            with open(uml_data_file, "w", encoding="utf-8") as f:
                json.dump(uml_data, f, indent=2, ensure_ascii=False)

            self.results["stages"]["uml"] = {
                "success": True,
                "nodes": len(uml_data["nodes"]),
                "edges": len(uml_data["edges"]),
                "formats_generated": ["plantuml", "mermaid", "graphviz"],
            }

            logger.info(
                f"Generated UML with {len(uml_data['nodes'])} nodes and {len(uml_data['edges'])} edges"
            )
            return True

        except Exception as e:
            logger.error(f"UML generation failed: {e}")
            self.results["stages"]["uml"] = {"success": False, "error": str(e)}
            return False

    async def _stage_4_generate_tei(self) -> bool:
        """Stage 4: Generate canonical TEI XML format"""
        logger.info("=== Stage 4: TEI Generation ===")

        try:
            # Load site AST
            site_ast_file = self.dirs["scraped"] / "site_ast.json"
            with open(site_ast_file, "r", encoding="utf-8") as f:
                site_ast = json.load(f)

            # Generate TEI XML
            tei_xml = self.tei_generator.generate_tei_document(site_ast)

            # Save TEI document
            tei_file = self.dirs["tei"] / "site_document.xml"
            self.tei_generator.save_tei_document(tei_xml, tei_file)

            # Validate TEI XML
            validation_result = self._validate_xml(tei_file)

            self.results["stages"]["tei"] = {
                "success": True,
                "tei_file": str(tei_file.relative_to(self.work_dir)),
                "file_size": tei_file.stat().st_size,
                "validation": validation_result,
            }

            logger.info(f"Generated TEI XML: {tei_file}")
            return True

        except Exception as e:
            logger.error(f"TEI generation failed: {e}")
            self.results["stages"]["tei"] = {"success": False, "error": str(e)}
            return False

    async def _stage_5_transform_formats(self) -> bool:
        """Stage 5: Transform TEI to multiple output formats"""
        logger.info("=== Stage 5: Multi-format Transformation ===")

        try:
            tei_file = self.dirs["tei"] / "site_document.xml"

            # Transform to all formats
            results = self.xslt_transformer.transform_all_formats(
                tei_file, self.dirs["transformed"]
            )

            # Generate format-specific reports
            format_details = {}
            for format_name, success in results.items():
                format_details[format_name] = {
                    "success": success,
                    "file_exists": (
                        self.dirs["transformed"] / f"document.{format_name}"
                    ).exists(),
                }

            successful_formats = sum(1 for success in results.values() if success)

            self.results["stages"]["transformation"] = {
                "success": successful_formats > 0,
                "formats": format_details,
                "successful_formats": successful_formats,
                "total_formats": len(results),
            }

            logger.info(
                f"Transformed to {successful_formats}/{len(results)} formats successfully"
            )
            return successful_formats > 0

        except Exception as e:
            logger.error(f"Transformation failed: {e}")
            self.results["stages"]["transformation"] = {
                "success": False,
                "error": str(e),
            }
            return False

    async def _stage_6_validate_pipeline(self) -> bool:
        """Stage 6: Validate pipeline and test isomorphism"""
        logger.info("=== Stage 6: Validation & Testing ===")

        try:
            validation_results = {}

            # Test HTML ↔ TEI isomorphism
            if (self.dirs["transformed"] / "document.html").exists():
                html_file = self.dirs["transformed"] / "document.html"
                isomorphism_result = self.html_tei_converter.test_isomorphism(html_file)
                validation_results["html_tei_isomorphism"] = isomorphism_result

            # Validate TEI structure
            tei_file = self.dirs["tei"] / "site_document.xml"
            if tei_file.exists():
                tei_validation = self._validate_tei_structure(tei_file)
                validation_results["tei_structure"] = tei_validation

            # Check format consistency
            format_consistency = self._check_format_consistency()
            validation_results["format_consistency"] = format_consistency

            # Generate pipeline summary
            self.results["stages"]["validation"] = {
                "success": len(validation_results) > 0,
                "results": validation_results,
            }

            logger.info("Validation completed successfully")
            return True

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            self.results["stages"]["validation"] = {"success": False, "error": str(e)}
            return False

    def _validate_xml(self, xml_file: Path) -> Dict[str, Any]:
        """Validate XML file"""
        try:
            result = subprocess.run(
                ["xmllint", "--noout", str(xml_file)], capture_output=True, text=True
            )

            return {
                "valid": result.returncode == 0,
                "error": result.stderr if result.returncode != 0 else None,
            }
        except FileNotFoundError:
            return {"valid": False, "error": "xmllint not found"}
        except Exception as e:
            return {"valid": False, "error": str(e)}

    def _validate_tei_structure(self, tei_file: Path) -> Dict[str, Any]:
        """Validate TEI structure"""
        try:
            # Check for required TEI elements
            checks = {
                "has_tei_header": self._xpath_count(tei_file, "count(//tei:teiHeader)")
                > 0,
                "has_text": self._xpath_count(tei_file, "count(//tei:text)") > 0,
                "has_body": self._xpath_count(tei_file, "count(//tei:body)") > 0,
                "has_pages": self._xpath_count(
                    tei_file, 'count(//tei:div[@type="page"])'
                )
                > 0,
            }

            return {
                "valid": all(checks.values()),
                "checks": checks,
                "total_divs": self._xpath_count(tei_file, "count(//tei:div)"),
            }

        except Exception as e:
            return {"valid": False, "error": str(e)}

    def _check_format_consistency(self) -> Dict[str, Any]:
        """Check consistency across generated formats"""
        consistency = {}

        try:
            # Check if all expected files exist
            expected_files = [
                "document.html",
                "document.tex",
                "document.pdf",
                "document.epub",
                "document.docx",
            ]
            existing_files = []

            for filename in expected_files:
                file_path = self.dirs["transformed"] / filename
                exists = file_path.exists()
                consistency[filename] = {
                    "exists": exists,
                    "size": file_path.stat().st_size if exists else None,
                }
                if exists:
                    existing_files.append(filename)

            consistency["summary"] = {
                "total_formats": len(expected_files),
                "existing_formats": len(existing_files),
                "generation_rate": len(existing_files) / len(expected_files),
            }

            return consistency

        except Exception as e:
            return {"error": str(e)}

    def _xpath_count(self, xml_file: Path, xpath: str) -> int:
        """Get XPath count from XML file"""
        try:
            result = subprocess.run(
                ["xmllint", "--xpath", xpath, str(xml_file)],
                capture_output=True,
                text=True,
                env={"LC_ALL": "C"},
            )

            if result.returncode == 0:
                return int(result.stdout.strip())
        except:
            pass

        return 0

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive pipeline report"""
        report = {
            "pipeline_info": {
                "version": "1.0.0",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "work_directory": str(self.work_dir),
            },
            "results": self.results,
            "directory_structure": self._get_directory_structure(),
            "recommendations": self._generate_recommendations(),
        }

        # Save report
        report_file = self.dirs["reports"] / f"pipeline_report_{int(time.time())}.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"Pipeline report saved to: {report_file}")
        return report

    def _get_directory_structure(self) -> Dict[str, Any]:
        """Get directory structure and file counts"""
        structure = {}

        for name, path in self.dirs.items():
            if path.exists():
                files = list(path.rglob("*"))
                structure[name] = {
                    "path": str(path),
                    "total_files": len([f for f in files if f.is_file()]),
                    "directories": len([f for f in files if f.is_dir()]),
                }
            else:
                structure[name] = {"path": str(path), "exists": False}

        return structure

    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on pipeline results"""
        recommendations = []

        if not self.results.get("success", False):
            recommendations.append("Pipeline failed - check error messages in results")

        # Check each stage
        for stage_name, stage_result in self.results.get("stages", {}).items():
            if not stage_result.get("success", False):
                recommendations.append(
                    f"Stage {stage_name} failed - review error details"
                )

        # Check success rates
        parsing_result = self.results.get("stages", {}).get("parsing", {})
        if parsing_result.get("parse_rate", 1.0) < 0.9:
            recommendations.append(
                "Consider improving content parsing - success rate < 90%"
            )

        transformation_result = self.results.get("stages", {}).get("transformation", {})
        if transformation_result.get("successful_formats", 0) < 4:
            recommendations.append(
                "Some format transformations failed - check dependencies"
            )

        validation_result = (
            self.results.get("stages", {}).get("validation", {}).get("results", {})
        )
        if "html_tei_isomorphism" in validation_result:
            if not validation_result["html_tei_isomorphism"].get("isomorphic", False):
                recommendations.append(
                    "HTML ↔ TEI isomorphism test failed - review transformation logic"
                )

        return recommendations


async def main():
    """Main pipeline execution"""
    import argparse

    parser = argparse.ArgumentParser(description="Master Content Pipeline")
    parser.add_argument("url", help="Website URL to process")
    parser.add_argument(
        "-o", "--output", default="content_pipeline", help="Output directory"
    )
    parser.add_argument(
        "-p", "--pages", type=int, default=100, help="Maximum pages to scrape"
    )
    parser.add_argument(
        "--report-only", action="store_true", help="Generate report only"
    )

    args = parser.parse_args()

    # Initialize pipeline
    pipeline = ContentPipeline(Path(args.output))

    if args.report_only:
        # Generate existing report
        report = pipeline.generate_report()
        print(json.dumps(report, indent=2))
        return

    # Execute pipeline
    success = await pipeline.process_website(args.url, args.pages)

    # Generate final report
    report = pipeline.generate_report()

    # Print summary
    print("\\n=== Pipeline Summary ===")
    print(f"Success: {report['results']['success']}")
    if report["results"]["duration"]:
        print(f"Duration: {report['results']['duration']:.2f} seconds")

    for stage, result in report["results"].get("stages", {}).items():
        status = "✅" if result.get("success", False) else "❌"
        print(f"{status} {stage.title()}: {result.get('success', False)}")

    if report.get("recommendations"):
        print("\\n=== Recommendations ===")
        for rec in report["recommendations"]:
            print(f"• {rec}")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
