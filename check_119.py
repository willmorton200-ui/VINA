import json
with open('D:/VINA/owner_eval/119/mapping.json', encoding='utf-8') as f:
    mapping = json.load(f)
cases = {c['query_id']: c for c in mapping['cases']}

failures = []
with open('D:/VINA/owner_eval/119/predictions.jsonl', encoding='utf-8') as f:
    for line in f:
        p = json.loads(line)
        qid = p['query_id']
        if qid in cases:
            if p['predicted_slug'] != cases[qid]['expected_slug']:
                failures.append({
                    'query_id': qid,
                    'image': cases[qid]['image_path'],
                    'expected': cases[qid]['expected_slug'],
                    'predicted': p['predicted_slug'],
                    'score': p.get('score', 0)
                })

for f in failures[:15]:
    print(f"{f['query_id']} | img: {f['image']} | expected: {f['expected']} | pred: {f['predicted']} | score: {f['score']}")
