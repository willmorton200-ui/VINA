import json

golden = {}
with open(r'D:\VINA\owner_eval\1\predictions.golden.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        data = json.loads(line)
        golden[data['image_path']] = data['predicted_slug']

failed_images = []
with open(r'D:\VINA\owner_eval\1\predictions.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        data = json.loads(line)
        img = data['image_path']
        pred = data['predicted_slug']
        if golden.get(img) != pred:
            failed_images.append(img)

print("Failed images:")
for img in failed_images:
    print(img)
