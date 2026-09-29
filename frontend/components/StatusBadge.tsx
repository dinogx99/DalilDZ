const tone: Record<string, string> = {
  VERIFIED: "status verified",
  CONSISTENT: "status consistent",
  CONFLICTING: "status conflicting",
  NOT_FOUND: "status neutral",
  NOT_VERIFIABLE: "status neutral",
  SOURCE_UNAVAILABLE: "status unavailable",
  OUTDATED: "status outdated",
  MANUAL_REVIEW_REQUIRED: "status review",
};

export function StatusBadge({ value }: { value: string }) {
  return <span className={tone[value] || "status neutral"}>{value.replaceAll("_", " ")}</span>;
}
