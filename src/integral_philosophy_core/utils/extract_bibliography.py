#!/usr/bin/env python3
"""
Bibliography Extractor for Integral Philosophy Publishing System

This script extracts citations from LaTeX files and generates bibliography files.
It can extract citations from all articles and create individual .bib files for each article.
"""

import re
import os
import sys
from pathlib import Path
import argparse


def extract_citations_from_latex(latex_file):
    """
    Extract all citation keys from a LaTeX file.

    Args:
        latex_file (Path): Path to the LaTeX file

    Returns:
        set: Set of citation keys found in the file
    """
    citations = set()

    try:
        with open(latex_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Find all citation patterns
        citation_patterns = [
            r"\\cite\{([^}]+)\}",
            r"\\cite\[([^\]]*)\]\{([^}]+)\}",
            r"\\citet\{([^}]+)\}",
            r"\\citep\{([^}]+)\}",
            r"\\citeauthor\{([^}]+)\}",
            r"\\citeyear\{([^}]+)\}",
            r"\\footcite\{([^}]+)\}",
            r"\\textcite\{([^}]+)\}",
            r"\\parencite\{([^}]+)\}",
        ]

        for pattern in citation_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                # Handle tuple patterns (like \cite[...]{...})
                if isinstance(match, tuple):
                    key = match[1] if len(match) > 1 else match[0]
                else:
                    key = match

                # Split multiple citations and clean
                for single_key in re.split(r"[,;\s]+", key):
                    clean_key = single_key.strip()
                    if clean_key and clean_key not in ["", "\\", ""]:
                        citations.add(clean_key)

    except Exception as e:
        print(f"❌ Error reading {latex_file}: {e}")

    return citations


def find_context_info(latex_file, author_name):
    """
    Find context information for an author in the text.

    Args:
        latex_file (Path): Path to the LaTeX file
        author_name (str): Author name to search for

    Returns:
        dict: Context information including year, title, etc.
    """
    context = {}

    try:
        with open(latex_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Look for publication years
        year_patterns = [
            rf"{author_name}[^\d]*(\d{{4}})",
            rf"\[(\d{{4}})[^\]]*{author_name}",
            rf"{author_name}[^(]*\((\d{{4}})\)",
        ]

        for pattern in year_patterns:
            match = re.search(pattern, content)
            if match:
                context["year"] = match.group(1)
                break

        # Look for work titles mentioned with the author
        title_patterns = [
            rf'{author_name}[^.]*["«]([^"»]+)["»]',
            rf'["«]([^"»]+)["»"][^.]*{author_name}',
            rf"{author_name}[^.]*\x22([^\x22]+)\x22",  # Unicode quotes
        ]

        for pattern in title_patterns:
            match = re.search(pattern, content)
            if match:
                context["title"] = match.group(1)
                break

    except Exception as e:
        print(f"❌ Error finding context for {author_name}: {e}")

    return context


def create_bibtex_entry(citation_key, latex_file):
    """
    Create a BibTeX entry for a citation based on context analysis.

    Args:
        citation_key (str): The citation key
        latex_file (Path): Path to the LaTeX file

    Returns:
        str: BibTeX entry or None if not enough information
    """
    # Check master bibliography first
    master_bib = Path("global-bibliography.bib")
    if master_bib.exists():
        try:
            with open(master_bib, "r", encoding="utf-8") as f:
                master_content = f.read()
                entry_pattern = (
                    rf"@\w+\s*\{{\s*{re.escape(citation_key)}\s*,.*?}}\s*(?=@|$)"
                )
                match = re.search(
                    entry_pattern, master_content, re.DOTALL | re.IGNORECASE
                )
                if match:
                    print(f"📚 Found {citation_key} in master bibliography")
                    return match.group(0)
        except Exception:
            pass

    # Generate entry based on context
    context = find_context_info(latex_file, citation_key)

    if context:
        entry_type = "article"
        if any(
            keyword in context.get("title", "").lower()
            for keyword in ["книга", "book", "монография", "трактат"]
        ):
            entry_type = "book"

        bibtex = f"@{entry_type}{{{citation_key},\n"
        bibtex += f"    author = {{{citation_key}}},\n"

        if "title" in context:
            bibtex += f"    title = {{{context['title']}}},\n"

        if "year" in context:
            bibtex += f"    year = {{{context['year']}}},\n"

        # Add placeholder fields if not found
        if "title" not in context:
            bibtex += f"    title = {{{context.get('title', 'Untitled Work')}}},\n"
        if "year" not in context:
            bibtex += f"    year = {{{context.get('year', 'n.d.')}}},\n"

        bibtex += "    note = {Auto-generated entry from article context}\n"
        bibtex += "}"

        return bibtex

    return None


def process_article(article_dir):
    """
    Process a single article and generate its bibliography file.

    Args:
        article_dir (Path): Path to the article directory

    Returns:
        int: Number of citations processed
    """
    latex_file = article_dir / "main.tex"
    if not latex_file.exists():
        print(f"⚠️ No main.tex found in {article_dir}")
        return 0

    print(f"\n📖 Processing article: {article_dir.name}")

    # Extract citations
    citations = extract_citations_from_latex(latex_file)

    if not citations:
        print("ℹ️ No citations found in article")
        return 0

    print(f"🔍 Found {len(citations)} citations: {', '.join(sorted(citations))}")

    # Generate bibliography entries
    entries = []
    for citation_key in sorted(citations):
        entry = create_bibtex_entry(citation_key, latex_file)
        if entry:
            entries.append(entry)
        else:
            # Create a basic entry
            basic_entry = f"@misc{{{citation_key},\n"
            basic_entry += f"    author = {{{citation_key}}},\n"
            basic_entry += f"    title = {{{citation_key}}},\n"
            basic_entry += f"    year = {{n.d.}},\n"
            basic_entry += f"    note = {{Basic auto-generated entry}}\n"
            basic_entry += "}"
            entries.append(basic_entry)
            print(f"⚠️ Created basic entry for {citation_key}")

    # Write bibliography file
    bib_file = article_dir / "references.bib"
    try:
        with open(bib_file, "w", encoding="utf-8") as f:
            f.write(f"% Bibliography for {article_dir.name}\n")
            f.write(f"% Auto-generated by extract_bibliography.py\n\n")

            for entry in entries:
                f.write(entry + "\n\n")

        print(f"✅ Generated {bib_file} with {len(entries)} entries")
        return len(citations)

    except Exception as e:
        print(f"❌ Error writing {bib_file}: {e}")
        return 0


def update_master_bibliography():
    """
    Update the master bibliography from all individual article bibliographies.
    """
    print("\n📚 Updating master bibliography...")

    all_entries = []
    articles_dir = Path("articles")

    for article_dir in articles_dir.iterdir():
        if article_dir.is_dir():
            bib_file = article_dir / "references.bib"
            if bib_file.exists():
                try:
                    with open(bib_file, "r", encoding="utf-8") as f:
                        content = f.read()
                        # Remove header comments
                        content = re.sub(r"^%.*$", "", content, flags=re.MULTILINE)
                        content = re.sub(r"\n\s*\n", "\n", content)
                        if content.strip():
                            all_entries.append(content)
                except Exception as e:
                    print(f"⚠️ Warning: Error reading {bib_file}: {e}")

    if all_entries:
        try:
            with open("global-bibliography.bib", "w", encoding="utf-8") as f:
                f.write(
                    "% Master bibliography for Integral Philosophy Publishing System\n"
                )
                f.write("% Auto-generated from all article references\n\n")

                for entry in all_entries:
                    f.write(entry + "\n\n")

            print(f"✅ Master bibliography updated with {len(all_entries)} articles")

        except Exception as e:
            print(f"❌ Error updating master bibliography: {e}")
            return False

    return True


def main():
    """Main function to handle command line arguments and run extraction."""
    parser = argparse.ArgumentParser(
        description="Extract bibliographies from LaTeX articles"
    )
    parser.add_argument(
        "command", choices=["extract", "update-master", "all"], help="Command to run"
    )
    parser.add_argument("--article", type=str, help="Process only this article")

    args = parser.parse_args()

    if args.command in ["extract", "all"]:
        if args.article:
            article_dir = Path("articles") / args.article
            if article_dir.exists():
                process_article(article_dir)
            else:
                print(f"❌ Article directory not found: {article_dir}")
        else:
            total_citations = 0
            articles_dir = Path("articles")

            for article_dir in articles_dir.iterdir():
                if article_dir.is_dir():
                    total_citations += process_article(article_dir)

            print(f"\n🎉 Total citations processed: {total_citations}")

    if args.command in ["update-master", "all"]:
        update_master_bibliography()


if __name__ == "__main__":
    main()
