import os
import json
import numpy as np
from PIL import Image as PILImage
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as ReportLabImage, PageBreak, KeepTogether
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\982dbb9e-4780-4467-a511-0a784bef8b97"
results_json_path = os.path.join(artifacts_dir, "batch_20_benchmark_results.json")
boards_dir = os.path.join(artifacts_dir, "batch_20_boards")

font_dir = r"C:\Windows\Fonts"
pdfmetrics.registerFont(TTFont("Arial", os.path.join(font_dir, "arial.ttf")))
pdfmetrics.registerFont(TTFont("Arial-Bold", os.path.join(font_dir, "arialbd.ttf")))
pdfmetrics.registerFont(TTFont("Arial-Italic", os.path.join(font_dir, "ariali.ttf")))

def generate_pdf_report():
    if not os.path.exists(results_json_path):
        print(f"Error: {results_json_path} not found.")
        return
        
    with open(results_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    output_pdf = r"d:\VINA\VINA_20_Bottles_OCR_Comparative_Report.pdf"
    
    # A4 dimensions: 595.27 x 841.89 pt, margins: 28 pt -> printable width: 539 pt
    doc = SimpleDocTemplate(
        output_pdf,
        pagesize=A4,
        leftMargin=28,
        rightMargin=28,
        topMargin=26,
        bottomMargin=26
    )
    
    styles = getSampleStyleSheet()
    
    t_style = ParagraphStyle("T", parent=styles["Normal"], fontName="Arial-Bold", fontSize=16, leading=20, textColor=colors.HexColor("#1A365D"))
    sub_style = ParagraphStyle("Sub", parent=styles["Normal"], fontName="Arial", fontSize=9, leading=13, textColor=colors.HexColor("#4A5568"))
    h1 = ParagraphStyle("H1", parent=styles["Normal"], fontName="Arial-Bold", fontSize=11, leading=14, textColor=colors.HexColor("#2B6CB0"), spaceBefore=6, spaceAfter=3, keepWithNext=True)
    h2 = ParagraphStyle("H2", parent=styles["Normal"], fontName="Arial-Bold", fontSize=9.5, leading=12.5, textColor=colors.HexColor("#2D3748"), spaceBefore=4, spaceAfter=2, keepWithNext=True)
    body = ParagraphStyle("B", parent=styles["Normal"], fontName="Arial", fontSize=8, leading=11, textColor=colors.HexColor("#2D3748"), spaceAfter=2)
    bullet = ParagraphStyle("Bul", parent=styles["Normal"], fontName="Arial", fontSize=8, leading=11, textColor=colors.HexColor("#2D3748"), leftIndent=10, spaceAfter=1.5)
    
    th = ParagraphStyle("TH", parent=styles["Normal"], fontName="Arial-Bold", fontSize=7.5, leading=9.5, textColor=colors.white, alignment=1)
    td = ParagraphStyle("TD", parent=styles["Normal"], fontName="Arial", fontSize=7.2, leading=9.2, textColor=colors.HexColor("#2D3748"))
    td_b = ParagraphStyle("TDB", parent=styles["Normal"], fontName="Arial-Bold", fontSize=7.2, leading=9.2, textColor=colors.HexColor("#1A365D"))
    td_g = ParagraphStyle("TDG", parent=styles["Normal"], fontName="Arial-Bold", fontSize=7.2, leading=9.2, textColor=colors.HexColor("#22543D"))
    
    def make_proportional_img(img_path, max_w=539, max_h=230):
        if not os.path.exists(img_path):
            return Paragraph(f"Image not found: {img_path}", body)
        pil_im = PILImage.open(img_path)
        iw, ih = pil_im.size
        aspect = ih / float(iw)
        w = max_w
        h = w * aspect
        if h > max_h:
            h = max_h
            w = h / aspect
        return ReportLabImage(img_path, width=w, height=h)
        
    story = []
    
    # =========================================================================
    # PAGE 1: EXECUTIVE SUMMARY & STATISTICAL COMPARISON TABLE
    # =========================================================================
    story.append(Paragraph("VINA: Сравнительный отчет по распознаванию этикеток (20 образцов)", t_style))
    story.append(Paragraph("<b>Анализ точности OCR:</b> Прямое распознавание (1x Кроп) против Развертки v1.2 (3D Coon's Patch + Universal Angles)", sub_style))
    story.append(Spacer(1, 4))
    
    total_raw_w = data["raw_total_words"]
    total_dew_w = data["dewarped_total_words"]
    gain_w = total_dew_w - total_raw_w
    pct_w = (gain_w / max(total_raw_w, 1)) * 100
    avg_raw_c = data["raw_avg_conf"] * 100.0 if data["raw_avg_conf"] <= 1.0 else data["raw_avg_conf"]
    avg_dew_c = data["dewarped_avg_conf"] * 100.0 if data["dewarped_avg_conf"] <= 1.0 else data["dewarped_avg_conf"]
    
    meta_t = Table([
        [
            Paragraph(f"<b>Всего образцов:</b> {data['total_bottles']}", td),
            Paragraph(f"<b>Слов без развертки:</b> {total_raw_w}", td),
            Paragraph(f"<b>Слов с разверткой v1.2:</b> <b>{total_dew_w}</b>", td_g),
            Paragraph(f"<b>Средняя уверенность OCR:</b> {avg_raw_c:.1f}% → <b>{avg_dew_c:.1f}%</b>", td_g)
        ]
    ], colWidths=[95, 120, 140, 184])
    meta_t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#EDF2F7")),
        ("PADDING", (0,0), (-1,-1), 4),
        ("BOX", (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0"))
    ]))
    story.append(meta_t)
    story.append(Spacer(1, 6))
    
    story.append(Paragraph("1. Сводная таблица сравнительного OCR по 20 образцам", h1))
    
    # Table header
    t_summary_rows = [
        [
            Paragraph("№", th),
            Paragraph("Файл образца", th),
            Paragraph("Без развертки", th),
            Paragraph("С разверткой v1.2", th),
            Paragraph("Прирост / Изменение", th),
            Paragraph("Уверенность OCR", th),
            Paragraph("Ключевой прочитанный текст", th)
        ]
    ]
    
    for item in data["items"]:
        b_num = item["bottle_num"]
        fn = item["filename"]
        if len(fn) > 22: fn = fn[:20] + ".."
        
        raw_cnt = item["raw_ocr"]["word_count"]
        dew_cnt = item["dewarped_ocr"]["word_count"]
        g_cnt = item["gain_words"]
        raw_cf = item["raw_ocr"]["avg_confidence"] * (100.0 if item["raw_ocr"]["avg_confidence"] <= 1.0 else 1.0)
        dew_cf = item["dewarped_ocr"]["avg_confidence"] * (100.0 if item["dewarped_ocr"]["avg_confidence"] <= 1.0 else 1.0)
        
        text_snip = item["dewarped_ocr"]["full_text"]
        if not text_snip:
            text_snip = item["raw_ocr"]["full_text"]
        if len(text_snip) > 38: text_snip = text_snip[:35] + "..."
        if not text_snip: text_snip = "—"
        
        g_style = td_g if g_cnt > 0 else (td_b if g_cnt == 0 else td)
        g_str = f"+{g_cnt} сл" if g_cnt > 0 else (f"{g_cnt} сл" if g_cnt < 0 else "0 (чистый текст)")
        
        t_summary_rows.append([
            Paragraph(f"{b_num:02d}", td_b),
            Paragraph(fn, td),
            Paragraph(f"{raw_cnt} сл ({raw_cf:.0f}%)", td),
            Paragraph(f"<b>{dew_cnt} сл</b> ({dew_cf:.0f}%)", td_b),
            Paragraph(f"<b>{g_str}</b>", g_style),
            Paragraph(f"{raw_cf:.0f}% → <b>{dew_cf:.0f}%</b>", td),
            Paragraph(text_snip, td)
        ])
        
    t_sum = Table(t_summary_rows, colWidths=[16, 105, 68, 72, 72, 68, 138])
    t_sum.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#2B6CB0")),
        ("PADDING", (0,0), (-1,-1), 2.2),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F7FAFC")])
    ]))
    story.append(t_sum)
    story.append(Spacer(1, 6))
    
    story.append(Paragraph("<b>Ключевые выводы сравнительного анализа:</b>", h2))
    story.append(Paragraph("1. <b>Восстановление скрытого и деформированного текста:</b> На изогнутых боковых краях бутылок (Castillo White #3, Twiga Hill #6, Brandvlei #9, Tbilvino #15, Krinitsa #20) развертка полностью восстановила ранее нечитаемые строки описания, сорта винограда (Cabernet Sauvignon, Chardonnay, Saperavi) и объем.", bullet))
    story.append(Paragraph("2. <b>Устранение оптических галлюцинаций OCR:</b> На необработанных снимках блики и перспективный наклон приводили к ложным символам (напр. 'ИЫНО', 'Аис', 'd3nmo'). Развертка устранила кривизну и очистила поток распознавания.", bullet))
    story.append(Paragraph("3. <b>Геометрическая ортогональность:</b> Универсальное правило минимального угла сопряжения (min internal angle) обеспечило идеальную посадку 3D-сетки Coon's Patch без срезания краевых букв.", bullet))
    
    # =========================================================================
    # PAGES 2..11: VISUAL COMPARISON BOARDS (2 BOTTLES PER PAGE)
    # =========================================================================
    for idx, item in enumerate(data["items"]):
        b_num = item["bottle_num"]
        board_path = item["board_path"]
        
        if idx % 2 == 0:
            story.append(PageBreak())
            story.append(Paragraph(f"2. Визуальные панели образцов #{idx+1:02d} – #{min(idx+2, len(data['items'])):02d}", h1))
            
        story.append(Paragraph(f"<b>Образец #{b_num:02d}: {item['filename']}</b> (Кроп {item['crop_w']}x{item['crop_h']} → Развертка {item['dewarped_w']}x{item['dewarped_h']}, Прирост: {item['gain_words']:+d} слов)", h2))
        story.append(make_proportional_img(board_path, max_w=539, max_h=230))
        story.append(Spacer(1, 4))
        
    doc.build(story)
    print(f"\nComprehensive 20-Bottle Technical Report generated: {output_pdf} ({os.path.getsize(output_pdf)} bytes)")

if __name__ == "__main__":
    generate_pdf_report()
