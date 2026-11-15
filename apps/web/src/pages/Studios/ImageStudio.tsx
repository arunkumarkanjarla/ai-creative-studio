
import { Image } from "lucide-react";

export default function ImageStudio() {
  return (
    <div className="content-page">
      <div className="studio-heading">
        <Image size={36} />
        <div>
          <h1>Image Studio</h1>
          <p>Create images using open-source AI models.</p>
        </div>
      </div>

      <div className="generation-card">
        <h3>Text to Image</h3>
        <textarea
          placeholder="Describe the image you want to generate..."
          rows={5}
        />

        <button className="primary-button" disabled>
          Generate Image — Coming Soon
        </button>
      </div>
    </div>
  );
}
