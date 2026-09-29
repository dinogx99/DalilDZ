import type { Check } from "../lib/api";
import { StatusBadge } from "./StatusBadge";

export function EvidenceTable({ checks }: { checks: Check[] }) {
  if (!checks.length) {
    return <div className="empty-state">No findings yet. Run analysis after adding claims or documents.</div>;
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Field</th>
            <th>Submitted</th>
            <th>Observed</th>
            <th>Status</th>
            <th>Why</th>
          </tr>
        </thead>
        <tbody>
          {checks.map((check) => (
            <tr key={check.id}>
              <td className="mono">{check.field}</td>
              <td>{check.submitted_value || "—"}</td>
              <td>{check.evidence_value || "—"}</td>
              <td><StatusBadge value={check.status} /></td>
              <td>{check.explanation}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
