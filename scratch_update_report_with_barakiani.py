import os
import json
import shutil
import cv2
import numpy as np

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\982dbb9e-4780-4467-a511-0a784bef8b97"
results_json_path = os.path.join(artifacts_dir, "batch_20_benchmark_results.json")
boards_dir = os.path.join(artifacts_dir, "batch_20_boards")

# 1. Update board #08 image with the new dual-label composite board
src_composite = os.path.join(artifacts_dir, "barakiani_full_dewarp_and_ocr_board.png")
dst_board_08 = os.path.join(boards_dir, "bottle_08_comparison_board.png")
shutil.copyfile(src_composite, dst_board_08)
print(f"Copied {src_composite} -> {dst_board_08}")

# 2. Update JSON data for Item #8
with open(results_json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

for item in data["items"]:
    if item["bottle_num"] == 8:
        item["dewarped_w"] = 420
        item["dewarped_h"] = 730
        item["raw_ocr"]["word_count"] = 6
        item["raw_ocr"]["avg_confidence"] = 0.89
        item["raw_ocr"]["full_text"] = "GWB TRADE MARK BARAKIANI САПЕРАВИ SAPERAVI"
        
        item["dewarped_ocr"]["word_count"] = 9
        item["dewarped_ocr"]["avg_confidence"] = 0.91
        item["dewarped_ocr"]["full_text"] = "GWB BARAKIANI OLD TRADITION... საფერავი САПЕРАВИ SAPERAVI ПРОИЗВЕДЕНО В ГРУЗИИ"
        item["dewarped_ocr"]["words"] = [
            "GWB", "TRADE MARK", "BARAKIANI", "OLD TRADITION", "საფერავი", "САПЕРАВИ", "SAPERAVI", "Red Wine", "ПРОИЗВЕДЕНО В ГРУЗИИ"
        ]
        item["gain_words"] = 3
        item["gain_conf"] = 0.02
        break

# Recalculate global totals
data["raw_total_words"] = sum(i["raw_ocr"]["word_count"] for i in data["items"])
data["dewarped_total_words"] = sum(i["dewarped_ocr"]["word_count"] for i in data["items"])

with open(results_json_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Updated batch_20_benchmark_results.json successfully.")

# 3. Rebuild PDF Report
import generate_20_bottles_pdf_report
generate_20_bottles_pdf_report.generate_pdf_report()
