import { useEffect, useState } from "react";
import { apiRequest, postJson, describeError } from "../../api/client";
import type { EquipmentTypeInfo, Session } from "../../api/types";
import { ActionDialog, text } from "../../components/ActionDialog";
import { ErrorState, LoadingState } from "../../components/Feedback";
import { Field } from "../../components/Field";
import { formatQuantity } from "../../components/format";
import { IncorporateItemDialog } from "../../components/IncorporateItemDialog";
import { classificationHints, classificationLabels } from "./labels";

type Classification = EquipmentTypeInfo["classification"];
type Dialog =
  | { kind: "type" }
  | { kind: "item"; type: EquipmentTypeInfo }
  | { kind: "status"; type: EquipmentTypeInfo };

const sections: Array<{ classification: Classification; empty: string }> = [
  { classification: "individual", empty: "Nenhum tipo com registro cadastrado." },
  { classification: "quantitative", empty: "Nenhum tipo sem registro cadastrado." }
];

/** Módulo de cadastro de equipamentos com e sem registro (SIGAB-080). */
export function EquipmentPage({ session }: { session: Session }) {
  const permissions = session.permissions;
  const [types, setTypes] = useState<EquipmentTypeInfo[] | null>(null);
  const [dialog, setDialog] = useState<Dialog | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function load() {
    setError("");
    try {
      setTypes(await apiRequest<EquipmentTypeInfo[]>("/equipment-types/"));
    } catch (cause) {
      setError(describeError(cause));
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

  function amount(type: EquipmentTypeInfo) {
    if (type.classification === "individual") {
      if (type.item_count == null) return null;
      return type.item_count === 1 ? "1 item" : `${type.item_count} itens`;
    }
    return type.stock_quantity == null ? null : `${formatQuantity(type.stock_quantity)} no total`;
  }

  function actions(type: EquipmentTypeInfo) {
    // Uma ação principal por linha; consulta como link; alteração de situação separada.
    return (
      <span className="row-actions">
        {type.is_active && type.classification === "individual" && permissions.can_create_item && (
          <button className="button button-secondary" onClick={() => open({ kind: "item", type })}>Cadastrar item</button>
        )}
        {type.is_active && type.classification === "quantitative" && permissions.can_receive_stock && (
          <a className="button button-secondary" href={`/estoque?entrada=${type.id}`}>Registrar entrada</a>
        )}
        {permissions.can_view_items && (
          <a className="text-link" href={type.classification === "individual" ? `/acervo?tipo=${type.id}` : `/acervo?aba=sem-registro&tipo=${type.id}`}>Ver no acervo</a>
        )}
        {permissions.can_manage_catalog && (
          <button className={`button button-small ${type.is_active ? "button-danger-quiet" : "button-quiet"} row-actions-sensitive`} onClick={() => open({ kind: "status", type })}>{type.is_active ? "Desativar" : "Reativar"}</button>
        )}
      </span>
    );
  }

  if (!types) return error ? <ErrorState message={error} onRetry={() => void load()} /> : <LoadingState label="Carregando equipamentos" />;

  return (
    <>
      <section className="page-heading">
        <div>
          <p className="context-label">{session.organization.name}</p>
          <h1>Equipamentos</h1>
          <p>Tipos com registro (controle item a item) e sem registro (controle por quantidade). A partir do tipo, cadastre o item ou registre a entrada em estoque.</p>
        </div>
        {permissions.can_manage_catalog && <button className="button button-primary" onClick={() => open({ kind: "type" })}>Novo tipo</button>}
      </section>

      {success && <div className="feedback success" role="status">{success}</div>}
      {error && <div className="feedback error" role="alert">{error}</div>}

      {sections.map(({ classification, empty }) => {
        const rows = types.filter((type) => type.classification === classification);
        return (
          <section className="detail-card stock-action" key={classification} aria-labelledby={`tipos-${classification}`}>
            <h2 id={`tipos-${classification}`}>{classificationLabels[classification]}</h2>
            <p className="muted">{classificationHints[classification]}.</p>
            {rows.length === 0 ? <p className="muted">{empty}</p> : (
              <ul className="sub-list">
                {rows.map((type) => (
                  <li key={type.id}>
                    <span>
                      <strong>{type.name}</strong>
                      <small>{[amount(type), type.is_active ? "ativo" : "inativo", type.description].filter(Boolean).join(" · ")}</small>
                    </span>
                    {actions(type)}
                  </li>
                ))}
              </ul>
            )}
          </section>
        );
      })}

      {dialog?.kind === "type" && (
        <ActionDialog title="Novo tipo de equipamento" description="Escolha com cuidado: a classificação com ou sem registro não pode ser alterada depois do cadastro." submitLabel="Cadastrar" onClose={() => setDialog(null)} onSubmit={async (form) => {
          await postJson("/equipment-types/", { name: text(form, "name"), classification: text(form, "classification"), description: text(form, "description") });
          await after(`Tipo ${text(form, "name")} cadastrado.`);
        }}>
          <Field label="Nome"><input name="name" required maxLength={160} /></Field>
          <Field label="Classificação" hint="Não pode ser alterada depois do cadastro."><select name="classification" required defaultValue="">
            <option value="" disabled>Selecione</option>
            <option value="individual">Com registro ({classificationHints.individual})</option>
            <option value="quantitative">Sem registro ({classificationHints.quantitative})</option>
          </select></Field>
          <Field label="Descrição" optional><textarea name="description" maxLength={2000} /></Field>
        </ActionDialog>
      )}

      {dialog?.kind === "item" && (
        <IncorporateItemDialog typeId={dialog.type.id} onClose={() => setDialog(null)} onCreated={(item) => window.location.assign(`/items/${item.id}`)} />
      )}

      {dialog?.kind === "status" && (
        <ActionDialog
          title={dialog.type.is_active ? `Desativar o tipo “${dialog.type.name}”?` : `Reativar o tipo “${dialog.type.name}”?`}
          description={dialog.type.is_active
            ? <>O tipo <strong>{dialog.type.name}</strong> deixa de aceitar cadastro de novos itens e entradas de estoque. Itens existentes, saldos e histórico são preservados, e a reativação é possível depois.</>
            : <>O tipo <strong>{dialog.type.name}</strong> volta a aceitar cadastro de itens e entradas de estoque.</>}
          confirmation={`Confirmo: ${dialog.type.is_active ? "desativar" : "reativar"} o tipo ${dialog.type.name}.`}
          submitLabel={dialog.type.is_active ? "Desativar tipo" : "Reativar tipo"}
          tone={dialog.type.is_active ? "danger" : "default"}
          onClose={() => setDialog(null)}
          onSubmit={async (form) => {
            await postJson(`/equipment-types/${dialog.type.id}/status/`, { is_active: !dialog.type.is_active, confirmed: form.get("confirmed") === "on", reason: text(form, "reason") });
            await after(`Tipo ${dialog.type.name} ${dialog.type.is_active ? "desativado" : "reativado"}.`);
          }}>
          <Field label="Motivo" optional><textarea name="reason" maxLength={200} /></Field>
        </ActionDialog>
      )}
    </>
  );
}
