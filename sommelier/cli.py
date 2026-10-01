# -*- coding: utf-8 -*-
"""Консольный диалог с сомелье:  python cli.py   (или python cli.py "запрос")"""
import sys
from sommelier import Sommelier

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

if __name__ == "__main__":
    s = Sommelier()
    if len(sys.argv) > 1:
        print(s.ask(" ".join(sys.argv[1:]))["text"])
    else:
        print("AI-сомелье (каталог: %d вин). Пустая строка — выход, /new — новый разговор." % len(s.wines))
        while True:
            try:
                q = input("\nВы: ").strip()
            except EOFError:
                break
            if not q:
                break
            if q == "/new":
                s.reset(); print("Начали заново."); continue
            print("\nСомелье:", s.ask(q)["text"])
