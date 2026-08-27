import markdown
import re

with open("GE_A2A_Import.md", "r", encoding="utf-8") as f:
    md_content = f.read()

# Convert markdown to HTML with extra extensions (tables, fenced code, etc.)
html_body = markdown.markdown(
    md_content,
    extensions=['tables', 'fenced_code', 'codehilite', 'nl2br']
)

html_template = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Gemini Enterprise A2A Agent Import Guide</title>
<style>
  body {{
    font-family: Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.5;
    color: #202124;
    margin: 40px;
    max-width: 900px;
  }}
  h1 {{
    font-size: 20pt;
    color: #1a73e8;
    border-bottom: 2px solid #1a73e8;
    padding-bottom: 8px;
    margin-top: 24px;
  }}
  h2 {{
    font-size: 15pt;
    color: #202124;
    border-bottom: 1px solid #dadce0;
    padding-bottom: 6px;
    margin-top: 24px;
  }}
  h3 {{
    font-size: 12pt;
    color: #3c4043;
    margin-top: 18px;
  }}
  table {{
    border-collapse: collapse;
    width: 100%;
    margin: 16px 0;
  }}
  th, td {{
    border: 1px solid #dadce0;
    padding: 8px 12px;
    text-align: left;
    font-size: 10pt;
  }}
  th {{
    background-color: #f1f3f4;
    font-weight: bold;
    color: #202124;
  }}
  tr:nth-child(even) {{
    background-color: #fafafa;
  }}
  pre {{
    background-color: #f8f9fa;
    border: 1px solid #dadce0;
    border-radius: 4px;
    padding: 12px;
    font-family: "Courier New", Courier, monospace;
    font-size: 9.5pt;
    overflow-x: auto;
    line-height: 1.4;
  }}
  code {{
    font-family: "Courier New", Courier, monospace;
    background-color: #f1f3f4;
    padding: 2px 4px;
    border-radius: 3px;
    font-size: 9.5pt;
  }}
  pre code {{
    background-color: transparent;
    padding: 0;
  }}
  blockquote {{
    border-left: 4px solid #1a73e8;
    background-color: #e8f0fe;
    padding: 10px 16px;
    margin: 16px 0;
    border-radius: 0 4px 4px 0;
  }}
  hr {{
    border: 0;
    border-top: 1px solid #dadce0;
    margin: 24px 0;
  }}
  ul, ol {{
    padding-left: 24px;
  }}
  li {{
    margin-bottom: 4px;
  }}
</style>
</head>
<body>
{html_body}
</body>
</html>
"""

with open("GE_A2A_Import_Docs.html", "w", encoding="utf-8") as f:
    f.write(html_template)

print("GE_A2A_Import_Docs.html generated successfully!")
