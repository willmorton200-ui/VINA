import sys

file_path = r"d:\VINA\pipeline\stage5_ocr.py"
with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

start_idx = -1
end_idx = -1

for i, line in enumerate(lines):
    if "# 3. Targeted Cyrillic Augmentation via EasyOCR" in line:
        start_idx = i
        break

for i, line in enumerate(lines[start_idx:]):
    if "# Sort top to bottom" in line:
        end_idx = start_idx + i
        break

if start_idx == -1 or end_idx == -1:
    print("Could not find block to replace")
    sys.exit(1)

print(f"Replacing lines {start_idx} to {end_idx}")

new_block = """
        # 3. Targeted Cyrillic Augmentation via EasyOCR (Consensus Mode)
        # We always run EasyOCR and merge results if it finds confident Cyrillic that RapidOCR missed or hallucinated as Latin.
        if self.easy_ru is not None:
            try:
                def get_iou(rect1, rect2):
                    x_left = max(rect1["x"], rect2["x"])
                    y_top = max(rect1["y"], rect2["y"])
                    x_right = min(rect1["x"] + rect1["w"], rect2["x"] + rect2["w"])
                    y_bottom = min(rect1["y"] + rect1["h"], rect2["y"] + rect2["h"])
                    if x_right < x_left or y_bottom < y_top:
                        return 0.0
                    intersection_area = (x_right - x_left) * (y_bottom - y_top)
                    rect1_area = rect1["w"] * rect1["h"]
                    rect2_area = rect2["w"] * rect2["h"]
                    iou = intersection_area / float(rect1_area + rect2_area - intersection_area)
                    return iou

                cyrillic_chars = set("абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ")
                latin_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
                
                easy_ru_results = self.easy_ru.readtext(cv2.cvtColor(img_enh, cv2.COLOR_BGR2RGB))
                
                for bbox, text, conf in easy_ru_results:
                    clean_text = text.strip()
                    if not clean_text or float(conf) < 0.25:
                        continue
                        
                    pts = np.array(bbox, dtype=np.float64) / scale
                    x_min, y_min = np.min(pts, axis=0)
                    x_max, y_max = np.max(pts, axis=0)
                    e_rect = {"x": int(x_min), "y": int(y_min), "w": int(x_max - x_min), "h": int(y_max - y_min)}
                    
                    has_cyr = sum(c in cyrillic_chars for c in clean_text) >= 2
                    
                    # Find if it overlaps with any RapidOCR block
                    matched_idx = -1
                    max_iou = 0
                    for i, r_block in enumerate(text_blocks):
                        iou = get_iou(e_rect, r_block["rect"])
                        if iou > max_iou:
                            max_iou = iou
                            matched_idx = i
                            
                    if max_iou > 0.3:
                        # Overlap exists. Should EasyOCR overwrite RapidOCR?
                        r_text = text_blocks[matched_idx]["text"]
                        r_conf = text_blocks[matched_idx]["confidence"]
                        
                        r_latin_cnt = sum(c in latin_chars for c in r_text)
                        r_cyr_cnt = sum(c in cyrillic_chars for c in r_text)
                        
                        # If RapidOCR found mostly Latin/gibberish, and EasyOCR found Cyrillic with decent confidence
                        if has_cyr and r_latin_cnt > r_cyr_cnt and float(conf) > 0.35:
                            text_blocks[matched_idx]["text"] = clean_text
                            text_blocks[matched_idx]["confidence"] = round(float(conf), 3)
                            text_blocks[matched_idx]["bbox"] = [[int(p[0]), int(p[1])] for p in pts]
                            text_blocks[matched_idx]["rect"] = e_rect
                        # Or if EasyOCR is just much more confident
                        elif has_cyr and float(conf) > r_conf + 0.2:
                            text_blocks[matched_idx]["text"] = clean_text
                            text_blocks[matched_idx]["confidence"] = round(float(conf), 3)
                            text_blocks[matched_idx]["bbox"] = [[int(p[0]), int(p[1])] for p in pts]
                            text_blocks[matched_idx]["rect"] = e_rect
                    else:
                        # No overlap, it's a new block (e.g. RapidOCR missed it completely)
                        if has_cyr and float(conf) > 0.45:
                            text_blocks.append({
                                "text": clean_text,
                                "confidence": round(float(conf), 3),
                                "bbox": [[int(p[0]), int(p[1])] for p in pts],
                                "rect": e_rect
                            })
                            
            except Exception as e:
                print(f"[Stage5] EasyOCR ru consensus error: {e}")

"""

with open(file_path, "w", encoding="utf-8") as f:
    f.writelines(lines[:start_idx])
    f.write(new_block)
    f.writelines(lines[end_idx:])

print("Successfully patched stage5_ocr.py")
