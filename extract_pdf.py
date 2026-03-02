#!/usr/bin/env python3
"""Extract text from PDF pages for review pipeline.

Produces one .txt file per page in the output directory.
Usage: python extract_pdf.py <input.pdf> <output_dir>
"""
import sys
import os

def extract_pages(pdf_path, output_dir):
    """Extract text from each page of the PDF."""
    if not os.path.isfile(pdf_path):
        print(f"ERROR: PDF not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    try:
        import pdfplumber
    except ImportError:
        print("ERROR: pdfplumber not installed. Run: pip install pdfplumber", file=sys.stderr)
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)
    page_count = 0

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            page_file = os.path.join(output_dir, f'page-{i+1:04d}.txt')
            try:
                text = page.extract_text() or ''
                tables = page.extract_tables() or []
                table_text = ''
                for table in tables:
                    for row in table:
                        cells = [str(c or '') for c in row]
                        table_text += ' | '.join(cells) + '\n'

                with open(page_file, 'w', encoding='utf-8') as f:
                    f.write(f'--- PAGE {i+1} ---\n')
                    f.write(text)
                    if table_text:
                        f.write('\n\n--- TABLES ---\n')
                        f.write(table_text)
            except Exception as e:
                print(f"WARNING: Failed to extract page {i+1}: {e}", file=sys.stderr)
                with open(page_file, 'w', encoding='utf-8') as f:
                    f.write(f'--- PAGE {i+1} ---\n[Extraction failed: {e}]\n')

            page_count += 1

    manifest_file = os.path.join(output_dir, 'manifest.txt')
    with open(manifest_file, 'w', encoding='utf-8') as f:
        f.write(f'Pages: {page_count}\n')
        f.write(f'Source: {os.path.basename(pdf_path)}\n')
        for i in range(page_count):
            f.write(f'page-{i+1:04d}.txt\n')

    print(f'Extracted {page_count} pages to {output_dir}')
    return page_count

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(f'Usage: {sys.argv[0]} <input.pdf> <output_dir>', file=sys.stderr)
        sys.exit(1)
    extract_pages(sys.argv[1], sys.argv[2])
