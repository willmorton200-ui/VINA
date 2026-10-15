#!/usr/bin/env python3
"""
Генератор официального PDF-документа:
«Каталог винной продукции последней базы заказчика, рассортированный по производителям».
Охватывает все 2 037 вин и 135 производителей.
"""

import json
import os
import sys
import time
from pathlib import Path
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


# ==============================================================================
# 1. Регистрация шрифтов с поддержкой кириллицы
# ==============================================================================
FONT_DIR = r"C:\Windows\Fonts"
pdfmetrics.registerFont(TTFont("Arial", os.path.join(FONT_DIR, "arial.ttf")))
pdfmetrics.registerFont(TTFont("Arial-Bold", os.path.join(FONT_DIR, "arialbd.ttf")))
pdfmetrics.registerFont(TTFont("Arial-Italic", os.path.join(FONT_DIR, "ariali.ttf")))


# ==============================================================================
# 2. NumberedCanvas: Двухпроходный расчет страниц, колонтитулы
# ==============================================================================
class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_decorations(self, page_count):
        self.saveState()
        page_w, page_h = A4
        left_m = 25
        right_m = page_w - 25

        # Верхний колонтитул (начиная со 2 страницы)
        if self._pageNumber > 1:
            self.setFont("Arial", 7)
            self.setFillColor(colors.HexColor("#64748B"))
            self.drawString(left_m, page_h - 20, "VINA • РЕЕСТР ВИННОЙ ПРОДУКЦИИ ЗАКАЗЧИКА (2 037 ВИН)")
            self.drawRightString(right_m, page_h - 20, "Классификатор по производителям")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(left_m, page_h - 24, right_m, page_h - 24)

        # Нижний колонтитул (на всех страницах)
        self.setFont("Arial", 7)
        self.setFillColor(colors.HexColor("#64748B"))
        self.drawString(left_m, 16, "VINA Intelligence System • Актуальная база заказчика 2026 • 135 производителей")
        self.drawRightString(right_m, 16, f"Страница {self._pageNumber} из {page_count}")
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(left_m, 24, right_m, 24)

        self.restoreState()


