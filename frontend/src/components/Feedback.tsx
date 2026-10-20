export function LoadingState({ label = "Carregando dados" }: { label?: string }) {
  return (
    <div className="loading-state" role="status" aria-live="polite">
      <span className="loading-line" />
      <span className="loading-line short" />
      <span className="sr-only">{label}</span>
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <section className="feedback error" role="alert">
      <strong>Não foi possível carregar esta área.</strong>
      <p>{message}</p>
      {onRetry && <button className="button button-secondary" onClick={onRetry}>Tentar novamente</button>}
    </section>
  );
}
