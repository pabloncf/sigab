import { FormEvent, ReactNode, useEffect, useId, useRef, useState } from "react";

interface SearchFormProps {
  label: string;
  placeholder?: string;
  /** Termo aplicado na consulta atual. */
  value: string;
  onSearch: (term: string) => void;
  /** Mínimo de caracteres exigido pelo servidor; comunicado antes do envio. */
  minLength?: number;
  hint?: ReactNode;
}

/**
 * Busca explícita: rótulo associado, botão "Buscar" visível e "Limpar".
 * Enter continua funcionando, mas não é o único caminho.
 */
export function SearchForm({ label, placeholder, value, onSearch, minLength = 0, hint }: SearchFormProps) {
  const id = useId();
  const [draft, setDraft] = useState(value);
  const [problem, setProblem] = useState("");

  useEffect(() => { setDraft(value); }, [value]);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const term = draft.trim();
    if (term && term.length < minLength) {
      setProblem(`Digite ao menos ${minLength} caracteres para buscar.`);
      return;
    }
    setProblem("");
    onSearch(term);
  }

  function clear() {
    setDraft("");
    setProblem("");
    if (value) onSearch("");
  }

  const hintText = hint ?? (minLength > 1 ? `Mínimo de ${minLength} caracteres. Pressione Enter ou use “Buscar”.` : "Pressione Enter ou use “Buscar”.");

  return (
    <form className="search-form" role="search" onSubmit={submit}>
      <label htmlFor={id}>{label}</label>
      <div className="search-row">
        <input id={id} type="search" value={draft} placeholder={placeholder} autoComplete="off"
          aria-describedby={`${id}-dica`} aria-invalid={problem ? true : undefined}
          onChange={(event) => { setDraft(event.target.value); setProblem(""); }} />
        <button className="button button-secondary" type="submit">Buscar</button>
        {(draft || value) && <button className="button button-quiet" type="button" onClick={clear}>Limpar</button>}
      </div>
      <small className={problem ? "field-error" : "field-hint"} id={`${id}-dica`} role={problem ? "alert" : undefined}>{problem || hintText}</small>
    </form>
  );
}

export interface AppliedFilter {
  label: string;
  value: string;
  onRemove: () => void;
}

/** Mostra o que está filtrando a consulta e permite remover cada filtro. */
export function AppliedFilters({ filters, onClearAll }: { filters: AppliedFilter[]; onClearAll?: () => void }) {
  if (filters.length === 0) return null;
  return (
    <div className="applied-filters" aria-label="Filtros aplicados">
      <span className="applied-filters-label">Filtros aplicados:</span>
      <ul>
        {filters.map((filter) => (
          <li key={filter.label}>
            <span>{filter.label}: <strong>{filter.value}</strong></span>
            <button type="button" className="chip-remove" onClick={filter.onRemove} aria-label={`Remover filtro ${filter.label}`}>×</button>
          </li>
        ))}
      </ul>
      {onClearAll && filters.length > 1 && <button type="button" className="link-button" onClick={onClearAll}>Limpar todos</button>}
    </div>
  );
}

interface PagerProps {
  offset: number;
  limit: number;
  count: number;
  onChange: (offset: number) => void;
  noun?: [string, string];
}

/** Intervalo exibido e navegação entre páginas; a ordenação vem do servidor e é estável. */
export function Pager({ offset, limit, count, onChange, noun = ["registro", "registros"] }: PagerProps) {
  if (count === 0) return null;
  const first = offset + 1;
  const last = Math.min(offset + limit, count);
  const page = Math.floor(offset / limit) + 1;
  const pages = Math.max(1, Math.ceil(count / limit));
  return (
    <nav className="pager" aria-label="Paginação">
      <span className="pager-range" aria-live="polite">Exibindo <strong>{first}–{last}</strong> de <strong>{count}</strong> {count === 1 ? noun[0] : noun[1]}</span>
      {pages > 1 && (
        <span className="pager-controls">
          <button className="button button-quiet" type="button" disabled={page <= 1} onClick={() => onChange(Math.max(0, offset - limit))}>‹ Anterior</button>
          <span className="pager-page">Página {page} de {pages}</span>
          <button className="button button-quiet" type="button" disabled={page >= pages} onClick={() => onChange(offset + limit)}>Próxima ›</button>
        </span>
      )}
    </nav>
  );
}

/** Lê e grava o estado da consulta na URL, para preservá-lo ao voltar de um detalhe. */
export function useUrlQuery<T extends Record<string, string>>(defaults: T) {
  const initialDefaults = useRef(defaults);
  function read() {
    const params = new URLSearchParams(window.location.search);
    return Object.fromEntries(Object.entries(initialDefaults.current).map(([key, fallback]) => [key, params.get(key) ?? fallback])) as T;
  }
  const [state, setState] = useState<T>(read);
  const currentState = useRef(state);
  currentState.current = state;

  useEffect(() => {
    const restore = () => { const next = read(); currentState.current = next; setState(next); };
    window.addEventListener("popstate", restore);
    return () => window.removeEventListener("popstate", restore);
  }, []);

  function update(patch: Partial<T>) {
    const next = { ...currentState.current, ...patch };
    const params = new URLSearchParams(window.location.search);
    for (const [key, value] of Object.entries(next)) {
      if (value !== initialDefaults.current[key]) params.set(key, value);
      else params.delete(key);
    }
    const search = params.toString();
    const url = `${window.location.pathname}${search ? `?${search}` : ""}${window.location.hash}`;
    if (url !== `${window.location.pathname}${window.location.search}${window.location.hash}`) {
      window.history.pushState(window.history.state, "", url);
    }
    currentState.current = next;
    setState(next);
  }

  return [state, update] as const;
}

const SCROLL_KEY = "sigab:scroll:";

/**
 * Guarda a consulta atual (com filtros e página) como destino do "Voltar" do detalhe e
 * restaura a rolagem quando a pessoa retorna.
 */
export function useListMemory(storageKey: string, ready: boolean) {
  const restored = useRef(false);

  useEffect(() => {
    const save = () => {
      try {
        const url = `${window.location.pathname}${window.location.search}`;
        sessionStorage.setItem(storageKey, url);
        sessionStorage.setItem(SCROLL_KEY + url, String(window.scrollY));
      } catch { /* armazenamento indisponível: segue sem memória */ }
    };
    window.addEventListener("pagehide", save);
    document.addEventListener("click", save, true);
    return () => {
      window.removeEventListener("pagehide", save);
      document.removeEventListener("click", save, true);
    };
  }, [storageKey]);

  useEffect(() => {
    if (!ready || restored.current) return;
    restored.current = true;
    try {
      const url = `${window.location.pathname}${window.location.search}`;
      sessionStorage.setItem(storageKey, url);
      const y = Number(sessionStorage.getItem(SCROLL_KEY + url));
      if (y > 0) window.scrollTo({ top: y });
    } catch { /* idem */ }
  }, [ready, storageKey]);
}

/** Endereço da última consulta da lista, para o link "Voltar" do detalhe. */
export function lastListUrl(storageKey: string, fallback: string): string {
  try {
    return sessionStorage.getItem(storageKey) ?? fallback;
  } catch {
    return fallback;
  }
}
