import os
import shutil
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# 1. Register Windows Cyrillic Fonts
font_dir = r"C:\Windows\Fonts"
arial_regular = os.path.join(font_dir, "arial.ttf")
arial_bold = os.path.join(font_dir, "arialbd.ttf")
arial_italic = os.path.join(font_dir, "ariali.ttf")

pdfmetrics.registerFont(TTFont("Arial", arial_regular))
pdfmetrics.registerFont(TTFont("Arial-Bold", arial_bold))
pdfmetrics.registerFont(TTFont("Arial-Italic", arial_italic))

pdf_path = r"d:\VINA\VINA_Technology_Overview.pdf"
doc = SimpleDocTemplate(
    pdf_path,
    pagesize=A4,
    leftMargin=30,
    rightMargin=30,
    topMargin=26,
    bottomMargin=26
)

styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    "DocTitle",
    parent=styles["Normal"],
    fontName="Arial-Bold",
    fontSize=17,
    leading=21,
    textColor=colors.HexColor("#1A365D"),
    spaceAfter=2
)

subtitle_style = ParagraphStyle(
    "DocSubTitle",
    parent=styles["Normal"],
    fontName="Arial",
    fontSize=9.5,
    leading=13,
    textColor=colors.HexColor("#4A5568"),
    spaceAfter=6
)

h1_style = ParagraphStyle(
    "Heading1_Custom",
    parent=styles["Normal"],
    fontName="Arial-Bold",
    fontSize=10.5,
    leading=13.5,
    textColor=colors.HexColor("#2B6CB0"),
    spaceBefore=5,
    spaceAfter=2
)

body_style = ParagraphStyle(
    "Body_Custom",
    parent=styles["Normal"],
    fontName="Arial",
    fontSize=8.5,
    leading=11.5,
    textColor=colors.HexColor("#2D3748")
)

bullet_style = ParagraphStyle(
    "Bullet_Custom",
    parent=styles["Normal"],
    fontName="Arial",
    fontSize=8.2,
    leading=11.0,
    textColor=colors.HexColor("#2D3748"),
    leftIndent=10,
    spaceAfter=1.5
)

box_header_style = ParagraphStyle(
    "BoxHeader",
    parent=styles["Normal"],
    fontName="Arial-Bold",
    fontSize=8.5,
    leading=11.5,
    textColor=colors.HexColor("#1A365D")
)

box_text_style = ParagraphStyle(
    "BoxText",
    parent=styles["Normal"],
    fontName="Arial",
    fontSize=7.8,
    leading=10.5,
    textColor=colors.HexColor("#2D3748")
)

elements = []

# Title & Subtitle
elements.append(Paragraph("VINA: Cylindrical Dewarping & OCR System", title_style))
elements.append(Paragraph("Краткое описание технологий и архитектуры 5-этапного аппаратно-ускоренного конвейера (CUDA)", subtitle_style))
elements.append(HRFlowable(width="100%", thickness=1.2, color=colors.HexColor("#CBD5E0"), spaceAfter=5))

# Intro
intro_text = (
    "<b>VINA</b> — инженерная система для высокоточной реконструкции, "
    "ортогонального разворачивания цилиндрических винных этикеток и оптического распознавания текста (OCR) "
    "на основе сочетания глубокого обучения, начертательной геометрии и бикубических поверхностей Кунса."
)
elements.append(Paragraph(intro_text, body_style))
elements.append(Spacer(1, 3))

# Stage 1
elements.append(Paragraph("1. Этап 1: Детекция, сегментация и деротация оси", h1_style))
s1_bullets = [
    "<b>YOLOv8 (Custom Trained):</b> Первичная локализация бутылок и этикеток в кадре, фильтрация ложных межбутылочных зазоров по площади и пропорциям (w/h).",
    "<b>SAM (Segment Anything Model, ViT-H):</b> Высокоточная попиксельная сегментация сложной формы этикетки (арки, фигурные контуры, золотое тиснение).",
    "<b>MSRCR (Multi-Scale Retinex with Color Restoration):</b> Нормализация освещения, устранение световых бликов на стекле и выравнивание теней.",
    "<b>Axial Rectification (Деротация по биссектрисе):</b> Нахождение центральной оси бутылки как биссектрисы угла между боковыми образующими и поворот кадра строго вертикально (θ = 0°)."
]
for b in s1_bullets:
    elements.append(Paragraph(f"• {b}", bullet_style))

