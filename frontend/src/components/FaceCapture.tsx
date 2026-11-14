import { useEffect, useRef, useState } from "react";

interface FaceCaptureProps {
  /** Rótulo do botão de captura. */
  label: string;
  disabled?: boolean;
  onCapture: (image: Blob) => void;
  onUnavailable?: () => void;
}

/** Proporção da área de vídeo exibida (largura / altura); deve coincidir com o CSS. */
const VIEW_ASPECT = 4 / 3;

/**
 * Moldura do rosto em coordenadas relativas à área exibida (0–1). Centralizada na
 * horizontal, para que o espelhamento da prévia não altere o recorte. Inclui uma margem
 * ao redor do oval para que o detector encontre o contorno completo do rosto.
 */
export const FACE_FRAME = { x: 0.24, y: 0.04, width: 0.52, height: 0.92 } as const;

export interface CropRect { x: number; y: number; width: number; height: number }

/**
 * Converte a moldura exibida em pixels do quadro original. A prévia usa `object-fit: cover`,
 * então só a faixa central do quadro com a proporção VIEW_ASPECT está visível.
 */
export function faceCropRect(videoWidth: number, videoHeight: number, frame = FACE_FRAME): CropRect {
  const visibleWidth = Math.min(videoWidth, videoHeight * VIEW_ASPECT);
  const visibleHeight = visibleWidth / VIEW_ASPECT;
  const left = (videoWidth - visibleWidth) / 2;
  const top = (videoHeight - visibleHeight) / 2;
  return {
    x: Math.round(left + frame.x * visibleWidth),
    y: Math.round(top + frame.y * visibleHeight),
    width: Math.round(frame.width * visibleWidth),
    height: Math.round(frame.height * visibleHeight)
  };
}

/**
 * Captura um quadro da webcam do balcão (ADR 0008), recortado à moldura do rosto: o que fica
 * fora dela (fundo, outras pessoas) não é enviado.
 *
 * A imagem existe só em memória até ser enviada ao servidor da instalação; nada é gravado
 * no navegador (sem cache, armazenamento local ou sessionStorage).
 */
export function FaceCapture({ label, disabled, onCapture, onUnavailable }: FaceCaptureProps) {
  const video = useRef<HTMLVideoElement>(null);
  const stream = useRef<MediaStream | null>(null);
  const [error, setError] = useState("");
  const [ready, setReady] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const unavailable = useRef(onUnavailable);
  unavailable.current = onUnavailable;

  useEffect(() => {
    if (attempt === 0) return;
    let cancelled = false;
    setError("");
    setReady(false);
    if (!navigator.mediaDevices?.getUserMedia) {
      setError("Este navegador não dá acesso à câmera. Use um navegador compatível em uma conexão segura ou siga pelo termo.");
      unavailable.current?.();
      return;
    }
    navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" }, audio: false })
      .then((media) => {
        if (cancelled) { media.getTracks().forEach((track) => track.stop()); return; }
        stream.current = media;
        if (video.current) video.current.srcObject = media;
      })
      .catch((cause: unknown) => {
        if (cancelled) return;
        const name = cause instanceof DOMException ? cause.name : "";
        setError(name === "NotAllowedError"
          ? "Acesso à câmera negado. Permita o acesso nas configurações deste site e tente novamente."
          : name === "NotFoundError"
            ? "Nenhuma câmera encontrada. Conecte uma câmera e tente novamente."
            : "Não foi possível ativar a câmera. Verifique se ela está em uso por outro aplicativo e tente novamente.");
        unavailable.current?.();
      });
    return () => {
      cancelled = true;
      stream.current?.getTracks().forEach((track) => track.stop());
    };
  }, [attempt]);

  function capture() {
    const source = video.current;
    if (!source || !source.videoWidth) return;
    const crop = faceCropRect(source.videoWidth, source.videoHeight);
    const canvas = document.createElement("canvas");
    canvas.width = crop.width;
    canvas.height = crop.height;
    canvas.getContext("2d")?.drawImage(source, crop.x, crop.y, crop.width, crop.height, 0, 0, crop.width, crop.height);
    canvas.toBlob((blob) => { if (blob) onCapture(blob); }, "image/jpeg", 0.92);
  }

  return (
    <div className="face-capture">
      <p className="field-hint">Ative a câmera e posicione o rosto dentro da moldura, sem outras pessoas. Só a área da moldura é enviada, e apenas ao usar o botão de captura.</p>
      {error && <p className="feedback warning" role="alert">{error}</p>}
      {attempt > 0 && !error && (
        <div className="face-viewport">
          <video ref={video} autoPlay playsInline muted aria-label="Imagem da câmera do balcão"
            onLoadedData={() => setReady(true)} />
          <div className="face-frame" aria-hidden="true"
            style={{ left: `${FACE_FRAME.x * 100}%`, top: `${FACE_FRAME.y * 100}%`, width: `${FACE_FRAME.width * 100}%`, height: `${FACE_FRAME.height * 100}%` }}>
            <span className="face-oval" />
          </div>
        </div>
      )}
      {(attempt === 0 || error) && <button className="button button-secondary" type="button" disabled={disabled} onClick={() => setAttempt((value) => value + 1)}>{error ? "Tentar ativar câmera novamente" : "Ativar câmera"}</button>}
      {attempt > 0 && !error && !ready && <p className="muted" role="status">Aguardando acesso à câmera…</p>}
      <button className="button button-secondary" type="button" disabled={disabled || !ready} onClick={capture}>{label}</button>
      {attempt > 0 && <button className="button button-quiet" type="button" disabled={disabled} onClick={() => { setAttempt(0); setReady(false); setError(""); }}>Desativar câmera</button>}
    </div>
  );
}
