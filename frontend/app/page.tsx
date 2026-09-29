"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import type { CaseRecord } from "../lib/api";
import { jsonFetch } from "../lib/api";
import { copy, type Lang } from "../lib/i18n";

export default function Home() {
  const router = useRouter();
  const [lang, setLang] = useState<Lang>("en");
  const [cases, setCases] = useState<CaseRecord[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const t = copy[lang];

  useEffect(() => {
    const browser = navigator.language.toLowerCase();
    if (browser.startsWith("ar")) setLang("ar");
    else if (browser.startsWith("fr")) setLang("fr");
    jsonFetch<{ items: CaseRecord[] }>("/api/v1/cases?limit=8")
      .then((result) => setCases(result.items))
      .catch(() => undefined);
  }, []);

  async function createCase(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const data = new FormData(event.currentTarget);
    const name = String(data.get("name") || "").trim();
    const claims: Record<string, string> = { legal_name: name };
    for (const field of ["rc", "nif", "website", "wilaya"]) {
      const value = String(data.get(field) || "").trim();
      if (value) claims[field] = value;
    }
    try {
      const created = await jsonFetch<CaseRecord>("/api/v1/cases", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ name, claims }),
      });
      router.push(`/cases/${created.id}`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to create case");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="shell" dir={lang === "ar" ? "rtl" : "ltr"}>
      <header className="topbar">
        <a className="brand" href="/">Dalil<span>DZ</span></a>
        <div className="top-actions">
          <a href="https://github.com/dinogx99/DalilDZ" target="_blank">GitHub</a>
          <select value={lang} onChange={(event) => setLang(event.target.value as Lang)} aria-label="Language">
            <option value="ar">العربية</option>
            <option value="fr">Français</option>
            <option value="en">English</option>
          </select>
        </div>
      </header>

      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">OPEN SOURCE · ALGERIA · EVIDENCE FIRST</p>
          <h1>{t.headline}</h1>
          <p className="lede">{t.subhead}</p>
          <div className="principle">
            <strong>DalilDZ ≠ fraud detector</strong>
            <span>It explains what was checked, against what, when, by which method, and with which result.</span>
          </div>
        </div>

        <article className="create-card">
          <p className="eyebrow">{t.start}</p>
          <h2>{t.tagline}</h2>
          <form onSubmit={createCase} className="case-form">
            <label>{t.company}<input name="name" required /></label>
            <div className="form-grid">
              <label>{t.rc}<input name="rc" /></label>
              <label>{t.nif}<input name="nif" /></label>
            </div>
            <div className="form-grid">
              <label>{t.website}<input name="website" placeholder="https://example.dz" /></label>
              <label>{t.wilaya}<input name="wilaya" /></label>
            </div>
            <button disabled={busy}>{busy ? "…" : t.create}</button>
          </form>
          {error && <p className="error">{error}</p>}
        </article>
      </section>

      <section className="principles-grid">
        <article><span className="index">01</span><h3>{t.evidenceFirst}</h3><p>{t.evidenceText}</p></article>
        <article><span className="index">02</span><h3>{t.deterministic}</h3><p>{t.deterministicText}</p></article>
        <article><span className="index">03</span><h3>{t.sourceFailure}</h3><p>{t.sourceFailureText}</p></article>
      </section>

      <section className="workflow">
        <div className="section-head">
          <div><p className="eyebrow">HOW IT WORKS</p><h2>Claims → evidence → checks → report</h2></div>
        </div>
        <ol className="workflow-steps">
          <li><b>01</b><span>Submit identity claims</span><small>RC · NIF · name · legal form · website · wilaya</small></li>
          <li><b>02</b><span>Add documents</span><small>Direct PDF extraction first; OCR only when required</small></li>
          <li><b>03</b><span>Collect public evidence</span><small>Website · DNS · TLS · RDAP · manual official verification</small></li>
          <li><b>04</b><span>Run deterministic checks</span><small>Exact identifiers and explainable normalized comparisons</small></li>
          <li><b>05</b><span>Export auditable report</span><small>JSON · CSV · printable HTML · immutable input fingerprint</small></li>
        </ol>
      </section>

      <section className="recent">
        <div className="section-head"><div><p className="eyebrow">WORKSPACE</p><h2>{t.recent}</h2></div><span>{cases.length}</span></div>
        <div className="case-list">
          {cases.map((item) => (
            <a key={item.id} href={`/cases/${item.id}`} className="case-row">
              <div><strong>{item.name}</strong><p>{Object.keys(item.claims).join(" · ") || "No claims"}</p></div>
              <time>{new Date(item.updated_at).toLocaleDateString()}</time>
            </a>
          ))}
          {!cases.length && <div className="empty-state">{t.empty}</div>}
        </div>
      </section>

      <footer>
        <strong>DalilDZ</strong>
        <p>Evidence and consistency engine. No trust score. No fraud verdict.</p>
      </footer>
    </main>
  );
}
