import { Field } from "../components/Field";
import { useEffect, useState } from "react";
import { apiRequest, postJson, describeError } from "../api/client";
import type { LocationInfo, UnitInfo } from "../api/types";
import { ActionDialog, text } from "../components/ActionDialog";
import { ErrorState, LoadingState } from "../components/Feedback";

type Dialog =
  | { kind: "unit" }
  | { kind: "location"; unit: UnitInfo }
  | { kind: "status"; label: string; url: string; isActive: boolean };

export function CatalogPage() {
  const [units, setUnits] = useState<UnitInfo[]>([]);
  const [dialog, setDialog] = useState<Dialog | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    setError("");
    try {
      setUnits(await apiRequest<UnitInfo[]>("/units/"));
    } catch (requestError) {
      setError(describeError(requestError));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, []);

  function open(next: Dialog) {
    setSuccess("");
    setDialog(next);
  }

  async function after(message: string) {
    setSuccess(message);
    await load();
  }

  function statusButton(label: string, url: string, isActive: boolean) {
    return <button className={`button button-small ${isActive ? "button-danger-quiet" : "button-quiet"}`} onClick={() => open({ kind: "status", label, url, isActive })}>{isActive ? "Desativar" : "Reativar"}</button>;
  }

  function locationRow(location: LocationInfo) {
    return (
      <li key={location.id}>
        <span><strong>{location.code}</strong><small>{location.name} · {location.is_active ? "ativo" : "inativo"}</small></span>
        {statusButton(`o local ${location.code}`, `/locations/${location.id}/status/`, location.is_active)}
      </li>
    );
  }

  if (loading) return <LoadingState />;
  if (error && units.length === 0) return <ErrorState message={error} onRetry={() => void load()} />;

  return (
    <>
      <section className="page-heading">
        <div>
          <p className="context-label">Cadastros</p>
          <h1>Estrutura da organização</h1>
          <p>Unidades e locais de guarda. Tipos e itens ficam em <a href="/equipamentos">Equipamentos</a>. Desativar impede novos vínculos e preserva o histórico.</p>
        </div>
        <button className="button button-primary" onClick={() => open({ kind: "unit" })}>Nova unidade</button>
      </section>

      {success && <div className="feedback success" role="status">{success}</div>}
      {error && <div className="feedback error" role="alert">{error}</div>}

      <div className="single-column">
        <section className="detail-card">
          <h2>Unidades e locais de guarda</h2>
          {units.length === 0 ? <p className="muted">Nenhuma unidade cadastrada.</p> : (
            <ul className="sub-list unit-list">
              {units.map((unit) => (
                <li key={unit.id}>
                  <div className="list-content">
                    <strong>{unit.code} · {unit.name}</strong>
                    <small>{unit.is_active ? "ativa" : "inativa"} · {unit.locations.length === 1 ? "1 local" : `${unit.locations.length} locais`}</small>
                    {unit.locations.length > 0 && <ul className="sub-list">{unit.locations.map(locationRow)}</ul>}
                  </div>
                  <span className="actions-inline">
                    {unit.is_active && <button className="button button-secondary" onClick={() => open({ kind: "location", unit })}>Novo local</button>}
                    {statusButton(`a unidade ${unit.code}`, `/units/${unit.id}/status/`, unit.is_active)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>

      </div>

      {dialog?.kind === "unit" && (
        <ActionDialog title="Nova unidade" submitLabel="Cadastrar unidade" onClose={() => setDialog(null)} onSubmit={async (form) => {
          await postJson("/units/", { code: text(form, "code"), name: text(form, "name") });
          await after("Unidade cadastrada.");
        }}>
          <Field label="Código"><input name="code" required maxLength={40} /></Field>
          <Field label="Nome"><input name="name" required maxLength={160} /></Field>
        </ActionDialog>
      )}

      {dialog?.kind === "location" && (
        <ActionDialog title="Novo local de guarda" description={`Unidade ${dialog.unit.code} · ${dialog.unit.name}.`} submitLabel="Cadastrar local" onClose={() => setDialog(null)} onSubmit={async (form) => {
          await postJson(`/units/${dialog.unit.id}/locations/`, { code: text(form, "code"), name: text(form, "name") });
          await after("Local de guarda cadastrado.");
        }}>
          <Field label="Código"><input name="code" required maxLength={40} /></Field>
          <Field label="Nome"><input name="name" required maxLength={120} /></Field>
        </ActionDialog>
      )}

      {dialog?.kind === "status" && (
        <ActionDialog title={`${dialog.isActive ? "Desativar" : "Reativar"} ${dialog.label}?`} description={dialog.isActive ? `${capitalize(dialog.label)} deixa de aceitar novos vínculos. O histórico e os registros existentes são preservados.` : `${capitalize(dialog.label)} volta a aceitar novos vínculos.`} confirmation={`Confirmo: ${dialog.isActive ? "desativar" : "reativar"} ${dialog.label}.`} submitLabel={dialog.isActive ? "Desativar" : "Reativar"} tone={dialog.isActive ? "danger" : "default"} onClose={() => setDialog(null)} onSubmit={async (form) => {
          await postJson(dialog.url, { is_active: !dialog.isActive, confirmed: form.get("confirmed") === "on", reason: text(form, "reason") });
          await after("Situação atualizada.");
        }}>
          <label><span>Motivo <span className="field-optional">(opcional)</span></span><textarea name="reason" maxLength={200} /></label>
        </ActionDialog>
      )}
    </>
  );
}

function capitalize(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}
