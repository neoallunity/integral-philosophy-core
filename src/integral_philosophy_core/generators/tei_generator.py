#!/usr/bin/env python3
"""
TEI XML Canonical Storage Format
Converts site AST and MarkdownTeX to TEI XML for canonical storage
Supports academic publishing standards and preservation
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from xml.etree.ElementTree import Element, SubElement, tostring, ElementTree
from xml.dom import minidom
import re

# Import from our parsers
try:
    from markdowntex_parser import ASTNode, NodeType, MarkdownTeXParser
except ImportError:
    from scripts.markdowntex_parser import ASTNode, NodeType, MarkdownTeXParser


class TEIGenerator:
    """Generate TEI XML from AST and site data"""

    def __init__(self):
        self.tei_ns = "http://www.tei-c.org/ns/1.0"
        self.xml_ns = "http://www.w3.org/XML/1998/namespace"

        # Register namespaces
        self.ns_map = {"tei": self.tei_ns, "xml": self.xml_ns}

    def generate_tei_header(self, site_metadata: Dict[str, Any]) -> Element:
        """Generate TEI header with site metadata"""
        # Create TEI element
        tei = Element(
            f"{{{self.tei_ns}}}TEI",
            attrib={f"{{{self.xml_ns}}}lang": site_metadata.get("language", "en")},
        )

        # File description
        file_desc = SubElement(tei, f"{{{self.tei_ns}}}teiHeader")
        title_stmt = SubElement(file_desc, f"{{{self.tei_ns}}}fileDesc")

        # Title statement
        title_stmt = SubElement(title_stmt, f"{{{self.tei_ns}}}titleStmt")
        title = SubElement(
            title_stmt,
            f"{{{self.tei_ns}}}title",
            attrib={
                f"{{{self.xml_ns}}}lang": site_metadata.get("language", "en"),
                "type": "main",
            },
        )
        title.text = site_metadata.get(
            "title", site_metadata.get("base_url", "Untitled Site")
        )

        # Author statement
        author_stmt = SubElement(title_stmt, f"{{{self.tei_ns}}}author")
        author_name = SubElement(author_stmt, f"{{{self.tei_ns}}}name")
        author_name.text = site_metadata.get("author", "Web Scraper")

        # Publication statement
        publication_stmt = SubElement(title_stmt, f"{{{self.tei_ns}}}publicationStmt")
        publisher = SubElement(publication_stmt, f"{{{self.tei_ns}}}publisher")
        publisher.text = "Integral Philosophy Publishing System"

        date = SubElement(
            publication_stmt,
            f"{{{self.tei_ns}}}date",
            attrib={
                "when": datetime.now().isoformat().split("T")[0],
                "type": "creation",
            },
        )
        date.text = datetime.now().strftime("%Y-%m-%d")

        # Source description
        source_desc = SubElement(title_stmt, f"{{{self.tei_ns}}}sourceDesc")
        source_bibl = SubElement(source_desc, f"{{{self.tei_ns}}}bibl")

        source_title = SubElement(source_bibl, f"{{{self.tei_ns}}}title")
        source_title.text = site_metadata.get("base_url", "Unknown Source")

        if "scraped_at" in site_metadata:
            source_note = SubElement(
                source_bibl, f"{{{self.tei_ns}}}note", attrib={"type": "scraper"}
            )
            source_note.text = f"Scraped on {site_metadata['scraped_at']}"

        # Profile description
        profile_desc = SubElement(file_desc, f"{{{self.tei_ns}}}profileDesc")
        lang_usage = SubElement(profile_desc, f"{{{self.tei_ns}}}langUsage")
        language = SubElement(
            lang_usage,
            f"{{{self.tei_ns}}}language",
            attrib={"ident": site_metadata.get("language", "en")},
        )
        language.text = site_metadata.get("language", "English")

        # Encoding description
        encoding_desc = SubElement(profile_desc, f"{{{self.tei_ns}}}encodingDesc")
        project_desc = SubElement(encoding_desc, f"{{{self.tei_ns}}}projectDesc")
        project_desc.text = "This document was automatically generated from web content using the Integral Philosophy Publishing System."

        return tei

    def generate_text_body(self, pages: Dict[str, Any]) -> Element:
        """Generate TEI text body from page content"""
        body = Element(f"{{{self.tei_ns}}}text")

        # Front matter with table of contents
        front = SubElement(body, f"{{{self.tei_ns}}}front")
        div_toc = SubElement(
            front, f"{{{self.tei_ns}}}div", attrib={"type": "contents"}
        )
        toc_head = SubElement(div_toc, f"{{{self.tei_ns}}}head")
        toc_head.text = "Table of Contents"

        # Generate table of contents
        for url, page_info in pages.items():
            page_metadata = page_info.get("metadata", {})
            title = page_metadata.get("title", url)

            toc_item = SubElement(
                div_toc, f"{{{self.tei_ns}}}div", attrib={"type": "toc-entry"}
            )
            toc_ref = SubElement(
                toc_item,
                f"{{{self.tei_ns}}}ref",
                attrib={"target": f"#{self._create_page_id(url)}"},
            )
            toc_ref.text = title

        # Main body with page content
        main_body = SubElement(body, f"{{{self.tei_ns}}}body")

        for url, page_info in pages.items():
            page_div = self._convert_page_to_tei_div(url, page_info)
            main_body.append(page_div)

        return body

    def _convert_page_to_tei_div(self, url: str, page_info: Dict[str, Any]) -> Element:
        """Convert a single page to TEI div"""
        page_id = self._create_page_id(url)
        page_metadata = page_info.get("metadata", {})

        # Create page div (temporarily without parent)
        page_div = Element(
            f"{{{self.tei_ns}}}div",
            attrib={"type": "page", f"{{{self.xml_ns}}}id": page_id},
        )

        # Page header
        page_head = SubElement(page_div, f"{{{self.tei_ns}}}head")
        page_head.text = page_metadata.get("title", url)

        # Add page metadata as teiHeader within the div
        if page_metadata:
            meta_div = SubElement(
                page_div, f"{{{self.tei_ns}}}div", attrib={"type": "metadata"}
            )

            # URL
            if "url" in page_metadata:
                url_p = SubElement(
                    meta_div, f"{{{self.tei_ns}}}p", attrib={"type": "url"}
                )
                url_p.text = f"URL: {page_metadata['url']}"

            # Language
            if "language" in page_metadata:
                lang_p = SubElement(
                    meta_div, f"{{{self.tei_ns}}}p", attrib={"type": "language"}
                )
                lang_p.text = f"Language: {page_metadata['language']}"

            # Description
            if "description" in page_metadata and page_metadata["description"]:
                desc_p = SubElement(
                    meta_div, f"{{{self.tei_ns}}}p", attrib={"type": "description"}
                )
                desc_p.text = f"Description: {page_metadata['description']}"

            # Keywords
            if "keywords" in page_metadata and page_metadata["keywords"]:
                keywords_p = SubElement(
                    meta_div, f"{{{self.tei_ns}}}p", attrib={"type": "keywords"}
                )
                keywords_p.text = f"Keywords: {page_metadata['keywords']}"

            # Scraped date
            if "scraped_at" in page_metadata:
                date_p = SubElement(
                    meta_div, f"{{{self.tei_ns}}}p", attrib={"type": "scraped-date"}
                )
                date_p.text = f"Scraped: {page_metadata['scraped_at']}"

        # Convert page content
        if "content" in page_info:
            # Parse content if it's a string
            if isinstance(page_info["content"], str):
                parser = MarkdownTeXParser()
                ast = parser.parse(page_info["content"])
                content_div = self._convert_ast_to_tei(ast)
            else:
                # Assume it's already parsed AST
                content_div = self._convert_ast_to_tei(page_info["content"])

            page_div.append(content_div)

        # Add links section
        if "links" in page_info and page_info["links"]:
            links_div = SubElement(
                page_div, f"{{{self.tei_ns}}}div", attrib={"type": "links"}
            )
            links_head = SubElement(links_div, f"{{{self.tei_ns}}}head")
            links_head.text = "Links"

            links_list = SubElement(
                links_div, f"{{{self.tei_ns}}}list", attrib={"type": "bulleted"}
            )

            for link_url in page_info["links"]:
                link_item = SubElement(links_list, f"{{{self.tei_ns}}}item")
                link_ref = SubElement(
                    link_item, f"{{{self.tei_ns}}}ref", attrib={"target": link_url}
                )
                link_ref.text = link_url

        return page_div

    def _convert_ast_to_tei(self, ast_node: Union[ASTNode, Dict]) -> Element:
        """Convert AST node to TEI XML"""
        # Handle both ASTNode and dictionary representations
        if isinstance(ast_node, dict):
            node_type = NodeType(ast_node["type"])
            content = ast_node.get("content")
            attributes = ast_node.get("attributes", {})
        else:
            node_type = ast_node.type
            content = ast_node.content
            attributes = ast_node.attributes or {}

        # Create TEI element based on node type
        if node_type == NodeType.DOCUMENT:
            div = SubElement(None, f"{{{self.tei_ns}}}div", attrib={"type": "document"})
            if isinstance(content, list):
                for child in content:
                    child_elem = self._convert_ast_to_tei(child)
                    if child_elem is not None:
                        div.append(child_elem)
            return div

        elif node_type == NodeType.HEADING:
            level = attributes.get("level", 1)
            head = SubElement(
                None, f"{{{self.tei_ns}}}head", attrib={"type": f"heading-{level}"}
            )

            if isinstance(content, list):
                for child in content:
                    child_elem = self._convert_ast_to_tei(child)
                    if isinstance(child_elem, Element):
                        head.text = (head.text or "") + (child_elem.text or "")
            elif content:
                head.text = str(content)

            return head

        elif node_type == NodeType.PARAGRAPH:
            p = SubElement(None, f"{{{self.tei_ns}}}p")

            if isinstance(content, list):
                for child in content:
                    child_elem = self._convert_ast_to_tei(child)
                    if child_elem is not None:
                        p.append(child_elem)
            elif content:
                p.text = str(content)

            return p

        elif node_type == NodeType.LINK:
            ref = SubElement(
                None,
                f"{{{self.tei_ns}}}ref",
                attrib={"target": attributes.get("href", "")},
            )

            if isinstance(content, list):
                for child in content:
                    child_elem = self._convert_ast_to_tei(child)
                    if isinstance(child_elem, Element):
                        ref.text = (ref.text or "") + (child_elem.text or "")
            elif content:
                ref.text = str(content)

            return ref

        elif node_type == NodeType.IMAGE:
            figure = SubElement(None, f"{{{self.tei_ns}}}figure")
            graphic = SubElement(
                figure,
                f"{{{self.tei_ns}}}graphic",
                attrib={"url": attributes.get("src", ""), "mimeType": "image/jpeg"},
            )

            if attributes.get("alt"):
                fig_desc = SubElement(figure, f"{{{self.tei_ns}}}figDesc")
                fig_desc.text = attributes["alt"]

            return figure

        elif node_type == NodeType.CODE_BLOCK:
            quote = SubElement(
                None,
                f"{{{self.tei_ns}}}quote",
                attrib={"type": "code", "xml:lang": attributes.get("language", "")},
            )
            quote.text = str(content) if content else ""
            return quote

        elif node_type == NodeType.INLINE_CODE:
            hi = SubElement(None, f"{{{self.tei_ns}}}hi", attrib={"rend": "t"})
            hi.text = str(content) if content else ""
            return hi

        elif node_type == NodeType.MATH_BLOCK:
            formula = SubElement(
                None,
                f"{{{self.tei_ns}}}formula",
                attrib={"notation": attributes.get("format", "latex")},
            )
            formula.text = str(content) if content else ""
            return formula

        elif node_type == NodeType.INLINE_MATH:
            hi = SubElement(None, f"{{{self.tei_ns}}}hi", attrib={"rend": "it"})
            formula = SubElement(
                hi,
                f"{{{self.tei_ns}}}formula",
                attrib={"notation": attributes.get("format", "latex")},
            )
            formula.text = str(content) if content else ""
            return hi

        elif node_type == NodeType.LIST:
            list_elem = SubElement(
                None,
                f"{{{self.tei_ns}}}list",
                attrib={"type": "ordered" if attributes.get("ordered") else "bulleted"},
            )

            if isinstance(content, list):
                for item in content:
                    item_elem = self._convert_ast_to_tei(item)
                    if item_elem is not None:
                        list_elem.append(item_elem)

            return list_elem

        elif node_type == NodeType.LIST_ITEM:
            item = SubElement(None, f"{{{self.tei_ns}}}item")

            if isinstance(content, list):
                for child in content:
                    child_elem = self._convert_ast_to_tei(child)
                    if child_elem is not None:
                        item.append(child_elem)
            elif content:
                item.text = str(content)

            return item

        elif node_type == NodeType.QUOTE:
            quote = SubElement(None, f"{{{self.tei_ns}}}quote")

            if isinstance(content, list):
                for child in content:
                    child_elem = self._convert_ast_to_tei(child)
                    if child_elem is not None:
                        quote.append(child_elem)
            elif content:
                quote.text = str(content)

            return quote

        elif node_type == NodeType.STRONG:
            hi = SubElement(None, f"{{{self.tei_ns}}}hi", attrib={"rend": "bold"})

            if isinstance(content, list):
                for child in content:
                    child_elem = self._convert_ast_to_tei(child)
                    if isinstance(child_elem, Element):
                        hi.text = (hi.text or "") + (child_elem.text or "")
            elif content:
                hi.text = str(content)

            return hi

        elif node_type == NodeType.EMPHASIS:
            hi = SubElement(None, f"{{{self.tei_ns}}}hi", attrib={"rend": "it"})

            if isinstance(content, list):
                for child in content:
                    child_elem = self._convert_ast_to_tei(child)
                    if isinstance(child_elem, Element):
                        hi.text = (hi.text or "") + (child_elem.text or "")
            elif content:
                hi.text = str(content)

            return hi

        elif node_type == NodeType.TEXT:
            span = SubElement(None, f"{{{self.tei_ns}}}span")
            span.text = str(content) if content else ""
            return span

        # Return None for unsupported types
        return None

    def _create_page_id(self, url: str) -> str:
        """Create valid TEI XML ID from URL"""
        # Clean URL to create valid XML ID
        clean_id = re.sub(r"[^a-zA-Z0-9_-]", "_", url)
        clean_id = re.sub(r"^[^a-zA-Z_]", "_", clean_id)
        clean_id = clean_id[:50]  # Limit length
        return clean_id or f"page_{uuid.uuid4().hex[:8]}"

    def generate_tei_document(self, site_ast: Dict[str, Any]) -> str:
        """Generate complete TEI XML document"""

        # Extract metadata and pages
        site_metadata = site_ast.get("metadata", {})
        pages = site_ast.get("pages", {})

        # Generate TEI structure
        tei_root = self.generate_tei_header(site_metadata)
        text_body = self.generate_text_body(pages)
        tei_root.append(text_body)

        # Add TEI specific elements
        # Add revision history
        revision_desc = SubElement(
            tei_root.find(f".//{{{self.tei_ns}}}teiHeader"),
            f"{{{self.tei_ns}}}revisionDesc",
        )

        change = SubElement(
            revision_desc,
            f"{{{self.tei_ns}}}change",
            attrib={"when": datetime.now().isoformat(), "who": "#web_scraper"},
        )
        change.text = "Initial TEI XML generation from scraped web content"

        # Add stand-off markup for links and metadata
        standoff = SubElement(tei_root, f"{{{self.tei_ns}}}standOff")

        # Add link graph as standoff markup
        link_list = SubElement(
            standoff, f"{{{self.tei_ns}}}listBibl", attrib={"type": "links"}
        )

        link_graph = site_ast.get("links", {})
        for source_url, target_urls in link_graph.items():
            for target_url in target_urls:
                link_item = SubElement(link_list, f"{{{self.tei_ns}}}bibl")
                link_ref = SubElement(
                    link_item,
                    f"{{{self.tei_ns}}}ref",
                    attrib={"target": f"#{self._create_page_id(target_url)}"},
                )
                link_ref.text = f"Link from {source_url} to {target_url}"

        # Pretty print XML
        rough_string = tostring(tei_root, encoding="unicode")
        reparsed = minidom.parseString(rough_string)

        # Add XML declaration and DOCTYPE
        pretty_xml = reparsed.toprettyxml(indent="  ")

        # Add DOCTYPE declaration
        pretty_xml = pretty_xml.replace(
            '<?xml version="1.0" ?>',
            '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE TEI PUBLIC "-//TEI P5//DTD//EN" "http://www.tei-c.org/release/xml/tei/custom/schema/dtd/tei.dtd">',
        )

        return pretty_xml

    def save_tei_document(self, tei_xml: str, output_path: Union[str, Path]) -> None:
        """Save TEI XML document to file"""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(tei_xml)

        print(f"TEI XML document saved to: {output_path}")


def main():
    """Main function for testing"""
    import argparse

    parser = argparse.ArgumentParser(description="Generate TEI XML from site AST")
    parser.add_argument("input", help="Input site AST JSON file")
    parser.add_argument(
        "-o",
        "--output",
        default="tei_output/site_document.xml",
        help="Output TEI XML file",
    )

    args = parser.parse_args()

    # Load site AST
    with open(args.input, "r", encoding="utf-8") as f:
        site_ast = json.load(f)

    # Generate TEI XML
    generator = TEIGenerator()
    tei_xml = generator.generate_tei_document(site_ast)

    # Save TEI document
    generator.save_tei_document(tei_xml, args.output)

    print("TEI XML generation completed successfully!")


if __name__ == "__main__":
    main()
