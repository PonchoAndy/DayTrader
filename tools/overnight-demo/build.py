"""Embed demo-data.json into template.html -> overnight-demo.html (the published page)."""
from pathlib import Path

here = Path(__file__).resolve().parent
data = (here / "demo-data.json").read_text().replace("</", "<\\/")
page = (here / "template.html").read_text().replace("__DEMODATA__", data)
(here / "overnight-demo.html").write_text(page)
print(f"overnight-demo.html: {len(page) / 1e3:.0f} KB")
