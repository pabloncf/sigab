import { FormEvent, useEffect, useRef, useState } from "react";
import { ApiError, apiRequest, postForm, postJson, describeError } from "../../api/client";
import type { BiometricStatus } from "../../api/types";
import { FaceCapture } from "../../components/FaceCapture";
import { formatDateTime } from "../../components/format";
import { useLatestRequest } from "../../hooks/useLatestRequest";

interface BiometricPanelProps {
  personId: string;
  personName: string;
  registration?: string;
  onChange?: (status: BiometricStatus) => void;
  onClose?: () => void;
  onBusyChange?: (busy: boolean) => void;
}

/**
 * Cadastro, recadastro e exclusão da biometria facial de uma pessoa (SIGAB-085).
 *
 * Mostra apenas cadastrada/não cadastrada e a data; o modelo biométrico nunca chega ao
 * navegador.
 */
export function BiometricPanel(props: BiometricPanelProps) {
  // Identity changes must never reuse consent, messages or an unfinished delete form.
  return <PersonBiometricPanel key={props.personId} {...props} />;
}

function PersonBiometricPanel({ personId, personName, registration, onChange, onClose, onBusyChange }: BiometricPanelProps) {
  const [status, setStatus] = useState<BiometricStatus | null>(null);
  const [mode, setMode] = useState<"idle" | "capture" | "delete">("idle");
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ kind: "success" | "error"; text: string } | null>(null);
  const panel = useRef<HTMLElement>(null);
  const beginRequest = useLatestRequest();

  async function load() {
    const current = beginRequest();
    setMessage(null);
    try {
      const result = await apiRequest<BiometricStatus>(`/people/${personId}/biometric/`);
      if (current()) setStatus(result);
    } catch (cause) {
      if (current()) setMessage({ kind: "error", text: describeError(cause) });
    }
  }

  useEffect(() => { void load(); if (onClose) panel.current?.focus(); }, []);
  useEffect(() => { onBusyChange?.(busy); }, [busy, onBusyChange]);

  function update(next: BiometricStatus, text: string) {
    setStatus(next);
    setMode("idle");
    setConsent(false);
    setMessage({ kind: "success", text });
    onChange?.(next);
  }

  async function enroll(image: Blob) {
    setBusy(true);
    setMessage(null);
    const form = new FormData();
    form.set("confirmed", "true");
    form.set("image", image, "captura.jpg");
    try {
      update(await postForm<BiometricStatus>(`/people/${personId}/biometric/`, form), status?.enrolled ? "Biometria recadastrada." : "Biometria cadastrada.");
    } catch (cause) {
      setMessage({ kind: "error", text: cause instanceof ApiError ? cause.message : "Não foi possível cadastrar." });
    } finally {
      setBusy(false);
    }
  }

  async function remove(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const reason = String(new FormData(event.currentTarget).get("reason") ?? "").trim();
    setBusy(true);
    setMessage(null);
    try {
      update(await postJson<BiometricStatus>(`/people/${personId}/biometric/delete/`, { reason, confirmed: true }), "Biometria excluída.");
    } catch (cause) {
      setMessage({ kind: "error", text: cause instanceof ApiError ? cause.message : "Não foi possível excluir." });
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="detail-card biometric-panel" aria-label={`Biometria facial de ${personName}`} tabIndex={-1} ref={panel} aria-busy={busy || undefined}>
      <header className="section-header">
        <div><h2>Biometria facial</h2><p className="panel-person"><strong>{personName}</strong>{registration && ` · matrícula ${registration}`}</p></div>
        {onClose && <button className="button button-quiet" type="button" disabled={busy} onClick={onClose}>Fechar painel</button>}
      </header>
      {message && <div className={`feedback ${message.kind}`} role={message.kind === "error" ? "alert" : "status"}>{message.text}</div>}
      {!status ? message?.kind === "error" ? <button className="button button-secondary" type="button" onClick={() => void load()}>Tentar novamente</button> : <p className="muted" role="status">Carregando biometria…</p> : (
        <p>{status.enrolled ? <>Cadastrada em <strong>{status.enrolled_at ? formatDateTime(status.enrolled_at) : "—"}</strong></> : "Não cadastrada"}</p>
      )}
      {mode === "idle" && status && (
        <div className="actions-inline">
          <button className="button button-primary" type="button" onClick={() => setMode("capture")}>{status.enrolled ? "Recadastrar" : "Cadastrar"}</button>
          {status.enrolled && <button className="button button-danger-quiet" type="button" onClick={() => setMode("delete")}>Excluir</button>}
        </div>
      )}
      {mode === "capture" && (
        <div className="identity-check">
          <label className="confirmation"><input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} /><span>{personName} está presente e foi informada da finalidade, da retenção e de que a biometria é exigida para retirar e devolver material.</span></label>
          <FaceCapture label={busy ? "Cadastrando…" : "Capturar e cadastrar"} disabled={!consent || busy} onCapture={(image) => void enroll(image)} />
          <div className="dialog-actions"><button className="button button-quiet" type="button" disabled={busy} onClick={() => { setMode("idle"); setConsent(false); }}>Cancelar</button></div>
        </div>
      )}
      {mode === "delete" && (
        <form className="dialog-form" onSubmit={remove} aria-label="Excluir biometria">
          <p className="muted">A exclusão da biometria de <strong>{personName}</strong>{registration && `, matrícula ${registration},`} é definitiva. A auditoria registra o fato, sem o dado biométrico.</p>
          <label><span>Motivo da exclusão</span><input name="reason" required maxLength={500} /></label>
          <div className="dialog-actions">
            <button className="button button-quiet" type="button" disabled={busy} onClick={() => setMode("idle")}>Voltar</button>
            <button className="button button-danger" disabled={busy}>{busy ? "Excluindo biometria…" : "Excluir biometria"}</button>
          </div>
        </form>
      )}
    </section>
  );
}
