import React, { useState, useEffect } from "react";

const API_BASE = "http://127.0.0.1:8000/api";

export default function HardwareAdvisor() {
  const [systemData, setSystemData] = useState(null);
  const [selectedGoal, setSelectedGoal] = useState("ai_local_finetuning");
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [evaluating, setEvaluating] = useState(false);

  // Fetch initial telemetry and location on load
  useEffect(() => {
    fetch(`${API_BASE}/status`)
      .then((res) => res.json())
      .then((data) => {
        setSystemData(data);
        setLoading(false);
        runEvaluation("ai_local_finetuning", false);
      })
      .catch((err) => {
        console.error("Backend connection failed:", err);
        setLoading(false);
      });
  }, []);

  const runEvaluation = async (goalKey, forceRescan = false) => {
    setEvaluating(true);
    try {
      const response = await fetch(`${API_BASE}/evaluate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ goal_key: goalKey, force_rescan: forceRescan }),
      });
      const data = await response.json();
      setReport(data);
    } catch (err) {
      console.error("Evaluation failed:", err);
    } finally {
      setEvaluating(false);
    }
  };

  const handleGoalChange = (e) => {
    const newGoal = e.target.value;
    setSelectedGoal(newGoal);
    runEvaluation(newGoal, false);
  };

  if (loading) {
    return <div style={styles.loader}>Scanning system telemetry & local market rates...</div>;
  }

  if (!systemData) {
    return <div style={styles.error}>Could not connect to Python backend on port 8000.</div>;
  }

  const { specs, location, available_goals } = systemData;
  const recs = report?.recommendations || {};

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <div>
          <h1 style={styles.title}>System Telemetry & Upgrade Architect</h1>
          <p style={styles.subtitle}>
            Location: <strong>{location.city}, {location.country_name}</strong> ({location.currency})
          </p>
        </div>
        <button
          style={styles.rescanBtn}
          onClick={() => runEvaluation(selectedGoal, true)}
          disabled={evaluating}
        >
          {evaluating ? "Scanning..." : "Rescan Hardware"}
        </button>
      </header>

      {/* Current Hardware Telemetry Bar */}
      <section style={styles.telemetryGrid}>
        <div style={styles.statCard}>
          <span style={styles.statLabel}>Processor</span>
          <strong style={styles.statValue}>{specs.cpu.brand}</strong>
          <small style={styles.statSub}>{specs.cpu.physical_cores} Physical / {specs.cpu.logical_cores} Logical Cores</small>
        </div>
        <div style={styles.statCard}>
          <span style={styles.statLabel}>System Memory</span>
          <strong style={styles.statValue}>{specs.ram.total_gb} GB RAM</strong>
          <small style={styles.statSub}>{specs.ram.available_gb} GB Free</small>
        </div>
        <div style={styles.statCard}>
          <span style={styles.statLabel}>Primary Storage</span>
          <strong style={styles.statValue}>{specs.storage.total_gb} GB</strong>
          <small style={styles.statSub}>{specs.storage.free_gb} GB Available</small>
        </div>
        <div style={styles.statCard}>
          <span style={styles.statLabel}>Primary GPU</span>
          <strong style={styles.statValue}>{specs.gpus[0]?.name}</strong>
          <small style={styles.statSub}>{specs.gpus[0]?.vram_total_gb} GB Dedicated VRAM</small>
        </div>
      </section>

      {/* Workload Selector */}
      <section style={styles.selectorBox}>
        <label style={styles.label}>Select Target Workload / Goal:</label>
        <select value={selectedGoal} onChange={handleGoalChange} style={styles.select}>
          {available_goals.map((g) => (
            <option key={g.key} value={g.key}>
              [{g.tier.toUpperCase()}] {g.title}
            </option>
          ))}
        </select>
      </section>

      {/* Bottleneck Analysis */}
      {report && (
        <section style={{
          ...styles.bottleneckBox,
          borderLeft: report.system_passed ? "5px solid #10b981" : "5px solid #ef4444"
        }}>
          <h3 style={styles.sectionHeading}>
            {report.system_passed ? "✅ System Meets Baseline Specs" : "⚠️ Detected Hardware Bottlenecks"}
          </h3>
          <ul style={styles.list}>
            {report.detected_bottlenecks.map((item, idx) => (
              <li key={idx} style={styles.listItem}>{item}</li>
            ))}
          </ul>
        </section>
      )}

      {/* Upgrade Recommendations */}
      {report && (
        <section>
          {recs.small_datacenter_blueprint ? (
            /* Route 1: Small Data Center Rack Blueprint */
            <div style={styles.datacenterCard}>
              <div style={styles.warningBanner}>{recs.warning}</div>
              <h2 style={styles.cardTitle}>🏢 Small Data Center / Server Rack Blueprint</h2>
              <div style={styles.specRows}>
                <p><strong>Compute Nodes:</strong> {recs.small_datacenter_blueprint.compute_nodes}</p>
                <p><strong>GPU Cluster:</strong> {recs.small_datacenter_blueprint.gpu_cluster}</p>
                <p><strong>ECC Memory:</strong> {recs.small_datacenter_blueprint.memory}</p>
                <p><strong>Storage SAN:</strong> {recs.small_datacenter_blueprint.storage_san}</p>
                <p><strong>Rack & Power Infrastructure:</strong> {recs.small_datacenter_blueprint.infrastructure}</p>
              </div>
              <div style={styles.budgetFooter}>
                <span>Estimated Local CapEx ({location.currency}):</span>
                <strong style={styles.priceTag}>{recs.small_datacenter_blueprint.estimated_budget}</strong>
                <small style={styles.taxNote}>
                  Base USD: {recs.small_datacenter_blueprint.pricing_details.base_usd_range} | Regional Duty/Tax Multiplier: {recs.small_datacenter_blueprint.pricing_details.regional_tax_multiplier}x
                </small>
              </div>
            </div>
          ) : (
            /* Route 2: Modular Desktop PC + Laptop Grid */
            <div style={styles.dualGrid}>
              {/* Desktop PC Card */}
              <div style={styles.upgradeCard}>
                <h2 style={styles.cardTitle}>🖥️ Custom Desktop / Workstation Build</h2>
                <div style={styles.specRows}>
                  <p><strong>Processor:</strong> {recs.desktop_pc_upgrade?.cpu}</p>
                  <p><strong>Graphics (GPU):</strong> {recs.desktop_pc_upgrade?.gpu}</p>
                  <p><strong>Memory:</strong> {recs.desktop_pc_upgrade?.ram}</p>
                  <p><strong>NVMe Storage:</strong> {recs.desktop_pc_upgrade?.storage}</p>
                </div>
                <div style={styles.budgetFooter}>
                  <span>Estimated Local Street Price:</span>
                  <strong style={styles.priceTag}>{recs.desktop_pc_upgrade?.estimated_budget}</strong>
                  <small style={styles.taxNote}>
                    Base USD: {recs.desktop_pc_upgrade?.pricing_details.base_usd_range} (Incl. {recs.desktop_pc_upgrade?.pricing_details.regional_tax_multiplier}x local tax/import factor)
                  </small>
                </div>
              </div>

              {/* Laptop Alternative Card */}
              <div style={styles.upgradeCard}>
                <h2 style={styles.cardTitle}>💻 Mobile Workstation / Laptop Equivalent</h2>
                <div style={styles.specRows}>
                  <p><strong>Recommended Models:</strong> {recs.laptop_alternative?.recommended_models}</p>
                  <p><strong>Target Configuration:</strong> {recs.laptop_alternative?.target_specs}</p>
                </div>
                <div style={styles.budgetFooter}>
                  <span>Estimated Local Street Price:</span>
                  <strong style={styles.priceTag}>{recs.laptop_alternative?.estimated_budget}</strong>
                  <small style={styles.taxNote}>
                    Base USD: {recs.laptop_alternative?.pricing_details.base_usd_range} (Incl. {recs.laptop_alternative?.pricing_details.regional_tax_multiplier}x local tax/import factor)
                  </small>
                </div>
              </div>
            </div>
          )}
        </section>
      )}
    </div>
  );
}

const styles = {
  container: { maxWidth: "1100px", margin: "0 auto", padding: "32px 20px", fontFamily: "system-ui, sans-serif", color: "#e2e8f0", backgroundColor: "#0f172a", minHeight: "100vh" },
  header: { display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #334155", paddingBottom: "16px", marginBottom: "24px" },
  title: { margin: 0, fontSize: "24px", color: "#f8fafc" },
  subtitle: { margin: "4px 0 0", color: "#94a3b8", fontSize: "14px" },
  rescanBtn: { backgroundColor: "#3b82f6", color: "#fff", border: "none", padding: "10px 16px", borderRadius: "6px", cursor: "pointer", fontWeight: 600 },
  telemetryGrid: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px", marginBottom: "24px" },
  statCard: { backgroundColor: "#1e293b", padding: "16px", borderRadius: "8px", border: "1px solid #334155", display: "flex", flexDirection: "column" },
  statLabel: { fontSize: "12px", textTransform: "uppercase", color: "#94a3b8", marginBottom: "4px" },
  statValue: { fontSize: "16px", color: "#f8fafc", marginBottom: "4px" },
  statSub: { fontSize: "12px", color: "#64748b" },
  selectorBox: { backgroundColor: "#1e293b", padding: "20px", borderRadius: "8px", marginBottom: "24px", border: "1px solid #334155" },
  label: { display: "block", marginBottom: "8px", fontWeight: 600, color: "#cbd5e1" },
  select: { width: "100%", padding: "12px", borderRadius: "6px", backgroundColor: "#0f172a", color: "#f8fafc", border: "1px solid #475569", fontSize: "15px" },
  bottleneckBox: { backgroundColor: "#1e293b", padding: "16px 20px", borderRadius: "8px", marginBottom: "24px" },
  sectionHeading: { margin: "0 0 10px 0", fontSize: "16px" },
  list: { margin: 0, paddingLeft: "20px", color: "#cbd5e1" },
  listItem: { marginBottom: "6px" },
  dualGrid: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(420px, 1fr))", gap: "20px" },
  upgradeCard: { backgroundColor: "#1e293b", borderRadius: "10px", padding: "24px", border: "1px solid #334155", display: "flex", flexDirection: "column", justifyContent: "space-between" },
  datacenterCard: { backgroundColor: "#1e1b4b", borderRadius: "10px", padding: "24px", border: "1px solid #4f46e5" },
  warningBanner: { backgroundColor: "#4338ca", color: "#e0e7ff", padding: "12px", borderRadius: "6px", marginBottom: "16px", fontSize: "14px", fontWeight: 500 },
  cardTitle: { margin: "0 0 16px 0", fontSize: "18px", color: "#f8fafc", borderBottom: "1px solid #334155", paddingBottom: "10px" },
  specRows: { lineHeight: "1.7", fontSize: "14px", color: "#cbd5e1", marginBottom: "20px" },
  budgetFooter: { backgroundColor: "#0f172a", padding: "16px", borderRadius: "8px", display: "flex", flexDirection: "column", gap: "4px" },
  priceTag: { fontSize: "22px", color: "#38bdf8" },
  taxNote: { fontSize: "12px", color: "#64748b" },
  loader: { padding: "40px", textAlign: "center", color: "#94a3b8", fontFamily: "sans-serif" },
  error: { padding: "40px", textAlign: "center", color: "#ef4444", fontFamily: "sans-serif" }
};