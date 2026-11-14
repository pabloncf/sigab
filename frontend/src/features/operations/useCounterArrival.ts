import { useState } from "react";
import { postJson } from "../../api/client";

/**
 * Pessoa e verificação facial trazidas da entrada do balcão (?pessoa=&verificacao=).
 *
 * A verificação é de uso único: depois de uma tentativa de confirmação ela sai do estado e
 * da URL, e uma nova confirmação passa de novo pela etapa de identidade. Cancelar invalida a
 * verificação no servidor e volta ao Início.
 */
export function useCounterArrival() {
  const [state, setState] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    return { personId: params.get("pessoa") ?? "", verificationId: params.get("verificacao") ?? "" };
  });

  function consume() {
    setState((current) => ({ ...current, verificationId: "" }));
    const url = new URL(window.location.href);
    url.searchParams.delete("verificacao");
    window.history.replaceState(window.history.state, "", url);
  }

  /** Depois de concluída a operação: o balcão volta a pedir a próxima matrícula. */
  function reset() {
    setState({ personId: "", verificationId: "" });
    const url = new URL(window.location.href);
    url.searchParams.delete("pessoa");
    url.searchParams.delete("verificacao");
    window.history.replaceState(window.history.state, "", url);
  }

  async function cancel() {
    if (state.verificationId) {
      await postJson(`/face-verifications/${state.verificationId}/cancel/`, { confirmed: true });
    }
    window.location.assign("/");
  }

  return { ...state, consume, reset, cancel };
}
