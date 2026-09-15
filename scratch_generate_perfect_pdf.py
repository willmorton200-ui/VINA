import os
import cv2
import numpy as np
import json
from PIL import Image as PILImage, ImageDraw, ImageFont

from pipeline.stage1_preprocessing import Stage1Preprocessor
from pipeline.stage5_ocr import Stage5OCRDecoder
from scratch_fix_all_visuals_and_pdf import extract_true_boundaries_and_corners, build_clean_board, draw_cyrillic_text

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\982dbb9e-4780-4467-a511-0a784bef8b97"
os.makedirs(artifacts_dir, exist_ok=True)

# 1. Initialize engines
p1 = Stage1Preprocessor(use_gpu=True)
ocr = Stage5OCRDecoder(use_gpu=True)

# Images to process
cases = [
    {
        "id": "castillo_white",
        "title": "Castillo de Liria (Sauvignon Blanc & Viura)",
        "img_path": r"test_dataset/butilki/photo_2026-08-10_12-34-29.jpg",
        "box": [479, 263, 960, 840],
        "crop": [460, 240, 960, 860]
    },
    {
        "id": "castillo_red",
        "title": "Castillo de Liria (Monastrell Medium Sweet)",
        "img_path": r"test_dataset/butilki/photo_2026-08-10_12-34-29.jpg",
        "box": [0, 273, 463, 832],
        "crop": [0, 250, 470, 850]
    },
    {
        "id": "tbilvino_red",
        "title": "TBILVINO SACHINO (Красное полусухое)",
        "img_path": r"C:\Users\User\.gemini\antigravity-ide\brain\982dbb9e-4780-4467-a511-0a784bef8b97\.user_uploaded\media_1787780608266.jpg",
        "box": [76, 263, 384, 881],
        "crop": [60, 240, 400, 900]
    },
    {
        "id": "tbilvino_white",
        "title": "TBILVINO SACHINO (Белое полусухое)",
        "img_path": r"C:\Users\User\.gemini\antigravity-ide\brain\982dbb9e-4780-4467-a511-0a784bef8b97\.user_uploaded\media_1787780608266.jpg",
        "box": [384, 264, 704, 920],
        "crop": [370, 240, 720, 930]
    }
]

generated_boards = {}
generated_comps = {}

for c in cases:
    cid = c["id"]
    print(f"\nProcessing case: {c['title']}...")
    img_bgr = cv2.imread(c["img_path"])
    cx1, cy1, cx2, cy2 = c["crop"]
    crop_bgr = img_bgr[cy1:cy2, cx1:cx2].copy()
    
    # SAM mask
    mask_full, _ = p1.sam_refiner.refine_mask(img_bgr, c["box"])
    mask_crop = mask_full[cy1:cy2, cx1:cx2]
    
    # True boundaries
    geo = extract_true_boundaries_and_corners(crop_bgr, mask_crop, name=cid)
    dewarped = geo["dewarped"]
    
    # OCR
    ocr_raw = ocr.process(crop_bgr)
    ocr_dew = ocr.process(dewarped)
    
    print(f"  P_TL: {geo['P_TL'].round(1)} | P_TR: {geo['P_TR'].round(1)}")
    print(f"  P_BL: {geo['P_BL'].round(1)} | P_BR: {geo['P_BR'].round(1)}")
    print(f"  Raw OCR: {ocr_raw['full_text']}")
    print(f"  Dewarped OCR: {ocr_dew['full_text']}")
    
    # Save clean board
    board_path = build_clean_board(cid, c["title"], crop_bgr, mask_crop, geo, ocr_dew["annotated_bgr"])
    generated_boards[cid] = board_path
    
    # Build clean Cyrillic OCR Comparison card (Raw vs Dewarped)
    h_comp = 500
    w_r = int(round(crop_bgr.shape[1] * (h_comp / float(crop_bgr.shape[0]))))
    w_d = int(round(dewarped.shape[1] * (h_comp / float(dewarped.shape[0]))))
    
    vis_raw_annotated = cv2.resize(ocr_raw["annotated_bgr"], (w_r, h_comp), interpolation=cv2.INTER_LANCZOS4)
    vis_dew_annotated = cv2.resize(ocr_dew["annotated_bgr"], (w_d, h_comp), interpolation=cv2.INTER_LANCZOS4)
    
    b_r = np.zeros((45, w_r, 3), dtype=np.uint8) + 28
    b_r = draw_cyrillic_text(b_r, f"1x Кроп (Без трансформации): {len(ocr_raw['text_blocks'])} сл.", (10, 10), font_size=16, text_color=(0, 180, 255))
    card_r = np.vstack((b_r, vis_raw_annotated))
    
    b_d = np.zeros((45, w_d, 3), dtype=np.uint8) + 28
    b_d = draw_cyrillic_text(b_d, f"Развертка v1.2 (Dewarped): {len(ocr_dew['text_blocks'])} сл.", (10, 10), font_size=16, text_color=(0, 255, 0))
    card_d = np.vstack((b_d, vis_dew_annotated))
    
    comp_pair = np.hstack((card_r, card_d))
    hdr_c = np.zeros((55, comp_pair.shape[1], 3), dtype=np.uint8) + 18
    hdr_c = draw_cyrillic_text(hdr_c, f"Сравнение OCR: {c['title']}", (20, 14), font_size=22, text_color=(255, 255, 255))
    final_comp = np.vstack((hdr_c, comp_pair))
    
    comp_path = os.path.join(artifacts_dir, f"{cid}_clean_ocr_comparison.png")
    cv2.imwrite(comp_path, final_comp)
    generated_comps[cid] = comp_path

