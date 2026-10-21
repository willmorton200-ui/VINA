"""
Stage 5 VLM: High-Fidelity Vision-Language Model OCR & Label Inspector
Uses local Qwen2-VL-2B-Instruct from D:\\models\\Qwen2-VL-2B-Instruct.
Zero heuristics, zero regexes — reads complex calligraphy, ligatures,
church-slavonic fonts, foil stamping, and stylized wine brands directly.
"""

import os
import re
import time
import cv2
import numpy as np
import torch
from PIL import Image
from typing import Optional, Dict, Any, List

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LOCAL_VLM_PATH = BASE_DIR / "models" / "Qwen2-VL-2B-Instruct"

def ensure_vlm_model(target_dir: Path = LOCAL_VLM_PATH) -> str:
    """
    Проверяет наличие весов Qwen2-VL-2B-Instruct внутри VINA/models/.
    Если они отсутствуют (например, чистый клон репозитория у коллег или Docker) —
    автоматически скачивает их напрямую с Hugging Face в папку models/Qwen2-VL-2B-Instruct.
    """
    if target_dir.exists() and (any(target_dir.glob("*.safetensors")) or any(target_dir.glob("*.bin"))):
        return str(target_dir)

    target_dir.mkdir(parents=True, exist_ok=True)
    repo_id = "Qwen/Qwen2-VL-2B-Instruct"
    token = os.environ.get("HF_TOKEN", None)

    print(f"[WineVLMDecoder] Модель {repo_id} не найдена в {target_dir}.")
    print(f"[WineVLMDecoder] Запуск автоматической загрузки весов с Hugging Face в {target_dir}...")
    try:
        from huggingface_hub import snapshot_download
        snapshot_download(
            repo_id=repo_id,
            local_dir=str(target_dir),
            local_dir_use_symlinks=False,
            token=token,
        )
        print(f"[WineVLMDecoder] Веса {repo_id} успешно скачаны в {target_dir}.")
        return str(target_dir)
    except Exception as e_direct:
        print(f"[WineVLMDecoder] Прямая загрузка с HF завершилась с ошибкой: {e_direct}")
        print(f"[WineVLMDecoder] Пробуем резервное зеркало https://hf-mirror.com ...")
        try:
            from huggingface_hub import snapshot_download
            snapshot_download(
                repo_id=repo_id,
                local_dir=str(target_dir),
                local_dir_use_symlinks=False,
                token=token,
                endpoint="https://hf-mirror.com",
            )
            print(f"[WineVLMDecoder] Веса {repo_id} успешно скачаны через зеркало в {target_dir}.")
            return str(target_dir)
        except Exception as e_mirror:
            print(f"[WineVLMDecoder] Ошибка скачивания в models: {e_mirror}. Фолбэк на transformers cache.")
            return repo_id

DEFAULT_VLM_PATH = str(LOCAL_VLM_PATH)

