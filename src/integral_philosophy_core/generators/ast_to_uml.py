#!/usr/bin/env python3
"""
AST to UML Transformation System
Converts site AST into UML diagrams for visualization
Supports PlantUML, Mermaid, and Graphviz formats
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import logging

# Import from our MarkdownTeX parser
try:
    from markdowntex_parser import ASTNode, NodeType, MarkdownTeXParser
except ImportError:
    from scripts.markdowntex_parser import ASTNode, NodeType, MarkdownTeXParser

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class UMLFormat(Enum):
    """Supported UML output formats"""

    PLANTUML = "plantuml"
    MERMAID = "mermaid"
    GRAPHVIZ = "graphviz"
    DOT = "dot"


@dataclass
class UMLNode:
    """UML node representation"""

    id: str
    label: str
    type: str = "component"
    style: Optional[Dict[str, str]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class UMLEdge:
    """UML edge/connection representation"""

    source: str
    target: str
    label: Optional[str] = None
    style: Optional[Dict[str, str]] = None


class ASTToUMLTransformer:
    """Transforms site AST into UML diagrams"""

    def __init__(self):
        self.nodes: Dict[str, UMLNode] = {}
        self.edges: List[UMLEdge] = []
        self.site_structure = {}
        self.page_hierarchy = {}
        self.link_graph = {}

    def transform_site_ast(self, site_ast: Dict[str, Any]) -> Dict[str, Any]:
        """Transform entire site AST to UML representation"""

        # Extract pages from site AST
        pages = site_ast.get("pages", {})
        metadata = site_ast.get("metadata", {})

        # Create UML nodes for each page
        for url, page_info in pages.items():
            self._create_page_node(url, page_info)

        # Create edges based on page links
        self._create_link_edges(pages)

        # Create hierarchical structure
        self._create_hierarchy(pages)

        return {
            "metadata": metadata,
            "nodes": self._serialize_nodes(),
            "edges": self._serialize_edges(),
            "hierarchy": self.page_hierarchy,
            "statistics": self._calculate_statistics(),
        }

    def _create_page_node(self, url: str, page_info: Dict[str, Any]) -> None:
        """Create UML node for a page"""
        page_id = self._sanitize_id(url)

        # Extract metadata
        page_metadata = page_info.get("metadata", {})
        title = page_metadata.get("title", url.split("/")[-1] or "Home")
        description = page_metadata.get("description", "")

        # Determine node type based on URL structure
        node_type = self._classify_page_type(url, page_metadata)

        # Create label with title and description
        if description:
            label = f"{title}\\n{description[:50]}..."
        else:
            label = title

        # Apply styling based on page type
        style = self._get_page_style(node_type)

        node = UMLNode(
            id=page_id,
            label=label,
            type=node_type,
            style=style,
            metadata={
                "url": url,
                "filename": page_info.get("filename", ""),
                "title": title,
                "description": description,
                "language": page_metadata.get("language", ""),
                "word_count": page_metadata.get("word_count", 0),
                "scraped_at": page_metadata.get("scraped_at", ""),
            },
        )

        self.nodes[page_id] = node

    def _classify_page_type(self, url: str, metadata: Dict[str, Any]) -> str:
        """Classify page type based on URL and metadata"""
        url_lower = url.lower()

        # Homepage
        if url.rstrip("/") == url_lower.split("/")[0] + "//" or url.endswith(
            "/index.html"
        ):
            return "homepage"

        # Content types
        if any(keyword in url_lower for keyword in ["blog", "post", "article", "news"]):
            return "article"

        if any(
            keyword in url_lower
            for keyword in ["doc", "documentation", "guide", "help"]
        ):
            return "documentation"

        if any(keyword in url_lower for keyword in ["category", "tag", "taxonomy"]):
            return "taxonomy"

        if any(keyword in url_lower for keyword in ["author", "user", "profile"]):
            return "profile"

        if any(keyword in url_lower for keyword in ["search", "find", "query"]):
            return "search"

        if any(keyword in url_lower for keyword in ["contact", "about", "team"]):
            return "information"

        return "page"

    def _get_page_style(self, page_type: str) -> Dict[str, str]:
        """Get styling for page type"""
        styles = {
            "homepage": {"color": "#4CAF50", "shape": "box", "style": "filled"},
            "article": {"color": "#2196F3", "shape": "note"},
            "documentation": {"color": "#FF9800", "shape": "folder"},
            "taxonomy": {"color": "#9C27B0", "shape": "diamond"},
            "profile": {"color": "#607D8B", "shape": "oval"},
            "search": {"color": "#795548", "shape": "octagon"},
            "information": {"color": "#00BCD4", "shape": "rounded"},
            "page": {"color": "#757575", "shape": "rectangle"},
        }
        return styles.get(page_type, {})

    def _create_link_edges(self, pages: Dict[str, Any]) -> None:
        """Create edges representing links between pages"""
        for url, page_info in pages.items():
            source_id = self._sanitize_id(url)
            links = page_info.get("links", [])

            for link_url in links:
                if link_url in pages:
                    target_id = self._sanitize_id(link_url)

                    edge = UMLEdge(
                        source=source_id,
                        target=target_id,
                        label="link",
                        style={"color": "#1976D2", "style": "dashed"},
                    )
                    self.edges.append(edge)

    def _create_hierarchy(self, pages: Dict[str, Any]) -> None:
        """Create hierarchical structure from URL paths"""

        def get_hierarchy_level(url: str) -> Tuple[str, ...]:
            """Get hierarchy level tuple for URL"""
            parsed = url.rstrip("/")
            if not parsed.startswith("http"):
                return tuple()

            path = "/".join(parsed.split("/")[3:])  # Remove protocol and domain
            if not path:
                return tuple()

            return tuple(part for part in path.split("/") if part)

        # Group pages by hierarchy level
        hierarchy_map = {}

        for url in pages.keys():
            levels = get_hierarchy_level(url)

            # Add to hierarchy at each level
            for i in range(len(levels) + 1):
                level_key = "/".join(levels[:i]) if i > 0 else "root"
                if level_key not in hierarchy_map:
                    hierarchy_map[level_key] = []

                if url not in hierarchy_map[level_key]:
                    hierarchy_map[level_key].append(url)

        self.page_hierarchy = hierarchy_map

    def _calculate_statistics(self) -> Dict[str, Any]:
        """Calculate statistics about the site structure"""
        page_types = {}
        total_links = len(self.edges)

        for node in self.nodes.values():
            page_type = node.type
            page_types[page_type] = page_types.get(page_type, 0) + 1

        return {
            "total_pages": len(self.nodes),
            "total_links": total_links,
            "page_types": page_types,
            "hierarchy_levels": len(self.page_hierarchy),
            "average_links_per_page": total_links / len(self.nodes)
            if self.nodes
            else 0,
        }

    def _sanitize_id(self, url: str) -> str:
        """Create a valid UML node ID from URL"""
        # Remove protocol and domain
        sanitized = url.replace("https://", "").replace("http://", "")
        # Replace invalid characters
        sanitized = re.sub(r"[^\w\-_]", "_", sanitized)
        # Ensure it starts with a letter
        if sanitized and sanitized[0].isdigit():
            sanitized = "p_" + sanitized

        return sanitized or "homepage"

    def _serialize_nodes(self) -> List[Dict[str, Any]]:
        """Serialize nodes to dictionary format"""
        return [
            {
                "id": node.id,
                "label": node.label,
                "type": node.type,
                "style": node.style,
                "metadata": node.metadata,
            }
            for node in self.nodes.values()
        ]

    def _serialize_edges(self) -> List[Dict[str, Any]]:
        """Serialize edges to dictionary format"""
        return [
            {
                "source": edge.source,
                "target": edge.target,
                "label": edge.label,
                "style": edge.style,
            }
            for edge in self.edges
        ]

    def generate_plantuml(self, uml_data: Dict[str, Any]) -> str:
        """Generate PlantUML representation"""
        lines = ["@startuml", "!theme materia", "skinparam handwritten false", ""]

        # Add title
        title = (
            f"Site Structure: {uml_data['metadata'].get('base_url', 'Unknown Site')}"
        )
        lines.append(f"title {title}")
        lines.append("")

        # Add nodes
        for node_data in uml_data["nodes"]:
            style_parts = []
            if node_data["style"]:
                style_parts.append(f"color {node_data['style'].get('color', 'black')}")
                if "shape" in node_data["style"]:
                    style_parts.append(f"shape {node_data['style']['shape']}")
                if "style" in node_data["style"]:
                    style_parts.append(f"style {node_data['style']['style']}")

            style_str = f" [{', '.join(style_parts)}]" if style_parts else ""

            lines.append(
                f'component "{node_data["label"]}" as {node_data["id"]}{style_str}'
            )

        lines.append("")

        # Add edges
        for edge_data in uml_data["edges"]:
            if edge_data.get("label"):
                lines.append(
                    f"{edge_data['source']} --> {edge_data['target']} : {edge_data['label']}"
                )
            else:
                lines.append(f"{edge_data['source']} --> {edge_data['target']}")

        lines.append("")

        # Add statistics as note
        stats = uml_data["statistics"]
        note_lines = [
            "Site Statistics:",
            f"Total Pages: {stats['total_pages']}",
            f"Total Links: {stats['total_links']}",
            f"Hierarchy Levels: {stats['hierarchy_levels']}",
        ]

        lines.append(f"note as stats\\n" + "\\n".join(note_lines) + "\\nend note")
        lines.append("")

        lines.append("@enduml")

        return "\\n".join(lines)

    def generate_mermaid(self, uml_data: Dict[str, Any]) -> str:
        """Generate Mermaid diagram"""
        lines = ["graph TD"]
        lines.append("")

        # Add title
        lines.append(
            f"%% Site Structure: {uml_data['metadata'].get('base_url', 'Unknown Site')}"
        )
        lines.append("")

        # Define classes for different page types
        classes = set()
        for node_data in uml_data["nodes"]:
            classes.add(node_data["type"])

        for cls in sorted(classes):
            style = self._get_page_style(cls)
            color = style.get("color", "#333")
            lines.append(f"classDef {cls} fill:{color},stroke:#333,stroke-width:2px")

        lines.append("")

        # Add nodes
        for node_data in uml_data["nodes"]:
            node_id = node_data["id"]
            label = node_data["label"].replace('"', '\\"')
            node_type = node_data["type"]
            lines.append(f'{node_id}["{label}"]:::{node_type}')

        lines.append("")

        # Add edges
        for edge_data in uml_data["edges"]:
            source = edge_data["source"]
            target = edge_data["target"]
            label = edge_data.get("label", "")

            if label:
                lines.append(f"{source} --> |{label}| {target}")
            else:
                lines.append(f"{source} --> {target}")

        return "\\n".join(lines)

    def generate_graphviz(self, uml_data: Dict[str, Any]) -> str:
        """Generate Graphviz DOT representation"""
        lines = ["digraph site_structure {"]
        lines.append("  rankdir=TB;")
        lines.append("  splines=ortho;")
        lines.append('  node [shape=box, style=rounded, fontname="Arial"];')
        lines.append('  edge [fontname="Arial", fontsize=10];')
        lines.append("")

        # Add title as label
        title = (
            f"Site Structure: {uml_data['metadata'].get('base_url', 'Unknown Site')}"
        )
        lines.append(f'  label = "{title}";')
        lines.append('  labelloc = "t";')
        lines.append("")

        # Add nodes
        for node_data in uml_data["nodes"]:
            node_id = node_data["id"]
            label = node_data["label"].replace('"', '\\"')

            # Get styling
            if node_data.get("style"):
                color = node_data["style"].get("color", "lightgray")
                shape = node_data["style"].get("shape", "box")

                if shape == "note":
                    shape = "note"
                elif shape == "diamond":
                    shape = "diamond"
                elif shape == "oval":
                    shape = "ellipse"
                elif shape == "octagon":
                    shape = "octagon"
                elif shape == "rounded":
                    shape = "box", "style=rounded"

                lines.append(
                    f'  {node_id} [label="{label}", fillcolor="{color}", shape="{shape}", style="filled"];'
                )
            else:
                lines.append(f'  {node_id} [label="{label}"];')

        lines.append("")

        # Add edges
        for edge_data in uml_data["edges"]:
            source = edge_data["source"]
            target = edge_data["target"]
            label = edge_data.get("label", "")

            if label:
                lines.append(f'  {source} -> {target} [label="{label}"];')
            else:
                lines.append(f"  {source} -> {target};")

        lines.append("}")

        return "\\n".join(lines)

    def generate_all_formats(self, uml_data: Dict[str, Any], output_dir: Path) -> None:
        """Generate all supported UML formats"""

        formats = [
            (UMLFormat.PLANTUML, self.generate_plantuml, "site_structure.puml"),
            (UMLFormat.MERMAID, self.generate_mermaid, "site_structure.mmd"),
            (UMLFormat.GRAPHVIZ, self.generate_graphviz, "site_structure.dot"),
        ]

        output_dir.mkdir(parents=True, exist_ok=True)

        for format_type, generator_func, filename in formats:
            try:
                uml_content = generator_func(uml_data)
                output_path = output_dir / filename

                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(uml_content)

                logger.info(f"Generated {format_type.value} diagram: {output_path}")

            except Exception as e:
                logger.error(f"Error generating {format_type.value} diagram: {e}")

        # Save UML data as JSON
        json_path = output_dir / "uml_data.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(uml_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved UML data: {json_path}")


def main():
    """Main function for testing"""
    import argparse

    parser = argparse.ArgumentParser(description="Transform site AST to UML diagrams")
    parser.add_argument("input", help="Input site AST JSON file")
    parser.add_argument("-o", "--output", default="uml_output", help="Output directory")
    parser.add_argument(
        "-f",
        "--format",
        choices=["plantuml", "mermaid", "graphviz", "all"],
        default="all",
        help="UML format to generate",
    )

    args = parser.parse_args()

    # Load site AST
    with open(args.input, "r", encoding="utf-8") as f:
        site_ast = json.load(f)

    # Transform to UML
    transformer = ASTToUMLTransformer()
    uml_data = transformer.transform_site_ast(site_ast)

    output_dir = Path(args.output)

    if args.format == "all":
        transformer.generate_all_formats(uml_data, output_dir)
    else:
        # Generate specific format
        if args.format == "plantuml":
            content = transformer.generate_plantuml(uml_data)
            filename = "site_structure.puml"
        elif args.format == "mermaid":
            content = transformer.generate_mermaid(uml_data)
            filename = "site_structure.mmd"
        elif args.format == "graphviz":
            content = transformer.generate_graphviz(uml_data)
            filename = "site_structure.dot"

        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / filename

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"Generated {args.format} diagram: {output_path}")


if __name__ == "__main__":
    main()
