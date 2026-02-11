import React, { useState } from "react";

type Change = {
  id: string;
  before: string;
  after: string;
  risk: string;
  reason: string;
};

export default function ReviewPanel({ change }: { change: Change }) {
  const [decision, setDecision] = useState("approve");

  async function submit() {
    await fetch("/api/review/submit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        change_id: change.id,
        decision,
      }),
    });
    alert("Decision submitted");
  }

  return (
    <div style={{ border: "1px solid #333", padding: 12, marginBottom: 12 }}>
      <h4>Change Review</h4>
      <pre>{change.before}</pre>
      <pre>{change.after}</pre>
      <p>Risk: <b>{change.risk}</b> — {change.reason}</p>

      <select value={decision} onChange={(e) => setDecision(e.target.value)}>
        <option value="approve">Approve</option>
        <option value="reject">Reject</option>
        <option value="edit">Edit</option>
      </select>

      <button onClick={submit} style={{ marginLeft: 8 }}>
        Submit
      </button>
    </div>
  );
}
