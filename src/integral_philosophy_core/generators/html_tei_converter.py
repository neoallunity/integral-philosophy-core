#!/usr/bin/env python3
"""
Bidirectional HTML ↔ TEI Converter with Isomorphism Testing
Supports HTML5 to TEI conversion and back for content preservation validation
"""

import subprocess
import json
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple
import hashlib
from dataclasses import dataclass
from xml.etree import ElementTree as ET
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class ConversionResult:
    """Result of conversion operation"""

    success: bool
    output_file: Path
    input_file: Path
    conversion_time: float
    checksum: str
    metadata: Dict[str, Any]


class HTMLTEIConverter:
    """Bidirectional HTML ↔ TEI converter with validation"""

    def __init__(self, work_dir: Optional[Path] = None):
        self.work_dir = work_dir or Path("conversion_workspace")
        self.work_dir.mkdir(exist_ok=True)

        # Create subdirectories
        (self.work_dir / "html").mkdir(exist_ok=True)
        (self.work_dir / "tei").mkdir(exist_ok=True)
        (self.work_dir / "build").mkdir(exist_ok=True)
        (self.work_dir / "xslt").mkdir(exist_ok=True)

        # Initialize conversion tools
        self._create_xslt_stylesheets()

    def _create_xslt_stylesheets(self) -> None:
        """Create XSLT stylesheets for HTML ↔ TEI conversion"""

        # HTML to TEI XSLT
        html_to_tei_xslt = """<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:h="http://www.w3.org/1999/xhtml"
    xmlns:tei="http://www.tei-c.org/ns/1.0"
    xmlns="http://www.tei-c.org/ns/1.0"
    exclude-result-prefixes="h">

<xsl:output method="xml" indent="yes" encoding="UTF-8"/>

<xsl:template match="/h:html">
    <TEI>
        <teiHeader>
            <fileDesc>
                <titleStmt>
                    <title><xsl:value-of select="//h:title"/></title>
                    <author><xsl:value-of select="//h:meta[@name='author']/@content"/></author>
                </titleStmt>
                <publicationStmt>
                    <publisher>Generated from HTML</publisher>
                    <date><xsl:value-of select="//h:meta[@name='date']/@content"/></date>
                </publicationStmt>
                <sourceDesc>
                    <bibl>
                        <title><xsl:value-of select="//h:title"/></title>
                        <url>Original HTML</url>
                    </bibl>
                </sourceDesc>
            </fileDesc>
            <profileDesc>
                <langUsage>
                    <language ident="{//h:html/@lang}"/>
                </langUsage>
            </profileDesc>
        </teiHeader>
        <text>
            <body>
                <xsl:apply-templates select="//h:body"/>
            </body>
        </text>
    </TEI>
</xsl:template>

<xsl:template match="h:section | h:article | h:main">
    <div type="section">
        <xsl:attribute name="xml:id">
            <xsl:value-of select="@id"/>
        </xsl:attribute>
        <xsl:apply-templates/>
    </div>
</xsl:template>

<xsl:template match="h:header">
    <div type="header">
        <xsl:apply-templates/>
    </div>
</xsl:template>

<xsl:template match="h:footer">
    <div type="footer">
        <xsl:apply-templates/>
    </div>
</xsl:template>

<xsl:template match="h:nav">
    <div type="navigation">
        <xsl:apply-templates/>
    </div>
</xsl:template>

<xsl:template match="h:aside">
    <div type="aside">
        <xsl:apply-templates/>
    </div>
</xsl:template>

<xsl:template match="h:h1">
    <head type="h1">
        <xsl:apply-templates/>
    </head>
</xsl:template>

<xsl:template match="h:h2">
    <head type="h2">
        <xsl:apply-templates/>
    </head>
</xsl:template>

<xsl:template match="h:h3">
    <head type="h3">
        <xsl:apply-templates/>
    </head>
</xsl:template>

<xsl:template match="h:h4|h:h5|h:h6">
    <head>
        <xsl:value-of select="local-name()"/>
        <xsl:text>: </xsl:text>
        <xsl:apply-templates/>
    </head>
</xsl:template>

<xsl:template match="h:p">
    <p>
        <xsl:apply-templates/>
    </p>
</xsl:template>

<xsl:template match="h:div">
    <div>
        <xsl:if test="@class">
            <xsl:attribute name="type">
                <xsl:value-of select="@class"/>
            </xsl:attribute>
        </xsl:if>
        <xsl:if test="@id">
            <xsl:attribute name="xml:id">
                <xsl:value-of select="@id"/>
            </xsl:attribute>
        </xsl:if>
        <xsl:apply-templates/>
    </div>
</xsl:template>

<xsl:template match="h:span">
    <span>
        <xsl:if test="@class">
            <xsl:attribute name="type">
                <xsl:value-of select="@class"/>
            </xsl:attribute>
        </xsl:if>
        <xsl:apply-templates/>
    </span>
</xsl:template>

<xsl:template match="h:a">
    <ref>
        <xsl:attribute name="target">
            <xsl:value-of select="@href"/>
        </xsl:attribute>
        <xsl:apply-templates/>
    </ref>
</xsl:template>

<xsl:template match="h:img">
    <figure>
        <graphic>
            <xsl:attribute name="url">
                <xsl:value-of select="@src"/>
            </xsl:attribute>
            <xsl:if test="@alt">
                <xsl:attribute name="alt">
                    <xsl:value-of select="@alt"/>
                </xsl:attribute>
            </xsl:if>
        </graphic>
        <xsl:if test="@alt">
            <figDesc><xsl:value-of select="@alt"/></figDesc>
        </xsl:if>
    </figure>
</xsl:template>

<xsl:template match="h:ul|h:ol">
    <list>
        <xsl:if test="local-name()='ol'">
            <xsl:attribute name="type">ordered</xsl:attribute>
        </xsl:if>
        <xsl:apply-templates/>
    </list>
</xsl:template>

<xsl:template match="h:li">
    <item>
        <xsl:apply-templates/>
    </item>
</xsl:template>

<xsl:template match="h:blockquote">
    <quote>
        <xsl:apply-templates/>
    </quote>
</xsl:template>

<xsl:template match="h:pre">
    <code>
        <xsl:attribute name="lang">text</xsl:attribute>
        <xsl:value-of select="."/>
    </code>
</xsl:template>

<xsl:template match="h:code">
    <hi rend="t">
        <xsl:value-of select="."/>
    </hi>
</xsl:template>

<xsl:template match="h:strong|h:b">
    <hi rend="bold">
        <xsl:apply-templates/>
    </hi>
</xsl:template>

<xsl:template match="h:em|h:i">
    <hi rend="it">
        <xsl:apply-templates/>
    </hi>
</xsl:template>

<xsl:template match="h:table">
    <table>
        <xsl:apply-templates/>
    </table>
</xsl:template>

<xsl:template match="h:tr">
    <row>
        <xsl:apply-templates/>
    </row>
</xsl:template>

<xsl:template match="h:td|h:th">
    <cell>
        <xsl:if test="local-name()='th'">
            <xsl:attribute name="role">header</xsl:attribute>
        </xsl:if>
        <xsl:apply-templates/>
    </cell>
</xsl:template>

<!-- Math elements -->
<xsl:template match="h:math">
    <formula notation="mathml">
        <xsl:copy-of select="node()"/>
    </formula>
</xsl:template>

<!-- Script and style elements (ignored for TEI) -->
<xsl:template match="h:script|h:style"/>

</xsl:stylesheet>"""

        # TEI to HTML XSLT
        tei_to_html_xslt = """<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:tei="http://www.tei-c.org/ns/1.0"
    xmlns="http://www.w3.org/1999/xhtml"
    exclude-result-prefixes="tei">

<xsl:output method="xml" 
    doctype-public="-//W3C//DTD XHTML 1.1//EN"
    doctype-system="http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd"
    indent="yes" encoding="UTF-8"/>

<xsl:template match="/tei:TEI">
    <html xml:lang="{tei:text/@xml:lang}">
        <head>
            <title><xsl:value-of select="tei:teiHeader/tei:fileDesc/tei:titleStmt/tei:title"/></title>
            <meta charset="UTF-8"/>
            <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
            <style>
                body { font-family: serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; }
                .metadata { background: #f0f0f0; padding: 1em; margin: 1em 0; border-radius: 4px; }
                .section { border-bottom: 1px solid #ccc; margin-bottom: 2em; }
                table { border-collapse: collapse; width: 100%; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
            </style>
        </head>
        <body>
            <header class="metadata">
                <h1><xsl:value-of select="tei:teiHeader/tei:fileDesc/tei:titleStmt/tei:title"/></h1>
                <p>Author: <xsl:value-of select="tei:teiHeader/tei:fileDesc/tei:titleStmt/tei:author/tei:name"/></p>
                <p>Date: <xsl:value-of select="tei:teiHeader/tei:fileDesc/tei:titleStmt/tei:date"/></p>
            </header>
            
            <main>
                <xsl:apply-templates select="tei:text/tei:body"/>
            </main>
        </body>
    </html>
</xsl:template>

<xsl:template match="tei:div[@type='section']">
    <section class="section">
        <xsl:if test="@xml:id">
            <xsl:attribute name="id">
                <xsl:value-of select="@xml:id"/>
            </xsl:attribute>
        </xsl:if>
        <xsl:apply-templates/>
    </section>
</xsl:template>

<xsl:template match="tei:div">
    <div>
        <xsl:if test="@type">
            <xsl:attribute name="class">
                <xsl:value-of select="@type"/>
            </xsl:attribute>
        </xsl:if>
        <xsl:if test="@xml:id">
            <xsl:attribute name="id">
                <xsl:value-of select="@xml:id"/>
            </xsl:attribute>
        </xsl:if>
        <xsl:apply-templates/>
    </div>
</xsl:template>

<xsl:template match="tei:head[@type='h1']">
    <h1><xsl:apply-templates/></h1>
</xsl:template>

<xsl:template match="tei:head[@type='h2']">
    <h2><xsl:apply-templates/></h2>
</xsl:template>

<xsl:template match="tei:head[@type='h3']">
    <h3><xsl:apply-templates/></h3>
</xsl:template>

<xsl:template match="tei:head">
    <h4><xsl:apply-templates/></h4>
</xsl:template>

<xsl:template match="tei:p">
    <p><xsl:apply-templates/></p>
</xsl:template>

<xsl:template match="tei:ref">
    <a href="{@target}"><xsl:apply-templates/></a>
</xsl:template>

<xsl:template match="tei:figure">
    <figure>
        <img src="{tei:graphic/@url}">
            <xsl:if test="tei:graphic/@alt">
                <xsl:attribute name="alt">
                    <xsl:value-of select="tei:graphic/@alt"/>
                </xsl:attribute>
            </xsl:if>
        </img>
        <xsl:if test="tei:figDesc">
            <figcaption><xsl:value-of select="tei:figDesc"/></figcaption>
        </xsl:if>
    </figure>
</xsl:template>

<xsl:template match="tei:list">
    <xsl:choose>
        <xsl:when test="@type='ordered'">
            <ol><xsl:apply-templates/></ol>
        </xsl:when>
        <xsl:otherwise>
            <ul><xsl:apply-templates/></ul>
        </xsl:otherwise>
    </xsl:choose>
</xsl:template>

<xsl:template match="tei:item">
    <li><xsl:apply-templates/></li>
</xsl:template>

<xsl:template match="tei:quote">
    <blockquote><xsl:apply-templates/></blockquote>
</xsl:template>

<xsl:template match="tei:code">
    <pre><xsl:apply-templates/></pre>
</xsl:template>

<xsl:template match="tei:hi[@rend='bold']">
    <strong><xsl:apply-templates/></strong>
</xsl:template>

<xsl:template match="tei:hi[@rend='it']">
    <em><xsl:apply-templates/></em>
</xsl:template>

<xsl:template match="tei:hi[@rend='t']">
    <code><xsl:apply-templates/></code>
</xsl:template>

<xsl:template match="tei:table">
    <table>
        <xsl:apply-templates/>
    </table>
</xsl:template>

<xsl:template match="tei:row">
    <tr><xsl:apply-templates/></tr>
</xsl:template>

<xsl:template match="tei:cell">
    <xsl:choose>
        <xsl:when test="@role='header'">
            <th><xsl:apply-templates/></th>
        </xsl:when>
        <xsl:otherwise>
            <td><xsl:apply-templates/></td>
        </xsl:otherwise>
    </xsl:choose>
</xsl:template>

</xsl:stylesheet>"""

        # Save XSLT files
        with open(
            self.work_dir / "xslt" / "html_to_tei.xslt", "w", encoding="utf-8"
        ) as f:
            f.write(html_to_tei_xslt)

        with open(
            self.work_dir / "xslt" / "tei_to_html.xslt", "w", encoding="utf-8"
        ) as f:
            f.write(tei_to_html_xslt)

    def html_to_tei(self, html_file: Path) -> ConversionResult:
        """Convert HTML to TEI using tidy + XSLT"""
        start_time = time.time()

        try:
            # Step 1: Tidy HTML to valid XHTML
            xhtml_file = self.work_dir / "build" / f"{html_file.stem}.xhtml"

            result = subprocess.run(
                ["tidy", "-q", "-xml", "-asxhtml", str(html_file)],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            if result.returncode != 0:
                logger.error(f"Tidy failed: {result.stderr}")
                return ConversionResult(False, Path(), html_file, 0, "", {})

            # Save cleaned XHTML
            with open(xhtml_file, "w", encoding="utf-8") as f:
                f.write(result.stdout)

            # Step 2: Transform XHTML to TEI using XSLT
            tei_file = self.work_dir / "tei" / f"{html_file.stem}.xml"

            result = subprocess.run(
                [
                    "saxon",
                    "-s:" + str(xhtml_file),
                    "-xsl:" + str(self.work_dir / "xslt" / "html_to_tei.xslt"),
                    "-o:" + str(tei_file),
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                logger.error(f"Saxon transformation failed: {result.stderr}")
                return ConversionResult(False, tei_file, html_file, 0, "", {})

            # Calculate checksum
            checksum = self._calculate_checksum(tei_file)

            conversion_time = time.time() - start_time

            logger.info(f"HTML → TEI: {html_file} → {tei_file}")

            return ConversionResult(
                success=True,
                output_file=tei_file,
                input_file=html_file,
                conversion_time=conversion_time,
                checksum=checksum,
                metadata={"elements": self._count_tei_elements(tei_file)},
            )

        except Exception as e:
            logger.error(f"Error converting HTML to TEI: {e}")
            return ConversionResult(False, Path(), html_file, 0, "", {})

    def tei_to_html(self, tei_file: Path) -> ConversionResult:
        """Convert TEI to HTML using XSLT"""
        start_time = time.time()

        try:
            # Transform TEI to HTML using XSLT
            html_file = self.work_dir / "html" / f"{tei_file.stem}.html"

            result = subprocess.run(
                [
                    "saxon",
                    "-s:" + str(tei_file),
                    "-xsl:" + str(self.work_dir / "xslt" / "tei_to_html.xslt"),
                    "-o:" + str(html_file),
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                logger.error(f"Saxon transformation failed: {result.stderr}")
                return ConversionResult(False, html_file, tei_file, 0, "", {})

            # Calculate checksum
            checksum = self._calculate_checksum(html_file)

            conversion_time = time.time() - start_time

            logger.info(f"TEI → HTML: {tei_file} → {html_file}")

            return ConversionResult(
                success=True,
                output_file=html_file,
                input_file=tei_file,
                conversion_time=conversion_time,
                checksum=checksum,
                metadata={"elements": self._count_html_elements(html_file)},
            )

        except Exception as e:
            logger.error(f"Error converting TEI to HTML: {e}")
            return ConversionResult(False, Path(), tei_file, 0, "", {})

    def test_isomorphism(self, original_html: Path) -> Dict[str, Any]:
        """Test HTML → TEI → HTML isomorphism"""
        logger.info(f"Testing isomorphism for: {original_html}")

        results = {
            "original_file": str(original_html),
            "steps": {},
            "comparisons": {},
            "isomorphic": False,
        }

        try:
            # Step 1: HTML → TEI
            html_to_tei_result = self.html_to_tei(original_html)
            if not html_to_tei_result.success:
                results["steps"]["html_to_tei"] = "Failed"
                return results

            results["steps"]["html_to_tei"] = "Success"
            tei_file = html_to_tei_result.output_file

            # Step 2: TEI → HTML
            tei_to_html_result = self.tei_to_html(tei_file)
            if not tei_to_html_result.success:
                results["steps"]["tei_to_html"] = "Failed"
                return results

            results["steps"]["tei_to_html"] = "Success"
            final_html = tei_to_html_result.output_file

            # Step 3: Compare original and final HTML
            comparison = self._compare_html_files(original_html, final_html)
            results["comparisons"] = comparison

            # Step 4: Determine isomorphism
            results["isomorphic"] = self._is_isomorphic(comparison)

            # Step 5: Generate detailed diff if needed
            if not results["isomorphic"]:
                results["diff"] = self._generate_html_diff(original_html, final_html)

            return results

        except Exception as e:
            logger.error(f"Error testing isomorphism: {e}")
            results["error"] = str(e)
            return results

    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum of file"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    def _count_tei_elements(self, tei_file: Path) -> Dict[str, int]:
        """Count TEI elements in file"""
        try:
            result = subprocess.run(
                ["xmllint", "--xpath", "count(//tei:*)", str(tei_file)],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                return {"total_elements": int(result.stdout.strip())}

        except:
            pass

        return {"total_elements": 0}

    def _count_html_elements(self, html_file: Path) -> Dict[str, int]:
        """Count HTML elements in file"""
        try:
            # Count sections, headings, links
            counts = {}

            for xpath, name in [
                ("count(//section)", "sections"),
                ("count(//h1|//h2|//h3|//h4|//h5|//h6)", "headings"),
                ("count(//a)", "links"),
                ("count(//p)", "paragraphs"),
                ("count(//div)", "divs"),
                ("count(//ul|//ol)", "lists"),
                ("count(//img)", "images"),
            ]:
                result = subprocess.run(
                    ["xmllint", "--xpath", xpath, str(html_file)],
                    capture_output=True,
                    text=True,
                )

                if result.returncode == 0:
                    try:
                        counts[name] = int(result.stdout.strip())
                    except ValueError:
                        counts[name] = 0

            return counts

        except Exception as e:
            logger.warning(f"Error counting HTML elements: {e}")
            return {}

    def _compare_html_files(self, original: Path, final: Path) -> Dict[str, Any]:
        """Compare two HTML files for structure and content preservation"""
        comparison = {"structure": {}, "headings": {}, "links": {}, "checksums": {}}

        try:
            # Clean both files with tidy
            orig_clean = self._clean_html_with_tidy(original)
            final_clean = self._clean_html_with_tidy(final)

            orig_file = self.work_dir / "build" / f"orig_clean.xhtml"
            final_file = self.work_dir / "build" / f"final_clean.xhtml"

            with open(orig_file, "w", encoding="utf-8") as f:
                f.write(orig_clean)

            with open(final_file, "w", encoding="utf-8") as f:
                f.write(final_clean)

            # Compare structure
            orig_sections = self._xpath_count(orig_file, "count(//section)")
            final_sections = self._xpath_count(final_file, "count(//section)")
            comparison["structure"]["sections_match"] = orig_sections == final_sections
            comparison["structure"]["original_sections"] = orig_sections
            comparison["structure"]["final_sections"] = final_sections

            # Compare headings
            orig_headings = self._xpath_text(orig_file, "//h1|//h2|//h3/text()")
            final_headings = self._xpath_text(final_file, "//h1|//h2|//h3/text()")
            comparison["headings"]["match"] = orig_headings == final_headings
            comparison["headings"]["original"] = orig_headings
            comparison["headings"]["final"] = final_headings

            # Compare links
            orig_links = self._xpath_links(orig_file)
            final_links = self._xpath_links(final_file)
            comparison["links"]["match"] = orig_links == final_links
            comparison["links"]["original_count"] = len(orig_links)
            comparison["links"]["final_count"] = len(final_links)

            # Compare checksums
            comparison["checksums"]["original"] = self._calculate_checksum(original)
            comparison["checksums"]["final"] = self._calculate_checksum(final)

        except Exception as e:
            logger.error(f"Error comparing HTML files: {e}")
            comparison["error"] = str(e)

        return comparison

    def _clean_html_with_tidy(self, html_file: Path) -> str:
        """Clean HTML with tidy"""
        result = subprocess.run(
            ["tidy", "-q", "-xml", "-asxhtml", "-indent", str(html_file)],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        return result.stdout if result.returncode == 0 else ""

    def _xpath_count(self, file_path: Path, xpath: str) -> int:
        """Get XPath count from file"""
        result = subprocess.run(
            ["xmllint", "--xpath", xpath, str(file_path)],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            try:
                return int(result.stdout.strip())
            except ValueError:
                pass

        return 0

    def _xpath_text(self, file_path: Path, xpath: str) -> List[str]:
        """Get XPath text content from file"""
        result = subprocess.run(
            ["xmllint", "--xpath", xpath, str(file_path)],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            return [
                line.strip()
                for line in result.stdout.strip().split("\n")
                if line.strip()
            ]

        return []

    def _xpath_links(self, file_path: Path) -> List[str]:
        """Extract all href attributes from links"""
        result = subprocess.run(
            ["xmllint", "--xpath", "//a/@href", str(file_path)],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            links = [
                line.strip()
                for line in result.stdout.strip().split("\n")
                if line.strip()
            ]
            return sorted(links)  # Sort for comparison

        return []

    def _is_isomorphic(self, comparison: Dict[str, Any]) -> bool:
        """Determine if conversion preserves structure (isomorphism)"""
        if "error" in comparison:
            return False

        # Check key structural elements
        structure_ok = comparison.get("structure", {}).get("sections_match", False)
        headings_ok = comparison.get("headings", {}).get("match", False)
        links_ok = comparison.get("links", {}).get("match", False)

        # Consider isomorphic if major structural elements are preserved
        return structure_ok and headings_ok and links_ok

    def _generate_html_diff(self, original: Path, final: Path) -> str:
        """Generate diff between HTML files"""
        try:
            result = subprocess.run(
                ["diff", "-u", str(original), str(final)],
                capture_output=True,
                text=True,
            )

            return result.stdout if result.returncode != 0 else "No differences found"

        except:
            return "Diff generation failed"

    def batch_test_isomorphism(self, html_files: List[Path]) -> Dict[str, Any]:
        """Test isomorphism for multiple HTML files"""
        results = {
            "total_files": len(html_files),
            "successful_conversions": 0,
            "isomorphic_files": 0,
            "file_results": {},
            "summary": {},
        }

        for html_file in html_files:
            logger.info(f"Testing: {html_file}")
            file_result = self.test_isomorphism(html_file)
            results["file_results"][str(html_file)] = file_result

            if file_result.get("isomorphic", False):
                results["isomorphic_files"] += 1

            if (
                file_result.get("steps", {}).get("html_to_tei") == "Success"
                and file_result.get("steps", {}).get("tei_to_html") == "Success"
            ):
                results["successful_conversions"] += 1

        # Calculate summary statistics
        results["summary"] = {
            "conversion_success_rate": results["successful_conversions"]
            / len(html_files),
            "isomorphism_rate": results["isomorphic_files"] / len(html_files),
            "total_errors": sum(
                1 for r in results["file_results"].values() if "error" in r
            ),
        }

        return results


def main():
    """Main function for testing"""
    import argparse
    import time

    parser = argparse.ArgumentParser(description="Test HTML ↔ TEI isomorphism")
    parser.add_argument("input", nargs="+", help="Input HTML files or directory")
    parser.add_argument(
        "-o", "--output", default="isomorphism_test_results", help="Output directory"
    )
    parser.add_argument("--batch", action="store_true", help="Process multiple files")

    args = parser.parse_args()

    # Create converter
    converter = HTMLTEIConverter()

    # Get HTML files
    html_files = []
    for path in args.input:
        p = Path(path)
        if p.is_file() and p.suffix in [".html", ".htm"]:
            html_files.append(p)
        elif p.is_dir():
            html_files.extend(p.glob("**/*.html"))
            html_files.extend(p.glob("**/*.htm"))

    if not html_files:
        logger.error("No HTML files found")
        return

    logger.info(f"Found {len(html_files)} HTML files")

    # Test isomorphism
    if len(html_files) == 1:
        results = converter.test_isomorphism(html_files[0])
    else:
        results = converter.batch_test_isomorphism(html_files)

    # Save results
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    results_file = output_dir / "isomorphism_results.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    logger.info(f"Results saved to: {results_file}")

    # Print summary
    if isinstance(results, dict) and "summary" in results:
        summary = results["summary"]
        print(f"\n=== Isomorphism Test Summary ===")
        print(f"Total files: {results['total_files']}")
        print(f"Successful conversions: {results['successful_conversions']}")
        print(f"Isomorphic files: {results['isomorphic_files']}")
        print(f"Conversion success rate: {summary['conversion_success_rate']:.2%}")
        print(f"Isomorphism rate: {summary['isomorphism_rate']:.2%}")
    else:
        print(
            f"Single file result: {'Isomorphic' if results.get('isomorphic', False) else 'Not isomorphic'}"
        )


if __name__ == "__main__":
    import time

    main()
