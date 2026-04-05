import { useEffect, useMemo, useState } from "react";
import {
  getInstallations,
  getOverview,
  setGlobalBlock,
  setInstallationBlock,
} from "./api";

const DEFAULT_LIMIT = 100;

function formatDate(value) {
  if (!value) return "-";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString();
}

function Badge({ blocked }) {
  return (
    <span className={blocked ? "badge badge-red" : "badge badge-green"}>
      {blocked ? "Bloqueado" : "Activo"}
    </span>
  );
}

export default function App() {
  const [adminKey, setAdminKey] = useState(localStorage.getItem("tickets_admin_key") || "");
  const [overview, setOverview] = useState(null);
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [globalMessage, setGlobalMessage] = useState("Servicio disponible");
  const [blockingGlobal, setBlockingGlobal] = useState(false);

  const [filters, setFilters] = useState({
    search: "",
    appId: "all",
    blocked: "all",
    limit: DEFAULT_LIMIT,
    offset: 0,
  });

  const page = useMemo(() => Math.floor(filters.offset / filters.limit) + 1, [filters]);
  const totalPages = useMemo(() => Math.max(1, Math.ceil(total / filters.limit)), [total, filters.limit]);

  useEffect(() => {
    localStorage.setItem("tickets_admin_key", adminKey);
  }, [adminKey]);

  async function loadAll() {
    if (!adminKey) {
      setError("Ingresa la clave admin (X-Admin-Key).");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const [ov, list] = await Promise.all([
        getOverview(adminKey),
        getInstallations(adminKey, filters),
      ]);
      setOverview(ov);
      setGlobalMessage(ov?.global?.message || "Servicio disponible");
      setItems(list.items || []);
      setTotal(list.total || 0);
    } catch (err) {
      setError(String(err?.message || err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.offset, filters.search, filters.appId, filters.blocked, filters.limit]);

  useEffect(() => {
    if (!adminKey) return;
    const timer = setInterval(() => {
      loadAll();
    }, 15000);
    return () => clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [adminKey, filters]);

  async function onToggleGlobal() {
    if (!overview?.global) return;
    try {
      setBlockingGlobal(true);
      await setGlobalBlock(adminKey, !overview.global.blocked, globalMessage);
      await loadAll();
    } catch (err) {
      setError(String(err?.message || err));
    } finally {
      setBlockingGlobal(false);
    }
  }

  async function onRowToggle(item) {
    const reason =
      item.blocked
        ? ""
        : window.prompt("Razon de bloqueo para esta instalacion:", "Bloqueo administrativo") || "Bloqueo administrativo";

    try {
      await setInstallationBlock(adminKey, item.installation_id, !item.blocked, reason);
      await loadAll();
    } catch (err) {
      setError(String(err?.message || err));
    }
  }

  const blockedCount = overview?.stats?.blocked_installations || 0;
  const activeCount = overview?.stats?.active_installations || 0;
  const totalInstallations = overview?.stats?.total_installations || 0;

  return (
    <div className="layout">
      <header className="topbar">
        <div>
          <h1>Panel Avanzado de Licencias</h1>
          <p>Control global, auditoria por equipo y revocacion inmediata.</p>
        </div>
        <div className="topbar-actions">
          <input
            type="password"
            placeholder="Admin key"
            value={adminKey}
            onChange={(e) => setAdminKey(e.target.value)}
          />
          <button onClick={loadAll} disabled={loading}>Actualizar</button>
        </div>
      </header>

      {error ? <div className="alert">{error}</div> : null}

      <section className="kpi-grid">
        <article className="kpi-card">
          <h3>Instalaciones</h3>
          <strong>{totalInstallations}</strong>
        </article>
        <article className="kpi-card">
          <h3>Activas</h3>
          <strong>{activeCount}</strong>
        </article>
        <article className="kpi-card">
          <h3>Bloqueadas</h3>
          <strong>{blockedCount}</strong>
        </article>
        <article className="kpi-card">
          <h3>Estado Global</h3>
          <Badge blocked={Boolean(overview?.global?.blocked)} />
        </article>
      </section>

      <section className="panel-row">
        <article className="panel card-wide">
          <h2>Control Global</h2>
          <label>Mensaje global</label>
          <input value={globalMessage} onChange={(e) => setGlobalMessage(e.target.value)} />
          <button className="danger" onClick={onToggleGlobal} disabled={blockingGlobal || !overview}>
            {overview?.global?.blocked ? "Desbloquear sistema" : "Bloquear sistema"}
          </button>
        </article>

        <article className="panel">
          <h2>Apps registradas</h2>
          <ul>
            {(overview?.stats?.apps || []).map((app) => (
              <li key={app.app_id}>
                <span>{app.app_id}</span>
                <strong>{app.count}</strong>
              </li>
            ))}
          </ul>
        </article>
      </section>

      <section className="panel card-table">
        <h2>Instalaciones</h2>
        <div className="filters">
          <input
            placeholder="Buscar por id, host, usuario, ip, empresa"
            value={filters.search}
            onChange={(e) => setFilters((prev) => ({ ...prev, search: e.target.value, offset: 0 }))}
          />
          <select
            value={filters.appId}
            onChange={(e) => setFilters((prev) => ({ ...prev, appId: e.target.value, offset: 0 }))}
          >
            <option value="all">Todas las apps</option>
            <option value="emisora">emisora</option>
            <option value="receptora">receptora</option>
            <option value="unknown">unknown</option>
          </select>
          <select
            value={filters.blocked}
            onChange={(e) => setFilters((prev) => ({ ...prev, blocked: e.target.value, offset: 0 }))}
          >
            <option value="all">Todas</option>
            <option value="0">Activas</option>
            <option value="1">Bloqueadas</option>
          </select>
        </div>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Estado</th>
                <th>Installation ID</th>
                <th>App</th>
                <th>Empresa</th>
                <th>Host</th>
                <th>Usuario</th>
                <th>IP</th>
                <th>Ultimo seen</th>
                <th>Validaciones</th>
                <th>Accion</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.installation_id}>
                  <td><Badge blocked={item.blocked} /></td>
                  <td title={item.token}>{item.installation_id}</td>
                  <td>{item.app_id}</td>
                  <td>{item.empresa}</td>
                  <td>{item.hostname || "-"}</td>
                  <td>{item.usuario || "-"}</td>
                  <td>{item.last_ip || "-"}</td>
                  <td>{formatDate(item.last_seen)}</td>
                  <td>{item.total_validations}</td>
                  <td>
                    <button className={item.blocked ? "ok" : "danger"} onClick={() => onRowToggle(item)}>
                      {item.blocked ? "Desbloquear" : "Bloquear"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="pager">
          <button
            onClick={() => setFilters((prev) => ({ ...prev, offset: Math.max(0, prev.offset - prev.limit) }))}
            disabled={page <= 1}
          >
            Anterior
          </button>
          <span>Pagina {page} de {totalPages}</span>
          <button
            onClick={() => setFilters((prev) => ({ ...prev, offset: prev.offset + prev.limit }))}
            disabled={page >= totalPages}
          >
            Siguiente
          </button>
        </div>
      </section>
    </div>
  );
}
