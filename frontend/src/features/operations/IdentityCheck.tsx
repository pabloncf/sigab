import { FormEvent, useState } from "react";
import { ApiError, postForm, postJson } from "../../api/client";
import type { FaceVerificationResult, IdentityExceptionTerm } from "../../api/types";
import { FaceCapture } from "../../components/FaceCapture";

const REASONS = [
  { value: "verification_failed", label: "Verificação facial recusada" },
  { value: "camera_unavailable", label: "Câmera ou verificação indisponível" },
  { value: "not_enrolled", label: "Pessoa sem biometria cadastrada" },
  { value: "other", label: "Outro motivo" }
];

interface IdentityCheckProps {
  operation: "checkout" | "return";
  personId: string;
  personName: string;
  summary: string;
  /** Operação solicitada, gravada no termo quando a biometria não for possível. */
  request: Record<string, unknown>;
  busy?: boolean;
  onApproved: (verificationId: string) => void;
  onBack: () => void;
}

/**
 * Etapa obrigatória antes de confirmar retirada ou devolução (ADR 0008).
 *
 * Verificação facial 1:1 da pessoa selecionada, com conferência visual do operador.
 * Quando a biometria não for possível, gera o termo: a pessoa assina e só o administrador
 * do acervo aprova; nada é movimentado antes disso.
 */
export function IdentityCheck({ operation, personId, personName, summary, request, busy, onApproved, onBack }: IdentityCheckProps) {
  const [visual, setVisual] = useState(false);
  const [checking, setChecking] = useState(false);
  const [message, setMessage] = useState("");
  const [failures, setFailures] = useState(0);
  const [termOpen, setTermOpen] = useState(false);
  const [reasonCode, setReasonCode] = useState("verification_failed");
  const [termError, setTermError] = useState("");
  const [generating, setGenerating] = useState(false);
  const [termKey] = useState(() => crypto.randomUUID());

  async function verify(image: Blob) {
    setChecking(true);
    setMessage("");
    const form = new FormData();
    form.set("person_id", personId);
    form.set("operation", operation);
    form.set("operator_confirmed", visual ? "true" : "false");
    form.set("image", image, "captura.jpg");
    try {
      const result = await postForm<FaceVerificationResult>("/face-verifications/", form);
      if (result.result === "approved") {
        onApproved(result.id);
        return;
      }
      setFailures((count) => count + 1);
      setMessage("Verificação recusada. Ajuste a posição e a iluminação e tente de novo, ou gere o termo.");
    } catch (cause) {
      const text = cause instanceof ApiError ? cause.message : "Falha na verificação.";
      setMessage(text);
      if (cause instanceof ApiError && cause.status === 409) setReasonCode("not_enrolled");
      if (cause instanceof ApiError && cause.status === 503) setReasonCode("camera_unavailable");
    } finally {
      setChecking(false);
    }
  }

  async function createTerm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (generating) return;
    const form = new FormData(event.currentTarget);
    setGenerating(true);
    setTermError("");
    try {
      const term = await postJson<IdentityExceptionTerm>("/identity-exceptions/", {
        operation, person_id: personId, reason_code: reasonCode,
        reason: String(form.get("reason") ?? "").trim(), request,
        idempotency_key: termKey, confirmed: form.get("confirmed") === "on"
      });
      window.location.assign(`/atendimento/termos/${term.id}`);
    } catch (cause) {
      setTermError(cause instanceof ApiError ? cause.message : "Não foi possível gerar o termo.");
    } finally {
      setGenerating(false);
    }
  }

  return (
    <section className="detail-card identity-check" aria-label="Confirmação de identidade">
      <h2>Confirmação de identidade</h2>
      <p>{summary}</p>
      <p className="muted">Retirada e devolução exigem a verificação facial de <strong>{personName}</strong>, que retira ou devolve. O operador não faz reconhecimento facial.</p>
      <label className="confirmation"><input type="checkbox" checked={visual} onChange={(event) => setVisual(event.target.checked)} /><span>Conferi visualmente que {personName} está presente no balcão.</span></label>
      <FaceCapture label={checking ? "Verificando…" : "Capturar e verificar"} disabled={!visual || checking || busy}
        onCapture={(image) => void verify(image)} onUnavailable={() => setReasonCode("camera_unavailable")} />
      {message && <div className="feedback warning" role="alert">{message}</div>}

      {!termOpen ? (
        <div className="dialog-actions">
          <button className="button button-quiet" type="button" onClick={onBack} disabled={busy || checking}>Voltar</button>
          <button className={`button ${failures > 0 ? "button-primary" : "button-secondary"}`} type="button" disabled={busy || checking} onClick={() => setTermOpen(true)}>Biometria não foi possível: gerar termo</button>
        </div>
      ) : (
        <form className="dialog-form" aria-label="Gerar termo" onSubmit={createTerm}>
          <p className="muted">O termo será impresso e assinado pela pessoa. A operação só é confirmada depois da aprovação do administrador do acervo.</p>
          <label><span>Motivo</span><select value={reasonCode} onChange={(event) => setReasonCode(event.target.value)}>{REASONS.map((reason) => <option key={reason.value} value={reason.value}>{reason.label}</option>)}</select></label>
          <label><span>Detalhe do motivo{reasonCode === "other" ? "" : " (opcional)"}</span><textarea name="reason" maxLength={500} required={reasonCode === "other"} /></label>
          <label className="confirmation"><input name="confirmed" type="checkbox" required /><span>Confirmo que a biometria não foi possível e que a pessoa assinará o termo.</span></label>
          {termError && <div className="feedback error" role="alert">{termError}</div>}
          <div className="dialog-actions">
            <button className="button button-quiet" type="button" disabled={generating} onClick={() => setTermOpen(false)}>Voltar à verificação</button>
            <button className="button button-primary" disabled={generating}>{generating ? "Gerando termo…" : "Gerar termo"}</button>
          </div>
        </form>
      )}
    </section>
  );
}
