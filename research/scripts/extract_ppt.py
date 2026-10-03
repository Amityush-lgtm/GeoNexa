import zipfile
import xml.etree.ElementTree as ET
import os

pptx_path = r'GeoNexa_SIH2026 (1).pptx'
output_path = r'extracted_ppt_text.txt'

with zipfile.ZipFile(pptx_path, 'r') as z:
    slide_files = sorted(
        [f for f in z.namelist() if f.startswith('ppt/slides/slide') and f.endswith('.xml')],
        key=lambda x: int(''.join(filter(str.isdigit, x)) or 0)
    )
    
    with open(output_path, 'w', encoding='utf-8') as out:
        out.write(f"TOTAL SLIDES: {len(slide_files)}\n\n")
        for idx, sf in enumerate(slide_files):
            xml_content = z.read(sf)
            tree = ET.fromstring(xml_content)
            texts = []
            for elem in tree.iter():
                if elem.tag.endswith('}t') and elem.text:
                    texts.append(elem.text.strip())
            out.write(f"=== SLIDE {idx+1} ===\n")
            out.write("\n".join([t for t in texts if t]))
            out.write("\n\n" + "="*60 + "\n\n")

print(f"Extracted {len(slide_files)} slides to {output_path}")
