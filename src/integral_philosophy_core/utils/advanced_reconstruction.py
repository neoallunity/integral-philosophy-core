#!/usr/bin/env python3
"""
Advanced LaTeX to Markdown+TeX Reconstruction Tool
Enhanced version with better content extraction and structure preservation.
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json


class AdvancedTeXReconstructor:
    """Advanced reconstruction tool with better content parsing."""

    def __init__(self):
        self.content_cache = {}

    def extract_full_content(self, filepath: Path) -> Dict:
        """Extract and reconstruct full content from article files."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(filepath, "r", encoding="latin1") as f:
                    content = f.read()
            except Exception as e:
                return {"error": f"Cannot read file: {e}"}

        # Parse based on article structure
        if "ifprintabstract" in content:
            return self._parse_conditional_article(content, filepath)
        else:
            return self._parse_standard_article(content, filepath)

    def _parse_conditional_article(self, content: str, filepath: Path) -> Dict:
        """Parse articles with conditional content (English/Russian)."""

        # Extract English abstract
        english_part = ""
        if r"\begin{english}" in content:
            english_match = re.search(
                r"\\begin\{english\}(.*?)\\end\{english\}", content, re.DOTALL
            )
            if english_match:
                english_part = english_match.group(1).strip()

        # Extract Russian full text
        russian_part = ""
        if r"\else" in content and r"\end{english}" in content:
            russian_match = re.search(
                r"\\end\{english\}\\else(.*?)\\fi", content, re.DOTALL
            )
            if russian_match:
                russian_part = russian_match.group(1).strip()

        return {
            "filepath": str(filepath),
            "title": self._extract_title(content),
            "author": self._extract_author(content),
            "english_abstract": self._clean_latex(english_part),
            "russian_content": self._clean_latex(russian_part),
            "sections": self._extract_all_sections(content),
            "math_content": self._extract_math_content(content),
            "keywords": self._extract_keywords(content),
            "type": "academic_article",
        }

    def _parse_standard_article(self, content: str, filepath: Path) -> Dict:
        """Parse standard LaTeX articles."""
        return {
            "filepath": str(filepath),
            "title": self._extract_title(content),
            "author": self._extract_author(content),
            "content": self._clean_latex(content),
            "sections": self._extract_all_sections(content),
            "math_content": self._extract_math_content(content),
            "keywords": self._extract_keywords(content),
            "type": "standard_article",
        }

    def _extract_title(self, content: str) -> str:
        """Extract article title."""
        patterns = [
            r"\\subsubsection\{([^}]+)\\\\([^}]+)\}",
            r"\\subsection\{([^}]+)\}",
            r"\\section\{([^}]+)\}",
            r"\\JournalArticle\{[^}]+\}\{([^}]+)\}",
        ]

        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                title = match.group(1).strip()
                # Clean LaTeX formatting
                title = re.sub(r"\\\\", " - ", title)
                title = re.sub(r"\{[^}]*\}", "", title)
                return title

        return "Untitled Article"

    def _extract_author(self, content: str) -> str:
        """Extract author name."""
        patterns = [
            r"\\subsubsection\{([^}]+)\\\\",
            r"\\JournalArticle\{([^}]+)\}",
            r"\\author\{([^}]+)\}",
        ]

        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                author = match.group(1).strip()
                return re.sub(r"\\\\.*", "", author)

        return "Unknown Author"

    def _extract_all_sections(self, content: str) -> List[Dict]:
        """Extract all sections with hierarchy."""
        sections = []

        # Find all section commands
        section_pattern = r"\\(subsubsection|subsection|section|paragraph)(\*?)\{([^}]+)(?:\\\\([^}]*))?\}"

        for match in re.finditer(section_pattern, content):
            level = match.group(1)
            has_star = match.group(2)
            title = match.group(3).strip()
            subtitle = match.group(4) if match.group(4) else ""

            # Map to markdown levels
            level_map = {
                "section": 1,
                "subsection": 2,
                "subsubsection": 3,
                "paragraph": 4,
            }

            sections.append(
                {
                    "level": level_map.get(level, 2),
                    "title": title,
                    "subtitle": subtitle.strip(),
                    "original": match.group(0),
                }
            )

        return sections

    def _extract_math_content(self, content: str) -> List[Dict]:
        """Extract mathematical expressions."""
        math_items = []

        # Display math
        display_pattern = r"\\\[\s*([^\\\[]+?)\s*\\\]"
        for match in re.finditer(display_pattern, content, re.DOTALL):
            math_items.append(
                {
                    "type": "display",
                    "content": match.group(1).strip(),
                    "markdown": f"$$\n{match.group(1).strip()}\n$$",
                }
            )

        # Inline math
        inline_pattern = r"\$([^$]+)\$"
        for match in re.finditer(inline_pattern, content):
            math_items.append(
                {
                    "type": "inline",
                    "content": match.group(1).strip(),
                    "markdown": f"${match.group(1).strip()}$",
                }
            )

        return math_items

    def _extract_keywords(self, content: str) -> Dict:
        """Extract keywords in multiple languages."""
        keywords = {}

        # English keywords
        en_match = re.search(r"\\paragraph\{Keywords:\}\s*\\textit\{([^}]+)\}", content)
        if en_match:
            keywords["english"] = en_match.group(1).strip()

        # Russian keywords
        ru_match = re.search(
            r"\\paragraph\{Ключевые слова:\}\s*\\textit\{([^}]+)\}", content
        )
        if ru_match:
            keywords["russian"] = ru_match.group(1).strip()

        return keywords

    def _clean_latex(self, text: str) -> str:
        """Clean LaTeX commands while preserving structure."""
        if not text:
            return ""

        # Remove LaTeX commands but keep content
        text = re.sub(r"\\[a-zA-Z]+\*?(\{[^}]*\}|\[[^\]]*\])?", "", text)
        text = re.sub(r"\{([^}]*)\}", r"\1", text)
        text = re.sub(r"\\\\", "\n\n", text)
        text = re.sub(r"\n\s*\n", "\n\n", text)

        # Clean up extra whitespace
        text = re.sub(r" +", " ", text)
        text = re.sub(r"\n+", "\n", text)

        return text.strip()

    def reconstruct_to_markdown(self, article_data: Dict) -> str:
        """Reconstruct article data to comprehensive markdown."""
        if article_data.get("error"):
            return f"# Error\n\n{article_data['error']}"

        md_parts = []

        # Title and author
        title = article_data["title"]
        author = article_data["author"]

        md_parts.append(f"# {title}")
        md_parts.append(f"**{author}**")
        md_parts.append("")

        # Keywords if available
        keywords = article_data.get("keywords", {})
        if keywords:
            md_parts.append("## Keywords")
            if "english" in keywords:
                md_parts.append(f"**English:** {keywords['english']}")
            if "russian" in keywords:
                md_parts.append(f"**Русский:** {keywords['russian']}")
            md_parts.append("")

        # English Abstract (if available)
        if article_data.get("english_abstract"):
            md_parts.append("## English Abstract")
            md_parts.append("")
            abstract = article_data["english_abstract"]
            # Clean and format
            abstract = self._extract_text_content(abstract)
            md_parts.append(abstract)
            md_parts.append("")

        # Main content structure
        if article_data.get("russian_content"):
            md_parts.append("## Full Article (Russian)")
            md_parts.append("")

            # Extract structured content from Russian text
            russian_content = article_data["russian_content"]

            # Try to extract section-based content
            sections = article_data.get("sections", [])
            if sections:
                current_pos = 0
                for i, section in enumerate(sections):
                    if i > 0:  # Skip title section
                        md_parts.append(
                            f"{'#' * (section['level'] + 1)} {section['title']}"
                        )
                        if section["subtitle"]:
                            md_parts.append(f"*{section['subtitle']}*")
                        md_parts.append("")

                        # Extract content for this section (simplified)
                        section_marker = section["original"]
                        if section_marker in russian_content:
                            start_idx = russian_content.find(section_marker)
                            if i < len(sections) - 1:
                                next_marker = sections[i + 1]["original"]
                                end_idx = russian_content.find(next_marker)
                                if end_idx == -1:
                                    section_content = russian_content[start_idx:]
                                else:
                                    section_content = russian_content[start_idx:end_idx]
                            else:
                                section_content = russian_content[start_idx:]

                            clean_content = self._extract_text_content(section_content)
                            md_parts.append(clean_content)
                            md_parts.append("")
            else:
                # Fallback: clean entire content
                clean_content = self._extract_text_content(russian_content)
                md_parts.append(clean_content)
                md_parts.append("")

        # Mathematical content
        math_content = article_data.get("math_content", [])
        if math_content:
            md_parts.append("## Mathematical Content")
            md_parts.append("")
            for math_item in math_content:
                md_parts.append(math_item["markdown"])
                md_parts.append("")

        # Metadata
        md_parts.append("---")
        md_parts.append(f"*Source: {article_data['filepath']}*")
        md_parts.append(f"*Type: {article_data['type']}*")

        return "\n".join(md_parts)

    def _extract_text_content(self, latex_text: str) -> str:
        """Extract readable text from LaTeX content."""
        # Remove math environments for text extraction
        text = re.sub(
            r"\\begin\{(equation|align|gather)\}.*?\\end\{\1\}",
            "[Mathematical Expression]",
            latex_text,
            flags=re.DOTALL,
        )
        text = re.sub(
            r"\\\[\s*[^\\\[]+?\s*\\\]",
            "[Mathematical Expression]",
            text,
            flags=re.DOTALL,
        )
        text = re.sub(r"\$[^$]+\$", "[Inline Math]", text)

        # Handle lists
        text = re.sub(r"\\begin\{itemize\}", "", text)
        text = re.sub(r"\\end\{itemize\}", "", text)
        text = re.sub(r"\\item\s*", "- ", text)

        # Clean LaTeX commands
        text = self._clean_latex(text)

        # Split into paragraphs
        paragraphs = text.split("\n\n")
        clean_paragraphs = []

        for para in paragraphs:
            para = para.strip()
            if para and not para.startswith("["):  # Skip bracket-only content
                clean_paragraphs.append(para)

        return "\n\n".join(clean_paragraphs)


