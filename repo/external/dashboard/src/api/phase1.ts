export type Phase1Response = {
  status: "OK" | "BLOCKED";
  reason?: string | null;
  policy_id?: string | null;
  policy_version?: string | null;
  policy_hash?: string | null;
  deterministic_mode?: boolean | null;
  strict?: boolean;
  checked_at?: string | null;
  build_id?: string | null;
};

export async function fetchPhase1(): Promise<Phase1Response> {
  try {
    const res = await fetch("/api/system/phase1");
    if (!res.ok) {
      return {
        status: "BLOCKED",
        reason: `HTTP ${res.status}`,
      };
    }
    return res.json();
  } catch (e: any) {
    return {
      status: "BLOCKED",
      reason: e?.message ?? String(e),
    };
  }
}
