import { FormEvent, useState } from "react";
import { ApiError, apiRequest, postForm, describeError } from "../../api/client";
import type { CounterIdentity, FaceVerificationResult } from "../../api/types";
import { FaceCapture } from "../../components/FaceCapture";

type Operation = "checkout" | "return";

const OPERATION_PATH: Record<Operation, string> = {
  checkout: "/atendimento",
  return: "/atendimento/devolucao"
};

/** Endereço da operação já com a pessoa e, quando houver, a verificação facial aprovada. */
export function counterOperationHref(operation: Operation, personId: string, verificationId?: string) {
  const params = new URLSearchParams({ pessoa: personId });
  if (verificationId) params.set("verificacao", verificationId);
  return `${OPERATION_PATH[operation]}?${params.toString()}`;
}

/**
 * Entrada e saída no balcão (ADR 0008): matrícula, depois reconhecimento facial.
 *
 * A verificação aprovada acompanha a pessoa até a escolha dos materiais e é consumida na
 * confirmação. Sem biometria possível, segue para a operação, que gera o termo.
 */
interface CounterEntryProps {
  onClose?: () => void;
  /** Dentro da tela de retirada ou devolução a operação já está definida. */
  fixedOperation?: Operation;
  /** Falso só quando a instalação desligou a exigência (desenvolvimento). */
  faceRequired?: boolean;
}

export function CounterEntry({ onClose, fixedOperation, faceRequired = true }: CounterEntryProps) {
  const [registration, setRegistration] = useState("");
  const [person, setPerson] = useState<CounterIdentity | null>(null);
  const [operation, setOperation] = useState<Operation>(fixedOperation ?? "checkout");
  const [visual, setVisual] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function identify(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");
    setPerson(null);
    setVisual(false);
    try {
      const found = await apiRequest<CounterIdentity>(`/counter/identify/?registration=${encodeURIComponent(registration.trim())}`);
      if (found.own) {
        setError("Esta é a sua matrícula. O operador não registra a própria retirada ou devolução: peça a outro operador para atender você.");
        return;
      }
      setPerson(found);
      // Quem tem material em posse costuma vir devolver; o operador pode trocar.
      if (fixedOperation) {
        if (!found.operations[fixedOperation]) setError(`Sem permissão para registrar a ${fixedOperation === "checkout" ? "retirada" : "devolução"} desta pessoa.`);
      } else setOperation(found.operations.return && found.open_possessions > 0 ? "return" : found.operations.checkout ? "checkout" : "return");
    } catch (cause) {
      setError(cause instanceof ApiError && cause.status === 404 ? "Matrícula não encontrada ou sem vínculo ativo." : describeError(cause));
    } finally {
      setBusy(false);
    }
  }

  async function verify(image: Blob) {
    if (!person) return;
    setBusy(true);
    setMessage("");
    const form = new FormData();
    form.set("person_id", person.id);
    form.set("operation", operation);
    form.set("operator_confirmed", visual ? "true" : "false");
    form.set("image", image, "captura.jpg");
    try {
      const result = await postForm<FaceVerificationResult>("/face-verifications/", form);
      if (result.result === "approved") {
        window.location.assign(counterOperationHref(operation, person.id, result.id));
        return;
      }
      setMessage("Rosto não reconhecido. Ajuste a posição e a iluminação e tente de novo, ou siga sem biometria.");
    } catch (cause) {
      setMessage(cause instanceof ApiError ? cause.message : "Falha na verificação.");
    } finally {
      setBusy(false);
    }
  }

  const label = operation === "checkout" ? "saída (retirada)" : "entrada (devolução)";

  return (
    <section className="detail-card identity-check counter-entry" aria-label={fixedOperation ? "Identificação" : "Entrada e saída"}>
      <h2>{fixedOperation ? "Quem está no balcão?" : "Entrada e saída"}</h2>
      <form className="counter-entry-search" role="search" onSubmit={identify}>
        <label><span>Matrícula de quem retira ou devolve</span>
          <input value={registration} onChange={(event) => setRegistration(event.target.value)} disabled={busy} required maxLength={64} autoComplete="off" autoFocus />
        </label>
        <button className="button button-primary" disabled={busy || !registration.trim()}>Identificar</button>
      </form>
      {error && <div className="feedback error" role="alert">{error}</div>}

      {person && (
        <div className="identity-check" aria-label="Reconhecimento facial">
          <p><strong>{person.name}</strong> · matrícula {person.registration}{person.open_possessions > 0 && ` · ${person.open_possessions} ${person.open_possessions === 1 ? "material em posse" : "materiais em posse"}`}</p>
          {!fixedOperation && <fieldset className="choice-group" disabled={busy}>
            <legend>Operação</legend>
            {person.operations.checkout && <label className="checkbox"><input type="radio" name="operation" checked={operation === "checkout"} onChange={() => setOperation("checkout")} /><span>Saída (retirada)</span></label>}
            {person.operations.return && <label className="checkbox"><input type="radio" name="operation" checked={operation === "return"} onChange={() => setOperation("return")} /><span>Entrada (devolução)</span></label>}
          </fieldset>}
          {!faceRequired ? null : person.biometric_enrolled ? (
            <>
              <p className="muted">Posicione {person.name} diante da câmera. Só o rosto de quem retira ou devolve é verificado; o operador não faz reconhecimento facial.</p>
              <label className="confirmation"><input type="checkbox" checked={visual} onChange={(event) => setVisual(event.target.checked)} /><span>Conferi visualmente que {person.name} está presente no balcão.</span></label>
              <FaceCapture label={busy ? "Verificando…" : "Reconhecer rosto"} disabled={!visual || busy} onCapture={(image) => void verify(image)} />
            </>
          ) : (
            <div className="feedback warning" role="status">{person.name} não tem biometria facial cadastrada. A {label} seguirá por termo assinado e aprovado pelo administrador do acervo.</div>
          )}
          {message && <div className="feedback warning" role="alert">{message}</div>}
          <div className="dialog-actions">
            {onClose && <button className="button button-quiet" type="button" disabled={busy} onClick={onClose}>Fechar</button>}
            {person.operations[operation] && (
              <a className={`button ${faceRequired && person.biometric_enrolled ? "button-secondary" : "button-primary"}`} aria-disabled={busy || undefined} onClick={(event) => { if (busy) event.preventDefault(); }} href={counterOperationHref(operation, person.id)}>
                {faceRequired && person.biometric_enrolled ? "Biometria não foi possível: seguir com termo" : `Seguir para a ${label}`}
              </a>
            )}
          </div>
        </div>
      )}
      {!person && onClose && <div className="dialog-actions"><button className="button button-quiet" type="button" onClick={onClose}>Fechar</button></div>}
    </section>
  );
}
