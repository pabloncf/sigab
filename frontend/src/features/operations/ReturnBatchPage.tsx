import { FormEvent, useEffect, useState } from "react";
import { apiRequest, describeError } from "../../api/client";
import type { ReturnBatchResult, ReturnOptions, Session } from "../../api/types";
import { ErrorState, LoadingState } from "../../components/Feedback";
import { formatQuantity, scopeLabel } from "../../components/format";
import { useConfirmedRequest } from "../../hooks/useConfirmedRequest";
import { CounterEntry } from "./CounterEntry";
import { IdentityCheck } from "./IdentityCheck";
import { RegisteredPicker, UnregisteredPicker } from "./MaterialPickers";
import { PersonCard, useCounterPerson } from "./PersonCard";
import { useCounterArrival } from "./useCounterArrival";

interface ItemCheck {
  condition: "fit" | "unfit";
  reason: string;
}

/**
 * Devolução no balcão (SIGAB-082, RF-20 a RF-23): a pessoa é identificada pela matrícula e
 * pelo rosto; o operador digita os materiais devolvidos, em listas separadas com e sem
 * registro, e confere a condição de cada item.
 */
export function ReturnBatchPage({ session }: { session: Session }) {
  const faceRequired = Boolean(session.permissions.identity_check_required);
  const arrival = useCounterArrival();
  const { person, error: personError } = useCounterPerson(arrival.personId);
  const request = useConfirmedRequest<ReturnBatchResult>(
    `sigab:${session.organization.id}:${session.user.id}:return`
  );
  const [possession, setPossession] = useState<ReturnOptions | null>(null);
  const [checks, setChecks] = useState<Record<string, ItemCheck>>({});
  const [quantities, setQuantities] = useState<Record<string, string>>({});
  const [review, setReview] = useState<{ body: Record<string, unknown>; summary: string; lines: string[] } | null>(null);
  const [result, setResult] = useState<ReturnBatchResult | null>(null);
  const [identityStep, setIdentityStep] = useState(false);
  const [error, setError] = useState("");
  const [formError, setFormError] = useState("");

  async function loadPossession(id: string) {
    setPossession(null);
    setChecks({});
    setQuantities({});
    setReview(null);
    if (!id) return;
    setError("");
    try {
      setPossession(await apiRequest<ReturnOptions>(`/return-batches/options/?person=${id}`));
    } catch (cause) {
      setError(describeError(cause));
    }
  }

  useEffect(() => { void loadPossession(arrival.personId); }, [arrival.personId]);

  function updateCheck(id: string, change: Partial<ItemCheck>) {
    setChecks((current) => ({ ...current, [id]: { ...current[id], ...change } }));
  }

  async function complete(value: ReturnBatchResult | undefined) {
    if (!value) return;
    setResult(value);
    setReview(null);
    setIdentityStep(false);
    // O balcão volta a pedir a próxima matrícula.
    arrival.reset();
  }

  function prepare(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!possession) return;
    const items = (possession.items ?? []).filter((item) => checks[item.id]);
    const stock = (possession.stock ?? []).filter((loan) => Number(quantities[loan.loan_id] || 0) > 0);
    if (items.length === 0 && stock.length === 0) {
      setFormError("Adicione ao menos um material com ou sem registro.");
      return;
    }
    setFormError("");
    const lines = [
      ...items.map((item) => {
        const value = checks[item.id];
        return `${item.identifier} · ${item.equipment_type} · ${value.condition === "fit" ? "apto" : `inapto (${value.reason.trim()})`}`;
      }),
      ...stock.map((loan) => `${formatQuantity(quantities[loan.loan_id])} de ${loan.equipment_type} · apto`)
    ];
    setReview({
      lines,
      summary: `Devolução de ${person?.name ?? "pessoa"}: ${lines.join("; ")}`,
      body: {
        person_id: arrival.personId,
        items: items.map((item) => ({ item_id: item.id, condition: checks[item.id].condition, reason: checks[item.id].condition === "unfit" ? checks[item.id].reason.trim() : "" })),
        stock: stock.map((loan) => ({ loan_id: loan.loan_id, quantity: quantities[loan.loan_id] })),
        confirmed: true
      }
    });
  }

  function confirm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!review) return;
    if (faceRequired && arrival.verificationId) {
      // Identidade já confirmada na identificação (matrícula + face).
      void request.execute("/return-batches/", { ...review.body, face_verification_id: arrival.verificationId }, review.summary)
        .then((value) => {
          if (value || request.failureStatus() === 409) arrival.consume();
          return complete(value);
        });
    } else if (faceRequired) setIdentityStep(true);
    else void request.execute("/return-batches/", review.body, review.summary).then(complete);
  }

  const blocked = request.submitting || Boolean(request.pending);
  const pending = request.pending && (
    <section className="feedback warning" role="status">
      <p>Devolução aguardando confirmação: {request.pending.summary}</p>
      <p>Recupere o resultado desta tentativa antes de registrar outra devolução.</p>
      <button className="button button-secondary" disabled={request.submitting} onClick={() => void request.execute().then(complete)}>Verificar devolução</button>
    </section>
  );
  const heading = (
    <section className="page-heading">
      <div>
        <p className="context-label">Operação de balcão</p>
        <h1>Devolução</h1>
        <p>Identifique a pessoa pela matrícula e pelo rosto. Depois digite os materiais devolvidos e marque apto ou inapto. A confirmação é atômica: todos voltam juntos ou nenhum volta.</p>
      </div>
    </section>
  );
  const success = result && (
    <div className="feedback success" role="status">
      Devolução confirmada. Comprovante <strong>{result.receipt_code}</strong> · {result.items.length} {result.items.length === 1 ? "item" : "itens"} com registro, {result.stock.length} {result.stock.length === 1 ? "linha" : "linhas"} sem registro.
    </div>
  );

  if (!arrival.personId) {
    return <>{heading}{success}{pending}{request.error && <div className="feedback error" role="alert">{request.error}</div>}<CounterEntry fixedOperation="return" faceRequired={faceRequired} /></>;
  }
  if (personError) {
    return <>{heading}<div className="feedback error" role="alert">{personError}</div><button className="button button-secondary" type="button" onClick={arrival.reset}>Identificar outra pessoa</button></>;
  }
  if (!possession || !person) return <>{heading}{pending}{error ? <ErrorState message={error} onRetry={() => void loadPossession(arrival.personId)} /> : <LoadingState label="Carregando posse atual" />}</>;

  const items = possession.items ?? [];
  const loans = possession.stock ?? [];
  const pickedItems = items.filter((item) => checks[item.id]);
  const pickedLoans = loans.filter((loan) => Number(quantities[loan.loan_id]) > 0);
  const waiting = [...items.filter((item) => item.awaiting_approval).map((item) => item.identifier), ...loans.filter((loan) => loan.awaiting_approval).map((loan) => loan.equipment_type)];

  return (
    <>
      {heading}
      {pending}
      {request.error && <div className="feedback error" role="alert">{request.error}</div>}
      {error && <div className="feedback error" role="alert">{error}</div>}
      <PersonCard person={person} operation="return" verified={Boolean(arrival.verificationId)} faceRequired={faceRequired} disabled={request.submitting} onCancel={arrival.cancel} />
      {items.length === 0 && loans.length === 0 && <p className="empty-state">{person.name} não tem material em posse {scopeLabel(session)}.</p>}
      {waiting.length > 0 && <div className="feedback warning" role="status">Devolução aguardando aprovação do termo: {waiting.join(", ")}.</div>}

      <form className="dialog-form" onSubmit={prepare} hidden={Boolean(review)} aria-label="Materiais da devolução">
        <fieldset disabled={blocked}>
          <section className="detail-card material-section" aria-label="Materiais com registro">
            <h2>Com registro</h2>
            {items.length === 0 ? <p className="muted">Nenhum material com registro em posse.</p> : (
              <RegisteredPicker options={items.filter((item) => !item.awaiting_approval && !checks[item.id])}
                onAdd={(id) => setChecks((current) => ({ ...current, [id]: { condition: "fit", reason: "" } }))} />
            )}
            {pickedItems.length > 0 && (
              <ul className="picked" aria-label="Com registro selecionados">
                {pickedItems.map((item) => {
                  const value = checks[item.id];
                  return (
                    <li key={item.id}>
                      <span><strong>{item.identifier}</strong> · {item.equipment_type} · {item.unit}</span>
                      <button className="button button-quiet" type="button" aria-label={`Remover ${item.identifier}`} onClick={() => setChecks((current) => { const next = { ...current }; delete next[item.id]; return next; })}>Remover</button>
                      <div className="return-line-fields">
                        <label><span>Condição de {item.identifier}</span><select value={value.condition} onChange={(event) => updateCheck(item.id, { condition: event.target.value as ItemCheck["condition"] })}><option value="fit">Apto</option><option value="unfit">Inapto</option></select></label>
                        {value.condition === "unfit" && <label><span>Motivo de inapto de {item.identifier}</span><textarea required maxLength={200} value={value.reason} onChange={(event) => updateCheck(item.id, { reason: event.target.value })} /></label>}
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>

          <section className="detail-card material-section" aria-label="Materiais sem registro">
            <h2>Sem registro</h2>
            {loans.length === 0 ? <p className="muted">Nenhuma pendência de material sem registro.</p> : (
              <>
                <UnregisteredPicker
                  options={loans.filter((loan) => !loan.awaiting_approval).map((loan) => ({ id: loan.loan_id, name: loan.equipment_type, detail: loan.unit, max: loan.open_quantity }))}
                  onAdd={(id, quantity) => setQuantities((current) => ({ ...current, [id]: quantity }))} />
                <p className="muted">Devolva aqui apenas material apto. Consumo justificado fica no Estoque; material sem registro inapto aguarda a decisão SIGAB-008.</p>
              </>
            )}
            {pickedLoans.length > 0 && (
              <ul className="picked" aria-label="Sem registro selecionados">
                {pickedLoans.map((loan) => (
                  <li key={loan.loan_id}>
                    <span><strong>{formatQuantity(quantities[loan.loan_id])}</strong> de {formatQuantity(loan.open_quantity)} · {loan.equipment_type} · {loan.unit}</span>
                    <button className="button button-quiet" type="button" aria-label={`Remover ${loan.equipment_type}`} onClick={() => setQuantities((current) => { const next = { ...current }; delete next[loan.loan_id]; return next; })}>Remover</button>
                  </li>
                ))}
              </ul>
            )}
          </section>
          {formError && <div className="feedback error" role="alert">{formError}</div>}
          <div className="dialog-actions"><button className="button button-primary">Revisar devolução</button></div>
        </fieldset>
      </form>

      {review && (
        <section className="detail-card">
          <form className="dialog-form" aria-label="Resumo da devolução" hidden={identityStep} onSubmit={confirm}>
            <h2>Resumo da devolução</h2>
            <ul className="sub-list">{review.lines.map((line) => <li key={line}>{line}</li>)}</ul>
            <label className="confirmation"><input type="checkbox" required /><span>Conferi pessoa, materiais, quantidades e condição de cada item.</span></label>
            <div className="dialog-actions">
              <button className="button button-quiet" type="button" disabled={blocked} onClick={() => setReview(null)}>Voltar</button>
              <button className="button button-primary" disabled={blocked}>{request.submitting ? "Confirmando…" : faceRequired && !arrival.verificationId ? "Confirmar identidade" : "Confirmar devolução"}</button>
            </div>
          </form>
          {identityStep && (
            <IdentityCheck operation="return" personId={arrival.personId} personName={person.name}
              summary={review.summary} busy={request.submitting}
              request={{ items: review.body.items, stock: review.body.stock }}
              onApproved={(id) => void request.execute("/return-batches/", { ...review.body, face_verification_id: id }, review.summary).then(complete)}
              onBack={() => setIdentityStep(false)} />
          )}
        </section>
      )}
    </>
  );
}