class WineVLMDecoder:
    _instance = None

    @classmethod
    def get_instance(cls, model_path: str = None, device: str = "cuda"):
        """Returns the shared singleton instance of WineVLMDecoder (avoids duplicate VRAM allocation)."""
        if cls._instance is None:
            if model_path is None:
                model_path = ensure_vlm_model(LOCAL_VLM_PATH)
            cls._instance = cls(model_path=model_path, device=device, lazy=False)
        return cls._instance

    def __init__(self, model_path: str = None, device: str = "cuda", lazy: bool = True):
        if model_path is None:
            model_path = ensure_vlm_model(LOCAL_VLM_PATH)
        self.model_path = model_path
        self.device = device if torch.cuda.is_available() else "cpu"
        self.model = None
        self.processor = None
        self.is_loaded = False

        if not lazy:
            self.load()

    def load(self):
        """Loads Qwen2-VL-2B-Instruct into GPU memory (uses ~4.1 GB VRAM)."""
        if self.is_loaded:
            return

        is_local = os.path.exists(self.model_path)
        print(f"[WineVLMDecoder] Loading Qwen2-VL-2B-Instruct from {self.model_path} on {self.device}...")
        t0 = time.perf_counter()

        from transformers import Qwen2VLForConditionalGeneration, AutoProcessor

        self.model = Qwen2VLForConditionalGeneration.from_pretrained(
            self.model_path,
            torch_dtype=torch.bfloat16 if self.device.startswith("cuda") else torch.float32,
            device_map="cuda" if self.device.startswith("cuda") else None,
            local_files_only=is_local
        )
        self.processor = AutoProcessor.from_pretrained(self.model_path, local_files_only=is_local)
        self.is_loaded = True
        dt = (time.perf_counter() - t0) * 1000.0
        print(f"[WineVLMDecoder] Loaded in {dt:.1f} ms. VRAM: {torch.cuda.memory_allocated() / (1024**3):.2f} GB")

    def _prepare_image(self, image_input, max_dim: int = 1280) -> Image.Image:
        """Converts cv2 BGR, file path, or PIL.Image to RGB PIL Image and caps max dimension."""
        if isinstance(image_input, str):
            img = Image.open(image_input).convert("RGB")
        elif isinstance(image_input, np.ndarray):
            rgb = cv2.cvtColor(image_input, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb)
        elif isinstance(image_input, Image.Image):
            img = image_input.convert("RGB")
        else:
            raise ValueError(f"Unsupported image input type: {type(image_input)}")

        w, h = img.size
        if max(w, h) > max_dim:
            scale = max_dim / max(w, h)
            img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
        return img

    def read_label(
        self,
        image_input,
        prompt: str = "What words are written on this wine label from top to bottom? Do not miss any word.",
        max_tokens: int = 128
    ) -> Dict[str, Any]:
        """
        Extracts verbatim text from the wine label using Qwen2-VL.
        Handles ligatures, church-slavonic fonts, foil embossing, curved lines.
        """
        if not self.is_loaded:
            self.load()

        from qwen_vl_utils import process_vision_info

        pil_img = self._prepare_image(image_input)

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": pil_img},
                    {"type": "text", "text": prompt}
                ]
            }
        ]

        t0 = time.perf_counter()
        text_prompt = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        image_inputs, video_inputs = process_vision_info(messages)

        inputs = self.processor(
            text=[text_prompt],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt"
        )
        if self.device.startswith("cuda"):
            inputs = inputs.to(self.device)

        with torch.no_grad():
            generated_ids = self.model.generate(**inputs, max_new_tokens=max_tokens)

        generated_ids_trimmed = [
            out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        output_text = self.processor.batch_decode(
            generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )[0].strip()

        latency_ms = (time.perf_counter() - t0) * 1000.0

        # Clean list numbering (1., 2., -), intros, and prefixes
        lines = []
        for line in output_text.splitlines():
            line_str = line.strip()
            if not line_str:
                continue
            # Strip list numbering e.g. "1. ", "2) ", "- ", "* ", "• "
            line_clean = re.sub(r'^\s*(\d+[\.\)]\s*|[-\*•]\s*)', '', line_str).strip()
            low_line = line_clean.lower()
            intro_phrases = [
                "the words written", "the words on the wine label", "the words on the label",
                "the words on this wine label", "the wine label reads", "the label reads",
                "here are the words", "the text on the label", "текст на этикетке", "надписи на этикетке"
            ]
            if any(low_line.startswith(p) for p in intro_phrases):
                continue
            if line_clean.endswith(":") and len(line_clean.split()) <= 5 and any(w in low_line for w in ["words", "label", "reads", "текст"]):
                continue
            if line_clean:
                lines.append(line_clean)

        # Для вытянутых вертикальных этикеток (h / w >= 1.35)
        # проверяем, содержит ли уже распознанный текст ключевые параметры (сорт, цвет, сладость).
        # Если первый проход уже прочитал всю спецификацию вина, второй проход пропускается для скорости.
        pw, ph = pil_img.size
        need_bottom = False
        if ph / float(pw) >= 1.35:
            text_so_far = " ".join(lines).upper()
            try:
                from .wine_thesaurus import extract_grape_concepts, COLOR_ONTOLOGY, SWEETNESS_ONTOLOGY, SPECIAL_WINE_TERMS
                has_grape = bool(extract_grape_concepts(text_so_far))
                has_color = any(any(w in text_so_far for w in words) for words in COLOR_ONTOLOGY.values())
                has_sweet = any(any(w in text_so_far for w in words) for words in SWEETNESS_ONTOLOGY.values())
                has_special = any(any(w in text_so_far for w in words) for words in SPECIAL_WINE_TERMS.values())
                
                # Для Массандры строго проверяем: если нет ни сорта, ни Мускателя — обязательно запускаем нижний проход
                is_massandra = "МАССАНДРА" in text_so_far or "MASSANDRA" in text_so_far
                has_muskatel = any(w in text_so_far for w in SPECIAL_WINE_TERMS.get("MUSKATEL", []))
                
                if is_massandra and not (has_grape or has_muskatel):
                    need_bottom = True
                elif has_grape and (has_color or has_sweet or has_special):
                    need_bottom = False
                elif has_special and (has_color or has_sweet):
                    need_bottom = False
                else:
                    need_bottom = True
            except Exception:
                need_bottom = True

        if need_bottom:
            try:
                bot_crop = pil_img.crop((0, int(ph * 0.45), pw, ph))
                bot_messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "image", "image": bot_crop},
                            {"type": "text", "text": "What words are written on this wine label from top to bottom? Do not miss any word."}
                        ]
                    }
                ]
                bot_prompt = self.processor.apply_chat_template(bot_messages, tokenize=False, add_generation_prompt=True)
                b_imgs, b_vids = process_vision_info(bot_messages)
                b_inputs = self.processor(text=[bot_prompt], images=b_imgs, videos=b_vids, padding=True, return_tensors="pt")
                if self.device.startswith("cuda"):
                    b_inputs = b_inputs.to(self.device)
                with torch.no_grad():
                    b_gen_ids = self.model.generate(**b_inputs, max_new_tokens=max_tokens)
                b_trimmed = [out_ids[len(in_ids):] for in_ids, out_ids in zip(b_inputs.input_ids, b_gen_ids)]
                bot_text = self.processor.batch_decode(b_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0].strip()

                existing_upper = set(" ".join(lines).upper().split())
                for b_line in bot_text.splitlines():
                    b_clean = re.sub(r'^\s*(\d+[\.\)]\s*|[-\*•]\s*)', '', b_line.strip()).strip()
                    if b_clean and not any(b_clean.lower().startswith(p) for p in intro_phrases):
                        new_words = [w for w in b_clean.split() if w.upper() not in existing_upper]
                        if new_words:
                            lines.append(b_clean)
                            existing_upper.update(w.upper() for w in new_words)
            except Exception as e_bot:
                print(f"[WineVLMDecoder] Bottom zone pass notice: {e_bot}")

        clean_text = "\n".join(lines).strip() if lines else output_text.strip()
        clean_text = clean_text.strip(' "\'\n\r\t')

        # Filter out safety refusals, coordinate echoes, or prompt repetitions
        if clean_text.strip() == prompt.strip() or prompt.strip() in clean_text:
            clean_text = ""
        low_txt = clean_text.lower()
        if (low_txt.startswith("sorry") or "cannot assist" in low_txt or "can't assist" in low_txt 
            or "not visible" in low_txt or (low_txt.startswith("(") and low_txt.endswith(")"))):
            clean_text = ""

        return {
            "text": clean_text,
            "raw_output": output_text,
            "latency_ms": round(latency_ms, 1),
            "model": "Qwen2-VL-2B-Instruct"
        }

    def inspect_wine(self, image_input) -> Dict[str, Any]:
        """
        Extracts structured wine metadata directly from label visual features.
        Returns: {brand, winery, grape, vintage, color, sugar}
        """
        prompt = (
            "Ты винный эксперт-сомелье. Внимательно осмотри эту этикетку и извлеки данные в формате JSON:\n"
            "{\n"
            '  "brand": "название бренда / линейки",\n'
            '  "winery": "винодельня / производитель",\n'
            '  "grape": "сорт винограда (если указан)",\n'
            '  "vintage": "год урожая (если указан)",\n'
            '  "type": "тип (сухое, полусладкое, брют и т.д.)",\n'
            '  "raw_text": "весь видимый текст"\n'
            "}\n"
            "Выведи ТОЛЬКО валидный JSON без markdown блоков."
        )
        res = self.read_label(image_input, prompt=prompt, max_tokens=256)
        text = res["text"]
        import json
        import re

        # Parse JSON
        parsed = {}
        try:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                parsed = json.loads(match.group(0))
        except Exception:
            parsed = {"raw_text": text}

        res["structured"] = parsed
        return res
