const fs = require('fs');
const traces = fs.readFileSync('/home/jalue/lomba/qhome-ai-agent/runs-test/bulk-order-test-run/interactions.jsonl', 'utf-8').trim().split('\n').map(JSON.parse);

function fmt(str) {
  if (typeof str !== "string") return str;
  return str.split("_").map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
}

function getRiskClass(val) { return ""; }
function buildArtifact(fields, notes) { return ""; }

traces.forEach(step => {
  const output = step.output || {};
  const agentName = step.agent || "";
  
  try {
    if (agentName.includes("Router") || agentName.includes("Orchestrator") || output.selected_pipeline) {
      // triage
    } else if (agentName.includes("Intent") || agentName.includes("Classifier")) {
      const a = (output.missing_information || []).join(", ");
    } else if (agentName.includes("Knowledge")) {
      const a = (output.matched_policy_ids || []).join(", ");
    } else if (agentName.includes("Solution") || agentName.includes("Planner")) {
      const a = (output.recommended_actions || []).slice(0, 2).join("; ");
    } else if (agentName.includes("QA") || agentName.includes("Final")) {
      const a = (output.internal_next_steps || []).length;
    }
    console.log("SUCCESS:", agentName);
  } catch (e) {
    console.log("CRASH ON:", agentName, e.message);
  }
});
