#!/usr/bin/env python3
"""
Integral Philosophy Core CLI
Unified command-line interface for content processing
"""

import argparse
import sys
from pathlib import Path

def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(
        prog='integral-core',
        description='🧠 Integral Philosophy Core Engine - Content Processing CLI',
        epilog='Process academic content with elegance and precision'
    )
    
    parser.add_argument('--version', action='version', version='%(prog)s 2.0.0')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Parse command
    parse_parser = subparsers.add_parser('parse', help='Parse content from various formats')
    parse_parser.add_argument('input', help='Input file or URL')
    parse_parser.add_argument('--format', choices=['md', 'latex', 'html', 'tei'], default='auto', help='Input format')
    
    # Convert command
    convert_parser = subparsers.add_parser('convert', help='Convert between formats')
    convert_parser.add_argument('input', help='Input file')
    convert_parser.add_argument('--from', help='Source format')
    convert_parser.add_argument('--to', required=True, help='Target format')
    convert_parser.add_argument('--output', help='Output file')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate content')
    validate_parser.add_argument('input', help='Input file')
    validate_parser.add_argument('--strict', action='store_true', help='Strict validation')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        if args.command == 'parse':
            from .parsers import parse_content
            result = parse_content(args.input, args.format)
            print(f"✅ Parsed content: {result}")
            
        elif args.command == 'convert':
            from .converters import convert_content
            result = convert_content(args.input, args.from, args.to, args.output)
            print(f"✅ Converted content: {result}")
            
        elif args.command == 'validate':
            from .validators import validate_content
            result = validate_content(args.input, args.strict)
            print(f"✅ Validation result: {result}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
