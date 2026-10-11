"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { useLanguage } from "../components/LanguageProvider";
import { TopBar } from "../components/TopBar";
import type { CaseRecord } from "../lib/api";
import { jsonFetch, postJson, uploadFile } from "../lib/api";

const LEGAL_FORMS = ["SARL", "EURL", "SPA", "SNC", "SCS"];
const OPTIONAL_FIELDS = ["rc", "nif", "website", "wilaya", "legal_form", "email", "phone"] as const;

export default function Home() {
  const router = useRouter();
  const { t } = useLanguage();
  const [cases, setCases] = useState<CaseRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState("");
  const [bulkMessage, setBulkMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function loadCases() {
    const result = await jsonFetch<{ items: CaseRecord[]; total: number }>("/api/v1/cases?limit=8");
    setCases(result.items);
    setTotal(result.total);
  }

  useEffect(() => {
    loadCases().catch(() => undefined);
  }, []);

  async function createCase(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const name = String(data.get("name") || "").trim();
    if (!name) return;
    const claims: Record<string, string> = { legal_name: name };
    for (const field of OPTIONAL_FIELDS) {
      const value = String(data.get(field) || "").trim();
      if (value) claims[field] = value;
    }
    setBusy(true);
    setError("");
    try {
      const created = await postJson<CaseRecord>("/api/v1/cases", { name, claims });
      router.push(`/cases/${created.id}`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to create case");
      setBusy(false);
    }
  }

  async function bulkImport(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const input = form.elements.namedItem("bulk") as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    setBusy(true);
    setBulkMessage("");
    try {
      const result = await uploadFile<{ created: number }>("/api/v1/bulk/import", file);
      setBulkMessage(`${result.created} ${t.bulkDone}`);
      form.reset();
      await loadCases();
    } catch (reason) {
      setBulkMessage(reason instanceof Error ? reason.message : "Import failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="shell">
      <TopBar>
        <a href="/docs" target="_blank" rel="noreferrer">API</a>
      </TopBar>

      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">OPEN SOURCE · ALGERIA · EVIDENCE FIRST</p>
          <h1>{t.headline}</h1>
          <p className="lede">{t.subhead}</p>
          <div className="principle">
            <strong>{t.principleTitle}</strong>
            <span>{t.principleText}</span>
          </div>
        </div>

        <article className="create-card">
          <p className="eyebrow">{t.start}</p>
          <h2>{t.tagline}</h2>
          <form onSubmit={createCase} className="case-form">
            <label>
              {t.company}
              <input name="name" required maxLength={240} placeholder="SARL ALPHA DISTRIBUTION" />
            </label>
            <div className="form-grid">
              <label>{t.rc}<input name="rc" placeholder="16B0123456" /></label>
              <label>{t.nif}<input name="nif" inputMode="numeric" /></label>
            </div>
            <div className="form-grid">
              <label>{t.website}<input name="website" placeholder="example.dz" /></label>
              <label>{t.wilaya}<input name="wilaya" placeholder="Oran / 31 / وهران" /></label>
            </div>
            <details className="more-fields">
              <summary>{t.moreFields}</summary>
              <div className="form-grid">
                <label>
                  {t.legalForm}
                  <select name="legal_form" defaultValue="">
                    <option value="">{t.notSpecified}</option>
                    {LEGAL_FORMS.map((form) => <option key={form} value={form}>{form}</option>)}
                  </select>
                </label>
                <label>{t.phone}<input name="phone" type="tel" placeholder="0550 12 34 56" /></label>
              </div>
              <label>{t.email}<input name="email" type="email" /></label>
            </details>
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
          <div><p className="eyebrow">{t.howItWorks}</p><h2>{t.howTitle}</h2></div>
        </div>
        <ol className="workflow-steps">
          <li><b>01</b><span>{t.step1}</span><small>{t.step1Text}</small></li>
          <li><b>02</b><span>{t.step2}</span><small>{t.step2Text}</small></li>
          <li><b>03</b><span>{t.step3}</span><small>{t.step3Text}</small></li>
          <li><b>04</b><span>{t.step4}</span><small>{t.step4Text}</small></li>
          <li><b>05</b><span>{t.step5}</span><small>{t.step5Text}</small></li>
        </ol>
      </section>

      <section className="recent">
        <div className="section-head">
          <div><p className="eyebrow">{t.workspace}</p><h2>{t.recent}</h2></div>
          <span className="muted">{total}</span>
        </div>
        <div className="recent-grid">
          <div className="case-list">
            {cases.map((item) => (
              <Link key={item.id} href={`/cases/${item.id}`} className="case-row">
                <div>
                  <strong>{item.name}</strong>
                  <p>{Object.keys(item.claims).join(" · ") || t.noClaims}</p>
                </div>
                <time>{new Date(item.updated_at).toLocaleDateString()}</time>
              </Link>
            ))}
            {!cases.length && <div className="empty-state">{t.empty}</div>}
          </div>

          <article className="panel">
            <h3>{t.bulkTitle}</h3>
            <p className="muted small">{t.bulkText}</p>
            <form onSubmit={bulkImport} className="upload-form">
              <input type="file" name="bulk" accept=".csv,.xlsx" required />
              <button disabled={busy}>{t.bulkButton}</button>
            </form>
            {bulkMessage && <p className="message">{bulkMessage}</p>}
          </article>
        </div>
      </section>

      <footer>
        <strong>DalilDZ</strong>
        <p>{t.footer}</p>
      </footer>
    </main>
  );
}
