import urllib.request
import json

golden = {json.loads(line)['query_id']: json.loads(line) for line in open('D:/VINA/owner_eval/1/predictions.golden.jsonl')}
correct = 0

for q_id, g in golden.items():
    img_path = 'D:/VINA/owner_eval/1/queries/' + g['image_path']
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
    
    try:
        resp = urllib.request.urlopen(req)
        res_json = json.loads(resp.read().decode('utf-8'))
        pred = res_json.get('slug')
    except Exception as e:
        print('Error:', e)
        pred = None
        
    if pred == g['predicted_slug']:
        correct += 1
    else:
        print('Wrong:', q_id, 'Expected:', g['predicted_slug'], 'Got:', pred)

print('Total correct:', correct, 'out of', len(golden))
