import requests

url = "http://127.0.0.1:8080/v1/eval/predict"
img_path = r"D:\VINA\owner_eval\1\queries\e3f116c0.jpeg"
with open(img_path, 'rb') as f:
    files = {'image': f}
    data = {'expected_slug': 'test', 'expected_name': 'test'}
    response = requests.post(url, files=files, data=data)
    print("Status:", response.status_code)
    try:
        print("Response:", response.json())
    except Exception as e:
        print("Response text:", response.text)
