"""pdf_styles/word_builder.py — Professional Word doc builder matching presales quality."""
import os
from datetime import datetime
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

NAVY=RGBColor(0x0F,0x1F,0x38); BLUE=RGBColor(0x25,0x63,0xEB)
TEAL=RGBColor(0x0F,0x76,0x6E); WHITE=RGBColor(0xFF,0xFF,0xFF)
GRAY=RGBColor(0x47,0x55,0x69); AMBER=RGBColor(0xD9,0x77,0x06)

def _bg(cell, hex_color):
    tc=cell._tc; tcPr=tc.get_or_add_tcPr()
    shd=OxmlElement("w:shd")
    shd.set(qn("w:val"),"clear"); shd.set(qn("w:color"),"auto"); shd.set(qn("w:fill"),hex_color)
    tcPr.append(shd)

def _border_bottom(para, color="2563EB"):
    pPr=para._p.get_or_add_pPr(); pBdr=OxmlElement("w:pBdr")
    bot=OxmlElement("w:bottom")
    bot.set(qn("w:val"),"single"); bot.set(qn("w:sz"),"6")
    bot.set(qn("w:space"),"1"); bot.set(qn("w:color"),color)
    pBdr.append(bot); pPr.append(pBdr)

class WordBuilder:
    def __init__(self, project_name, doc_title, subtitle=""):
        self.doc=Document(); self.project_name=project_name
        self.doc_title=doc_title; self.subtitle=subtitle
        self._page_setup(); self._cover()

    def _page_setup(self):
        s=self.doc.sections[0]
        s.page_width=Cm(21); s.page_height=Cm(29.7)
        s.left_margin=Cm(2.5); s.right_margin=Cm(2.5)
        s.top_margin=Cm(2); s.bottom_margin=Cm(2)

    def _cover(self):
        t=self.doc.add_table(rows=1,cols=1); t.style="Table Grid"
        c=t.cell(0,0); _bg(c,"0F1F38")
        c.vertical_alignment=WD_ALIGN_VERTICAL.CENTER
        p=c.paragraphs[0]; p.alignment=WD_ALIGN_PARAGRAPH.LEFT
        r=p.add_run(self.doc_title); r.bold=True; r.font.size=Pt(22); r.font.color.rgb=WHITE
        if self.subtitle:
            p2=c.add_paragraph(); r2=p2.add_run(self.subtitle)
            r2.font.size=Pt(11); r2.font.color.rgb=RGBColor(0xCB,0xD8,0xE8)
        c.paragraphs[0].paragraph_format.space_before=Pt(14)
        c.paragraphs[0].paragraph_format.space_after=Pt(14)
        c.paragraphs[0].paragraph_format.left_indent=Cm(0.5)
        self.doc.add_paragraph()
        meta=self.doc.add_paragraph()
        today=datetime.today().strftime("%d %B %Y")
        r=meta.add_run(f"Project: {self.project_name}   |   Date: {today}   |   Version: 1.0")
        r.font.size=Pt(9); r.font.color.rgb=GRAY
        _border_bottom(meta,"D97706"); self.doc.add_paragraph()

    def add_heading(self, text, level=1):
        p=self.doc.add_paragraph()
        r=p.add_run(text); r.bold=True
        r.font.size=Pt(13) if level==1 else Pt(11)
        r.font.color.rgb=NAVY if level==1 else BLUE
        _border_bottom(p,"0F1F38" if level==1 else "2563EB")
        p.paragraph_format.space_before=Pt(12); p.paragraph_format.space_after=Pt(6)
        return self

    def add_subheading(self, text):
        p=self.doc.add_paragraph()
        r=p.add_run(text); r.bold=True; r.font.size=Pt(10); r.font.color.rgb=TEAL
        p.paragraph_format.space_before=Pt(8); p.paragraph_format.space_after=Pt(4)
        return self

    def add_body(self, text):
        if not text or not text.strip(): return self
        for line in text.split("\n"):
            line=line.strip()
            if not line: continue
            if line.startswith("# "): self.add_heading(line[2:],1); continue
            if line.startswith("## "): self.add_heading(line[3:],2); continue
            if line.startswith("### "): self.add_subheading(line[4:]); continue
            if line.startswith("- ") or line.startswith("* "):
                p=self.doc.add_paragraph(style="List Bullet")
                r=p.add_run(line[2:].strip())
                r.font.size=Pt(10); r.font.color.rgb=RGBColor(0x1E,0x29,0x3B)
            else:
                p=self.doc.add_paragraph()
                r=p.add_run(line); r.font.size=Pt(10)
                r.font.color.rgb=RGBColor(0x1E,0x29,0x3B)
                p.paragraph_format.space_after=Pt(4)
        return self

    def add_callout(self, text, color="EFF6FF", border_color="2563EB"):
        t=self.doc.add_table(rows=1,cols=1); t.style="Table Grid"
        c=t.cell(0,0); _bg(c,color)
        p=c.paragraphs[0]; r=p.add_run(text)
        r.font.size=Pt(9); r.font.italic=True
        self.doc.add_paragraph(); return self

    def add_table(self, rows_data, col_widths=None, header_color="0F1F38"):
        if not rows_data: return self
        n=max(len(r) for r in rows_data)
        t=self.doc.add_table(rows=len(rows_data),cols=n); t.style="Table Grid"
        if col_widths and len(col_widths)==n:
            for i,w in enumerate(col_widths):
                for cell in t.columns[i].cells: cell.width=Cm(w)
        for ri,rdata in enumerate(rows_data):
            is_hdr=ri==0
            bg=header_color if is_hdr else ("EFF6FF" if ri%2==0 else "FFFFFF")
            for ci,ct in enumerate(rdata):
                if ci>=n: break
                cell=t.rows[ri].cells[ci]; _bg(cell,bg)
                cell.vertical_alignment=WD_ALIGN_VERTICAL.CENTER
                p=cell.paragraphs[0]
                p.paragraph_format.space_before=Pt(4); p.paragraph_format.space_after=Pt(4)
                p.paragraph_format.left_indent=Cm(0.15)
                r=p.add_run(str(ct)); r.bold=is_hdr; r.font.size=Pt(9)
                r.font.color.rgb=WHITE if is_hdr else RGBColor(0x1E,0x29,0x3B)
        self.doc.add_paragraph(); return self

    def add_image(self, image_path, caption="", width_cm=14.0):
        if image_path and os.path.exists(image_path):
            try:
                p=self.doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
                p.add_run().add_picture(image_path,width=Cm(width_cm))
            except Exception as e: self.add_body(f"[Image error: {e}]")
        else: self.add_body(f"[Diagram not available: {caption}]")
        if caption:
            cp=self.doc.add_paragraph()
            cr=cp.add_run(f"Figure: {caption}"); cr.italic=True
            cr.font.size=Pt(9); cr.font.color.rgb=GRAY; cp.alignment=WD_ALIGN_PARAGRAPH.CENTER
        self.doc.add_paragraph(); return self

    def add_page_break(self):
        self.doc.add_page_break(); return self

    def add_footer_note(self, text):
        p=self.doc.add_paragraph(); _border_bottom(p,"D97706")
        r=p.add_run(text); r.font.size=Pt(8); r.font.italic=True; r.font.color.rgb=GRAY
        return self

    def save(self, path):
        os.makedirs(os.path.dirname(os.path.abspath(path)),exist_ok=True)
        self.doc.save(path); return path
