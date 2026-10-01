import urllib.request
import json

img_path = 'D:/VINA/owner_eval/119/queries/8f0d7e35-2cfb-4a00-95ad-12cc38571d42.jpg'
with open(img_path, 'rb') as f:
    img_data = f.read()

boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
body = (
    f'--{boundary}\r\n'
    f'Content-Disposition: form-data; name="image"; filename="image.jpg"\r\n'
    f'Content-Type: image/jpeg\r\n\r\n'
).encode('utf-8') + img_data + f'\r\n--{boundary}--\r\n'.encode('utf-8')

req = urllib.request.Request('http://127.0.0.1:8080/v1/eval/predict', data=body)
req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')

resp = urllib.request.urlopen(req)
res_json = json.loads(resp.read().decode('utf-8'))
print('Result for 119:', res_json.get('slug'))
