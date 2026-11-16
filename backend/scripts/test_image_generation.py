
from pathlib import Path
from optimum.intel import OVStableDiffusionPipeline
import time

# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "models" / "stable-diffusion-v1-5-openvino"
OUTPUT_DIR = BASE_DIR / "generated_images"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODEL_ID = "stable-diffusion-v1-5/stable-diffusion-v1-5"

print("Loading Stable Diffusion 1.5...")
print("First run downloads and converts the model.")

start_time = time.time()

if MODEL_DIR.exists() and (MODEL_DIR / "model_index.json").exists():
    print("Loading locally saved OpenVINO model...")
    pipe = OVStableDiffusionPipeline.from_pretrained(
        str(MODEL_DIR),
        device="GPU",
        compile=False
    )
else:
    print("Downloading and converting model to OpenVINO...")
    pipe = OVStableDiffusionPipeline.from_pretrained(
        MODEL_ID,
        export=True,
        device="GPU",
        compile=False
    )

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    pipe.save_pretrained(str(MODEL_DIR))
    print("OpenVINO model saved successfully.")

print("Compiling model...")
pipe.reshape(1, 512, 512, 1)
pipe.compile()

prompt = (
    "A beautiful futuristic smart city at sunset, "
    "cinematic lighting, ultra detailed, realistic architecture, "
    "professional digital art"
)

print("Generating image...")

result = pipe(
    prompt,
    height=512,
    width=512,
    num_inference_steps=20,
    guidance_scale=7.0,
    num_images_per_prompt=1
)

timestamp = time.strftime("%Y%m%d_%H%M%S")
output_file = OUTPUT_DIR / f"generated_image_{timestamp}.png"
result.images[0].save(output_file)

print(f"Image saved: {output_file}")
print(f"Total time: {time.time() - start_time:.2f} seconds")
