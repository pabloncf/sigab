import { FormEvent, useEffect, useState } from "react";
import { ApiError, apiRequest } from "../../api/client";
import type { ServiceBatchOptions, ServiceBatchResult, Session } from "../../api/types";
import { ErrorState, LoadingState } from "../../components/Feedback";
import { formatQuantity } from "../../components/format";
import { useConfirmedRequest } from "../../hooks/useConfirmedRequest";
import { CounterEntry } from "./CounterEntry";
import { IdentityCheck } from "./IdentityCheck";
import { RegisteredPicker, UnregisteredPicker } from "./MaterialPickers";
import { PersonCard, useCounterPerson } from "./PersonCard";
import { useCounterArrival } from "./useCounterArrival";

type Body = Record<string, unknown> & { recipient_id: string; item_ids: string[]; stock: unknown[]; custody_mode: string; due_at: string | null };

/**
 * Retirada no balcão: a pessoa é identificada pela matrícula (e pelo rosto), depois o
 * operador digita os materiais, sempre em listas separadas com e sem registro.
 */
export function ServiceBatchPage({ session }: { session: Session }) {
  const faceRequired = Boolean(session.permissions.identity_check_required);
  const arrival = useCounterArrival();
  const { person, error: personError } = useCounterPerson(arrival.personId);
  const request = useConfirmedRequest<ServiceBatchResult>(
    `sigab:${session.organization.id}:${session.user.id}:basket`
  );
  const [error, setError] = useState("");
  const [formError, setFormError] = useState("");
  const [result, setResult] = useState<ServiceBatchResult | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshError, setRefreshError] = useState("");
  const [options, setOptions] = useState<ServiceBatchOptions | null>(null);
  const [selectedItems, setSelectedItems] = useState<string[]>([]);
  const [stockQuantities, setStockQuantities] = useState<Record<string, string>>({});
  const [custodyMode, setCustodyMode] = useState("indefinite");
  const [identity, setIdentity] = useState<{ body: Body; summary: string } | null>(null);

  async function loadOptions(afterSuccess = false) {
    setRefreshing(true);
    setError("");
    setRefreshError("");
    try {
      setOptions(await apiRequest<ServiceBatchOptions>("/service-batches/options/"));
    } catch (requestError) {
      const message = requestError instanceof ApiError ? requestError.message : "Não foi possível atualizar os materiais.";
      if (afterSuccess) setRefreshError(`Retirada confirmada. Falha ao atualizar opções: ${message}`);
      else setError(message);
    } finally {
      setRefreshing(false);
    }
  }

  useEffect(() => { void loadOptions(); }, []);

  async function complete(value: ServiceBatchResult | undefined, form?: HTMLFormElement) {
    if (!value) return;
    setResult(value);
    setIdentity(null);
    form?.reset();
    setSelectedItems([]);
    setStockQuantities({});
    setCustodyMode("indefinite");
    // O balcão volta a pedir a próxima matrícula.
    arrival.reset();
    await loadOptions(true);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!options) return;
    const element = event.currentTarget;
    const form = new FormData(element);
    const stockLines = options.stock.filter((line) => Number(stockQuantities[line.id]) > 0);
    if (selectedItems.length === 0 && stockLines.length === 0) {
      setFormError("Adicione ao menos um material com ou sem registro.");
      return;
    }
    setFormError("");
    const rawDue = String(form.get("due_at") ?? "");
    const stock = stockLines.map((line) => ({
      equipment_type_id: line.equipment_type_id, unit_id: line.unit_id,
      storage_location_id: line.storage_location_id, quantity: stockQuantities[line.id]
    }));
    const itemNames = options.items.filter((item) => selectedItems.includes(item.id)).map((item) => item.identifier);
    const stockNames = stockLines.map((line) => `${line.equipment_type}: ${stockQuantities[line.id]}`);
    const summary = `${person?.name ?? "Destinatário"} · ${[...itemNames, ...stockNames].join(", ")}`;
    const body: Body = {
      recipient_id: arrival.personId, item_ids: selectedItems,
      stock, custody_mode: custodyMode,
      due_at: custodyMode === "fixed_term" && rawDue ? new Date(rawDue).toISOString() : null,
      confirmed: form.get("confirmed") === "on"
    };
    if (faceRequired && arrival.verificationId) {
      const value = await request.execute("/service-batches/", { ...body, face_verification_id: arrival.verificationId }, summary);
      // Erro de preenchimento não gasta a verificação (a transação é desfeita no servidor);
      // só sucesso ou conflito, como verificação vencida, exigem nova identificação.
      if (value || request.failureStatus() === 409) arrival.consume();
      await complete(value, element);
      return;
    }
    if (faceRequired) {
      // ADR 0008: sem verificação válida, a identidade é confirmada antes do envio.
      setIdentity({ body, summary });
      return;
    }
    await complete(await request.execute("/service-batches/", body, summary), element);
  }

  async function confirmWithVerification(verificationId: string) {
    if (!identity) return;
    await complete(await request.execute("/service-batches/", { ...identity.body, face_verification_id: verificationId }, identity.summary));
  }

  const pending = request.pending && <section className="feedback warning" role="status"><p>Retirada aguardando confirmação: {request.pending.summary}</p><p>Recupere o resultado desta tentativa antes de iniciar outra retirada.</p><button className="button button-secondary" disabled={request.submitting} onClick={() => void request.execute().then((value) => complete(value))}>Verificar retirada</button></section>;
  const heading = (
    <section className="page-heading">
      <div><p className="context-label">Operação de balcão</p><h1>Retirada</h1><p>Identifique a pessoa pela matrícula e pelo rosto. Depois digite os materiais: com registro pelo número, sem registro pelo nome e quantidade.</p></div>
    </section>
  );
  const success = result && <div className="feedback success" role="status">Retirada confirmada. Comprovante <strong>{result.receipt_code}</strong>.</div>;

  if (!arrival.personId) {
    return (
      <>
        {heading}{success}{pending}
        {request.error && <div className="feedback error" role="alert">{request.error}</div>}
        {refreshError && <div className="feedback warning" role="status">{refreshError}<button className="button button-secondary" onClick={() => void loadOptions(true)}>Atualizar materiais</button></div>}
        <CounterEntry fixedOperation="checkout" faceRequired={faceRequired} />
      </>
    );
  }
  if (personError) {
    return <>{heading}<div className="feedback error" role="alert">{personError}</div><button className="button button-secondary" type="button" onClick={arrival.reset}>Identificar outra pessoa</button></>;
  }
  if (!options || !person) return <>{heading}{pending}{error ? <ErrorState message={error} onRetry={() => void loadOptions()} /> : <LoadingState />}</>;

  const available = options.items.filter((item) => !selectedItems.includes(item.id));
  const pickedItems = options.items.filter((item) => selectedItems.includes(item.id));
  const pickedStock = options.stock.filter((line) => Number(stockQuantities[line.id]) > 0);
  const locked = refreshing || request.submitting || Boolean(request.pending) || Boolean(refreshError) || Boolean(error);

  return (
    <>
      {heading}
      {request.error && <div className="feedback error" role="alert">{request.error}</div>}
      {pending}
      {refreshError && <div className="feedback warning" role="status">{refreshError}<button className="button button-secondary" onClick={() => void loadOptions(true)}>Atualizar materiais</button></div>}
      {error && <div className="feedback error" role="alert">{error}</div>}
      <PersonCard person={person} operation="checkout" verified={Boolean(arrival.verificationId)} faceRequired={faceRequired} disabled={request.submitting} onCancel={arrival.cancel} />
      {identity && (
        <IdentityCheck operation="checkout" personId={arrival.personId} personName={person.name}
          summary={identity.summary} busy={request.submitting}
          request={{ items: identity.body.item_ids, stock: identity.body.stock, custody_mode: identity.body.custody_mode, due_at: identity.body.due_at }}
          onApproved={(id) => void confirmWithVerification(id)} onBack={() => setIdentity(null)} />
      )}
      <form className="dialog-form" onSubmit={submit} hidden={Boolean(identity)} aria-label="Materiais da retirada">
        <fieldset disabled={locked}>
          <section className="detail-card material-section" aria-label="Materiais com registro">
            <h2>Com registro</h2>
            {options.items.length === 0 ? <p className="muted">Nenhum material com registro disponível.</p> : <RegisteredPicker options={available} onAdd={(id) => setSelectedItems((current) => [...current, id])} />}
            {pickedItems.length > 0 && (
              <ul className="picked" aria-label="Com registro selecionados">
                {pickedItems.map((item) => (
                  <li key={item.id}>
                    <span><strong>{item.identifier}</strong> · {item.equipment_type} · {item.unit}</span>
                    <button className="button button-quiet" type="button" aria-label={`Remover ${item.identifier}`} onClick={() => setSelectedItems((current) => current.filter((id) => id !== item.id))}>Remover</button>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="detail-card material-section" aria-label="Materiais sem registro">
            <h2>Sem registro</h2>
            {options.stock.length === 0 ? <p className="muted">Nenhum saldo de material sem registro disponível.</p> : (
              <UnregisteredPicker
                options={options.stock.map((line) => ({ id: line.id, name: line.equipment_type, detail: `${line.unit} · ${line.storage_location}`, max: line.quantity }))}
                onAdd={(id, quantity) => setStockQuantities((current) => ({ ...current, [id]: quantity }))} />
            )}
            {pickedStock.length > 0 && (
              <ul className="picked" aria-label="Sem registro selecionados">
                {pickedStock.map((line) => (
                  <li key={line.id}>
                    <span><strong>{formatQuantity(stockQuantities[line.id])}</strong> · {line.equipment_type} · {line.unit} · {line.storage_location}</span>
                    <button className="button button-quiet" type="button" aria-label={`Remover ${line.equipment_type}`} onClick={() => setStockQuantities((current) => { const next = { ...current }; delete next[line.id]; return next; })}>Remover</button>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="detail-card material-section">
            <label><span>Modalidade</span><select name="custody_mode" value={custodyMode} onChange={(event) => setCustodyMode(event.target.value)}><option value="shift">Por turno</option><option value="fixed_term">Prazo determinado</option><option value="indefinite">Prazo indeterminado</option></select></label>
            {/* Só o prazo determinado tem data; nas demais modalidades o servidor recusa prazo. */}
            {custodyMode === "fixed_term" && <label><span>Prazo de devolução</span><input name="due_at" type="datetime-local" required /></label>}
            {formError && <div className="feedback error" role="alert">{formError}</div>}
            <label className="checkbox"><input name="confirmed" type="checkbox" required /><span>Confirmo pessoa, materiais e modalidade.</span></label>
            <button className="button button-primary" disabled={request.submitting}>{request.submitting ? "Confirmando…" : faceRequired && !arrival.verificationId ? "Confirmar identidade" : "Confirmar retirada"}</button>
          </section>
        </fieldset>
      </form>
    </>
  );
}
