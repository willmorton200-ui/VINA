import requests
import json
import os

url = 'http://127.0.0.1:8080/v1/eval/predict'
file_path = r'd:\VINA\owner_eval\119\queries\29afa3fa-4330-4cfa-814e-7c7779053510.jpg'
if not os.path.exists(file_path):
    print("File not found")
else:
    with open(file_path, 'rb') as f:
        files = {'image': f}
        response = requests.post(url, files=files)
        
        try:
            data = response.json()
            print(json.dumps(data, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"Error: {e}, Response: {response.text}")
