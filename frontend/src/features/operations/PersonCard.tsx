import { useEffect, useState } from "react";
import { ApiError, apiRequest, describeError } from "../../api/client";
import type { CounterIdentity } from "../../api/types";

/** Pessoa identificada no balcão; reabre pelo id da URL com as mesmas regras da matrícula. */
export function useCounterPerson(personId: string) {
  const [person, setPerson] = useState<CounterIdentity | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    setPerson(null);
    setError("");
    if (!personId) return;
    apiRequest<CounterIdentity>(`/counter/identify/?person=${encodeURIComponent(personId)}`).then(setPerson)
      .catch((cause) => setError(cause instanceof ApiError && cause.status === 404 ? "Pessoa não encontrada ou sem vínculo ativo." : describeError(cause)));
  }, [personId]);
  return { person, error };
}

interface PersonCardProps {
  person: CounterIdentity;
  operation: "checkout" | "return";
  verified: boolean;
  faceRequired: boolean;
  disabled?: boolean;
  onCancel: () => Promise<void>;
}

/** Quem está retirando ou devolvendo, como foi identificado, e a opção de desistir. */
export function PersonCard({ person, operation, verified, faceRequired, disabled, onCancel }: PersonCardProps) {
  const [asking, setAsking] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function cancel() {
    setBusy(true);
    setError("");
    try {
      await onCancel();
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "Não foi possível cancelar.");
      setBusy(false);
    }
  }

  const status = verified ? "Identidade confirmada por reconhecimento facial."
    : faceRequired ? (person.biometric_enrolled ? "Identidade ainda não confirmada: ao concluir, faça o reconhecimento facial ou gere o termo." : "Sem biometria cadastrada: ao concluir, a operação gera o termo para assinatura e aprovação.")
    : "Identificada pela matrícula.";

  return (
    <section className={`detail-card person-card ${verified ? "verified" : ""}`} aria-label="Pessoa identificada">
      <div>
        <p className="context-label">{operation === "checkout" ? "Retirada por" : "Devolução por"}</p>
        <h2>{person.name}</h2>
        <p>Matrícula <strong>{person.registration}</strong></p>
        <p className={verified ? "status-badge success" : "muted"} role="status">{status}</p>
      </div>
      {!asking ? (
        <button className="button button-quiet" type="button" disabled={disabled} onClick={() => setAsking(true)}>Cancelar operação</button>
      ) : (
        <div className="actions-inline">
          <span>Descartar a identificação e voltar ao Início? Nada será movimentado.</span>
          <button className="button button-quiet" type="button" disabled={busy} onClick={() => setAsking(false)}>Continuar operação</button>
          <button className="button button-secondary" type="button" disabled={busy} onClick={() => void cancel()}>{busy ? "Cancelando…" : "Sim, cancelar"}</button>
        </div>
      )}
      {error && <p role="alert">{error}</p>}
    </section>
  );
}