# Stage 2
elements.append(Paragraph("2. Этап 2: Параметрическая векторизация и геометрия", h1_style))
s2_bullets = [
    "<b>Direct Silhouette Tracing:</b> Боковые образующие L(v) и R(v) привязываются пиксель в пиксель к внешнему физическому силуэту маски без срезания.",
    "<b>True Semi-Ellipse Guides:</b> Верхняя T(u) и нижняя B(u) направляющие дуги строятся как истинные полуэллипсы цилиндрического сечения с непрерывной вертикальной касательностью к боковым граням.",
    "<b>Asymmetric Spur Pruning:</b> Робастное отсечение выбросов, автоматически срезающее выступающие вниз зубья, тени и штрихкодовые дефекты без нарушения основания этикетки."
]
for b in s2_bullets:
    elements.append(Paragraph(f"• {b}", bullet_style))

# Stage 3
elements.append(Paragraph("3. Этап 3: 3D-моделирование цилиндрической поверхности", h1_style))
s3_bullets = [
    "<b>Coon’s Surface Patch (Бикубическая поверхность Кунса):</b> Аналитическая интерполяция гладкой 3D-сетки (u, v) по четырем граничным контурам (L, R, T, B).",
    "<b>Orthogonal Mesh Optimization:</b> Построение ортогональной параметрической сетки в выровненном пространстве без косоугольных сдвигов и перекосов."
]
for b in s3_bullets:
    elements.append(Paragraph(f"• {b}", bullet_style))

# Stage 4
elements.append(Paragraph("4. Этап 4: Цилиндрическая развертка (Dewarping & Remapping)", h1_style))
s4_bullets = [
    "<b>Nonlinear Backward Remapping (cv2.remap):</b> Обратное координатное преобразование искривленного цилиндрического растра в плоское ортогональное изображение.",
    "<b>Lanczos-4 Interpolation:</b> 8-точечная интерполяция sinc-фильтром, устраняющая эффект сжатия текстуры по бокам цилиндра и сохраняющая резкость микрошрифтов."
]
for b in s4_bullets:
    elements.append(Paragraph(f"• {b}", bullet_style))

# Stage 5
elements.append(Paragraph("5. Этап 5: Гибридный многоязычный OCR", h1_style))
s5_bullets = [
    "<b>RapidOCR (PP-OCRv4 ONNX Runtime):</b> Основной скоростной движок GPU-детекции и распознавания текстовых блоков (латиница, кириллица, цифры, винтажные шрифты).",
    "<b>EasyOCR (Cyrillic-targeted):</b> Резервный модуль для специфических кириллических начертаний и стилизованных шрифтов.",
    "<b>Text CLAHE & Super-Resolution:</b> Адаптивное локальное контрастирование для уверенного чтения надписей на текстурированной бумаге и золотой фольге."
]
for b in s5_bullets:
    elements.append(Paragraph(f"• {b}", bullet_style))

elements.append(Spacer(1, 4))

# Tech Stack Table
table_data = [
    [Paragraph("Категория", box_header_style), Paragraph("Технологии и библиотеки", box_header_style)],
    [Paragraph("Ядро и вычисления", box_text_style), Paragraph("Python 3.11, PyTorch (CUDA 12.x), ONNX Runtime GPU", box_text_style)],
    [Paragraph("Компьютерное зрение", box_text_style), Paragraph("OpenCV (cv2), NumPy, SciPy, Pillow, Torchvision", box_text_style)],
    [Paragraph("Нейросетевые модели", box_text_style), Paragraph("YOLOv8 (Ultralytics), SAM (Segment Anything ViT-H), PP-OCRv4, EasyOCR", box_text_style)],
    [Paragraph("Геометрический аппарат", box_text_style), Paragraph("Coon's Patch (Бикубический патч Кунса), True Semi-Ellipse, Деротация по биссектрисе", box_text_style)],
    [Paragraph("Форматы и экспорт", box_text_style), Paragraph("Пакетный JSON-отчет, ортогональные PNG-сканы (Lanczos-4), 3D-сетки, PDF", box_text_style)]
]

tech_table = Table(table_data, colWidths=[140, 395])
tech_table.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EDF2F7")),
    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
    ("TOPPADDING", (0, 0), (-1, -1), 2.5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
]))

elements.append(tech_table)

doc.build(elements)

# Copy to artifacts directory
artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d"
artifact_pdf = os.path.join(artifacts_dir, "VINA_Technology_Overview.pdf")
shutil.copyfile(pdf_path, artifact_pdf)

print(f"Generated clean 1-page PDF successfully at: {pdf_path}")
