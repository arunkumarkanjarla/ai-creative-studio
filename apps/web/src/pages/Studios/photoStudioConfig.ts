export type StudioToolId =
  | "text_to_image"
  | "image_to_image"
  | "person_in_scene"
  | "face_swap"
  | "face_merge"
  | "background_change"
  | "object_replace"
  | "remove_background"
  | "upscale"
  | "restore"
  | "photo_to_artwork";

export interface StudioTool {
  id: StudioToolId;
  label: string;
  guestAllowed: boolean;
  needsImage1: boolean;
  needsImage2: boolean;
  badge?: string;
  description: string;
}

export const CREATE_TOOLS: StudioTool[] = [
  {
    id: "text_to_image",
    label: "Text to Image",
    guestAllowed: true,
    needsImage1: false,
    needsImage2: false,
    description: "Generate images from a text prompt.",
  },
  {
    id: "image_to_image",
    label: "Image to Image",
    guestAllowed: false,
    needsImage1: true,
    needsImage2: false,
    description: "Transform an uploaded photo with a prompt.",
  },
  {
    id: "person_in_scene",
    label: "Person in Scene",
    guestAllowed: false,
    needsImage1: true,
    needsImage2: true,
    badge: "New",
    description: "Place Person 2 into the scene from Photo 1.",
  },
  {
    id: "face_swap",
    label: "Face Swap",
    guestAllowed: false,
    needsImage1: true,
    needsImage2: true,
    description: "Replace the face in Photo 1 with the face from Photo 2.",
  },
  {
    id: "face_merge",
    label: "Face Merge",
    guestAllowed: false,
    needsImage1: true,
    needsImage2: true,
    description: "Blend facial characteristics from both photos.",
  },
  {
    id: "background_change",
    label: "Background Change",
    guestAllowed: false,
    needsImage1: true,
    needsImage2: false,
    description: "Keep the person and change only the background.",
  },
  {
    id: "object_replace",
    label: "Object Replace",
    guestAllowed: false,
    needsImage1: true,
    needsImage2: false,
    description: "Replace a selected object described in your prompt.",
  },
  {
    id: "remove_background",
    label: "Remove Background",
    guestAllowed: false,
    needsImage1: true,
    needsImage2: false,
    description: "Remove the background for a clean cutout.",
  },
  {
    id: "upscale",
    label: "Upscale & Enhance",
    guestAllowed: false,
    needsImage1: true,
    needsImage2: false,
    description: "Improve sharpness and detail of a photo.",
  },
  {
    id: "restore",
    label: "Restore Old Photo",
    guestAllowed: false,
    needsImage1: true,
    needsImage2: false,
    description: "Restore damaged or faded photos.",
  },
  {
    id: "photo_to_artwork",
    label: "Photo to Artwork",
    guestAllowed: false,
    needsImage1: true,
    needsImage2: false,
    description: "Convert a photo into an art style.",
  },
];

export const DIMENSIONS = [
  { id: "1:1", label: "1:1", width: 512, height: 512, hint: "1024×1024" },
  { id: "3:4", label: "3:4", width: 512, height: 768, hint: "768×1024" },
  { id: "4:3", label: "4:3", width: 768, height: 512, hint: "1024×768" },
  { id: "16:9", label: "16:9", width: 768, height: 512, hint: "1280×720" },
] as const;

export const PHOTO_TYPES = [
  { id: "passport", label: "Passport", hint: "35×45 mm" },
  { id: "id", label: "ID Card", hint: "2×2 inch" },
  { id: "album", label: "Album", hint: "4×6 inch" },
  { id: "social", label: "Social", hint: "1080×1080" },
  { id: "poster", label: "Poster", hint: "A4 / A3" },
] as const;

export const PHOTO_STYLES = [
  "Realistic",
  "Cinematic",
  "Natural",
  "Studio",
  "Vintage",
  "Wedding",
  "Fashion",
  "Headshot",
] as const;

export const SCENES = [
  "Beach",
  "Mountain",
  "Waterfall",
  "City",
  "Temple",
  "Garden",
  "Wedding",
  "Festival",
  "Indoor",
  "Custom",
] as const;

const PHOTO_TYPE_HINTS: Record<string, string> = {
  passport: "passport photo framing, plain backdrop, centered subject",
  id: "ID card photo framing, neutral backdrop, head and shoulders",
  album: "album print composition, natural portrait framing",
  social: "social media photo composition, eye-catching framing",
  poster: "poster composition, bold subject placement",
};

export function buildToolPrompt(
  tool: StudioToolId,
  userPrompt: string,
  style: string,
  scene: string,
  photoType: string = "album"
): string {
  const base = userPrompt.trim();
  const styleBit = style ? `${style.toLowerCase()} photography` : "";
  const sceneBit =
    scene && scene !== "Custom" ? `${scene.toLowerCase()} background` : "";
  const typeBit = PHOTO_TYPE_HINTS[photoType] || "";

  const extras = [styleBit, sceneBit, typeBit].filter(Boolean).join(", ");

  switch (tool) {
    case "background_change":
      return (
        base ||
        `change the background to ${sceneBit || "a clean backdrop"}, keep the same original subject, same details, same composition`
      );
    case "remove_background":
      return "change the background color to white, keep the same original subject, same details, same composition";

    case "face_swap":
      return (
        `${base || "replace the face in image 1 with the face from image 2"}, ` +
        `same pose, same composition, same lighting, photorealistic` +
        (extras ? `, ${extras}` : "")
      );
    case "person_in_scene":
      return (
        `${base || "put person 2 into photo 1"}, keep scene composition, pose and lighting from image 1, photorealistic` +
        (extras ? `, ${extras}` : "")
      );
    case "face_merge":
      return (
        `${base || "blend faces from both photos"}, natural face merge, photorealistic` +
        (extras ? `, ${extras}` : "")
      );
    case "image_to_image":
      return [base, extras].filter(Boolean).join(", ");
    case "object_replace":
      return `${base || "replace the object described"}, keep rest of image same, photorealistic`;
    case "upscale":
      return `${base || "enhance details, sharper, high quality"}, keep same subject and composition`;
    case "restore":
      return `${base || "restore old damaged photo"}, fix scratches, colorize naturally, keep same subject`;
    case "photo_to_artwork":
      return [base || "convert photo to artwork", "artistic style", extras]
        .filter(Boolean)
        .join(", ");
    case "text_to_image":
    default:
      return [base, extras].filter(Boolean).join(", ");
  }
}