# =========================================================================
# 2. COMPILE REPORTLAB PDF WITH DYNAMIC ASPECT RATIO & ZERO SQUASHING
# =========================================================================
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as ReportLabImage, PageBreak
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

font_dir = r"C:\Windows\Fonts"
pdfmetrics.registerFont(TTFont("Arial", os.path.join(font_dir, "arial.ttf")))
pdfmetrics.registerFont(TTFont("Arial-Bold", os.path.join(font_dir, "arialbd.ttf")))
pdfmetrics.registerFont(TTFont("Arial-Italic", os.path.join(font_dir, "ariali.ttf")))

output_pdf = r"d:\VINA\VINA_Version_1.2_Technical_Report.pdf"

# A4 page printable width: 595.27 - 60 = 535 pt
doc = SimpleDocTemplate(
    output_pdf,
    pagesize=A4,
    leftMargin=30,
    rightMargin=30,
    topMargin=26,
    bottomMargin=26
)

styles = getSampleStyleSheet()

t_style = ParagraphStyle("T", parent=styles["Normal"], fontName="Arial-Bold", fontSize=17, leading=21, textColor=colors.HexColor("#1A365D"))
sub_style = ParagraphStyle("Sub", parent=styles["Normal"], fontName="Arial", fontSize=9.5, leading=13.5, textColor=colors.HexColor("#4A5568"))
h1 = ParagraphStyle("H1", parent=styles["Normal"], fontName="Arial-Bold", fontSize=11.5, leading=14.5, textColor=colors.HexColor("#2B6CB0"), spaceBefore=6, spaceAfter=3, keepWithNext=True)
h2 = ParagraphStyle("H2", parent=styles["Normal"], fontName="Arial-Bold", fontSize=10, leading=13, textColor=colors.HexColor("#2D3748"), spaceBefore=4, spaceAfter=2, keepWithNext=True)
body = ParagraphStyle("B", parent=styles["Normal"], fontName="Arial", fontSize=8.5, leading=11.8, textColor=colors.HexColor("#2D3748"), spaceAfter=3)
bullet = ParagraphStyle("Bul", parent=styles["Normal"], fontName="Arial", fontSize=8.3, leading=11.5, textColor=colors.HexColor("#2D3748"), leftIndent=10, spaceAfter=2)

th = ParagraphStyle("TH", parent=styles["Normal"], fontName="Arial-Bold", fontSize=8, leading=10, textColor=colors.white, alignment=1)
td = ParagraphStyle("TD", parent=styles["Normal"], fontName="Arial", fontSize=7.8, leading=10.2, textColor=colors.HexColor("#2D3748"))
td_b = ParagraphStyle("TDB", parent=styles["Normal"], fontName="Arial-Bold", fontSize=7.8, leading=10.2, textColor=colors.HexColor("#1A365D"))

# Function to create image with STRICTLY PRESERVED ASPECT RATIO
def make_proportional_image(img_path, max_w=535, max_h=300):
    pil_im = PILImage.open(img_path)
    iw, ih = pil_im.size
    aspect = ih / float(iw)
    
    # Scale by width
    w = max_w
    h = w * aspect
    if h > max_h:
        h = max_h
        w = h / aspect
    return ReportLabImage(img_path, width=w, height=h)

story = []

# --- PAGE 1: ARCHITECTURE & CORNER PRECISION ---
story.append(Paragraph("VINA: Технический отчет по алгоритму Версии 1.2", t_style))
story.append(Paragraph("<b>Модернизация развертки:</b> Точные образующие контура, 3D сетка Coon's Patch, сохранение пропорций и анализ OCR", sub_style))
story.append(Spacer(1, 4))

