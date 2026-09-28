"""Generate 3-Slide PeX Asset-Led Strategy Deck in PowerPoint (.pptx)."""
import os
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

def create_deck():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    blank_layout = prs.slide_layouts[6]
    artifact_dir = Path(r"C:\Users\pawan\.gemini\antigravity\brain\c3f5b955-db50-474b-abe4-7055d673abfa")
    
    img1 = artifact_dir / "slide1_addressable_market_1790353411420.jpg"
    img2 = artifact_dir / "slide2_five_years_ambition_1790353431511.jpg"
    img3 = artifact_dir / "slide3_client_journey_farming_1790353450611.jpg"

    images = [
        ("Slide 1: Addressable Market", img1),
        ("Slide 2: Payments Asset-Led Services : Five Years Ambition", img2),
        ("Slide 3: Client Journey & Farming Map", img3),
    ]

    for title, img_path in images:
        slide = prs.slides.add_slide(blank_layout)
        if img_path.exists():
            slide.shapes.add_picture(str(img_path), Inches(0), Inches(0), width=Inches(13.333), height=Inches(7.5))

    out_file = Path(r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\PeX_Asset_Led_Planning_Deck.pptx")
    prs.save(str(out_file))
    print(f"Presentation saved successfully to: {out_file}")

if __name__ == "__main__":
    create_deck()
