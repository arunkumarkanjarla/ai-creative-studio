
from pathlib import Path
import time

from optimum.intel import OVStableDiffusionPipeline

BASE_DIR = Path(__file__).resolve().parent.parent

MODEL_ID = "SG161222/Realistic_Vision_V6.0_B1_noVAE"

OUTPUT_DIR = (
    BASE_DIR
    / "models"
    / "realistic-vision-v6-openvino"
)

print("Starting Realistic Vision V6.0 conversion...")
print(f"Source model: {MODEL_ID}")
print(f"Output folder: {OUTPUT_DIR}")

if OUTPUT_DIR.exists() and (OUTPUT_DIR / "model_index.json").exists():
    print("OpenVINO model already exists.")
    print("Skipping conversion.")
    raise SystemExit(0)

start_time = time.time()

print("Downloading and converting model...")

pipe = OVStableDiffusionPipeline.from_pretrained(
    MODEL_ID,
    export=True,
    device="GPU",
    compile=False
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("Saving OpenVINO model...")

pipe.save_pretrained(str(OUTPUT_DIR))

print("Conversion completed successfully!")
print(f"Model saved at: {OUTPUT_DIR}")
print(f"Total time: {time.time() - start_time:.2f} seconds")
