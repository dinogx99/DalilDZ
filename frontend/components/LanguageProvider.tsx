"use client";

import { createContext, useContext, useEffect, useState } from "react";

import { copy, LANGS, type Copy, type Lang } from "../lib/i18n";

type LanguageState = { lang: Lang; setLang: (lang: Lang) => void; t: Copy };

const STORAGE_KEY = "dalildz.lang";
const LanguageContext = createContext<LanguageState | null>(null);

function isLang(value: string | null): value is Lang {
  return value === "en" || value === "fr" || value === "ar";
}

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Lang>("en");

  useEffect(() => {
    let stored: string | null = null;
    try {
      stored = window.localStorage.getItem(STORAGE_KEY);
    } catch {
      // Storage can be unavailable (private mode); fall back to the browser language.
    }
    if (isLang(stored)) {
      setLangState(stored);
      return;
    }
    const browser = navigator.language.toLowerCase();
    if (browser.startsWith("ar")) setLangState("ar");
    else if (browser.startsWith("fr")) setLangState("fr");
  }, []);

  useEffect(() => {
    document.documentElement.lang = lang;
    document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
  }, [lang]);

  function setLang(next: Lang) {
    setLangState(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // Ignore storage failures; the choice still applies to this page view.
    }
  }

  return <LanguageContext.Provider value={{ lang, setLang, t: copy[lang] }}>{children}</LanguageContext.Provider>;
}

export function useLanguage(): LanguageState {
  const value = useContext(LanguageContext);
  if (!value) throw new Error("useLanguage must be used inside LanguageProvider");
  return value;
}

export function LanguageSelect() {
  const { lang, setLang } = useLanguage();
  return (
    <select value={lang} onChange={(event) => setLang(event.target.value as Lang)} aria-label="Language">
      {LANGS.map((item) => (
        <option key={item.code} value={item.code}>
          {item.label}
        </option>
      ))}
    </select>
  );
}
