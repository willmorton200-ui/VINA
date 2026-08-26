"""
Cylindrical Dewarping & OCR Pipeline CLI
Usage:
    python run_pipeline.py --input path/to/bottle.jpg --output_dir path/to/results
    python run_pipeline.py --input_dir test_dataset/cam --output_dir outputs --save_intermediate True
"""

import argparse
import os
import glob
import cv2
import json
from pipeline import CylindricalDewarpEngine, compute_image_metrics

def main():
    parser = argparse.ArgumentParser(description="Cylindrical Dewarping & OCR Pipeline")
    parser.add_argument("--input", type=str, help="Path to a single curved container image")
    parser.add_argument("--input_dir", type=str, help="Directory with multiple images (batch mode)")
    parser.add_argument("--output_dir", type=str, default="outputs", help="Directory to save results")
    parser.add_argument("--catalog_dir", type=str, default="test_dataset/calalog", help="Optional catalog images folder for metric comparison")
    parser.add_argument("--save_intermediate", type=str, default="True", help="Save intermediate stage artifacts (True/False)")
    parser.add_argument("--no_gpu", action="store_true", help="Disable GPU acceleration")
    args = parser.parse_args()

    save_intermediate = args.save_intermediate.lower() in ["true", "1", "yes"]
    use_gpu = not args.no_gpu

    print("==================================================================")
    print(" VINA Cylindrical Dewarping & OCR System")
    print(f" Mode: {'GPU (CUDA)' if use_gpu else 'CPU'}")
    print("==================================================================")

    engine = CylindricalDewarpEngine(use_gpu=use_gpu)
    os.makedirs(args.output_dir, exist_ok=True)

    # Collect images
    image_paths = []
    if args.input:
        if os.path.isdir(args.input):
            for ext in ["*.jpg", "*.jpeg", "*.png", "*.JPG", "*.PNG"]:
                image_paths.extend(glob.glob(os.path.join(args.input, ext)))
        else:
            image_paths.append(args.input)
    elif args.input_dir:
        for ext in ["*.jpg", "*.jpeg", "*.png", "*.JPG", "*.PNG"]:
            image_paths.extend(glob.glob(os.path.join(args.input_dir, ext)))
    else:
        print("Please provide --input or --input_dir. Example: python run_pipeline.py --input test_dataset/butilki")
        return

    image_paths = sorted(list(set(image_paths)))
    print(f"Found {len(image_paths)} images to process.\n")

    summary_results = []
    for idx, path in enumerate(image_paths, 1):
        filename = os.path.basename(path)
        base_name, _ = os.path.splitext(filename)
        print(f"[{idx}/{len(image_paths)}] Processing: {filename}...")

        img_bgr = cv2.imread(path)
        if img_bgr is None:
            print(f"  [ERROR] Failed to read {path}")
            continue

        # Look for matching reference catalog image
        ref_bgr = None
        if args.catalog_dir and os.path.exists(args.catalog_dir):
            # Extract id prefix e.g. "268"
            prefix = base_name.split('_')[0]
            cat_matches = glob.glob(os.path.join(args.catalog_dir, f"{prefix}_*"))
            if cat_matches:
                ref_bgr = cv2.imread(cat_matches[0])

        item_out_dir = os.path.join(args.output_dir, base_name) if save_intermediate else args.output_dir
        res = engine.process_image(img_bgr, reference_bgr=ref_bgr, save_dir=item_out_dir if save_intermediate else None)

        # Primary output is saved inside process_image if save_intermediate is True

        print(f"  -> Flattened scan generated. Extracted {res['num_words']} text tokens. Total time: {res['timings']['total_ms']}ms")
        if res.get("metrics"):
            print(f"  -> Metric SSIM: {res['metrics'].get('ssim')}, MSE: {res['metrics'].get('mse')}")

        summary_results.append({
            "filename": filename,
            "timings": res["timings"],
            "metrics": res["metrics"],
            "num_words": res["num_words"],
            "full_text": res["full_text"],
            "barcodes": res["barcodes"]
        })

    # Save batch summary
    summary_path = os.path.join(args.output_dir, "batch_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary_results, f, ensure_ascii=False, indent=2)

    print("\n==================================================================")
    print(f"Processing complete! Results saved to: {os.path.abspath(args.output_dir)}")
    print(f"Summary JSON: {summary_path}")
    print("==================================================================")

if __name__ == "__main__":
    main()
