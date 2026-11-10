import { FormEvent, useEffect, useState } from "react";
import { ApiError, apiRequest } from "../../api/client";
import type { ServiceBatchOptions, ServiceBatchResult, Session } from "../../api/types";
import { ErrorState, LoadingState } from "../../components/Feedback";
import { useConfirmedRequest } from "../../hooks/useConfirmedRequest";

export function ServiceBatchPage({ session }: { session: Session }) {
  const [error, setError] = useState("");
  const [result, setResult] = useState<ServiceBatchResult | null>(null);
  const request = useConfirmedRequest<ServiceBatchResult>(
    `sigab:${session.organization.id}:${session.user.id}:basket`
  );
  const [refreshing, setRefreshing] = useState(false);
  const [refreshError, setRefreshError] = useState("");
  const [options, setOptions] = useState<ServiceBatchOptions | null>(null);
  const [selectedItems, setSelectedItems] = useState<string[]>([]);
  const [stockQuantities, setStockQuantities] = useState<Record<string, string>>({});

  async function loadOptions(afterSuccess = false) {
    setRefreshing(true);
    setError("");
    setRefreshError("");
    try {
      setOptions(await apiRequest<ServiceBatchOptions>("/service-batches/options/"));
    } catch (requestError) {
      const message = requestError instanceof ApiError ? requestError.message : "Não foi possível atualizar os materiais.";
      if (afterSuccess) setRefreshError(`Atendimento confirmado. Falha ao atualizar opções: ${message}`);
      else setError(message);
    } finally {
      setRefreshing(false);
    }
  }

  useEffect(() => { void loadOptions(); }, []);

  async function complete(result: ServiceBatchResult | undefined, form?: HTMLFormElement) {
    if (!result) return;
    setResult(result);
    form?.reset();
    setSelectedItems([]);
    setStockQuantities({});
    await loadOptions(true);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const element = event.currentTarget;
    const form = new FormData(element);
    const rawDue = String(form.get("due_at") ?? "");
    const stock = (options?.stock ?? []).flatMap((line) => {
      const quantity = stockQuantities[line.id]?.trim();
      return quantity && Number(quantity) > 0 ? [{
        equipment_type_id: line.equipment_type_id, unit_id: line.unit_id,
        storage_location_id: line.storage_location_id, quantity
      }] : [];
    });
    const person = options?.people.find((entry) => entry.id === form.get("recipient_id"));
    const itemNames = (options?.items ?? []).filter((item) => selectedItems.includes(item.id)).map((item) => item.identifier);
    const stockNames = (options?.stock ?? []).filter((line) => Number(stockQuantities[line.id]) > 0)
      .map((line) => `${line.equipment_type}: ${stockQuantities[line.id]}`);
    const summary = `${person?.name ?? "Destinatário"} · ${[...itemNames, ...stockNames].join(", ")}`;
    await complete(await request.execute("/service-batches/", {
      recipient_id: String(form.get("recipient_id") ?? ""), item_ids: selectedItems,
      stock, custody_mode: String(form.get("custody_mode")),
      due_at: rawDue ? new Date(rawDue).toISOString() : null,
      confirmed: form.get("confirmed") === "on"
    }, summary), element);
  }

  const pending = request.pending && <section className="feedback warning" role="status"><p>Atendimento aguardando confirmação: {request.pending.summary}</p><p>Recupere o resultado desta tentativa antes de iniciar outro atendimento.</p><button className="button button-secondary" disabled={request.submitting} onClick={() => void request.execute().then((value) => complete(value))}>Verificar atendimento</button></section>;
  if (!options) return <>{pending}{request.error && <p role="alert">{request.error}</p>}{error ? <ErrorState message={error} onRetry={() => void loadOptions()} /> : <LoadingState />}</>;
  return (
    <>
      <section className="page-heading">
        <div><p className="context-label">Operação de balcão</p><h1>Novo atendimento</h1><p>Selecione a pessoa e materiais individuais ou quantitativos. A confirmação é atômica.</p></div>
      </section>
      {request.error && <div className="feedback error" role="alert">{request.error}</div>}
      {pending}
      {refreshError && <div className="feedback warning" role="status">{refreshError}<button className="button button-secondary" onClick={() => void loadOptions(true)}>Atualizar materiais</button></div>}
      {error && <div className="feedback error" role="alert">{error}</div>}
      {result && <div className="feedback success" role="status">Atendimento confirmado. Comprovante <strong>{result.receipt_code}</strong>.</div>}
      <section className="detail-card">
        <form className="dialog-form" onSubmit={submit}>
          <fieldset disabled={refreshing || request.submitting || Boolean(request.pending) || Boolean(refreshError) || Boolean(error)}>
          <legend>Materiais do atendimento</legend>
          <label><span>Pessoa destinatária</span><select name="recipient_id" required defaultValue=""><option value="" disabled>Selecione</option>{options.people.map((person) => <option key={person.id} value={person.id}>{person.name}</option>)}</select></label>
          <fieldset><legend>Itens individuais</legend>{options.items.length === 0 ? <p className="muted">Nenhum item disponível.</p> : options.items.map((item) => <label className="checkbox" key={item.id}><input type="checkbox" checked={selectedItems.includes(item.id)} onChange={(event) => setSelectedItems((current) => event.target.checked ? [...current, item.id] : current.filter((id) => id !== item.id))} /><span>{item.identifier} · {item.equipment_type} · {item.unit}</span></label>)}</fieldset>
          <fieldset><legend>Materiais quantitativos</legend>{options.stock.length === 0 ? <p className="muted">Nenhum saldo quantitativo disponível.</p> : options.stock.map((line) => <label key={line.id}><span>{line.equipment_type} · {line.unit} · saldo {line.quantity}</span><input type="number" min="0" max={line.quantity} step="0.001" value={stockQuantities[line.id] ?? ""} onChange={(event) => setStockQuantities((current) => ({ ...current, [line.id]: event.target.value }))} /></label>)}</fieldset>
          <label><span>Modalidade</span><select name="custody_mode" defaultValue="indefinite"><option value="shift">Por turno</option><option value="fixed_term">Prazo determinado</option><option value="indefinite">Prazo indeterminado</option></select></label>
          <label><span>Prazo, quando determinado</span><input name="due_at" type="datetime-local" /></label>
          <label className="checkbox"><input name="confirmed" type="checkbox" required /><span>Confirmo destinatário, itens e modalidade.</span></label>
          <button className="button button-primary" disabled={request.submitting}>{request.submitting ? "Confirmando…" : "Confirmar atendimento"}</button>
          </fieldset>
        </form>
      </section>
    </>
  );
}
