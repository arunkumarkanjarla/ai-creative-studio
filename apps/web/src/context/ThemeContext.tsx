import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import {
  FONT_OPTIONS,
  FONT_SIZE_DEFAULT,
  FONT_SIZE_MAX,
  FONT_SIZE_MIN,
  FONT_SIZE_OPTIONS,
  FONT_SIZE_STORAGE_KEY,
  FONT_STORAGE_KEY,
  THEME_OPTIONS,
  THEME_STORAGE_KEY,
  type FontId,
  type FontSizePreset,
  type ThemeId,
} from "../theme/themes";

interface ThemeContextType {
  themeId: ThemeId;
  fontId: FontId;
  fontSizePx: number;
  fontSizePreset: FontSizePreset | "custom";
  setThemeId: (id: ThemeId) => void;
  setFontId: (id: FontId) => void;
  setFontSizePx: (px: number) => void;
  setFontSizePreset: (preset: FontSizePreset) => void;
  bumpFontSize: (delta: number) => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

function clampFontSize(px: number) {
  return Math.min(FONT_SIZE_MAX, Math.max(FONT_SIZE_MIN, Math.round(px)));
}

function readStoredTheme(): ThemeId {
  const value = localStorage.getItem(THEME_STORAGE_KEY);
  if (THEME_OPTIONS.some((item) => item.id === value)) {
    return value as ThemeId;
  }
  return "default";
}

function readStoredFont(): FontId {
  const value = localStorage.getItem(FONT_STORAGE_KEY);
  if (FONT_OPTIONS.some((item) => item.id === value)) {
    return value as FontId;
  }
  return "inter";
}

function readStoredFontSize(): number {
  const raw = localStorage.getItem(FONT_SIZE_STORAGE_KEY);
  const parsed = Number(raw);
  if (Number.isFinite(parsed)) {
    return clampFontSize(parsed);
  }
  return FONT_SIZE_DEFAULT;
}

function presetFromPx(px: number): FontSizePreset | "custom" {
  const match = FONT_SIZE_OPTIONS.find((item) => item.px === px);
  return match ? match.id : "custom";
}

function applyTheme(themeId: ThemeId, fontId: FontId, fontSizePx: number) {
  const root = document.documentElement;
  root.setAttribute("data-theme", themeId);
  root.setAttribute("data-font", fontId);
  root.setAttribute("data-font-size", String(fontSizePx));

  const font = FONT_OPTIONS.find((item) => item.id === fontId);
  if (font) {
    root.style.setProperty("--font-sans", font.family);
  }

  root.style.setProperty("--app-font-size", `${fontSizePx}px`);
  root.style.setProperty(
    "--ui-scale",
    String(Number((fontSizePx / FONT_SIZE_DEFAULT).toFixed(3)))
  );
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [themeId, setThemeIdState] = useState<ThemeId>(() => readStoredTheme());
  const [fontId, setFontIdState] = useState<FontId>(() => readStoredFont());
  const [fontSizePx, setFontSizePxState] = useState<number>(() =>
    readStoredFontSize()
  );

  useEffect(() => {
    applyTheme(themeId, fontId, fontSizePx);
    localStorage.setItem(THEME_STORAGE_KEY, themeId);
    localStorage.setItem(FONT_STORAGE_KEY, fontId);
    localStorage.setItem(FONT_SIZE_STORAGE_KEY, String(fontSizePx));
  }, [themeId, fontId, fontSizePx]);

  const value = useMemo(
    () => ({
      themeId,
      fontId,
      fontSizePx,
      fontSizePreset: presetFromPx(fontSizePx),
      setThemeId: (id: ThemeId) => setThemeIdState(id),
      setFontId: (id: FontId) => setFontIdState(id),
      setFontSizePx: (px: number) => setFontSizePxState(clampFontSize(px)),
      setFontSizePreset: (preset: FontSizePreset) => {
        const option = FONT_SIZE_OPTIONS.find((item) => item.id === preset);
        if (option) setFontSizePxState(option.px);
      },
      bumpFontSize: (delta: number) =>
        setFontSizePxState((current) => clampFontSize(current + delta)),
    }),
    [themeId, fontId, fontSizePx]
  );

  return (
    <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used inside ThemeProvider");
  }
  return context;
}
