import os
import shutil
import json
import pandas as pd

def create_tasks():
    eval_dir = "D:/Eval"
    owner_eval_dir = "D:/VINA/owner_eval"
    queries_tsv = os.path.join(eval_dir, "queries.tsv")

    if not os.path.exists(queries_tsv):
        print(f"File not found: {queries_tsv}")
        return

    df = pd.read_csv(queries_tsv, sep='\t')
    batch_size = 25

    for i in range(0, len(df), batch_size):
        batch = df.iloc[i:i+batch_size]
        part_num = i // batch_size + 1
        part_dir = os.path.join(owner_eval_dir, f"part_{part_num}")
        queries_dir = os.path.join(part_dir, "queries")
        
        os.makedirs(queries_dir, exist_ok=True)
        
        cases = []
        for _, row in batch.iterrows():
            q_id = row['query_id']
            img_path = row['image_path']
            
            src_img = os.path.join(eval_dir, "queries", img_path)
            dst_img = os.path.join(queries_dir, img_path)
            if os.path.exists(src_img):
                shutil.copy2(src_img, dst_img)
            else:
                print(f"Warning: Image not found {src_img}")
                
            cases.append({
                "query_id": q_id,
                "expected_slug": "",
                "image_path": img_path
            })
            
        mapping = {
            "positive_count": len(cases),
            "cases": cases
        }
        
        with open(os.path.join(part_dir, "mapping.json"), 'w', encoding='utf-8') as f:
            json.dump(mapping, f, indent=2, ensure_ascii=False)
            
    print(f"Successfully created {len(df) // batch_size + (1 if len(df) % batch_size != 0 else 0)} tasks in {owner_eval_dir}")

if __name__ == "__main__":
    create_tasks()
