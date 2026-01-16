#!/usr/bin/env python3
"""
Multi-Format Converter: Markdown→Org→AsciiDoc→reST→Typst
Supports bidirectional conversion between multiple markup formats
Uses Pandoc as primary conversion engine with custom transformations
"""

import subprocess
import json
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple
import logging
import shutil

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FormatConverter:
    """Multi-format markup converter with bidirectional support"""

    # Supported input and output formats
    SUPPORTED_FORMATS = {
        "markdown": ["md", "markdown", "mdown", "mkd"],
        "org": ["org", "orgmode"],
        "asciidoc": ["adoc", "asciidoc", "asc"],
        "rst": ["rst", "rest", "restructuredtext"],
        "typst": ["typst", "typ"],
        "html": ["html", "htm"],
        "latex": ["tex", "latex"],
        "tei": ["xml", "tei"],
        "docbook": ["dbk", "docbook"],
        "jats": ["jats"],
        "json": ["json"],  # For Pandoc AST
    }

    def __init__(self, work_dir: Optional[Path] = None):
        self.work_dir = work_dir or Path("format_conversion")
        self.work_dir.mkdir(exist_ok=True)

        # Check dependencies
        self._check_dependencies()

    def _check_dependencies(self) -> None:
        """Check if required tools are available"""
        self.pandoc_available = shutil.which("pandoc") is not None
        self.pandoc_version = (
            self._get_pandoc_version() if self.pandoc_available else None
        )

        if not self.pandoc_available:
            logger.warning(
                "Pandoc not found. Install with: brew install pandoc or apt-get install pandoc"
            )

        logger.info(f"Pandoc available: {self.pandoc_available}")
        if self.pandoc_version:
            logger.info(f"Pandoc version: {self.pandoc_version}")

    def _get_pandoc_version(self) -> Optional[str]:
        """Get Pandoc version"""
        try:
            result = subprocess.run(
                ["pandoc", "--version"], capture_output=True, text=True
            )
            if result.returncode == 0:
                return result.stdout.split("\n")[0]
        except:
            pass
        return None

    def detect_format(self, file_path: Path) -> Optional[str]:
        """Detect format from file extension"""
        suffix = file_path.suffix.lower().lstrip(".")

        for format_name, extensions in self.SUPPORTED_FORMATS.items():
            if suffix in extensions:
                return format_name

        return None

    def convert(
        self,
        input_file: Path,
        output_format: str,
        output_file: Optional[Path] = None,
        **kwargs,
    ) -> Tuple[bool, Path]:
        """Convert file to specified format"""

        if not self.pandoc_available:
            logger.error("Pandoc not available for conversion")
            return False, Path()

        input_format = self.detect_format(input_file)
        if not input_format:
            logger.error(f"Cannot detect format for: {input_file}")
            return False, Path()

        if output_format not in self.SUPPORTED_FORMATS:
            logger.error(f"Unsupported output format: {output_format}")
            return False, Path()

        if output_file is None:
            output_file = (
                self.work_dir
                / f"{input_file.stem}.{self.SUPPORTED_FORMATS[output_format][0]}"
            )

        logger.info(f"Converting: {input_format} → {output_format}")

        try:
            # Use Pandoc for conversion
            success = self._convert_with_pandoc(
                input_file, input_format, output_file, output_format, **kwargs
            )

            if success:
                logger.info(f"Successfully converted: {output_file}")
                return True, output_file
            else:
                logger.error(f"Conversion failed: {input_file} → {output_format}")
                return False, Path()

        except Exception as e:
            logger.error(f"Error during conversion: {e}")
            return False, Path()

    def _convert_with_pandoc(
        self,
        input_file: Path,
        input_format: str,
        output_file: Path,
        output_format: str,
        **kwargs,
    ) -> bool:
        """Convert using Pandoc"""

        # Build Pandoc command
        cmd = ["pandoc", "-f", input_format, "-t", output_format]

        # Add format-specific options
        if output_format == "latex":
            cmd.extend(["--pdf-engine=xelatex", "--variable=geometry:margin=1in"])
        elif output_format == "html":
            cmd.extend(["--standalone", "--css=style.css"])
        elif output_format == "typst":
            cmd.extend(["--standalone"])
        # Org mode doesn't need special options
        else:
            pass  # No special options for other formats

        # Add metadata if provided
        if "metadata" in kwargs:
            for key, value in kwargs["metadata"].items():
                cmd.extend(["-M", f"{key}={value}"])

        # Add bibliography if provided
        if "bibliography" in kwargs:
            cmd.extend(["--bibliography", kwargs["bibliography"]])

        # Add citation style if provided
        if "csl" in kwargs:
            cmd.extend(["--csl", kwargs["csl"]])

        # Add input and output files
        cmd.extend([str(input_file), "-o", str(output_file)])

        # Run Pandoc
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.work_dir),
                timeout=300,  # 5 minute timeout
            )

            if result.returncode == 0:
                return True
            else:
                logger.error(f"Pandoc error: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("Pandoc conversion timed out")
            return False
        except FileNotFoundError:
            logger.error("Pandoc not found")
            return False

    def convert_to_ast(self, input_file: Path) -> Optional[Dict]:
        """Convert file to Pandoc JSON AST"""

        if not self.pandoc_available:
            logger.error("Pandoc not available")
            return None

        input_format = self.detect_format(input_file)
        if not input_format:
            logger.error(f"Cannot detect format for: {input_file}")
            return None

        try:
            # Convert to JSON AST
            ast_file = self.work_dir / f"{input_file.stem}.ast.json"

            cmd = ["pandoc", "-f", input_format, "-t", "json", str(input_file)]
            with open(ast_file, "w") as f:
                result = subprocess.run(cmd, stdout=f, text=True, timeout=60)

            if result.returncode == 0:
                # Load and return AST
                with open(ast_file, "r", encoding="utf-8") as f:
                    ast_data = json.load(f)

                logger.info(f"Generated AST: {ast_file}")
                return ast_data
            else:
                logger.error(f"AST conversion failed: {result.stderr}")
                return None

        except Exception as e:
            logger.error(f"Error generating AST: {e}")
            return None

    def convert_from_ast(
        self, ast_data: Dict, output_format: str, output_file: Path
    ) -> bool:
        """Convert from Pandoc AST to specified format"""

        if not self.pandoc_available:
            logger.error("Pandoc not available")
            return False

        if output_format not in self.SUPPORTED_FORMATS:
            logger.error(f"Unsupported output format: {output_format}")
            return False

        try:
            # Save AST to temporary file
            temp_ast = self.work_dir / "temp_ast.json"
            with open(temp_ast, "w", encoding="utf-8") as f:
                json.dump(ast_data, f, ensure_ascii=False)

            # Convert from AST to target format
            cmd = [
                "pandoc",
                "-f",
                "json",
                "-t",
                output_format,
                str(temp_ast),
                "-o",
                str(output_file),
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            # Clean up temp file
            temp_ast.unlink(missing_ok=True)

            if result.returncode == 0:
                logger.info(f"Converted AST to {output_format}: {output_file}")
                return True
            else:
                logger.error(f"AST conversion failed: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Error converting from AST: {e}")
            return False

    def batch_convert(
        self, input_files: List[Path], output_format: str
    ) -> Dict[Path, Tuple[bool, Path]]:
        """Convert multiple files to specified format"""

        results = {}

        for input_file in input_files:
            success, output_file = self.convert(input_file, output_format)
            results[input_file] = (success, output_file)

        return results

    def create_conversion_chain(
        self, input_file: Path, output_formats: List[str]
    ) -> Dict[str, Tuple[bool, Path]]:
        """Convert input file through chain of formats"""

        results = {}
        current_file = input_file

        for i, output_format in enumerate(output_formats):
            success, converted_file = self.convert(current_file, output_format)
            results[output_format] = (success, converted_file)

            if success:
                current_file = converted_file
            else:
                logger.warning(
                    f"Chain broken at {output_format}, stopping further conversions"
                )
                break

        return results

    def compare_conversions(
        self, original_file: Path, conversions: Dict[str, Path]
    ) -> Dict[str, Any]:
        """Compare different conversion results"""

        comparison = {
            "original": str(original_file),
            "conversions": {},
            "text_similarity": {},
            "structure_comparison": {},
        }

        try:
            # Read original text
            with open(original_file, "r", encoding="utf-8") as f:
                original_text = f.read()

            # Compare each conversion
            for format_name, converted_file in conversions.items():
                if converted_file.exists():
                    with open(converted_file, "r", encoding="utf-8") as f:
                        converted_text = f.read()

                    # Basic text similarity (can be improved with more sophisticated methods)
                    similarity = self._calculate_text_similarity(
                        original_text, converted_text
                    )
                    comparison["text_similarity"][format_name] = similarity

                    # Structure comparison
                    structure_diff = self._compare_structure(
                        original_file, converted_file
                    )
                    comparison["structure_comparison"][format_name] = structure_diff

                    comparison["conversions"][format_name] = str(converted_file)
                    comparison["conversions"][f"{format_name}_size"] = (
                        converted_file.stat().st_size
                    )

        except Exception as e:
            logger.error(f"Error during comparison: {e}")
            comparison["error"] = str(e)

        return comparison

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity (can be enhanced)"""

        # Remove common markup to compare content
        def clean_text(text):
            import re

            # Remove HTML tags
            text = re.sub(r"<[^>]+>", "", text)
            # Remove LaTeX commands
            text = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", text)
            # Remove extra whitespace
            text = " ".join(text.split())
            return text.lower()

        clean1 = clean_text(text1)
        clean2 = clean_text(text2)

        if len(clean1) == 0 and len(clean2) == 0:
            return 1.0
        if len(clean1) == 0 or len(clean2) == 0:
            return 0.0

        # Simple word overlap similarity
        words1 = set(clean1.split())
        words2 = set(clean2.split())

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union) if union else 0.0

    def _compare_structure(self, file1: Path, file2: Path) -> Dict[str, Any]:
        """Compare structure of two files"""

        comparison = {
            "file1_format": self.detect_format(file1),
            "file2_format": self.detect_format(file2),
            "headings_match": False,
            "headings_file1": [],
            "headings_file2": [],
        }

        try:
            # Extract headings from both files
            headings1 = self._extract_headings(file1)
            headings2 = self._extract_headings(file2)

            comparison["headings_file1"] = headings1
            comparison["headings_file2"] = headings2
            comparison["headings_match"] = headings1 == headings2

        except Exception as e:
            logger.error(f"Error comparing structure: {e}")
            comparison["error"] = str(e)

        return comparison

    def _extract_headings(self, file_path: Path) -> List[str]:
        """Extract headings from file"""

        format_type = self.detect_format(file_path)

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            headings = []

            if format_type == "markdown":
                import re

                # Markdown headings (# ## ###)
                matches = re.findall(r"^(#{1,6})\s+(.+)$", content, re.MULTILINE)
                headings = [f"#{len(level)} {text}" for level, text in matches]

            elif format_type == "html":
                import re

                # HTML headings (h1, h2, h3, etc.)
                matches = re.findall(
                    r"<h([1-6])[^>]*>([^<]+)</h[1-6]>", content, re.IGNORECASE
                )
                headings = [f"h{level} {text}" for level, text in matches]

            elif format_type == "latex":
                import re

                # LaTeX sections
                matches = re.findall(
                    r"\\(section|subsection|subsubsection)\*?\{([^}]+)\}", content
                )
                headings = [f"\\{cmd}{{{text}}}" for cmd, text in matches]

            elif format_type == "org":
                import re

                # Org-mode headings
                matches = re.findall(r"^(\*+)\s+(.+)$", content, re.MULTILINE)
                headings = [f"{level} {text}" for level, text in matches]

            elif format_type == "rst":
                import re

                # reST headings (underlined)
                lines = content.split("\n")
                for i, line in enumerate(lines):
                    if line.strip() and i < len(lines) - 1:
                        next_line = lines[i + 1]
                        if all(c in "=-~^" for c in next_line.strip()) and len(
                            next_line.strip()
                        ) >= len(line.strip()):
                            headings.append(line)

            return headings

        except Exception as e:
            logger.error(f"Error extracting headings from {file_path}: {e}")
            return []

    def create_format_matrix(self, input_file: Path) -> Dict[str, Any]:
        """Create conversion matrix for all supported formats"""

        matrix = {
            "input_file": str(input_file),
            "input_format": self.detect_format(input_file),
            "conversions": {},
            "success_rate": 0.0,
            "total_formats": len(self.SUPPORTED_FORMATS),
        }

        successful_conversions = 0

        for output_format in self.SUPPORTED_FORMATS.keys():
            if output_format != matrix["input_format"]:
                success, output_file = self.convert(input_file, output_format)

                matrix["conversions"][output_format] = {
                    "success": success,
                    "output_file": str(output_file) if success else None,
                    "file_size": output_file.stat().st_size
                    if success and output_file.exists()
                    else None,
                }

                if success:
                    successful_conversions += 1

        matrix["success_rate"] = successful_conversions / (
            len(self.SUPPORTED_FORMATS) - 1
        )

        return matrix


def main():
    """Main function for testing"""
    import argparse

    parser = argparse.ArgumentParser(description="Multi-format markup converter")
    parser.add_argument("input", help="Input file")
    parser.add_argument("-f", "--format", help="Output format")
    parser.add_argument("-o", "--output", help="Output file")
    parser.add_argument(
        "--chain", nargs="+", help="Conversion chain (multiple formats)"
    )
    parser.add_argument("--batch", nargs="+", help="Batch conversion files")
    parser.add_argument("--ast", action="store_true", help="Convert to AST")
    parser.add_argument("--from-ast", help="Convert from AST file")
    parser.add_argument(
        "--matrix", action="store_true", help="Create conversion matrix"
    )
    parser.add_argument("--compare", nargs="+", help="Compare conversions")
    parser.add_argument(
        "--work-dir", default="format_conversion", help="Working directory"
    )

    args = parser.parse_args()

    # Initialize converter
    converter = FormatConverter(Path(args.work_dir))

    input_file = Path(args.input)

    if args.matrix:
        # Create conversion matrix
        matrix = converter.create_format_matrix(input_file)
        print(json.dumps(matrix, indent=2, ensure_ascii=False))

    elif args.ast:
        # Convert to AST
        ast_data = converter.convert_to_ast(input_file)
        if ast_data:
            ast_file = converter.work_dir / f"{input_file.stem}.ast.json"
            with open(ast_file, "w", encoding="utf-8") as f:
                json.dump(ast_data, f, indent=2, ensure_ascii=False)
            print(f"AST saved to: {ast_file}")
        else:
            print("AST conversion failed")

    elif args.from_ast:
        # Convert from AST
        output_format = args.format or "html"
        output_file = (
            Path(args.output)
            if args.output
            else Path(f"output.{converter.SUPPORTED_FORMATS[output_format][0]}")
        )

        with open(args.from_ast, "r", encoding="utf-8") as f:
            ast_data = json.load(f)

        success = converter.convert_from_ast(ast_data, output_format, output_file)
        if success:
            print(f"Converted from AST to {output_format}: {output_file}")
        else:
            print("AST conversion failed")

    elif args.chain:
        # Conversion chain
        results = converter.create_conversion_chain(input_file, args.chain)

        print("Conversion Chain Results:")
        for format_name, (success, output_file) in results.items():
            status = "✅" if success else "❌"
            print(f"  {status} {format_name}: {output_file}")

    elif args.batch:
        # Batch conversion
        output_format = args.format or "html"
        files = [Path(f) for f in args.batch]
        results = converter.batch_convert(files, output_format)

        print("Batch Conversion Results:")
        for input_file, (success, output_file) in results.items():
            status = "✅" if success else "❌"
            print(f"  {status} {input_file.name} → {output_file}")

    elif args.compare:
        # Compare conversions
        conversions = {}
        output_format = args.format or "html"

        for compare_file in args.compare:
            success, output_file = converter.compare(input_file, compare_file)
            conversions[compare_file] = output_file

        comparison = converter.compare_conversions(input_file, conversions)
        print(json.dumps(comparison, indent=2, ensure_ascii=False))

    else:
        # Single conversion
        output_format = args.format or "html"
        output_file = Path(args.output) if args.output else None

        success, output_file = converter.convert(input_file, output_format, output_file)

        if success:
            print(f"✅ Converted: {input_file} → {output_file}")
        else:
            print(f"❌ Conversion failed: {input_file} → {output_format}")


if __name__ == "__main__":
    main()
