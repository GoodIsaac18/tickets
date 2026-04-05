const API_BASE = import.meta.env.VITE_API_BASE || "";

function adminHeaders(adminKey) {
  return {
    "Content-Type": "application/json",
    "X-Admin-Key": adminKey || "",
  };
}

async function parseResponse(response) {
  const text = await response.text();
  let data = {};
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { raw: text };
    }
  }
  if (!response.ok) {
    const msg = data?.error || data?.message || `HTTP ${response.status}`;
    throw new Error(msg);
  }
  return data;
}

export async function getOverview(adminKey) {
  const res = await fetch(`${API_BASE}/api/v1/admin/overview`, {
    headers: adminHeaders(adminKey),
  });
  return parseResponse(res);
}

export async function getInstallations(adminKey, filters) {
  const params = new URLSearchParams();
  params.set("search", filters.search || "");
  params.set("app_id", filters.appId || "all");
  params.set("blocked", filters.blocked || "all");
  params.set("limit", String(filters.limit || 100));
  params.set("offset", String(filters.offset || 0));

  const res = await fetch(`${API_BASE}/api/v1/admin/installations?${params.toString()}`, {
    headers: adminHeaders(adminKey),
  });
  return parseResponse(res);
}

export async function setGlobalBlock(adminKey, blocked, message) {
  const res = await fetch(`${API_BASE}/api/v1/admin/global`, {
    method: "POST",
    headers: adminHeaders(adminKey),
    body: JSON.stringify({ blocked, message }),
  });
  return parseResponse(res);
}

export async function setInstallationBlock(adminKey, installationId, blocked, reason) {
  const res = await fetch(`${API_BASE}/api/v1/admin/installations/block`, {
    method: "POST",
    headers: adminHeaders(adminKey),
    body: JSON.stringify({ installation_id: installationId, blocked, reason }),
  });
  return parseResponse(res);
}
