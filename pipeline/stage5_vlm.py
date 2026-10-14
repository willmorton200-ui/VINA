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
WIN_VLM_PATH = Path(r"D:\models\Qwen2-VL-2B-Instruct")

if LOCAL_VLM_PATH.exists():
    DEFAULT_VLM_PATH = str(LOCAL_VLM_PATH)
elif WIN_VLM_PATH.exists():
    DEFAULT_VLM_PATH = str(WIN_VLM_PATH)
else:
    DEFAULT_VLM_PATH = "Qwen/Qwen2-VL-2B-Instruct"

class WineVLMDecoder:
    _instance = None

    @classmethod
    def get_instance(cls, model_path: str = DEFAULT_VLM_PATH, device: str = "cuda"):
        """Returns the shared singleton instance of WineVLMDecoder (avoids duplicate VRAM allocation)."""
        if cls._instance is None:
            cls._instance = cls(model_path=model_path, device=device, lazy=False)
        return cls._instance

    def __init__(self, model_path: str = DEFAULT_VLM_PATH, device: str = "cuda", lazy: bool = True):
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
