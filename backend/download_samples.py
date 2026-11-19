#!/usr/bin/env python3
"""
Download sample preview images from freely licensed sources.
These images will be used for instant preview in the Image Studio.
"""
import hashlib
import json
import time
from pathlib import Path
from urllib import request
from urllib.error import HTTPError

# Free, high-quality stock photo URLs from Unsplash
# Unsplash images are freely usable under Unsplash License
SAMPLE_IMAGES = {
    # Photo Styles
    "realistic": {
        "url": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=800&q=80",
        "source": "Unsplash",
        "license": "Unsplash License",
        "photographer": "Joseph Gonzalez"
    },
    "cinematic": {
        "url": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=800&q=80",
        "source": "Unsplash",
        "license": "Unsplash License",
        "photographer": "Ayo Ogunseinde"
    },
    "natural": {
        "url": "https://images.unsplash.com/photo-1531746020798-e6953c6e8e04?w=800&q=80",
        "source": "Unsplash",
        "license": "Unsplash License",
        "photographer": "Ivana Cajina"
    },
    "studio": {
        "url": "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=800&q=80",
        "source": "Unsplash",
        "license": "Unsplash License",
        "photographer": "Amir Geshani"
    },
    "vintage": {
        "url": "https://images.unsplash.com/photo-1496080174650-637e3f22fa03?w=800&q=80",
        "source": "Unsplash",
        "license": "Unsplash License",
        "photographer": "Drew Hays"
    },
    "wedding": {
        "url": "https://images.unsplash.com/photo-1519741497674-611481863552?w=800&q=80",
        "source": "Unsplash",
        "license": "Unsplash License",
        "photographer": "Samantha Gades"
    },
    "fashion": {
        "url": "https://images.unsplash.com/photo-1509631179647-0177331693ae?w=800&q=80",
        "source": "Unsplash",
        "license": "Unsplash License",
        "photographer": "Hannah Morgan"
    },
    "headshot": {
        "url": "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=800&q=80",
        "source": "Unsplash",
        "license": "Unsplash License",
        "photographer": "Christopher Campbell"
    },
    
    # Scenes
    "beach": {
        "url": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=800&q=80",
        "source": "Unsplash",
        "license": "Unsplash License",
        "photographer": "Sean Oulashin"
    },
    "mountain": {
        "url": "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&q=80",
        "source": "Unsplash",
        "license": "Unsplash License",
        "photographer": "Rohit Tandon"
    },
    "waterfall": {
        "url": "https://images.unsplash.com/photo-1432405972618-c60b0225b8f9?w=800&q=80",
        "source": "Unsplash",
        "license": "Unsplash License",
        "photographer": "Rosan Harmens"
    },
    "city": {
        "url": "https://images.unsplash.com/photo-1449824913935-59a10b8d2000?w=800&q=80",
        "source": "Unsplash",
        "license": "Unsplash License",
        "photographer": "Pedro Lastra"
    },
    "temple": {
        "url": "https://images.unsplash.com/photo-1548013146-72479768bada?w=800&q=80",
        "source": "Unsplash",
        "license": "Unsplash License",
        "photographer": "Sonika Agarwal"
    },
    "garden": {
        "url": "https://images.unsplash.com/photo-1585320806297-9794b3e4eeae?w=800&q=80",
        "source": "Unsplash",
        "license": "Unsplash License",
        "photographer": "Marek Piwnicki"
    },
    "wedding_scene": {
        "url": "https://images.unsplash.com/photo-1511285560929-80b456fea0bc?w=800&q=80",
        "source": "Unsplash",
        "license": "Unsplash License",
        "photographer": "Samantha Gades"
    },
    "festival": {
        "url": "https://images.unsplash.com/photo-1533174072545-7a4b6ad7a6c3?w=800&q=80",
        "source": "Unsplash",
        "license": "Unsplash License",
        "photographer": "Pablo Heimplatz"
    },
    "indoor": {
        "url": "https://images.unsplash.com/photo-1513584684374-8bab748fbf90?w=800&q=80",
        "source": "Unsplash",
        "license": "Unsplash License",
        "photographer": "Samantha Gades"
    },
    
    # Photo Types
    "passport": {
        "url": "https://images.unsplash.com/photo-1557862921-37829c790f19?w=800&q=80",
        "source": "Unsplash",
        "license": "Unsplash License",
        "photographer": "Jurica Koletić"
    },
    "id_card": {
        "url": "https://images.unsplash.com/photo-1552374196-c4e7ffc6e126?w=800&q=80",
        "source": "Unsplash",
        "license": "Unsplash License",
        "photographer": "Clem Onojeghuo"
    },
    "album": {
        "url": "https://images.unsplash.com/photo-1529626455594-4ff0802cfb7e?w=800&q=80",
        "source": "Unsplash",
        "license": "Unsplash License",
        "photographer": "Allef Vinicius"
    },
    "social": {
        "url": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=800&q=80",
        "source": "Unsplash",
        "license": "Unsplash License",
        "photographer": "Monika Kozub"
    },
    "poster": {
        "url": "https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?w=800&q=80",
        "source": "Unsplash",
        "license": "Unsplash License",
        "photographer": "Aiony Haust"
    }
}

def download_image(key: str, info: dict, output_dir: Path) -> dict:
    """Download an image and return manifest entry."""
    url = info["url"]
    ext = "jpg"
    output_file = output_dir / f"{key}.{ext}"
    
    print(f"Downloading {key}...")
    
    try:
        # Download with User-Agent to avoid 403 errors
        req = request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with request.urlopen(req, timeout=30) as response:
            data = response.read()
        
        # Write file
        output_file.write_bytes(data)
        
        # Calculate hash for integrity
        file_hash = hashlib.sha256(data).hexdigest()[:16]
        file_size = len(data)
        
        print(f"  ✓ Downloaded {file_size} bytes to {output_file.name}")
        
        return {
            "filename": output_file.name,
            "key": key,
            "source": info["source"],
            "source_url": url,
            "license": info["license"],
            "photographer": info.get("photographer", "Unknown"),
            "hash": file_hash,
            "size_bytes": file_size
        }
    except HTTPError as e:
        print(f"  ✗ HTTP Error {e.code}: {e.reason}")
        return None
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return None


def main():
    # Setup paths
    script_dir = Path(__file__).parent
    preview_dir = script_dir / "preview_images"
    preview_dir.mkdir(exist_ok=True)
    
    manifest = {
        "version": "1.0",
        "description": "Sample preview images for AI Creative Studio",
        "license_info": "All images are from Unsplash and are freely usable under the Unsplash License (https://unsplash.com/license)",
        "images": []
    }
    
    # Download all images
    for key, info in SAMPLE_IMAGES.items():
        entry = download_image(key, info, preview_dir)
        if entry:
            manifest["images"].append(entry)
        time.sleep(0.5)  # Be nice to the server
    
    # Write manifest
    manifest_file = preview_dir / "manifest.json"
    manifest_file.write_text(json.dumps(manifest, indent=2))
    
    print(f"\n✓ Downloaded {len(manifest['images'])} images")
    print(f"✓ Manifest saved to {manifest_file}")


if __name__ == "__main__":
    main()
