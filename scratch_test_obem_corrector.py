import re

test_words = [
    "05bEM", "05bEM 0.7", "O5bEM 0,75L", "05ЬЕМ", "О5ЬЕМ", "05BEM", "ОБbЕМ", "ОБЬЕМ 0.75"
]

pattern = re.compile(r"\b[0OoОо][5БбBbВв][bьъЬЪBв][EeЕе][MmМм]\b")

for w in test_words:
    res = pattern.sub("ОБЪЕМ", w)
    print(f"Original: '{w}' -> Corrected: '{res}'")
