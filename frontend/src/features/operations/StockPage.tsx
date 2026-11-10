import { FormEvent, useEffect, useState } from "react";
import { ApiError, apiRequest } from "../../api/client";
import type { Session } from "../../api/types";
import { ErrorState, LoadingState } from "../../components/Feedback";
import { useConfirmedRequest } from "../../hooks/useConfirmedRequest";

interface StockOptions {
  equipment_types: Array<{ id: string; name: string }>;
  units: Array<{ id: string; name: string; can_receive: boolean; locations: Array<{ id: string; name: string }> }>;
}
interface Balance {
  id: string;
  equipment_type: string;
  quantity: string;
  unit: { id: string; name: string };
  storage_location: { id: string; name: string };
}
interface Loan {
  id: string;
  person: string;
  equipment_type: string;
  unit: string;
  location: string;
  quantity: string;
  can_settle: boolean;
}
interface StockData { options: StockOptions; balances: Balance[]; loans: Loan[] }
type Action = { type: "receive" } | { type: "return" | "consume"; loan: Loan };

export function StockPage({ session }: { session: Session }) {
  const [data, setData] = useState<StockData | null>(null);
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const [refreshError, setRefreshError] = useState("");
  const [success, setSuccess] = useState("");
  const [action, setAction] = useState<Action | null>(null);
  const [unitId, setUnitId] = useState("");
  const [review, setReview] = useState<{ path: string; body: Record<string, unknown>; summary: string } | null>(null);
  const request = useConfirmedRequest<{ id: string }>(
    `sigab:${session.organization.id}:${session.user.id}:stock`
  );

  async function load(afterSuccess = false) {
    setRefreshing(true);
    setError("");
    setRefreshError("");
    try {
      const [options, balances, loans] = await Promise.all([
        apiRequest<StockOptions>("/stock/options/"),
        apiRequest<Balance[]>("/stock/positions/"),
        apiRequest<Loan[]>("/stock/loans/")
      ]);
      setData({ options, balances, loans });
    } catch (cause) {
      const message = cause instanceof ApiError ? cause.message : "Não foi possível atualizar o estoque.";
      if (afterSuccess) setRefreshError(`Operação confirmada. Falha ao atualizar saldos: ${message}`);
      else setError(message);
    } finally {
      setRefreshing(false);
    }
  }
  useEffect(() => { void load(); }, []);

  async function complete(result: { id: string } | undefined) {
    if (!result) return;
    setSuccess("Operação confirmada.");
    setAction(null);
    setReview(null);
    setUnitId("");
    await load(true);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!action || !data) return;
    const form = new FormData(event.currentTarget);
    const quantity = String(form.get("quantity") ?? "");
    const reason = String(form.get("reason") ?? "").trim();
    let path: string;
    let body: Record<string, unknown>;
    let summary: string;
    if (action.type === "receive") {
      const kind = data.options.equipment_types.find((value) => value.id === form.get("equipment_type_id"));
      const unit = data.options.units.find((value) => value.id === unitId);
      const location = unit?.locations.find((value) => value.id === form.get("storage_location_id"));
      path = "/stock/positions/";
      body = { equipment_type_id: kind?.id, unit_id: unitId, storage_location_id: location?.id, quantity, reason, confirmed: true };
      summary = `Entrada de ${quantity} · ${kind?.name} · ${unit?.name} · ${location?.name} · ${reason}`;
    } else {
      path = `/stock/loans/${action.loan.id}/settle/`;
      body = { quantity, disposition: action.type, reason, confirmed: true };
      summary = `${action.type === "return" ? "Devolução apta" : "Consumo"} de ${quantity} · ${action.loan.person} · ${action.loan.equipment_type} · ${action.loan.unit} · ${reason}`;
    }
    setReview({ path, body, summary });
  }

  const pending = request.pending && <section className="feedback warning" role="status"><p>Operação aguardando confirmação: {request.pending.summary}</p><p>Verifique esta tentativa antes de registrar outra operação.</p><button className="button button-secondary" disabled={request.submitting} onClick={() => void request.execute().then(complete)}>Verificar operação</button></section>;
  if (!data) return <>{pending}{request.error && <p role="alert">{request.error}</p>}{error ? <ErrorState message={error} onRetry={() => void load()} /> : <LoadingState label="Carregando estoque" />}</>;
  const unit = data.options.units.find((value) => value.id === unitId);
  const blocked = refreshing || request.submitting || Boolean(request.pending) || Boolean(refreshError) || Boolean(error);
  return <>
    <section className="page-heading"><div><p className="context-label">Materiais quantitativos</p><h1>Estoque e pendências</h1><p>Registre entradas, devoluções aptas e consumo justificado. Confira os saldos após cada operação.</p></div>
      {data.options.units.some((value) => value.can_receive) && <button className="button button-primary" disabled={blocked} onClick={() => { setAction({ type: "receive" }); setReview(null); setSuccess(""); }}>Registrar entrada</button>}
    </section>
    {pending}
    {request.error && <div className="feedback error" role="alert">{request.error}</div>}
    {success && <div className="feedback success" role="status">{success}</div>}
    {(error || refreshError) && <div className="feedback warning" role="alert">{error || refreshError}<button className="button button-secondary" onClick={() => void load(Boolean(success))}>Atualizar estoque</button></div>}
    {action && !request.pending && <section className="detail-card stock-action">
      <h2>{action.type === "receive" ? "Entrada de estoque" : action.type === "return" ? "Devolução apta" : "Justificar consumo"}</h2>
      {review && <form className="dialog-form" aria-label="Resumo da operação" onSubmit={(event) => {
        event.preventDefault();
        void request.execute(review.path, review.body, review.summary).then(complete);
      }}><p>{review.summary}</p><label className="confirmation"><input type="checkbox" required /><span>Conferi material, quantidade, destino e justificativa desta operação.</span></label><div className="dialog-actions"><button className="button button-quiet" type="button" disabled={blocked} onClick={() => setReview(null)}>Voltar</button><button className="button button-primary" disabled={blocked}>Confirmar operação</button></div></form>}
      <form className="dialog-form" hidden={Boolean(review)} onSubmit={submit}><fieldset disabled={blocked}><legend>Conferência da operação</legend>
        {action.type === "receive" ? <>
          <label><span>Tipo de material</span><select name="equipment_type_id" required defaultValue=""><option value="" disabled>Selecione</option>{data.options.equipment_types.map((kind) => <option key={kind.id} value={kind.id}>{kind.name}</option>)}</select></label>
          <label><span>Unidade de entrada</span><select required value={unitId} onChange={(event) => setUnitId(event.target.value)}><option value="" disabled>Selecione</option>{data.options.units.filter((value) => value.can_receive).map((value) => <option key={value.id} value={value.id}>{value.name}</option>)}</select></label>
          <label><span>Local de guarda</span><select name="storage_location_id" required defaultValue="" key={unitId}><option value="" disabled>Selecione</option>{unit?.locations.map((location) => <option key={location.id} value={location.id}>{location.name}</option>)}</select></label>
        </> : <><p>{action.loan.person} · {action.loan.equipment_type} · {action.loan.unit} · {action.loan.location}</p><p>Pendência atual: <strong>{action.loan.quantity}</strong></p></>}
        <label><span>Quantidade</span><input name="quantity" type="number" min="0.001" step="0.001" max={action.type === "receive" ? undefined : action.loan.quantity} required /></label>
        <label><span>{action.type === "receive" ? "Referência ou justificativa da entrada" : action.type === "consume" ? "Justificativa do consumo" : "Observação da devolução (opcional)"}</span><textarea name="reason" maxLength={500} required={action.type !== "return"} /></label>
        {action.type === "return" && <p className="muted">Confirme que todo o material informado está apto. Material inapto não deve ser registrado por este fluxo.</p>}
        <div className="dialog-actions"><button className="button button-quiet" type="button" onClick={() => setAction(null)}>Cancelar</button><button className="button button-primary" disabled={blocked}>Revisar operação</button></div>
      </fieldset></form>
    </section>}
    <section className="list-panel" aria-label="Saldos disponíveis"><h2 className="list-summary">Saldos disponíveis</h2>{data.balances.length === 0 ? <p className="empty-state">Nenhum saldo registrado.</p> : <ul className="sub-list">{data.balances.map((balance) => <li key={balance.id}><span>{balance.equipment_type} · {balance.unit.name} · {balance.storage_location.name}</span><strong>Disponível: {balance.quantity}</strong></li>)}</ul>}</section>
    <section className="list-panel" aria-label="Pendências quantitativas"><h2 className="list-summary">Pendências quantitativas</h2>{data.loans.length === 0 ? <p className="empty-state">Nenhuma pendência quantitativa.</p> : <ul className="sub-list">{data.loans.map((loan) => <li key={loan.id}><span>{loan.person} · {loan.equipment_type} · {loan.unit} · {loan.location}<strong>Em aberto: {loan.quantity}</strong></span>{loan.can_settle && <div className="dialog-actions"><button className="button button-secondary" disabled={blocked} onClick={() => { setAction({ type: "return", loan }); setReview(null); setSuccess(""); }}>Devolver apto</button><button className="button button-secondary" disabled={blocked} onClick={() => { setAction({ type: "consume", loan }); setReview(null); setSuccess(""); }}>Justificar consumo</button></div>}</li>)}</ul>}</section>
  </>;
}
