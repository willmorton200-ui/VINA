import cv2
import numpy as np
import requests

# Test on the newly uploaded Castillo de Liria pair
fn = "castillo_liria_pair.jpg"
res = requests.post("http://127.0.0.1:8000/api/process_sample", json={"sample_filename": fn})
print("HTTP Status:", res.status_code)
data = res.json()
print("Selected Source:", data.get("selected_source"))
print("Status:", data.get("decision_status"))
print("Full Text:\n", data.get("full_text"))
print("Raw Words vs Dewarped Words:", data.get("comparison", {}).get("raw", {}).get("num_words"), "vs", data.get("comparison", {}).get("dewarped", {}).get("num_words"))