def main():
    """Main reconstruction function."""
    reconstructor = AdvancedTeXReconstructor()

    # Focus on full article files
    article_files = list(Path("articles").glob("*/main.tex"))
    print(f"Found {len(article_files)} full article files")

    reconstructed_articles = {}

    for article_file in article_files:
        print(f"Processing: {article_file}")
        article_data = reconstructor.extract_full_content(article_file)
        markdown = reconstructor.reconstruct_to_markdown(article_data)

        safe_name = f"{article_file.parent.name}_full.md"
        reconstructed_articles[safe_name] = {"data": article_data, "markdown": markdown}

    # Save results
    output_dir = Path("reconstructed_sources")
    output_dir.mkdir(exist_ok=True)

    # Save each article
    for filename, content in reconstructed_articles.items():
        filepath = output_dir / filename
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content["markdown"])
            print(f"Saved: {filepath}")
        except Exception as e:
            print(f"Error saving {filepath}: {e}")

    # Save comprehensive summary
    summary = {
        "total_articles": len(article_files),
        "articles_processed": [str(f) for f in article_files],
        "output_files": list(reconstructed_articles.keys()),
        "reconstruction_timestamp": str(Path().cwd()),
    }

    with open(
        output_dir / "articles_reconstruction_summary.json", "w", encoding="utf-8"
    ) as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\nReconstruction complete!")
    print(f"- Articles processed: {len(article_files)}")
    print(f"- Output directory: {output_dir}")
    print(f"- Summary saved to: articles_reconstruction_summary.json")


if __name__ == "__main__":
    main()