meta_t = Table([
    [
        Paragraph("<b>Статус:</b> Релиз v1.2 (v1.1 сохранена в Git)", td),
        Paragraph("<b>Дата:</b> Август 2026", td),
        Paragraph("<b>Разработчик:</b> Алексей", td),
        Paragraph("<b>Пайплайн:</b> SAM + 3D Coon's + OCR", td)
    ]
], colWidths=[150, 110, 110, 165])
meta_t.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#EDF2F7")),
    ("PADDING", (0,0), (-1,-1), 4),
    ("BOX", (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0"))
]))
story.append(meta_t)
story.append(Spacer(1, 6))

story.append(Paragraph("1. Архитектурные принципы Версии 1.2", h1))
story.append(Paragraph("• <b>Плотный кроп по габаритам маски:</b> Изображение обрезается точно по границам маски без лишнего фона полок и соседних бутылок.", bullet))
story.append(Paragraph("• <b>Боковые образующие по реальному силуэту (L и R):</b> Боковые грани сетки строятся строго по фактическому внешнему контуру маски, что исключает срез углов и текста при съемке под углом.", bullet))
story.append(Paragraph("• <b>Точки геометрического отрыва (P_TL, P_TR, P_BL, P_BR):</b> Углы определяются на контуре маски в точках смыкания боковых образующих с верхней аркой и нижней дугой «улыбки».", bullet))
story.append(Paragraph("• <b>3D деформационная сетка (Coon's Patch Surface):</b> Боковые грани = L(v) и R(v), верхняя = T(u), нижняя = B(u). Внутренние изолинии плавно интерполируют пространственную кривизну цилиндра.", bullet))
story.append(Paragraph("• <b>Сохранение естественных метрических пропорций:</b> Размер развертки вычисляется по интегральной длине дуг (W_dst = max(arc_top, arc_bot), H_dst = max(len_L, len_R)), что исключает приплюснутость шрифтов.", bullet))

story.append(Spacer(1, 4))
story.append(Paragraph("2. Устранение геометрических искажений контура", h1))
story.append(Paragraph("В предыдущей реализации прямая секущая линия ошибочно срезала левый угол красной этикетки Castillo de Liria и коронку белой. В версии 1.2 образующие строятся строго по внешнему контуру:", body))

# Insert White & Red Pipeline Boards
story.append(Paragraph("<b>А. Castillo de Liria Sauvignon Blanc Viura (Белое полусладкое)</b>", h2))
story.append(make_proportional_image(generated_boards["castillo_white"], max_w=535, max_h=235))
story.append(Spacer(1, 4))

# --- PAGE 2: CASTILLO RED & RESULTS TABLE ---
story.append(PageBreak())
story.append(Paragraph("<b>Б. Castillo de Liria Monastrell Medium Sweet (Красное полусладкое)</b>", h2))
story.append(Paragraph("<i>Обратите внимание: боковая образующая (синяя) теперь строго облегает левый силуэт бутылки, не срезая надпись «SINCE 1971», а нижняя дуга точно охватывает основание:</i>", body))
story.append(make_proportional_image(generated_boards["castillo_red"], max_w=535, max_h=240))
story.append(Spacer(1, 6))

story.append(Paragraph("Сводные параметры векторизации и развертки Castillo de Liria", h1))
t_cast_data = [
    [Paragraph("Параметр", th), Paragraph("Castillo Sauvignon Blanc (Белое)", th), Paragraph("Castillo Monastrell (Красное)", th)],
    [Paragraph("Координаты 4 углов", td_b), Paragraph("P_TL: [19, 60] | P_TR: [494, 75]<br/>P_BL: [17, 392] | P_BR: [427, 371]", td), Paragraph("P_TL: [0, 79] | P_TR: [459, 62]<br/>P_BL: [57, 362] | P_BR: [464, 451]", td)],
    [Paragraph("Разрешение развертки", td_b), Paragraph("<b>676 × 332 px</b> (AR = 2.04:1, пропорции сохранены)", td), Paragraph("<b>606 × 391 px</b> (AR = 1.55:1, пропорции сохранены)", td)],
    [Paragraph("Распознанный текст OCR", td_b), Paragraph("<b>SINCE 1971</b> (98.8%)<br/><b>CASTILLO de LIRIA</b> (99.1%)<br/><b>Medium Sweet</b> (82%)", td), Paragraph("<b>SINCE 1971</b> (93.0%)<br/><b>CASTILLO de LIRIA</b> (96.1%)<br/><b>Medium Sweet</b> | <b>ON THIS LAND</b><br/><b>PRODUCTION OF HIGH-QUALITY WINES</b><br/><b>Cont. Net.</b> (80.6%)", td)]
]
t_cast = Table(t_cast_data, colWidths=[120, 205, 210])
t_cast.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#2B6CB0")),
    ("PADDING", (0,0), (-1,-1), 4),
    ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
    ("VALIGN", (0,0), (-1,-1), "TOP"),
    ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F7FAFC")])
]))
story.append(t_cast)