# ==============================================================================
# 3. Основная функция генерации
# ==============================================================================
def generate_catalog_pdf():
    t0 = time.time()
    print("=" * 80)
    print("      ГЕНЕРАЦИЯ PDF КАТАЛОГА ВИН ПО ПРОИЗВОДИТЕЛЯМ")
    print("=" * 80)

    # Загрузка данных
    json_path = Path(r"D:\VINA\data\products_catalog.json")
    csv_path = Path(r"D:\VINA\data\wines_integrated.csv")
    pdf_output_path = Path(r"D:\VINA\Каталог_вин_по_производителям_2026.pdf")

    if not json_path.is_file():
        print(f"ОШИБКА: Файл {json_path} не найден!", file=sys.stderr)
        return 1

    with open(json_path, "r", encoding="utf-8") as f:
        products = json.load(f)

    df_csv = pd.read_csv(csv_path) if csv_path.is_file() else pd.DataFrame()
    csv_dict = {}
    if not df_csv.empty and "Slug" in df_csv.columns:
        csv_dict = {r["Slug"]: r for _, r in df_csv.iterrows() if pd.notna(r.get("Slug"))}

    print(f"• Загружено товаров: {len(products)}")

    # Группировка по производителям
    by_manufacturer = {}
    for p in products:
        slug = p.get("slug")
        if not slug:
            continue

        extra = csv_dict.get(slug, {})
        mfg = str(extra.get("Винодельня") or p.get("manufacturer") or "Прочие производители").strip()
        title = str(extra.get("Название вина") or p.get("title") or slug).strip()
        cat = str(extra.get("Категория") or "").strip()
        color = str(extra.get("Цвет") or "").strip()
        region = str(extra.get("Регион") or "").strip()
        grape = str(extra.get("Сорт винограда") or "").strip()

        # Формируем компактное описание категории
        cat_disp = cat
        if color and color.lower() not in cat.lower():
            cat_disp = f"{cat} ({color})" if cat else color

        item = {
            "title": title,
            "category": cat_disp or "—",
            "region": region or "—",
            "grape": grape or "—",
            "slug": slug,
        }

        if mfg not in by_manufacturer:
            by_manufacturer[mfg] = []
        by_manufacturer[mfg].append(item)

    # Сортировка производителей: сначала русские А-Я, затем латиница A-Z
    def mfg_sort_key(name: str):
        c = name[0].upper()
        is_cyr = 1040 <= ord(c) <= 1103 or c == "Ё"
        return (0 if is_cyr else 1, name.lower())

    sorted_manufacturers = sorted(by_manufacturer.keys(), key=mfg_sort_key)
    print(f"• Производителей для каталога: {len(sorted_manufacturers)}")

    # Стили
    styles = getSampleStyleSheet()

    header_title_style = ParagraphStyle(
        "CoverTitle",
        parent=styles["Normal"],
        fontName="Arial-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1E293B"),
        spaceAfter=4,
    )

    header_subtitle_style = ParagraphStyle(
        "CoverSubtitle",
        parent=styles["Normal"],
        fontName="Arial",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#475569"),
        spaceAfter=12,
    )

    kpi_num_style = ParagraphStyle(
        "KpiNum",
        parent=styles["Normal"],
        fontName="Arial-Bold",
        fontSize=16,
        leading=19,
        textColor=colors.HexColor("#722F37"),  # Wine burgundy
        alignment=1,  # Center
    )

    kpi_lbl_style = ParagraphStyle(
        "KpiLbl",
        parent=styles["Normal"],
        fontName="Arial",
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#64748B"),
        alignment=1,
    )

    mfg_title_style = ParagraphStyle(
        "MfgTitle",
        parent=styles["Normal"],
        fontName="Arial-Bold",
        fontSize=9.5,
        leading=12.5,
        textColor=colors.white,
    )

    th_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Arial-Bold",
        fontSize=7,
        leading=8.5,
        textColor=colors.white,
        alignment=0,
    )

    th_center_style = ParagraphStyle(
        "TableHeaderCenter",
        parent=th_style,
        alignment=1,
    )

    cell_num_style = ParagraphStyle(
        "CellNum",
        parent=styles["Normal"],
        fontName="Arial",
        fontSize=7,
        leading=8.5,
        textColor=colors.HexColor("#64748B"),
        alignment=1,
    )

    cell_title_style = ParagraphStyle(
        "CellTitle",
        parent=styles["Normal"],
        fontName="Arial-Bold",
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#0F172A"),
    )

    cell_text_style = ParagraphStyle(
        "CellText",
        parent=styles["Normal"],
        fontName="Arial",
        fontSize=6.5,
        leading=8.5,
        textColor=colors.HexColor("#334155"),
    )

    cell_slug_style = ParagraphStyle(
        "CellSlug",
        parent=styles["Normal"],
        fontName="Arial",
        fontSize=5.5,
        leading=7.0,
        textColor=colors.HexColor("#64748B"),
    )

    # Параметры страницы
    page_w, page_h = A4
    left_m = 25
    right_m = 25
    usable_w = page_w - left_m - right_m  # 545.27 pt

    doc = SimpleDocTemplate(
        str(pdf_output_path),
        pagesize=A4,
        leftMargin=left_m,
        rightMargin=right_m,
        topMargin=32,
        bottomMargin=32,
    )

    story = []

    # ==========================================================================
    # ТИТУЛЬНАЯ ШАПКА И KPI КАРТОЧКИ
    # ==========================================================================
    story.append(Paragraph("РЕЕСТР И КАТАЛОГ ВИННОЙ ПРОДУКЦИИ", header_title_style))
    story.append(Paragraph("Актуальная база данных заказчика 2026 • Полная номенклатура по производителям", header_subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#722F37"), spaceAfter=10))

    # KPI карточки
    total_wines_cnt = len(products)
    total_mfg_cnt = len(sorted_manufacturers)

    kpi_data = [
        [
            Paragraph(f"{total_wines_cnt:,}".replace(",", " "), kpi_num_style),
            Paragraph(f"{total_mfg_cnt}", kpi_num_style),
            Paragraph("100%", kpi_num_style),
            Paragraph("SigLIP 2 + FAISS", kpi_num_style),
        ],
        [
            Paragraph("Всего наименований вин", kpi_lbl_style),
            Paragraph("Производителей в базе", kpi_lbl_style),
            Paragraph("Каталожных карточек", kpi_lbl_style),
            Paragraph("Архитектура поиска VINA", kpi_lbl_style),
        ],
    ]
    kpi_col_w = usable_w / 4.0
    kpi_table = Table(kpi_data, colWidths=[kpi_col_w] * 4)
    kpi_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ])
    )
    story.append(kpi_table)
    story.append(Spacer(1, 14))

    # ==========================================================================
    # СВОДНЫЙ АЛФАВИТНЫЙ УКАЗАТЕЛЬ ПРОИЗВОДИТЕЛЕЙ (3 колонки)
    # ==========================================================================
    idx_heading_style = ParagraphStyle(
        "IdxHeading",
        parent=styles["Normal"],
        fontName="Arial-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#1E293B"),
        spaceAfter=6,
    )
    story.append(Paragraph("Алфавитный указатель производителей и объём позиций:", idx_heading_style))

    mfg_summary_items = [(m, len(by_manufacturer[m])) for m in sorted_manufacturers]
    rows_per_col = (len(mfg_summary_items) + 2) // 3

    idx_th = [
        Paragraph("<b>Производитель</b>", th_style),
        Paragraph("<b>Поз.</b>", th_center_style),
        Paragraph("<b>Производитель</b>", th_style),
        Paragraph("<b>Поз.</b>", th_center_style),
        Paragraph("<b>Производитель</b>", th_style),
        Paragraph("<b>Поз.</b>", th_center_style),
    ]
    idx_table_data = [idx_th]

    idx_col_w = usable_w / 3.0
    col_subwidths = [idx_col_w - 30, 30, idx_col_w - 30, 30, idx_col_w - 30, 30]

    for r in range(rows_per_col):
        row_cells = []
        for c in range(3):
            item_idx = c * rows_per_col + r
            if item_idx < len(mfg_summary_items):
                m_name, count = mfg_summary_items[item_idx]
                row_cells.append(Paragraph(f"{m_name[:26]}", cell_text_style))
                row_cells.append(Paragraph(f"<b>{count}</b>", cell_num_style))
            else:
                row_cells.append(Paragraph("", cell_text_style))
                row_cells.append(Paragraph("", cell_num_style))
        idx_table_data.append(row_cells)

    idx_table = Table(idx_table_data, colWidths=col_subwidths, repeatRows=1)
    idx_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ])
    )
    story.append(idx_table)
    story.append(Spacer(1, 14))
    story.append(PageBreak())

    # ==========================================================================
    # ДЕТАЛЬНЫЙ КАТАЛОГ ПО ПРОИЗВОДИТЕЛЯМ (ЕДИНЫЙ ТАБЛИЧНЫЙ ПОТОК)
    # ==========================================================================
    # Ширины колонок: №, Название, Категория/Цвет, Сортовой состав, Регион, Идентификатор
    # Сумма: 20 + 175 + 75 + 130 + 72 + 73 = 545 pt (ровно usable_w)
    col_w = [20, 175, 75, 130, 72, 73]

    grand_total_wines = 0

    for mfg_idx, mfg_name in enumerate(sorted_manufacturers, 1):
        wines_list = by_manufacturer[mfg_name]
        wines_list.sort(key=lambda x: x["title"].lower())
        count = len(wines_list)
        grand_total_wines += count

        # Определяем основной регион производителя
        regions = [w["region"] for w in wines_list if w["region"] != "—"]
        dominant_reg = max(set(regions), key=regions.count) if regions else ""
        reg_info = f" • Регион: {dominant_reg}" if dominant_reg else ""

        # Строка 0: Шапка производителя (плашка на всю ширину)
        header_banner_cell = Paragraph(
            f"<b>{mfg_name.upper()}</b>  <font color='#FDE047'>• Всего позиций: {count}{reg_info}</font>",
            mfg_title_style,
        )
        row_0_banner = [header_banner_cell, "", "", "", "", ""]

        # Строка 1: Колонки таблицы
        row_1_cols = [
            Paragraph("<b>№</b>", th_center_style),
            Paragraph("<b>Наименование вина</b>", th_style),
            Paragraph("<b>Тип / Цвет</b>", th_style),
            Paragraph("<b>Сортовой состав</b>", th_style),
            Paragraph("<b>Регион</b>", th_style),
            Paragraph("<b>Код (Slug)</b>", th_style),
        ]

        table_rows = [row_0_banner, row_1_cols]

        for w_idx, w in enumerate(wines_list, 1):
            table_rows.append([
                Paragraph(str(w_idx), cell_num_style),
                Paragraph(w["title"], cell_title_style),
                Paragraph(w["category"], cell_text_style),
                Paragraph(w["grape"], cell_text_style),
                Paragraph(w["region"], cell_text_style),
                Paragraph(w["slug"], cell_slug_style),
            ])

        table_style = [
            # Стили для строки 0 (баннер производителя)
            ("SPAN", (0, 0), (-1, 0)),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4A0E17")),  # Deep Wine Burgundy
            ("TOPPADDING", (0, 0), (-1, 0), 4),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
            ("LEFTPADDING", (0, 0), (-1, 0), 6),
            ("RIGHTPADDING", (0, 0), (-1, 0), 6),
            ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),

            # Стили для строки 1 (колонки)
            ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#1E293B")),  # Dark Navy
            ("TOPPADDING", (0, 1), (-1, 1), 2.5),
            ("BOTTOMPADDING", (0, 1), (-1, 1), 2.5),
            ("LEFTPADDING", (0, 1), (-1, 1), 3),
            ("RIGHTPADDING", (0, 1), (-1, 1), 3),

            # Сетка и рамка
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 1), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),

            # Данные вин (начиная со 2 строки)
            ("ROWBACKGROUNDS", (0, 2), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ("TOPPADDING", (0, 2), (-1, -1), 2.0),
            ("BOTTOMPADDING", (0, 2), (-1, -1), 2.0),
            ("LEFTPADDING", (0, 2), (-1, -1), 3),
            ("RIGHTPADDING", (0, 2), (-1, -1), 3),
            ("VALIGN", (0, 2), (-1, -1), "TOP"),
        ]

        # repeatRows=2 повторяет и плашку производителя, и колонки при переносе на след. страницу
        wine_table = Table(table_rows, colWidths=col_w, repeatRows=2)
        wine_table.setStyle(TableStyle(table_style))

        story.append(wine_table)
        story.append(Spacer(1, 11))

    print(f"• Построение документа SimpleDocTemplate...")
    doc.build(story, canvasmaker=NumberedCanvas)

    elapsed = time.time() - t0
    size_mb = pdf_output_path.stat().st_size / (1024 * 1024)
    print("=" * 80)
    print(f"✓ PDF ДОКУМЕНТ УСПЕШНО СГЕНЕРИРОВАН!")
    print(f"• Путь к файлу   : {pdf_output_path}")
    print(f"• Размер файла   : {size_mb:.2f} МБ")
    print(f"• Производителей : {total_mfg_cnt}")
    print(f"• Всего вин      : {grand_total_wines}")
    print(f"• Время создания : {elapsed:.1f} с")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(generate_catalog_pdf())
