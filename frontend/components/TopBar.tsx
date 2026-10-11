"use client";

import Link from "next/link";

import { LanguageSelect } from "./LanguageProvider";

export function TopBar({ children }: { children?: React.ReactNode }) {
  return (
    <header className="topbar">
      <Link className="brand" href="/">
        Dalil<span>DZ</span>
      </Link>
      <div className="top-actions">
        {children}
        <a href="https://github.com/dinogx99/DalilDZ" target="_blank" rel="noreferrer">
          GitHub
        </a>
        <LanguageSelect />
      </div>
    </header>
  );
}
