"""Convert '10. РСХБ.Цифра.pdf' to markdown using pymupdf."""
import pymupdf
import pathlib, textwrap

pdf_path = pathlib.Path(r"D:\VINA\TZ\10. РСХБ.Цифра.pdf")
out_path = pdf_path.with_suffix(".md")

doc = pymupdf.open(str(pdf_path))

lines = []
for page_num, page in enumerate(doc, 1):
    lines.append(f"\n---\n## Страница {page_num}\n")
    
    # Extract text blocks sorted by position
    blocks = page.get_text("blocks")
    # Sort by vertical position (y0), then horizontal (x0)
    blocks.sort(key=lambda b: (b[1], b[0]))
    
    for block in blocks:
        # block: (x0, y0, x1, y1, text, block_no, block_type)
        if block[6] == 0:  # text block
            text = block[4].strip()
            if text:
                lines.append(text)
                lines.append("")

doc.close()

content = "\n".join(lines)
out_path.write_text(content, encoding="utf-8")
print(f"Saved to {out_path}")
print(f"Total pages: {page_num}")
print(f"Content length: {len(content)} chars")
