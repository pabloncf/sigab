import { useEffect, useState } from "react";
import { ApiError, apiRequest } from "../../api/client";
import type { MyPossessions } from "../../api/types";
import { ErrorState, LoadingState } from "../../components/Feedback";

export function MyPossessionsPage() {
  const [data, setData] = useState<MyPossessions | null>(null);
  const [error, setError] = useState("");

  async function load() {
    setError("");
    try {
      setData(await apiRequest<MyPossessions>("/me/possessions/"));
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "Erro inesperado.");
    }
  }

  useEffect(() => { void load(); }, []);

  if (error) return <ErrorState message={error} onRetry={() => void load()} />;
  if (!data) return <LoadingState />;
  return (
    <>
      <section className="page-heading">
        <div>
          <p className="context-label">Autosserviço</p>
          <h1>Minha posse</h1>
          <p>Somente materiais vinculados à sua pessoa. Nenhum identificador de terceiro é aceito nesta consulta.</p>
        </div>
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