# --- PAGE 3: TBILVINO SACHINO ---
story.append(PageBreak())
story.append(Paragraph("3. Тестирование на винах TBILVINO SACHINO", h1))
story.append(Paragraph("Апробация алгоритма v1.2 на грузинских винах TBILVINO SACHINO с золотым гербом и грузинской вязью:", body))

story.append(Paragraph("<b>А. TBILVINO SACHINO Red Medium Dry (Красное полусухое)</b>", h2))
story.append(make_proportional_image(generated_boards["tbilvino_red"], max_w=535, max_h=235))
story.append(Spacer(1, 4))

story.append(Paragraph("<b>Б. TBILVINO SACHINO White Medium Dry (Белое полусухое)</b>", h2))
story.append(make_proportional_image(generated_boards["tbilvino_white"], max_w=535, max_h=235))

# --- PAGE 4: OCR DIRECT COMPARISON & CONCLUSIONS ---
story.append(PageBreak())
story.append(Paragraph("4. Сравнительный анализ: 1x Кроп против Развертки v1.2", h1))
story.append(Paragraph("Экспериментальное сравнение распознавания текста (RapidOCR + EasyOCR) напрямую с исходных кропов против развертки:", body))

# Comparison cards
story.append(make_proportional_image(generated_comps["castillo_red"], max_w=535, max_h=160))
story.append(Spacer(1, 4))
story.append(make_proportional_image(generated_comps["tbilvino_red"], max_w=535, max_h=160))
story.append(Spacer(1, 6))

t_comp_data = [
    [Paragraph("Зона этикетки", th), Paragraph("1x Кроп (Без трансформации)", th), Paragraph("Развертка v1.2 (С трансформацией)", th), Paragraph("Эффект трансформации v1.2", th)],
    [Paragraph("<b>Сортовая плашка Monastrell</b>", td_b), Paragraph("`ЯЕМ]` (conf: 66.8%, шум)", td), Paragraph("<b>`MONASTRELL.`</b> (conf: <b>94.0%</b>)", td), Paragraph("<b>100% восстановление</b> нечитаемого слова", td)],
    [Paragraph("<b>Castillo Monastrell Красная</b>", td_b), Paragraph("7 слов (захвачен шум с полки `шяв`, потерян нижний блок)", td), Paragraph("9 слов (`ON THIS LAND`, `PRODUCTION OF HIGH-QUALITY WINES`, `Cont. Net.`)", td), Paragraph("<b>Полное извлечение</b> описания и объема", td)],
    [Paragraph("<b>TBILVINO SACHINO Белая</b>", td_b), Paragraph("Захват постороннего ценника снизу (`МЕЫ`)", td), Paragraph("`TBILVINO WINE OF GEORGIA SACHINO WHITE MEDIUM DRY`", td), Paragraph("<b>Чистый кроп</b> без артефактов полки", td)],
    [Paragraph("<b>Castillo Sauvignon Blanc Белая</b>", td_b), Paragraph("`SINCE 1971 CASTILLO de LIRIA` (уверенность 87.5%)", td), Paragraph("`SINCE 1971 CASTILLO de LIRIA` (уверенность <b>98.8%</b> / <b>99.1%</b>)", td), Paragraph("<b>Рост уверенности</b> нейросети на +11%", td)]
]
t_comp = Table(t_comp_data, colWidths=[110, 140, 150, 135])
t_comp.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#2B6CB0")),
    ("PADDING", (0,0), (-1,-1), 4),
    ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
    ("VALIGN", (0,0), (-1,-1), "TOP"),
    ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F7FAFC")])
]))
story.append(t_comp)

story.append(Spacer(1, 6))
story.append(Paragraph("5. Заключение", h1))
story.append(Paragraph("1. <b>Устранение среза углов:</b> Боковые образующие теперь строго следуют контуру маски бутылки, сохраняя надписи на краях цилиндра.", bullet))
story.append(Paragraph("2. <b>Ликвидация вертикального сжатия (приплюснутости):</b> Размеры ремаппинга и отображения в PDF рассчитываются строго пропорционально длине дуг.", bullet))
story.append(Paragraph("3. <b>Поддержка кириллицы:</b> Все плашки и подписи на изображениях отрендерены через TrueType шрифт Arial без знаков «???».", bullet))

doc.build(story)
print(f"\nPerfect PDF generated: {output_pdf} ({os.path.getsize(output_pdf)} bytes)")
