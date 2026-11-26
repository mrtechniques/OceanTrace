#!/usr/bin/env python3
"""
OceanTrace — CLI for Satellite SAR Oil Spill Detection.

Usage:
    python scripts/predict_spill.py --input path/to/sar_scene.tif [options]
    python scripts/predict_spill.py --input path/to/image.png --threshold 0.5 --save-overlay output.png
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

# Add project root to sys.path so 'src' can be imported cleanly
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PIL import Image

from src.detection.segmentation.predict import predict_oil_spill
from src.detection.utils.visualization import (
    create_prediction_figure,
    save_prediction_visualization,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("predict_spill")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="OceanTrace: Satellite SAR Oil Spill Detection & Inference CLI",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-i", "--input",
        required=True,
        type=str,
        help="Path to input SAR scene or image (PNG, JPG, JPEG, GeoTIFF).",
    )
    parser.add_argument(
        "-m", "--model-path",
        type=str,
        default="models/best_oil_spill_unet.pth",
        help="Path to trained PyTorch ResNet34 U-Net checkpoint (.pth).",
    )
    parser.add_argument(
        "-o", "--output-dir",
        type=str,
        default="data/processed/masks",
        help="Directory to save generated mask and metadata files.",
    )
    parser.add_argument(
        "-t", "--threshold",
        type=float,
        default=0.5,
        help="Probability threshold for positive oil spill classification.",
    )
    parser.add_argument(
        "--norm",
        type=str,
        default="percentile",
        choices=["percentile", "minmax", "imagenet", "zscore", "none"],
        help="Normalization method applied to the input imagery.",
    )
    parser.add_argument(
        "--tile-size",
        type=int,
        default=512,
        help="Patch tile dimension for tiled inference on large satellite scenes.",
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=64,
        help="Overlap in pixels between adjacent tiles for seamless blending.",
    )
    parser.add_argument(
        "--force-tile",
        action="store_true",
        help="Force tiled inference even if the image is smaller than tile-size.",
    )
    parser.add_argument(
        "--force-direct",
        action="store_true",
        help="Force direct (single-patch) inference without tiling.",
    )
    parser.add_argument(
        "--device",
        type=str,
        default=None,
        choices=["cpu", "cuda", None],
        help="Computation device ('cpu' or 'cuda'). Defaults to auto-detection.",
    )
    parser.add_argument(
        "--save-overlay",
        type=str,
        default=None,
        help="Custom path to save the 3-panel visualization figure (PNG).",
    )
    parser.add_argument(
        "--benchmark",
        type=int,
        default=0,
        help="Run N benchmark iterations to accurately measure average inference latency.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        logger.error("Input file not found: %s", input_path.resolve())
        return 1

    model_path = Path(args.model_path)
    if not model_path.exists():
        logger.error("Model checkpoint not found: %s", model_path.resolve())
        return 1

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    use_tiling = None
    if args.force_tile:
        use_tiling = True
    elif args.force_direct:
        use_tiling = False

    logger.info("Running OceanTrace oil spill inference on: %s", input_path.name)
    logger.info("Using checkpoint: %s", model_path.name)
    logger.info("Normalization: %s | Threshold: %.2f", args.norm, args.threshold)

    # 1. Primary inference run
    res = predict_oil_spill(
        image_input=input_path,
        checkpoint_path=model_path,
        device=args.device,
        threshold=args.threshold,
        norm_method=args.norm,
        tile_size=args.tile_size,
        overlap=args.overlap,
        use_tiling=use_tiling,
    )

    # 2. Benchmark if requested
    benchmark_avg_ms = None
    if args.benchmark > 0:
        logger.info("Running %d benchmark iterations...", args.benchmark)
        latencies = []
        for _ in range(args.benchmark):
            t0 = time.perf_counter()
            _ = predict_oil_spill(
                image_input=input_path,
                checkpoint_path=model_path,
                device=args.device,
                threshold=args.threshold,
                norm_method=args.norm,
                tile_size=args.tile_size,
                overlap=args.overlap,
                use_tiling=use_tiling,
            )
            latencies.append((time.perf_counter() - t0) * 1000.0)
        benchmark_avg_ms = sum(latencies) / len(latencies)
        res.metadata["benchmark_iterations"] = args.benchmark
        res.metadata["benchmark_avg_latency_ms"] = round(benchmark_avg_ms, 2)

    # 3. Save binary mask as PNG
    stem = input_path.stem
    mask_out_path = out_dir / f"{stem}_mask.png"
    mask_png = Image.fromarray((res.binary_mask * 255).astype("uint8"))
    mask_png.save(mask_out_path)
    logger.info("Saved binary spill mask to: %s", mask_out_path)

    # 4. Save metadata JSON
    meta_out_path = out_dir / f"{stem}_metadata.json"
    with open(meta_out_path, "w", encoding="utf-8") as f:
        # Convert non-serializable items
        clean_meta = {
            k: (v if isinstance(v, (int, float, str, bool, list, dict, type(None))) else str(v))
            for k, v in res.metadata.items()
        }
        json.dump(clean_meta, f, indent=2)
    logger.info("Saved inference metadata to: %s", meta_out_path)

    # 5. Generate and save 3-panel visualization
    overlay_out_path = (
        Path(args.save_overlay) if args.save_overlay else out_dir / f"{stem}_detection_overlay.png"
    )
    fig = create_prediction_figure(
        original_image=res.original_image,
        probability_map=res.probability_map,
        binary_mask=res.binary_mask,
        metadata=res.metadata,
    )
    save_prediction_visualization(fig, overlay_out_path)
    logger.info("Saved 3-panel visualization overlay to: %s", overlay_out_path)

    # 6. Console summary
    print("\n" + "=" * 60)
    print("           OCEANTRACE DETECTION SUMMARY")
    print("=" * 60)
    print(f" Input Image:       {input_path.name} ({res.metadata['input_dimensions'][0]}x{res.metadata['input_dimensions'][1]})")
    print(f" Target Device:     {res.metadata['device']}")
    print(f" Spill Detected:    {'YES' if res.spill_detected else 'NO'}")
    print(f" Spill Pixel Count: {res.spill_pixel_count:,} pixels")
    print(f" Area Coverage:     {res.metadata['spill_coverage_percentage']:.2f}%")
    print(f" Inference Latency: {res.metadata['inference_time_ms']:.1f} ms")
    if benchmark_avg_ms:
        print(f" Benchmark Avg:     {benchmark_avg_ms:.1f} ms ({args.benchmark} runs)")
    print(f" Probability Range: [{res.metadata['prob_min']:.4f}, {res.metadata['prob_max']:.4f}]")
    print(f" Output Mask:       {mask_out_path}")
    print(f" Output Overlay:    {overlay_out_path}")
    print("=" * 60 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
