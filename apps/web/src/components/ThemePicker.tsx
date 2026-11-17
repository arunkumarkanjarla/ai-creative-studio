import { useEffect, useRef, useState } from "react";
import { Check, Minus, Palette, Plus, Type } from "lucide-react";

import { useTheme } from "../context/ThemeContext";
import {
  FONT_OPTIONS,
  FONT_SIZE_MAX,
  FONT_SIZE_MIN,
  FONT_SIZE_OPTIONS,
  THEME_OPTIONS,
} from "../theme/themes";

export default function ThemePicker() {
  const {
    themeId,
    fontId,
    fontSizePx,
    fontSizePreset,
    setThemeId,
    setFontId,
    setFontSizePreset,
    bumpFontSize,
  } = useTheme();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onPointerDown(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onPointerDown);
    return () => document.removeEventListener("mousedown", onPointerDown);
  }, []);

  return (
    <div className="theme-picker" ref={rootRef}>
      <button
        type="button"
        className="theme-picker-trigger"
        aria-expanded={open}
        aria-haspopup="dialog"
        onClick={() => setOpen((value) => !value)}
      >
        <Palette size={16} />
        <span>Theme</span>
      </button>

      {open && (
        <div
          className="theme-picker-panel"
          role="dialog"
          aria-label="Theme settings"
        >
          <div className="theme-picker-section">
            <div className="theme-picker-heading">
              <Palette size={15} />
              <strong>Color theme</strong>
            </div>
            <div className="theme-swatch-grid">
              {THEME_OPTIONS.map((theme) => (
                <button
                  key={theme.id}
                  type="button"
                  title={theme.description}
                  className={`theme-swatch${
                    themeId === theme.id ? " is-active" : ""
                  }`}
                  onClick={() => setThemeId(theme.id)}
                >
                  <span
                    className="theme-swatch-color"
                    style={{ background: theme.preview }}
                  />
                  <strong>{theme.label}</strong>
                  {themeId === theme.id && <Check size={13} />}
                </button>
              ))}
            </div>
          </div>

          <div className="theme-picker-section">
            <div className="theme-picker-heading">
              <Type size={15} />
              <strong>Font</strong>
            </div>
            <div className="theme-font-grid">
              {FONT_OPTIONS.map((font) => (
                <button
                  key={font.id}
                  type="button"
                  className={`theme-font-btn${
                    fontId === font.id ? " is-active" : ""
                  }`}
                  style={{ fontFamily: font.family }}
                  onClick={() => setFontId(font.id)}
                >
                  <span>{font.label}</span>
                  {fontId === font.id && <Check size={13} />}
                </button>
              ))}
            </div>
          </div>

          <div className="theme-picker-section">
            <div className="theme-picker-heading">
              <Type size={15} />
              <strong>Font size</strong>
            </div>

            <div className="theme-size-presets">
              {FONT_SIZE_OPTIONS.map((size) => (
                <button
                  key={size.id}
                  type="button"
                  className={`theme-size-btn${
                    fontSizePreset === size.id ? " is-active" : ""
                  }`}
                  onClick={() => setFontSizePreset(size.id)}
                >
                  {size.label}
                </button>
              ))}
            </div>

            <div className="theme-size-stepper">
              <button
                type="button"
                className="theme-size-step"
                aria-label="Decrease font size"
                disabled={fontSizePx <= FONT_SIZE_MIN}
                onClick={() => bumpFontSize(-1)}
              >
                <Minus size={14} />
              </button>
              <span className="theme-size-value">{fontSizePx}px</span>
              <button
                type="button"
                className="theme-size-step"
                aria-label="Increase font size"
                disabled={fontSizePx >= FONT_SIZE_MAX}
                onClick={() => bumpFontSize(1)}
              >
                <Plus size={14} />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
