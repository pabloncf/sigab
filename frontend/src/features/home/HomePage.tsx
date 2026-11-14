import { useEffect, useState } from "react";
import { apiRequest, describeError } from "../../api/client";
import type { Overview, Session } from "../../api/types";
import { ErrorState, LoadingState } from "../../components/Feedback";
import { formatDateTime, formatQuantity, scopeLabel } from "../../components/format";
import { CounterEntry } from "../operations/CounterEntry";

export function HomePage({ session }: { session: Session }) {
  const [data, setData] = useState<Overview | null>(null);
  const [error, setError] = useState("");
  const [entryOpen, setEntryOpen] = useState(false);

  async function load() {
    setError("");
    try {
      setData(await apiRequest<Overview>("/overview/"));
    } catch (cause) {
      setError(describeError(cause));
    }
  }

  useEffect(() => { void load(); }, []);

  // Espelha a permissão do backend só para exibir o botão; a API continua decidindo.
  const counter = Boolean(session.permissions.can_checkout || session.permissions.can_return);

  const scope = scopeLabel(session);

  return (
    <>
      <section className="page-heading">
        <div>
          <p className="context-label">{session.organization.name}</p>
          <h1>Início</h1>
          <p>O que exige atenção, a situação da reserva e as últimas retiradas e devoluções {scope}.</p>
        </div>
      </section>

      {counter && (entryOpen ? <CounterEntry onClose={() => setEntryOpen(false)} faceRequired={Boolean(session.permissions.identity_check_required)} /> : (
        <div className="quick-links">
          <button className="button button-primary" type="button" onClick={() => setEntryOpen(true)}>Entrada e saída</button>
        </div>
      ))}

      {error ? <ErrorState message={error} onRetry={() => void load()} /> : !data ? <LoadingState label="Carregando resumo" /> : (
        <>
          <AttentionSection data={data} />

          <h2 className="section-title">Itens com registro</h2>
          <ul className="stat-grid" aria-label="Itens com registro por situação">
            <StatLink label="Disponível" value={data.individual.totals.available} href="/acervo?situacao=available" />
            <StatLink label="Em posse" value={data.individual.totals.in_custody} href="/acervo?situacao=in_custody" />
            <StatLink label="Indisponível (inapto)" value={data.individual.totals.unavailable} href="/acervo?situacao=unavailable" />
            <StatLink label="Total ativo" value={data.individual.totals.total} href="/acervo" />
          </ul>

          <h2 className="section-title">Material sem registro</h2>
          {data.quantitative.length === 0 ? <p className="inline-empty">Nenhum material sem registro {scope}.</p> : (
            <section className="list-panel" aria-label="Saldos de material sem registro">
              <ul className="sub-list feed">
                {data.quantitative.map((row) => (
                  <li key={row.equipment_type_id}>
                    <a href={`/acervo?aba=sem-registro&tipo=${row.equipment_type_id}`}><strong>{row.equipment_type}</strong></a>
                    <span className="numbers">
                      <span>Em reserva: <strong>{formatQuantity(row.reserve)}</strong></span>
                      <span>Em posse: <strong>{formatQuantity(row.in_custody)}</strong></span>
                      <span>Total: <strong>{formatQuantity(row.total)}</strong></span>
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <div className="section-header">
            <h2 className="section-title">Últimas retiradas e devoluções</h2>
            {counter && <a className="text-link" href="/atendimento/registro">Ver registro completo ›</a>}
          </div>
          {data.recent.length === 0 ? <p className="inline-empty">Nenhuma retirada ou devolução registrada {scope}.</p> : (
          <section className="list-panel" aria-label="Últimas retiradas e devoluções">
              <ul className="sub-list feed">
                {data.recent.map((row) => (
                  <li key={`${row.kind}-${row.id}`}>
                    <span>
                      <strong>
                        {row.type_label} · {row.item_id ? <a href={`/items/${row.item_id}`}>{row.identifier}</a> : `${formatQuantity(row.quantity ?? "0")} ${row.equipment_type}`}
                        {row.item_id && ` · ${row.equipment_type}`}
                      </strong>
                      <small>{row.type === "checkout" ? "Retirou" : "Devolveu"}: {row.recipient ?? "—"} · {row.type === "checkout" ? "Entregue por" : "Recebido por"}: {row.operator} · {row.unit}</small>
                    </span>
                    <small>{formatDateTime(row.occurred_at)}{row.receipt_code && ` · ${row.receipt_code}`}</small>
                  </li>
                ))}
              </ul>
          </section>
          )}
        </>
      )}
    </>
  );
}

function StatLink({ label, value, href, tone }: { label: string; value: number; href?: string; tone?: "danger" | "warning" }) {
  const content = <><small>{label}</small><strong>{value}</strong></>;
  return (
    <li className={`stat${tone ? ` stat-${tone}` : ""}`}>
      {href ? <a className="stat-link" href={href}>{content}<span className="stat-cta">Ver consulta ›</span></a> : content}
    </li>
  );
}

/** Exceções primeiro: prazo vencido e item inapto exigem ação; o resto é situação. */
function AttentionSection({ data }: { data: Overview }) {
  const overdue = data.pending.quantitative_overdue;
  const unfit = data.individual.totals.unavailable;
  if (overdue === 0 && unfit === 0) {
    return <div className="feedback success attention-ok" role="status">Nenhum prazo vencido de material sem registro e nenhum item inapto.</div>;
  }
  return (
    <section className="attention" aria-labelledby="atencao">
      <h2 className="section-title" id="atencao">Requer atenção</h2>
      <ul className="stat-grid">
        {overdue > 0 && <StatLink label={overdue === 1 ? "Retirada com prazo vencido" : "Retiradas com prazo vencido"} value={overdue} tone="danger" />}
        {unfit > 0 && <StatLink label={unfit === 1 ? "Item inapto aguardando liberação" : "Itens inaptos aguardando liberação"} value={unfit} href="/acervo?situacao=unavailable" tone="warning" />}
      </ul>
      {overdue > 0 && <a className="text-link" href="/estoque">Consultar saldos e pendências do estoque ›</a>}
    </section>
  );
}
