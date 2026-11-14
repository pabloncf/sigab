import { ReactNode, useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";

const FOCUSABLE = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled]):not([type=\"hidden\"])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  "[tabindex]:not([tabindex=\"-1\"])"
].join(",");
const FIELDS = "input:not([disabled]):not([type=\"hidden\"]):not([type=\"checkbox\"]), select:not([disabled]), textarea:not([disabled])";

let openModals = 0;

/** Torna o restante da aplicação indisponível enquanto há diálogo aberto. */
function lockBackground() {
  openModals += 1;
  const root = document.getElementById("root");
  root?.setAttribute("inert", "");
  root?.setAttribute("aria-hidden", "true");
  document.body.style.overflow = "hidden";
  return () => {
    openModals -= 1;
    if (openModals > 0) return;
    root?.removeAttribute("inert");
    root?.removeAttribute("aria-hidden");
    document.body.style.overflow = "";
  };
}

export interface ModalProps {
  title: ReactNode;
  description?: ReactNode;
  size?: "default" | "wide";
  /**
   * Envio em andamento. O diálogo não fecha até a resposta: fechar não cancela a requisição
   * e deixaria a pessoa sem saber se a operação foi concluída.
   */
  busy?: boolean;
  onClose: () => void;
  children: ReactNode;
}

/**
 * Diálogo modal acessível: recebe o foco ao abrir, mantém o Tab dentro dele, fecha com Esc,
 * devolve o foco a quem o abriu e torna o fundo inerte.
 *
 * Proteção contra perda de dados: depois que algo é preenchido, o clique fora não fecha e
 * o Esc pede uma segunda confirmação.
 */
export function Modal({ title, description, size = "default", busy = false, onClose, children }: ModalProps) {
  const titleId = useId();
  const descriptionId = useId();
  const dialogRef = useRef<HTMLElement>(null);
  const openerRef = useRef<HTMLElement | null>(null);
  const escapeArmed = useRef(false);
  const [dirty, setDirty] = useState(false);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    openerRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const unlock = lockBackground();
    const dialog = dialogRef.current;
    const target = dialog?.querySelector<HTMLElement>("[autofocus]") ?? dialog?.querySelector<HTMLElement>(FIELDS) ?? dialog;
    target?.focus();
    return () => {
      unlock();
      const opener = openerRef.current;
      // O botão de origem pode ter sumido (ex.: "Registrar saída" após a saída).
      if (opener && opener.isConnected && !opener.closest("[inert]")) opener.focus();
      else document.getElementById("conteudo")?.focus();
    };
  }, []);

  useEffect(() => {
    if (!busy) setNotice((current) => (current.startsWith("O envio") ? "" : current));
  }, [busy]);

  function requestClose(source: "escape" | "backdrop") {
    if (busy) {
      setNotice("O envio está em andamento. Aguarde a resposta para saber se a operação foi concluída.");
      return;
    }
    if (dirty && source === "backdrop") {
      setNotice("Há dados preenchidos. Use “Cancelar” para descartá-los.");
      return;
    }
    if (dirty && !escapeArmed.current) {
      escapeArmed.current = true;
      setNotice("Há dados preenchidos. Pressione Esc novamente para descartá-los.");
      return;
    }
    onClose();
  }

  // Escuta no documento: o foco pode sair do diálogo (ex.: botão desabilitado durante o envio).
  const requestCloseRef = useRef(requestClose);
  requestCloseRef.current = requestClose;
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      const dialog = dialogRef.current;
      if (!dialog) return;
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        requestCloseRef.current("escape");
        return;
      }
      if (event.key !== "Tab") return;
      const focusable = [...dialog.querySelectorAll<HTMLElement>(FOCUSABLE)].filter((element) => element.offsetParent !== null);
      if (focusable.length === 0) {
        event.preventDefault();
        dialog.focus();
        return;
      }
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const active = document.activeElement;
      const outside = !active || !dialog.contains(active);
      if (event.shiftKey && (outside || active === first || active === dialog)) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && (outside || active === last)) {
        event.preventDefault();
        first.focus();
      }
    }
    document.addEventListener("keydown", handleKeyDown, true);
    return () => document.removeEventListener("keydown", handleKeyDown, true);
  }, []);

  // Se o elemento focado for desabilitado ou removido, o foco volta ao diálogo.
  useEffect(() => {
    const dialog = dialogRef.current;
    if (busy && dialog && !dialog.contains(document.activeElement)) dialog.focus();
  });

  return createPortal(
    <div className="dialog-backdrop" role="presentation" onMouseDown={(event) => {
      if (event.target !== event.currentTarget) return;
      event.preventDefault(); // mantém o foco dentro do diálogo
      requestClose("backdrop");
    }}>
      <section
        ref={dialogRef}
        className={`dialog${size === "wide" ? " dialog-wide" : ""}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={description ? descriptionId : undefined}
        aria-busy={busy || undefined}
        tabIndex={-1}
        onInput={() => { setDirty(true); escapeArmed.current = false; }}
      >
        <h2 id={titleId}>{title}</h2>
        {description && <div className="dialog-description" id={descriptionId}>{description}</div>}
        <p className="dialog-notice" role="status" aria-live="polite">{notice}</p>
        {children}
      </section>
    </div>,
    document.body
  );
}
