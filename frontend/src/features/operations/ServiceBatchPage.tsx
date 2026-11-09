import { FormEvent, useEffect, useState } from "react";
import { ApiError, apiRequest, postJson } from "../../api/client";
import type { ServiceBatchOptions, ServiceBatchResult } from "../../api/types";
import { ErrorState, LoadingState } from "../../components/Feedback";

function newKey() {
  return crypto.randomUUID();
}
export function ServiceBatchPage() {
  const [error, setError] = useState("");
  const [result, setResult] = useState<ServiceBatchResult | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [options, setOptions] = useState<ServiceBatchOptions | null>(null);
  const [selectedItems, setSelectedItems] = useState<string[]>([]);
  const [stockQuantities, setStockQuantities] = useState<Record<string, string>>({});

  async function loadOptions() {
    setError("");
    try {
      setOptions(await apiRequest<ServiceBatchOptions>("/service-batches/options/"));
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "Erro inesperado.");
    }
  }

  useEffect(() => { void loadOptions(); }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    const form = new FormData(event.currentTarget);
    const custodyMode = String(form.get("custody_mode"));
    const rawDue = String(form.get("due_at") ?? "");
    try {
      setResult(await postJson<ServiceBatchResult>("/service-batches/", {
        recipient_id: String(form.get("recipient_id") ?? ""),
        item_ids: selectedItems,
        stock: (options?.stock ?? []).flatMap((line) => {
          const quantity = stockQuantities[line.id]?.trim();
          return quantity && Number(quantity) > 0 ? [{
            equipment_type_id: line.equipment_type_id,
            unit_id: line.unit_id,
            storage_location_id: line.storage_location_id,
            quantity
          }] : [];
        }),
        custody_mode: custodyMode,
        due_at: rawDue ? new Date(rawDue).toISOString() : null,
        idempotency_key: newKey(),
        confirmed: form.get("confirmed") === "on"
      }));
      event.currentTarget.reset();
      setSelectedItems([]);
      setStockQuantities({});
      await loadOptions();
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "Erro inesperado.");
    } finally {
      setSubmitting(false);
    }
  }

  if (!options && !error) return <LoadingState />;
  if (!options && error) return <ErrorState message={error} onRetry={() => void loadOptions()} />;
  if (!options) return null;
  return (
    <>
      <section className="page-heading">
        <div><p className="context-label">Operação de balcão</p><h1>Novo atendimento</h1><p>Selecione a pessoa e materiais individuais ou quantitativos. A confirmação é atômica.</p></div>
      </section>
      {error && <div className="feedback error" role="alert">{error}</div>}
      {result && <div className="feedback success" role="status">Atendimento confirmado. Comprovante <strong>{result.receipt_code}</strong>.</div>}
      <section className="detail-card">
        <form className="dialog-form" onSubmit={submit}>
          <label><span>Pessoa destinatária</span><select name="recipient_id" required defaultValue=""><option value="" disabled>Selecione</option>{options.people.map((person) => <option key={person.id} value={person.id}>{person.name}</option>)}</select></label>
          <fieldset><legend>Itens individuais</legend>{options.items.length === 0 ? <p className="muted">Nenhum item disponível.</p> : options.items.map((item) => <label className="checkbox" key={item.id}><input type="checkbox" checked={selectedItems.includes(item.id)} onChange={(event) => setSelectedItems((current) => event.target.checked ? [...current, item.id] : current.filter((id) => id !== item.id))} /><span>{item.identifier} · {item.equipment_type} · {item.unit}</span></label>)}</fieldset>
          <fieldset><legend>Materiais quantitativos</legend>{options.stock.length === 0 ? <p className="muted">Nenhum saldo quantitativo disponível.</p> : options.stock.map((line) => <label key={line.id}><span>{line.equipment_type} · {line.unit} · saldo {line.quantity}</span><input type="number" min="0" max={line.quantity} step="0.001" value={stockQuantities[line.id] ?? ""} onChange={(event) => setStockQuantities((current) => ({ ...current, [line.id]: event.target.value }))} /></label>)}</fieldset>
          <label><span>Modalidade</span><select name="custody_mode" defaultValue="indefinite"><option value="shift">Por turno</option><option value="fixed_term">Prazo determinado</option><option value="indefinite">Prazo indeterminado</option></select></label>
          <label><span>Prazo, quando determinado</span><input name="due_at" type="datetime-local" /></label>
          <label className="checkbox"><input name="confirmed" type="checkbox" required /><span>Confirmo destinatário, itens e modalidade.</span></label>
          <button className="button button-primary" disabled={submitting}>{submitting ? "Confirmando…" : "Confirmar atendimento"}</button>
        </form>
      </section>
    </>
  );
}
