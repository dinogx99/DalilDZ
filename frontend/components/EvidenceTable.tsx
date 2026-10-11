"use client";

import type { Check } from "../lib/api";
import { useLanguage } from "./LanguageProvider";
import { StatusBadge } from "./StatusBadge";

export function EvidenceTable({ checks }: { checks: Check[] }) {
  const { t } = useLanguage();
  if (!checks.length) {
    return <div className="empty-state">{t.noFindings}</div>;
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>{t.field}</th>
            <th>{t.submitted}</th>
            <th>{t.observed}</th>
            <th>{t.status}</th>
            <th>{t.source}</th>
            <th>{t.why}</th>
          </tr>
        </thead>
        <tbody>
          {checks.map((check) => {
            const sourceId = check.metadata?.source_id;
            const sourceUrl = check.metadata?.source_url;
            return (
              <tr key={check.id}>
                <td className="mono">{check.field}</td>
                <td dir="auto">{check.submitted_value || "—"}</td>
                <td dir="auto">{check.evidence_value || "—"}</td>
                <td><StatusBadge value={check.status} /></td>
                <td className="mono small">
                  {typeof sourceUrl === "string" && /^https?:\/\//.test(sourceUrl) ? (
                    <a href={sourceUrl} target="_blank" rel="noreferrer noopener">{String(sourceId || "link")}</a>
                  ) : (
                    String(sourceId || "—")
                  )}
                </td>
                <td>
                  {check.explanation}
                  <div className="muted small mono">{check.method}</div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
