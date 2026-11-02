import { useEffect, useState } from "react";
import { ApiError, apiRequest, postJson } from "../api/client";
import type { EquipmentTypeInfo, LocationInfo, UnitInfo } from "../api/types";
import { ActionDialog, text } from "../components/ActionDialog";
import { ErrorState, LoadingState } from "../components/Feedback";

type Dialog =
  | { kind: "unit" }
  | { kind: "location"; unit: UnitInfo }
  | { kind: "type" }
  | { kind: "status"; label: string; url: string; isActive: boolean };

export function CatalogPage() {
  const [units, setUnits] = useState<UnitInfo[]>([]);
  const [types, setTypes] = useState<EquipmentTypeInfo[]>([]);
  const [dialog, setDialog] = useState<Dialog | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const [loadedUnits, loadedTypes] = await Promise.all([
        apiRequest<UnitInfo[]>("/units/"),
        apiRequest<EquipmentTypeInfo[]>("/equipment-types/")
      ]);
      setUnits(loadedUnits);
      setTypes(loadedTypes);
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "Erro inesperado.");
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
    return <button className="button button-quiet" onClick={() => open({ kind: "status", label, url, isActive })}>{isActive ? "Desativar" : "Reativar"}</button>;
  }

  function locationRow(location: LocationInfo) {
    return (
      <li key={location.id}>
        <span><strong>{location.code}</strong><small>{location.name} · {location.is_active ? "ativo" : "inativo"}</small></span>
        {statusButton(`local ${location.code}`, `/locations/${location.id}/status/`, location.is_active)}
      </li>
    );
  }

  if (loading) return <LoadingState />;
  if (error && units.length === 0 && types.length === 0) return <ErrorState message={error} onRetry={() => void load()} />;

  return (
    <>
      <section className="page-heading">
        <div>
          <p className="context-label">Cadastros</p>
          <h1>Estrutura e catálogo</h1>
          <p>Unidades, locais de guarda e tipos de equipamento. Desativar impede novos vínculos e preserva o histórico.</p>
        </div>
      </section>

      {success && <div className="feedback success" role="status">{success}</div>}
      {error && <div className="feedback error" role="alert">{error}</div>}

      <div className="detail-grid">
        <section className="detail-card">
          <h2>Unidades e locais de guarda</h2>
          {units.length === 0 ? <p className="muted">Nenhuma unidade cadastrada.</p> : (
            <ul className="sub-list">
              {units.map((unit) => (
                <li key={unit.id}>
                  <span>
                    <strong>{unit.code} · {unit.name}</strong>
                    <small>{unit.is_active ? "ativa" : "inativa"} · {unit.locations.length === 1 ? "1 local" : `${unit.locations.length} locais`}</small>
                    {unit.locations.length > 0 && <ul className="sub-list">{unit.locations.map(locationRow)}</ul>}
                  </span>
                  <span className="actions-inline">
                    {unit.is_active && <button className="button button-secondary" onClick={() => open({ kind: "location", unit })}>Novo local</button>}
                    {statusButton(`unidade ${unit.code}`, `/units/${unit.id}/status/`, unit.is_active)}
                  </span>
                </li>
              ))}
            </ul>
          )}
          <div className="actions"><button className="button button-primary" onClick={() => open({ kind: "unit" })}>Nova unidade</button></div>
        </section>

        <section className="history-card">
          <h2>Tipos de equipamento</h2>
          {types.length === 0 ? <p className="muted">Nenhum tipo cadastrado.</p> : (
            <ul className="sub-list">
              {types.map((type) => (
                <li key={type.id}>
                  <span><strong>{type.name}</strong><small>{type.classification_label} · {type.is_active ? "ativo" : "inativo"}{type.description && ` · ${type.description}`}</small></span>
                  {statusButton(`tipo ${type.name}`, `/equipment-types/${type.id}/status/`, type.is_active)}
                </li>
              ))}
            </ul>
          )}
          <div className="actions"><button className="button button-primary" onClick={() => open({ kind: "type" })}>Novo tipo</button></div>
        </section>
      </div>

      {dialog?.kind === "unit" && (
        <ActionDialog title="Nova unidade" submitLabel="Cadastrar" onClose={() => setDialog(null)} onSubmit={async (form) => {
          await postJson("/units/", { code: text(form, "code"), name: text(form, "name") });
          await after("Unidade cadastrada.");
        }}>
          <label><span>Código</span><input name="code" required maxLength={40} /></label>
          <label><span>Nome</span><input name="name" required maxLength={160} /></label>
        </ActionDialog>
      )}

      {dialog?.kind === "location" && (
        <ActionDialog title="Novo local de guarda" description={`Unidade ${dialog.unit.code} · ${dialog.unit.name}.`} submitLabel="Cadastrar" onClose={() => setDialog(null)} onSubmit={async (form) => {
          await postJson(`/units/${dialog.unit.id}/locations/`, { code: text(form, "code"), name: text(form, "name") });
          await after("Local de guarda cadastrado.");
        }}>
          <label><span>Código</span><input name="code" required maxLength={40} /></label>
          <label><span>Nome</span><input name="name" required maxLength={120} /></label>
        </ActionDialog>
      )}

      {dialog?.kind === "type" && (
        <ActionDialog title="Novo tipo de equipamento" description="A classificação não poderá ser alterada depois." submitLabel="Cadastrar" onClose={() => setDialog(null)} onSubmit={async (form) => {
          await postJson("/equipment-types/", { name: text(form, "name"), classification: text(form, "classification"), description: text(form, "description") });
          await after("Tipo cadastrado.");
        }}>
          <label><span>Nome</span><input name="name" required maxLength={160} /></label>
          <label><span>Classificação</span><select name="classification" required defaultValue="individual"><option value="individual">Individual (controle por item)</option><option value="quantitative">Quantitativo (controle por quantidade)</option></select></label>
          <label><span>Descrição</span><textarea name="description" maxLength={2000} /></label>
        </ActionDialog>
      )}

      {dialog?.kind === "status" && (
        <ActionDialog title={`${dialog.isActive ? "Desativar" : "Reativar"} ${dialog.label}`} description="O histórico e os registros existentes são preservados." confirmation="Confirmo a alteração da situação." onClose={() => setDialog(null)} onSubmit={async (form) => {
          await postJson(dialog.url, { is_active: !dialog.isActive, confirmed: form.get("confirmed") === "on", reason: text(form, "reason") });
          await after("Situação atualizada.");
        }}>
          <label><span>Motivo</span><textarea name="reason" maxLength={200} /></label>
        </ActionDialog>
      )}
    </>
  );
}
