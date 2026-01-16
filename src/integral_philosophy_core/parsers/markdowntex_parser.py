#!/usr/bin/env python3
"""
MarkdownTeX Parser with Link Preservation
Handles CommonMark + Pandoc extensions with inline TeX support
Converts between multiple formats while preserving structure and links
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass, asdict
from enum import Enum
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class NodeType(Enum):
    """AST node types for MarkdownTeX"""

    DOCUMENT = "document"
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    TEXT = "text"
    LINK = "link"
    IMAGE = "image"
    CODE_BLOCK = "code_block"
    INLINE_CODE = "inline_code"
    MATH_BLOCK = "math_block"
    INLINE_MATH = "inline_math"
    LIST = "list"
    LIST_ITEM = "list_item"
    TABLE = "table"
    TABLE_ROW = "table_row"
    TABLE_CELL = "table_cell"
    QUOTE = "quote"
    THEMATIC_BREAK = "thematic_break"
    EMPHASIS = "emphasis"
    STRONG = "strong"
    RAW_HTML = "raw_html"
    METADATA = "metadata"


@dataclass
class ASTNode:
    """Abstract Syntax Tree node for MarkdownTeX content"""

    type: NodeType
    content: Optional[Union[str, List["ASTNode"]]] = None
    attributes: Optional[Dict[str, Any]] = None
    position: Optional[Dict[str, int]] = None

    def __post_init__(self):
        if self.attributes is None:
            self.attributes = {}
        if self.position is None:
            self.position = {}

    def to_dict(self) -> Dict:
        """Convert node to dictionary representation"""
        return {
            "type": self.type.value,
            "content": self.content,
            "attributes": self.attributes,
            "position": self.position,
        }


class MarkdownTeXParser:
    """Parser for CommonMark with LaTeX extensions"""

    def __init__(self):
        # Regex patterns for parsing
        self.patterns = {
            "heading": re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE),
            "math_block": re.compile(r"\$\$(.*?)\$\$", re.DOTALL),
            "inline_math": re.compile(r"\$([^$]+)\$"),
            "code_block": re.compile(
                r"^```(\w+)?\s*\n(.*?)\n```", re.MULTILINE | re.DOTALL
            ),
            "inline_code": re.compile(r"`([^`]+)`"),
            "link": re.compile(r"\[([^\]]+)\]\(([^)]+)\)"),
            "image": re.compile(r"!\[([^\]]*)\]\(([^)]+)\)"),
            "emphasis": re.compile(r"\*([^*]+)\*"),
            "strong": re.compile(r"\*\*([^*]+)\*\*"),
            "list_item": re.compile(r"^\s*[-*+]\s+(.+)$", re.MULTILINE),
            "ordered_list_item": re.compile(r"^\s*\d+\.\s+(.+)$", re.MULTILINE),
            "quote": re.compile(r"^>\s+(.+)$", re.MULTILINE),
            "table_row": re.compile(r"^\|(.+)\|$", re.MULTILINE),
            "metadata": re.compile(
                r"^---\s*\n(.*?)\n---\s*\n", re.MULTILINE | re.DOTALL
            ),
        }

        # TeX block patterns
        self.tex_patterns = {
            "equation": re.compile(
                r"\\begin\{equation\}(.*?)\\end\{equation\}", re.DOTALL
            ),
            "align": re.compile(
                r"\\begin\{align\*?\}(.*?)\\end\{align\*?\}", re.DOTALL
            ),
            "gather": re.compile(r"\\begin\{gather\}(.*?)\\end\{gather\}", re.DOTALL),
            "theorem": re.compile(
                r"\\begin\{theorem\}(.*?)\\end\{theorem\}", re.DOTALL
            ),
            "proof": re.compile(r"\\begin\{proof\}(.*?)\\end\{proof\}", re.DOTALL),
        }

    def parse(self, markdown_text: str) -> ASTNode:
        """Parse MarkdownTeX text into AST"""
        # Extract metadata first
        metadata = self._extract_metadata(markdown_text)

        # Remove metadata from content
        if metadata:
            content_text = self.patterns["metadata"].sub("", markdown_text).strip()
        else:
            content_text = markdown_text

        # Create document node
        doc_node = ASTNode(
            type=NodeType.DOCUMENT,
            content=[],
            attributes={"metadata": metadata} if metadata else {},
        )

        # Parse content blocks
        blocks = self._split_into_blocks(content_text)

        for block in blocks:
            parsed_block = self._parse_block(block)
            if parsed_block:
                if isinstance(parsed_block, list):
                    doc_node.content.extend(parsed_block)
                else:
                    doc_node.content.append(parsed_block)

        return doc_node

    def _extract_metadata(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract YAML-style metadata from the beginning of the text"""
        match = self.patterns["metadata"].match(text)
        if match:
            try:
                import yaml

                return yaml.safe_load(match.group(1))
            except ImportError:
                # Fallback to simple key-value parsing
                metadata = {}
                lines = match.group(1).strip().split("\n")
                for line in lines:
                    if ":" in line:
                        key, value = line.split(":", 1)
                        metadata[key.strip()] = value.strip()
                return metadata
        return None

    def _split_into_blocks(self, text: str) -> List[str]:
        """Split text into logical blocks"""
        # Handle different block types
        blocks = []
        current_block = ""
        in_code_block = False
        in_math_block = False
        code_fence = None

        lines = text.split("\n")

        for line in lines:
            # Check for code fence
            if line.strip().startswith("```"):
                if not in_code_block:
                    if current_block.strip():
                        blocks.append(current_block.strip())
                        current_block = ""
                    in_code_block = True
                    code_fence = line.strip()
                    current_block = line + "\n"
                else:
                    current_block += line + "\n"
                    blocks.append(current_block.strip())
                    current_block = ""
                    in_code_block = False
                    code_fence = None
                continue

            # Check for math block
            if "$$" in line and not in_math_block:
                if current_block.strip():
                    blocks.append(current_block.strip())
                    current_block = ""
                in_math_block = True
                current_block = line + "\n"
                continue
            elif "$$" in line and in_math_block:
                current_block += line + "\n"
                blocks.append(current_block.strip())
                current_block = ""
                in_math_block = False
                continue

            current_block += line + "\n"

            # Block separator for non-code/math content
            if not in_code_block and not in_math_block and line.strip() == "":
                if current_block.strip():
                    blocks.append(current_block.strip())
                    current_block = ""

        # Add remaining content
        if current_block.strip():
            blocks.append(current_block.strip())

        return [b for b in blocks if b.strip()]

    def _parse_block(self, block: str) -> Union[ASTNode, List[ASTNode], None]:
        """Parse a single block of content"""
        if not block.strip():
            return None

        # Math block
        if "$$" in block:
            return self._parse_math_block(block)

        # Code block
        if block.strip().startswith("```"):
            return self._parse_code_block(block)

        # TeX blocks
        for tex_type, pattern in self.tex_patterns.items():
            if pattern.match(block):
                return self._parse_tex_block(block, tex_type)

        # Heading
        heading_match = self.patterns["heading"].match(block.strip())
        if heading_match:
            level = len(heading_match.group(1))
            text = heading_match.group(2)
            content = self._parse_inline(text)
            return ASTNode(
                type=NodeType.HEADING, content=content, attributes={"level": level}
            )

        # List
        if self.patterns["list_item"].match(block) or self.patterns[
            "ordered_list_item"
        ].match(block):
            return self._parse_list(block)

        # Table
        if "|" in block and block.strip().startswith("|"):
            return self._parse_table(block)

        # Quote
        if block.strip().startswith(">"):
            return self._parse_quote(block)

        # Thematic break
        if block.strip().replace("-", "").strip() == "":
            return ASTNode(type=NodeType.THEMATIC_BREAK)

        # Paragraph (default)
        return self._parse_paragraph(block)

    def _parse_math_block(self, text: str) -> ASTNode:
        """Parse mathematical block"""
        content = text.strip("$\n")
        return ASTNode(
            type=NodeType.MATH_BLOCK, content=content, attributes={"format": "latex"}
        )

    def _parse_code_block(self, text: str) -> ASTNode:
        """Parse code block"""
        lines = text.strip().split("\n")
        if lines and lines[0].startswith("```"):
            lang = lines[0][3:].strip()
            code = "\n".join(lines[1:-1])
        else:
            lang = ""
            code = text

        return ASTNode(
            type=NodeType.CODE_BLOCK, content=code, attributes={"language": lang}
        )

    def _parse_tex_block(self, text: str, tex_type: str) -> ASTNode:
        """Parse TeX block"""
        return ASTNode(
            type=NodeType.MATH_BLOCK,
            content=text,
            attributes={"format": "latex", "environment": tex_type},
        )

    def _parse_list(self, text: str) -> ASTNode:
        """Parse list block"""
        lines = text.strip().split("\n")
        items = []
        is_ordered = False

        for line in lines:
            ordered_match = self.patterns["ordered_list_item"].match(line)
            unordered_match = self.patterns["list_item"].match(line)

            if ordered_match:
                if not is_ordered:
                    is_ordered = True
                item_content = self._parse_inline(ordered_match.group(1))
                items.append(ASTNode(type=NodeType.LIST_ITEM, content=item_content))
            elif unordered_match:
                item_content = self._parse_inline(unordered_match.group(1))
                items.append(ASTNode(type=NodeType.LIST_ITEM, content=item_content))

        return ASTNode(
            type=NodeType.LIST, content=items, attributes={"ordered": is_ordered}
        )

    def _parse_table(self, text: str) -> ASTNode:
        """Parse table block"""
        lines = [
            line for line in text.strip().split("\n") if line.strip().startswith("|")
        ]
        rows = []

        for line in lines:
            cells = [cell.strip() for cell in line.split("|")[1:-1]]
            cell_nodes = []

            for cell in cells:
                cell_content = self._parse_inline(cell)
                cell_nodes.append(
                    ASTNode(type=NodeType.TABLE_CELL, content=cell_content)
                )

            rows.append(ASTNode(type=NodeType.TABLE_ROW, content=cell_nodes))

        return ASTNode(type=NodeType.TABLE, content=rows)

    def _parse_quote(self, text: str) -> ASTNode:
        """Parse blockquote"""
        lines = text.strip().split("\n")
        quoted_lines = []

        for line in lines:
            if line.strip().startswith(">"):
                quoted_text = line.strip()[1:].strip()
                quoted_lines.append(quoted_text)

        quote_content = "\n".join(quoted_lines)
        parsed_content = self._parse_inline(quote_content)

        return ASTNode(type=NodeType.QUOTE, content=parsed_content)

    def _parse_paragraph(self, text: str) -> ASTNode:
        """Parse paragraph"""
        content = self._parse_inline(text.strip())
        return ASTNode(type=NodeType.PARAGRAPH, content=content)

    def _parse_inline(self, text: str) -> List[ASTNode]:
        """Parse inline content"""
        nodes = []
        remaining_text = text

        # Process patterns in order of specificity
        patterns = [
            ("image", self.patterns["image"]),
            ("link", self.patterns["link"]),
            ("inline_code", self.patterns["inline_code"]),
            ("inline_math", self.patterns["inline_math"]),
            ("strong", self.patterns["strong"]),
            ("emphasis", self.patterns["emphasis"]),
        ]

        while remaining_text:
            match_found = False

            for pattern_name, pattern in patterns:
                match = pattern.search(remaining_text)
                if match:
                    # Add text before match
                    if match.start() > 0:
                        text_before = remaining_text[: match.start()]
                        if text_before:
                            nodes.append(
                                ASTNode(type=NodeType.TEXT, content=text_before)
                            )

                    # Add matched element
                    if pattern_name == "image":
                        alt, src = match.groups()
                        nodes.append(
                            ASTNode(
                                type=NodeType.IMAGE, attributes={"alt": alt, "src": src}
                            )
                        )
                    elif pattern_name == "link":
                        text, href = match.groups()
                        link_content = self._parse_inline(text)
                        nodes.append(
                            ASTNode(
                                type=NodeType.LINK,
                                content=link_content,
                                attributes={"href": href},
                            )
                        )
                    elif pattern_name == "inline_code":
                        code = match.group(1)
                        nodes.append(ASTNode(type=NodeType.INLINE_CODE, content=code))
                    elif pattern_name == "inline_math":
                        math = match.group(1)
                        nodes.append(
                            ASTNode(
                                type=NodeType.INLINE_MATH,
                                content=math,
                                attributes={"format": "latex"},
                            )
                        )
                    elif pattern_name == "strong":
                        strong_text = match.group(1)
                        content = self._parse_inline(strong_text)
                        nodes.append(ASTNode(type=NodeType.STRONG, content=content))
                    elif pattern_name == "emphasis":
                        emphasis_text = match.group(1)
                        content = self._parse_inline(emphasis_text)
                        nodes.append(ASTNode(type=NodeType.EMPHASIS, content=content))

                    remaining_text = remaining_text[match.end() :]
                    match_found = True
                    break

            if not match_found:
                # Add remaining text
                if remaining_text:
                    nodes.append(ASTNode(type=NodeType.TEXT, content=remaining_text))
                break

        return nodes

    def ast_to_dict(self, ast: ASTNode) -> Dict:
        """Convert AST to dictionary format"""
        return self._node_to_dict(ast)

    def _node_to_dict(self, node: ASTNode) -> Dict:
        """Convert node to dictionary recursively"""
        result = {"type": node.type.value, "attributes": node.attributes}

        if node.content is not None:
            if isinstance(node.content, str):
                result["content"] = node.content
            elif isinstance(node.content, list):
                result["content"] = [
                    self._node_to_dict(child) for child in node.content
                ]
            elif isinstance(node.content, ASTNode):
                result["content"] = self._node_to_dict(node.content)

        if node.position:
            result["position"] = node.position

        return result

    def dict_to_ast(self, data: Dict) -> ASTNode:
        """Convert dictionary back to AST"""
        node_type = NodeType(data["type"])
        attributes = data.get("attributes", {})

        content = data.get("content")
        if isinstance(content, list):
            parsed_content = [self.dict_to_ast(item) for item in content]
        elif isinstance(content, dict):
            parsed_content = self.dict_to_ast(content)
        else:
            parsed_content = content

        return ASTNode(
            type=node_type,
            content=parsed_content,
            attributes=attributes,
            position=data.get("position", {}),
        )

    def save_ast(self, ast: ASTNode, filepath: Union[str, Path]) -> None:
        """Save AST to JSON file"""
        ast_dict = self.ast_to_dict(ast)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(ast_dict, f, indent=2, ensure_ascii=False)

        logger.info(f"AST saved to {filepath}")

    def load_ast(self, filepath: Union[str, Path]) -> ASTNode:
        """Load AST from JSON file"""
        with open(filepath, "r", encoding="utf-8") as f:
            ast_dict = json.load(f)

        return self.dict_to_ast(ast_dict)

    def extract_links(self, ast: ASTNode) -> List[Dict[str, str]]:
        """Extract all links from AST"""
        links = []

        def traverse(node):
            if node.type == NodeType.LINK:
                links.append(
                    {
                        "text": self._extract_text_content(node),
                        "href": node.attributes.get("href", ""),
                    }
                )
            elif node.type == NodeType.IMAGE:
                links.append(
                    {
                        "text": node.attributes.get("alt", ""),
                        "href": node.attributes.get("src", ""),
                    }
                )

            # Recursively process children
            if isinstance(node.content, list):
                for child in node.content:
                    traverse(child)
            elif isinstance(node.content, ASTNode):
                traverse(node.content)

        traverse(ast)
        return links

    def _extract_text_content(self, node: ASTNode) -> str:
        """Extract plain text from a node"""
        if node.type == NodeType.TEXT:
            return node.content or ""
        elif node.type in [
            NodeType.LINK,
            NodeType.IMAGE,
            NodeType.EMPHASIS,
            NodeType.STRONG,
        ]:
            if isinstance(node.content, list):
                return "".join(
                    self._extract_text_content(child) for child in node.content
                )
            elif isinstance(node.content, ASTNode):
                return self._extract_text_content(node.content)
            else:
                return node.content or ""
        else:
            return ""


def main():
    """Main function for testing the parser"""
    import argparse

    parser = argparse.ArgumentParser(
        description="MarkdownTeX Parser with link preservation"
    )
    parser.add_argument("input", help="Input MarkdownTeX file")
    parser.add_argument("-o", "--output", help="Output JSON file for AST")
    parser.add_argument("--links", action="store_true", help="Extract links only")

    args = parser.parse_args()

    # Read input file
    with open(args.input, "r", encoding="utf-8") as f:
        content = f.read()

    # Parse content
    parser_instance = MarkdownTeXParser()
    ast = parser_instance.parse(content)

    if args.links:
        # Extract links
        links = parser_instance.extract_links(ast)
        print(f"Found {len(links)} links:")
        for link in links:
            print(f"  [{link['text']}]({link['href']})")
    else:
        # Save AST
        output_file = args.output or f"{args.input}.ast.json"
        parser_instance.save_ast(ast, output_file)
        logger.info(f"AST saved to {output_file}")


if __name__ == "__main__":
    main()
