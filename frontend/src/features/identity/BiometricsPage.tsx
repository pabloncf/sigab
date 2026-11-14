import { useEffect, useRef, useState } from "react";
import { apiRequest, describeError } from "../../api/client";
import type { BiometricStatus } from "../../api/types";
import { ErrorState, LoadingState, UpdatingState } from "../../components/Feedback";
import { AppliedFilters, SearchForm, useUrlQuery } from "../../components/Query";
import { BiometricPanel } from "./BiometricPanel";
import { useLatestRequest } from "../../hooks/useLatestRequest";

interface Row extends BiometricStatus {
  id: string;
  name: string;
  registrations: string[];
}

/** Módulo Biometria: quem ainda precisa cadastrar a face antes de retirar material (ADR 0008). */
export function BiometricsPage() {
  const [rows, setRows] = useState<Row[] | null>(null);
  const [filters, setFilters] = useUrlQuery({ q: "", cadastro: "" });
  const query = filters.q;
  const pendingOnly = filters.cadastro === "pendente";
  const [selected, setSelected] = useState<Row | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const opener = useRef<HTMLButtonElement | null>(null);
  const beginRequest = useLatestRequest();

  async function load(term = query) {
    const current = beginRequest();
    setLoading(true);
    setError("");
    try {
      const result = await apiRequest<Row[]>(`/biometrics/${term.trim() ? `?q=${encodeURIComponent(term.trim())}` : ""}`);
      if (current()) setRows(result);
    } catch (cause) {
      if (current()) setError(describeError(cause));
    } finally {
      if (current()) setLoading(false);
    }
  }

  useEffect(() => { void load(); }, [query]);

  function search(term: string) {
    setFilters({ q: term });
  }

  const visible = (rows ?? []).filter((row) => !pendingOnly || !row.enrolled);
  const missing = (rows ?? []).filter((row) => !row.enrolled).length;

  return (
    <>
      <section className="page-heading">
        <div>
          <p className="context-label">Gestão</p>
          <h1>Biometria facial</h1>
          <p>Consulte e cadastre a biometria das pessoas da organização.</p>
        </div>
      </section>
      <div className="filter-bar" inert={busy || undefined}>
        <SearchForm label="Buscar pessoa" placeholder="Nome ou matrícula" value={query} onSearch={search} />
        <label className="checkbox filter-checkbox"><input type="checkbox" checked={pendingOnly} onChange={(event) => setFilters({ cadastro: event.target.checked ? "pendente" : "" })} /><span>Somente sem cadastro</span></label>
      </div>
      <AppliedFilters filters={[
        ...(query ? [{ label: "Busca", value: query, onRemove: () => { if (!busy) search(""); } }] : []),
        ...(pendingOnly ? [{ label: "Cadastro", value: "somente sem cadastro", onRemove: () => { if (!busy) setFilters({ cadastro: "" }); } }] : [])
      ]} />
      {selected && <BiometricPanel personId={selected.id} personName={selected.name} registration={selected.registrations.join(", ")} onBusyChange={setBusy}
        onClose={() => { setSelected(null); opener.current?.focus(); }} onChange={() => void load()} />}
      {loading && rows && <UpdatingState />}
      {error ? <ErrorState message={error} onRetry={() => void load()} /> : !rows ? <LoadingState /> : (
        <section className="list-panel stock-history" aria-label="Pessoas e biometria">
          <div className="list-summary"><span><strong>{rows.length}</strong> {rows.length === 1 ? "pessoa ativa" : "pessoas ativas"} · <strong>{missing}</strong> sem cadastro</span></div>
          {visible.length === 0 && <p className="inline-empty">Nenhuma pessoa corresponde aos filtros aplicados.</p>}
          <ul className="sub-list feed" inert={busy || loading || undefined} aria-busy={loading || undefined}>
            {visible.map((row) => (
              <li key={row.id} className={selected?.id === row.id ? "selected-row" : undefined}>
                <span><strong>{row.name}</strong><small>{row.registrations.join(", ")} · {row.enrolled ? "cadastrada" : "não cadastrada"}</small></span>
                <button className="button button-secondary" type="button" aria-pressed={selected?.id === row.id} aria-label={`${row.enrolled ? "Gerenciar" : "Cadastrar"} biometria de ${row.name}`} onClick={(event) => { opener.current = event.currentTarget; setSelected(row); }}>{row.enrolled ? "Gerenciar" : "Cadastrar"}</button>
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
  );
}
