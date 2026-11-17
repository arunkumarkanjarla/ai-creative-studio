export type ThemeId = "default" | "dark" | "light" | "ocean" | "sunset";
export type FontId = "inter" | "poppins" | "space" | "nunito" | "serif";

export interface ThemeOption {
  id: ThemeId;
  label: string;
  description: string;
  preview: string;
}

export interface FontOption {
  id: FontId;
  label: string;
  family: string;
}

export const THEME_OPTIONS: ThemeOption[] = [
  {
    id: "default",
    label: "Studio",
    description: "Current purple studio look",
    preview: "#7952e8",
  },
  {
    id: "dark",
    label: "Dark",
    description: "High-contrast dark mode",
    preview: "#111827",
  },
  {
    id: "light",
    label: "Light",
    description: "Bright readable light mode",
    preview: "#f8fafc",
  },
  {
    id: "ocean",
    label: "Ocean",
    description: "Cool blue creative theme",
    preview: "#0ea5e9",
  },
  {
    id: "sunset",
    label: "Sunset",
    description: "Warm coral creative theme",
    preview: "#f97316",
  },
];

export const FONT_OPTIONS: FontOption[] = [
  {
    id: "inter",
    label: "Inter",
    family: '"Inter", system-ui, sans-serif',
  },
  {
    id: "poppins",
    label: "Poppins",
    family: '"Poppins", system-ui, sans-serif',
  },
  {
    id: "space",
    label: "Space Grotesk",
    family: '"Space Grotesk", system-ui, sans-serif',
  },
  {
    id: "nunito",
    label: "Nunito",
    family: '"Nunito", system-ui, sans-serif',
  },
  {
    id: "serif",
    label: "Source Serif",
    family: '"Source Serif 4", Georgia, serif',
  },
];

export type FontSizePreset = "small" | "medium" | "large";

export interface FontSizeOption {
  id: FontSizePreset;
  label: string;
  px: number;
}

export const FONT_SIZE_OPTIONS: FontSizeOption[] = [
  { id: "small", label: "Small", px: 12 },
  { id: "medium", label: "Medium", px: 14 },
  { id: "large", label: "Large", px: 16 },
];

export const FONT_SIZE_MIN = 11;
export const FONT_SIZE_MAX = 20;
export const FONT_SIZE_DEFAULT = 14;

export const THEME_STORAGE_KEY = "acs_theme_id";
export const FONT_STORAGE_KEY = "acs_font_id";
export const FONT_SIZE_STORAGE_KEY = "acs_font_size_px";
