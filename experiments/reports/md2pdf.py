import markdown
import os
from playwright.sync_api import sync_playwright

def generate_pdf():
    # Read Markdown
    with open('instruction.md', 'r', encoding='utf-8') as f:
        md_text = f.read()
    
    # Convert to HTML
    html_content = markdown.markdown(md_text, extensions=['tables', 'fenced_code'])
    
    # Wrap in HTML template with styling
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                padding: 40px;
                color: #333;
            }}
            h1, h2, h3 {{
                color: #2c3e50;
            }}
            code {{
                background: #f4f4f4;
                padding: 2px 5px;
                border-radius: 3px;
                font-family: monospace;
            }}
            pre {{
                background: #f4f4f4;
                padding: 10px;
                border-radius: 5px;
                overflow-x: auto;
            }}
            table {{
                border-collapse: collapse;
                width: 100%;
                margin: 20px 0;
            }}
            th, td {{
                border: 1px solid #ddd;
                padding: 8px;
                text-align: left;
            }}
            th {{
                background-color: #f2f2f2;
            }}
        </style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """
    
    html_path = os.path.abspath('instruction.html')
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(full_html)
        
    print(f"HTML saved to {html_path}")
    
    # Generate PDF using Playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"file://{html_path}")
        pdf_path = os.path.abspath('instruction.pdf')
        page.pdf(path=pdf_path, format="A4", margin={"top": "20mm", "bottom": "20mm", "left": "20mm", "right": "20mm"})
        browser.close()
        
    print(f"PDF saved to {pdf_path}")
    
if __name__ == '__main__':
    generate_pdf()
