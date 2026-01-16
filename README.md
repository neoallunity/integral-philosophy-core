# 🧠 Integral Philosophy Core Engine

The core content processing engine for academic publishing.

## 📦 What's Included

- **📝 Content Parsers** - Markdown, LaTeX, HTML, XML, etc.
- **🔄 Format Converters** - 10+ format transformations
- **🕷️ Web Scrapers** - JavaScript-enabled content extraction
- **📊 Content Generators** - TEI XML, UML diagrams
- **✅ Validators** - Content quality and integrity checks
- **🧠 Content Pipeline** - Unified processing workflow

## 🚀 Quick Start

\`\`\`bash
# Install
pip install integral-philosophy-core

# Use
from integral_philosophy_core import ContentPipeline

pipeline = ContentPipeline()
result = pipeline.process_url("https://example.com")
\`\`\`

## 🏗️ Architecture

\`\`\`
📚 Input Sources → 🧠 Processing Engine → 📚 Output Formats
     │                    │                    │
  • Websites         • Content Parsers      • HTML
  • Documents        • Format Converters   • PDF
  • Articles         • Content Generators   • EPUB
  • Markdown         • Content Validators   • TEI XML
                     • Content Pipeline     • DOCX
\`\`\`

## 📦 Installation

\`\`\`bash
pip install integral-philosophy-core[all]  # Full installation
pip install integral-philosophy-core[web]  # Web scraping
pip install integral-philosophy-core[tei]  # TEI generation
\`\`\`

## 🔧 Development

\`\`\`bash
# Setup development environment
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest tests/
\`\`\`

## 📚 Documentation

- [API Reference](docs/api.md)
- [User Guide](docs/user.md)
- [Developer Guide](docs/dev.md)

## 🤝 Contributing

1. Fork
2. Feature branch
3. Pull request

## 📄 License

MIT License - see LICENSE file
