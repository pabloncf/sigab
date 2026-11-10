import { useEffect, useState } from "react";
import { ApiError, apiRequest, postJson } from "../../api/client";
import { ActionDialog, text } from "../../components/ActionDialog";
import { ErrorState, LoadingState } from "../../components/Feedback";

interface Restriction {
  id: string; person_id: string; person_name: string; category: string; summary: string;
  source: string; reference: string; starts_at: string; ends_at: string | null;
  equipment_type_ids: string[]; closed_at: string | null;
  history?: Array<{ id: string; action: string; reason: string; occurred_at: string }>;
}
interface RestrictionList {
  restrictions: Restriction[];
  people: Array<{ id: string; name: string }>;
  equipment_types: Array<{ id: string; name: string }>;
}
const localInstant = (value?: string | null) => {
  if (!value) return "";
  const date = new Date(value);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
};
const instant = (form: FormData, field: string) => text(form, field) ? new Date(text(form, field)).toISOString() : null;
const dateLabel = (value: string) => new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" }).format(new Date(value));

export function RestrictionsPage() {
  const [data, setData] = useState<RestrictionList | null>(null);
  const [error, setError] = useState("");
  const [dialog, setDialog] = useState<"create" | "change" | "close" | null>(null);
  const [selected, setSelected] = useState<Restriction | null>(null);

  async function load() {
    setError("");
    try { setData(await apiRequest<RestrictionList>("/restrictions/")); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Não foi possível carregar as restrições."); }
  }
  useEffect(() => { void load(); }, []);

  async function open(value: Restriction, action: "change" | "close" | "history") {
    setError("");
    try {
      setSelected(await apiRequest<Restriction>(`/restrictions/${value.id}/`));
      setDialog(action === "history" ? null : action);
    } catch (err) { setError(err instanceof ApiError ? err.message : "Não foi possível abrir a restrição."); }
  }
  async function submit(form: FormData) {
    const body = {
      confirmed: form.get("confirmed") === "on", reason: text(form, "reason"),
      ...(dialog !== "close" ? {
        person_id: text(form, "person_id"), category: text(form, "category"),
        summary: text(form, "summary"), source: text(form, "source"), reference: text(form, "reference"),
        starts_at: instant(form, "starts_at"), ends_at: instant(form, "ends_at"),
        equipment_type_ids: form.getAll("equipment_type_ids")
      } : {}),
      ...(dialog !== "create" ? { action: dialog } : {})
    };
    await postJson(dialog === "create" ? "/restrictions/" : `/restrictions/${selected!.id}/`, body);
    setSelected(null);
    await load();
  }
  if (!data) return error ? <ErrorState message={error} onRetry={() => void load()} /> : <LoadingState />;
  return <>
    <section className="page-heading"><div><p className="context-label">Elegibilidade operacional</p><h1>Restrições</h1><p>Dados restritos à gestão. Informe somente referência e motivo resumido, sem laudos ou diagnósticos.</p></div><button className="button button-primary" onClick={() => { setSelected(null); setDialog("create"); }}>Cadastrar restrição</button></section>
    {error && <div className="feedback error" role="alert">{error}</div>}
    <section className="list-panel" aria-label="Restrições da organização">
      {data.restrictions.length === 0 ? <p>Nenhuma restrição cadastrada.</p> : <ul className="sub-list">{data.restrictions.map((value) => <li key={value.id}><span><strong>{value.person_name}</strong><small>{value.closed_at ? "Encerrada" : value.ends_at && Date.parse(value.ends_at) <= Date.now() ? "Expirada" : Date.parse(value.starts_at) > Date.now() ? "Futura" : "Vigente"} · desde {dateLabel(value.starts_at)}</small></span><div className="actions"><button className="button button-secondary" onClick={() => void open(value, "history")}>Histórico de {value.person_name}</button>{!value.closed_at && <><button className="button button-secondary" onClick={() => void open(value, "change")}>Alterar</button><button className="button button-quiet" onClick={() => void open(value, "close")}>Encerrar</button></>}</div></li>)}</ul>}
    </section>
    {selected && !dialog && <section className="history-card" aria-label="Histórico da restrição"><h2>{selected.person_name}</h2><p>{selected.summary} · {selected.source} · {selected.reference}</p><ol>{selected.history?.map((event) => <li key={event.id}>{event.action} · {dateLabel(event.occurred_at)} · {event.reason}</li>)}</ol></section>}
    {dialog && <ActionDialog title={dialog === "create" ? "Cadastrar restrição" : dialog === "change" ? "Alterar restrição" : "Encerrar restrição"} confirmation="Confirmo os dados e o escopo desta restrição." onClose={() => setDialog(null)} onSubmit={submit}>
      {dialog !== "close" && <>
        {dialog === "create" && <label><span>Pessoa</span><select name="person_id" required defaultValue=""><option value="" disabled>Selecione</option>{data.people.map((person) => <option key={person.id} value={person.id}>{person.name}</option>)}</select></label>}
        <label><span>Categoria</span><select name="category" defaultValue={selected?.category ?? "administrativa"}><option value="administrativa">Administrativa</option><option value="judicial">Judicial</option><option value="saude">Saúde</option><option value="outra">Outra</option></select></label>
        <label><span>Motivo resumido</span><textarea name="summary" required maxLength={200} defaultValue={selected?.summary} /></label>
        <label><span>Fonte</span><input name="source" required maxLength={160} defaultValue={selected?.source} /></label>
        <label><span>Referência do documento</span><input name="reference" maxLength={160} defaultValue={selected?.reference} /></label>
        <label><span>Início</span><input name="starts_at" type="datetime-local" required defaultValue={localInstant(selected?.starts_at)} /></label>
        <label><span>Fim opcional</span><input name="ends_at" type="datetime-local" defaultValue={localInstant(selected?.ends_at)} /></label>
        <fieldset><legend>Tipos de material — nenhum selecionado aplica a todos</legend>{data.equipment_types.map((kind) => <label className="confirmation" key={kind.id}><input name="equipment_type_ids" value={kind.id} type="checkbox" defaultChecked={selected?.equipment_type_ids.includes(kind.id)} /><span>{kind.name}</span></label>)}</fieldset>
      </>}
      {dialog !== "create" && <label><span>Motivo da alteração ou encerramento</span><textarea name="reason" required maxLength={200} /></label>}
    </ActionDialog>}
  </>;
}
