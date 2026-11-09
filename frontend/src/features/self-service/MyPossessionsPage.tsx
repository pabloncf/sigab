import { useEffect, useState } from "react";
import { ApiError, apiRequest } from "../../api/client";
import type { MyPossessions, PersonalHistory, PersonalReceipt } from "../../api/types";
import { ErrorState, LoadingState } from "../../components/Feedback";

export function MyPossessionsPage() {
  const [data, setData] = useState<MyPossessions | null>(null);
  const [error, setError] = useState("");
  const [history, setHistory] = useState<PersonalHistory | null>(null);
  const [receipt, setReceipt] = useState<PersonalReceipt | null>(null);
  const [receiptLoading, setReceiptLoading] = useState(false);

  async function load() {
    setError("");
    try {
      const [possessions, personalHistory] = await Promise.all([
        apiRequest<MyPossessions>("/me/possessions/"),
        apiRequest<PersonalHistory>("/me/history/")
      ]);
      setData(possessions);
      setHistory(personalHistory);
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "Erro inesperado.");
    }
  }

  useEffect(() => { void load(); }, []);

  async function openReceipt(id: string) {
    setReceiptLoading(true);
    setError("");
    setReceipt(null);
    try {
      setReceipt(await apiRequest<PersonalReceipt>(`/me/receipts/${id}/`));
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "Erro inesperado.");
    } finally {
      setReceiptLoading(false);
    }
  }

  const formatDate = (value: string) => new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" }).format(new Date(value));
  const labels: Record<string, string> = { checkout: "Saída", return: "Devolução", consume: "Consumo", reversal: "Estorno" };
  const entries = history ? [...history.individual, ...history.quantitative].sort((a, b) => Date.parse(b.occurred_at) - Date.parse(a.occurred_at)) : [];

  if (error) return <ErrorState message={error} onRetry={() => void load()} />;
  if (!data) return <LoadingState />;
  return (
    <>
      <section className="page-heading">
        <div>
          <p className="context-label">Autosserviço</p>
          <h1>Minha posse</h1>
          <p>Consulte seus materiais, movimentações e comprovantes de atendimento.</p>
        </div>
      </section>
      <section className="history-card" aria-label="Meu histórico">
        <h2>Meu histórico</h2>
        {entries.length === 0 ? <p>Nenhuma movimentação registrada.</p> : <ol className="timeline">{entries.map((entry) => <li key={entry.id}><div><strong>{labels[entry.type] ?? entry.type} · {entry.equipment_type}</strong><small>{entry.identifier ?? `${entry.quantity} unidades`} · {formatDate(entry.occurred_at)}</small></div></li>)}</ol>}
      </section>
      <section className="detail-card" aria-label="Meus comprovantes">
        <h2>Meus comprovantes</h2>
        {!history?.receipts.length ? <p>Nenhum comprovante disponível.</p> : <ul className="sub-list">{history.receipts.map((entry) => <li key={entry.id}><span>{entry.code} · {formatDate(entry.confirmed_at)}</span><button className="button button-secondary" disabled={receiptLoading} onClick={() => void openReceipt(entry.id)}>Abrir {entry.code}</button></li>)}</ul>}
        {receiptLoading && <LoadingState label="Carregando comprovante" />}
        {receipt && <article aria-label={`Comprovante ${receipt.receipt_code}`}><h3>{receipt.receipt_code}</h3><p>{receipt.recipient.name} · {formatDate(receipt.confirmed_at)}</p><p>Operador: {receipt.operator.username}</p><p>Modalidade: {({ shift: "Por turno", fixed_term: "Prazo determinado", indefinite: "Prazo indeterminado" } as Record<string, string>)[receipt.custody_mode] ?? receipt.custody_mode}{receipt.due_at && ` · até ${formatDate(receipt.due_at)}`}</p><ul>{receipt.items.map((item) => <li key={item.id}>{item.identifier} · {item.equipment_type}</li>)}{receipt.stock.map((line) => <li key={line.loan_id}>{line.equipment_type} · entregue: {line.quantity} · em aberto: {line.open_quantity}</li>)}</ul></article>}
      </section>
      <section className="list-panel" aria-label="Materiais sob minha responsabilidade">
        <div className="list-summary"><strong>{data.possessions.length}</strong> materiais em posse</div>
        {data.possessions.length === 0 ? (
          <div className="empty-state"><h2>Nenhuma pendência</h2><p>Não há material em posse desta conta.</p></div>
        ) : (
          <div className="item-list">
            {data.possessions.map((entry) => (
              <div className="item-row" key={`${entry.kind}-${entry.id}`}>
                <span className="item-identity"><strong>{entry.identifier ?? entry.equipment_type}</strong><small>{entry.equipment_type}</small></span>
                <span className="status-badge success">{entry.kind === "individual" ? "Individual" : `${entry.quantity} em aberto`}</span>
                <span className="holder"><small>Unidade</small>{entry.unit}</span>
              </div>
            ))}
          </div>
        )}
      </section>
    </>
  );
}
