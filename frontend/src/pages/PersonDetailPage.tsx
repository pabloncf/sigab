import { useEffect, useState } from "react";
import { ApiError, apiRequest, postJson, sendJson } from "../api/client";
import type { AccountInfo, Membership, PersonDetail, UnitOption } from "../api/types";
import { ActionDialog, text } from "../components/ActionDialog";
import { ErrorState, LoadingState } from "../components/Feedback";

type Dialog =
  | { kind: "edit" }
  | { kind: "person-status" }
  | { kind: "membership" }
  | { kind: "membership-status"; membership: Membership }
  | { kind: "account" }
  | { kind: "account-action"; account: AccountInfo; action: AccountAction };

type AccountAction = "suspend" | "reactivate" | "revoke";

const ACCOUNT_STATUS: Record<AccountInfo["status"], { label: string; tone: string }> = {
  active: { label: "Ativa", tone: "success" },
  suspended: { label: "Suspensa", tone: "warning" },
  revoked: { label: "Revogada", tone: "danger" }
};

const ACCOUNT_ACTION_TEXT: Record<AccountAction, { title: string; description: string; label: string }> = {
  suspend: { title: "Suspender conta", description: "O acesso é bloqueado imediatamente. Pessoa, vínculos e histórico não mudam.", label: "Suspender" },
  reactivate: { title: "Reativar conta", description: "A conta volta a permitir acesso com a senha atual.", label: "Reativar" },
  revoke: { title: "Revogar conta", description: "A revogação é definitiva: a senha é invalidada e as concessões são revogadas. Uma nova conta poderá ser criada depois.", label: "Revogar" }
};

export function PersonDetailPage({ personId }: { personId: string }) {
  const [person, setPerson] = useState<PersonDetail | null>(null);
  const [units, setUnits] = useState<UnitOption[]>([]);
  const [dialog, setDialog] = useState<Dialog | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(true);

  async function loadPerson() {
    setLoading(true);
    setError("");
    try {
      setPerson(await apiRequest<PersonDetail>(`/people/${personId}/`));
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "Erro inesperado.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void loadPerson(); }, [personId]);

  async function openMembershipDialog() {
    setSuccess("");
    if (units.length === 0) {
      try {
        setUnits(await apiRequest<UnitOption[]>("/units/"));
      } catch (requestError) {
        setError(requestError instanceof ApiError ? requestError.message : "Erro inesperado.");
        return;
      }
    }
    setDialog({ kind: "membership" });
  }

  function open(next: Dialog) {
    setSuccess("");
    setDialog(next);
  }

  function done(message: string) {
    return (updated: PersonDetail) => {
      setPerson(updated);
      setSuccess(message);
    };
  }

  if (loading) return <LoadingState />;
  if (error && !person) return <ErrorState message={error} onRetry={() => void loadPerson()} />;
  if (!person) return null;

  const openAccount = person.accounts.find((account) => account.status !== "revoked");
  const pastAccounts = person.accounts.filter((account) => account.status === "revoked");
  const suggestedUsername = person.memberships.find((membership) => membership.is_active)?.registration ?? "";

  return (
    <>
      <a className="back-link" href="/pessoas">‹ Voltar a pessoas</a>
      <section className="detail-heading">
        <div><p className="context-label">Pessoa</p><h1>{person.functional_name || person.name}</h1></div>
        <span className={`status-badge ${person.is_active ? "success" : "warning"}`}>{person.is_active ? "Ativa" : "Inativa"}</span>
      </section>

      {success && <div className="feedback success" role="status">{success}</div>}
      {error && <div className="feedback error" role="alert">{error}</div>}

      <div className="detail-grid">
        <section className="detail-card">
          <h2>Dados cadastrais</h2>
          <dl className="facts">
            <div><dt>Nome</dt><dd>{person.name}</dd></div>
            <div><dt>Nome funcional</dt><dd>{person.functional_name || "—"}</dd></div>
            <div><dt>Celular</dt><dd>{person.phone || "—"}</dd></div>
            <div><dt>CPF</dt><dd>{person.cpf_masked || "Não informado"}</dd></div>
          </dl>
          <div className="actions">
            <button className="button button-secondary" onClick={() => open({ kind: "edit" })}>Editar dados</button>
            <button className="button button-quiet" onClick={() => open({ kind: "person-status" })}>{person.is_active ? "Desativar pessoa" : "Reativar pessoa"}</button>
          </div>
        </section>

        <div className="stack">
          <section className="history-card">
            <h2>Vínculos</h2>
            {person.memberships.length === 0 ? <p className="muted">Nenhum vínculo cadastrado.</p> : (
              <ul className="sub-list">
                {person.memberships.map((membership) => (
                  <li key={membership.id}>
                    <span><strong>{membership.registration}</strong><small>{membership.main_unit.code} · {membership.main_unit.name}{membership.rank && ` · ${membership.rank}`} · {membership.is_active ? "ativo" : "inativo"}</small></span>
                    <button className="button button-quiet" onClick={() => open({ kind: "membership-status", membership })}>{membership.is_active ? "Desativar" : "Reativar"}</button>
                  </li>
                ))}
              </ul>
            )}
            <div className="actions"><button className="button button-secondary" onClick={() => void openMembershipDialog()}>Adicionar vínculo</button></div>
          </section>

          <section className="history-card">
            <h2>Conta de acesso</h2>
            {openAccount ? (
              <ul className="sub-list">
                <li>
                  <span><strong>{openAccount.username}</strong><small>{openAccount.last_login ? `Último acesso em ${new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" }).format(new Date(openAccount.last_login))}` : "Sem acesso registrado"}</small></span>
                  <span className={`status-badge ${ACCOUNT_STATUS[openAccount.status].tone}`}>{ACCOUNT_STATUS[openAccount.status].label}</span>
                </li>
              </ul>
            ) : <p className="muted">Esta pessoa não possui conta de acesso.</p>}
            {pastAccounts.length > 0 && <p className="muted">{pastAccounts.length === 1 ? "1 conta revogada" : `${pastAccounts.length} contas revogadas`} no histórico.</p>}
            <div className="actions">
              {!openAccount && person.is_active && <button className="button button-secondary" onClick={() => open({ kind: "account" })}>Criar conta</button>}
              {openAccount?.status === "active" && <button className="button button-secondary" onClick={() => open({ kind: "account-action", account: openAccount, action: "suspend" })}>Suspender</button>}
              {openAccount?.status === "suspended" && <button className="button button-secondary" onClick={() => open({ kind: "account-action", account: openAccount, action: "reactivate" })}>Reativar</button>}
              {openAccount && <button className="button button-quiet" onClick={() => open({ kind: "account-action", account: openAccount, action: "revoke" })}>Revogar</button>}
            </div>
          </section>
        </div>
      </div>

      {dialog?.kind === "edit" && (
        <ActionDialog title="Editar dados" description="Deixe o CPF em branco para mantê-lo; ele nunca é exibido completo." submitLabel="Salvar" onClose={() => setDialog(null)} onSubmit={async (form) => {
          const values: Record<string, string> = { name: text(form, "name"), functional_name: text(form, "functional_name"), phone: text(form, "phone") };
          if (text(form, "cpf").trim()) values.cpf = text(form, "cpf");
          done("Dados atualizados.")(await sendJson<PersonDetail>("PATCH", `/people/${person.id}/`, values));
        }}>
          <label><span>Nome completo</span><input name="name" required maxLength={180} defaultValue={person.name} /></label>
          <label><span>Nome funcional</span><input name="functional_name" maxLength={120} defaultValue={person.functional_name} /></label>
          <label><span>Celular</span><input name="phone" inputMode="tel" maxLength={24} defaultValue={person.phone} /></label>
          <label><span>Novo CPF</span><input name="cpf" inputMode="numeric" maxLength={14} autoComplete="off" /></label>
        </ActionDialog>
      )}

      {dialog?.kind === "person-status" && (
        <ActionDialog title={person.is_active ? "Desativar pessoa" : "Reativar pessoa"} description={person.is_active ? "A pessoa deixa de receber saídas. Vínculos, conta e histórico são preservados." : "A pessoa volta a poder receber saídas, se tiver vínculo ativo."} confirmation="Confirmo a alteração da situação desta pessoa." onClose={() => setDialog(null)} onSubmit={async (form) => {
          done("Situação atualizada.")(await postJson<PersonDetail>(`/people/${person.id}/status/`, { is_active: !person.is_active, confirmed: form.get("confirmed") === "on", reason: text(form, "reason") }));
        }}>
          <label><span>Motivo</span><textarea name="reason" maxLength={200} /></label>
        </ActionDialog>
      )}

      {dialog?.kind === "membership" && (
        <ActionDialog title="Adicionar vínculo" submitLabel="Adicionar" onClose={() => setDialog(null)} onSubmit={async (form) => {
          done("Vínculo adicionado.")(await postJson<PersonDetail>(`/people/${person.id}/memberships/`, { registration: text(form, "registration"), main_unit_id: text(form, "main_unit_id"), rank: text(form, "rank") }));
        }}>
          <label><span>Matrícula</span><input name="registration" required maxLength={64} /></label>
          <label><span>Unidade principal</span><select name="main_unit_id" required defaultValue=""><option value="" disabled>Selecione</option>{units.map((unit) => <option key={unit.id} value={unit.id}>{unit.code} · {unit.name}</option>)}</select></label>
          <label><span>Posto ou graduação</span><input name="rank" maxLength={80} /></label>
        </ActionDialog>
      )}

      {dialog?.kind === "membership-status" && (
        <ActionDialog title={dialog.membership.is_active ? "Desativar vínculo" : "Reativar vínculo"} description={`Matrícula ${dialog.membership.registration}.`} confirmation="Confirmo a alteração deste vínculo." onClose={() => setDialog(null)} onSubmit={async (form) => {
          done("Vínculo atualizado.")(await postJson<PersonDetail>(`/memberships/${dialog.membership.id}/status/`, { is_active: !dialog.membership.is_active, confirmed: form.get("confirmed") === "on", reason: text(form, "reason") }));
        }}>
          <label><span>Motivo</span><textarea name="reason" maxLength={200} /></label>
        </ActionDialog>
      )}

      {dialog?.kind === "account" && (
        <ActionDialog title="Criar conta de acesso" description="Informe a senha inicial à pessoa por canal seguro." submitLabel="Criar conta" onClose={() => setDialog(null)} onSubmit={async (form) => {
          done("Conta criada.")(await postJson<PersonDetail>(`/people/${person.id}/account/`, { username: text(form, "username"), email: text(form, "email"), password: text(form, "password") }));
        }}>
          <label><span>Identificador de login</span><input name="username" required maxLength={150} defaultValue={suggestedUsername} autoComplete="off" /></label>
          <label><span>E-mail (opcional)</span><input name="email" type="email" maxLength={254} /></label>
          <label><span>Senha inicial</span><input name="password" type="password" required autoComplete="new-password" /></label>
        </ActionDialog>
      )}

      {dialog?.kind === "account-action" && (
        <ActionDialog title={ACCOUNT_ACTION_TEXT[dialog.action].title} description={ACCOUNT_ACTION_TEXT[dialog.action].description} submitLabel={ACCOUNT_ACTION_TEXT[dialog.action].label} confirmation={`Confirmo: ${ACCOUNT_ACTION_TEXT[dialog.action].label.toLowerCase()} a conta ${dialog.account.username}.`} onClose={() => setDialog(null)} onSubmit={async (form) => {
          done("Conta atualizada.")(await postJson<PersonDetail>(`/accounts/${dialog.account.id}/${dialog.action}/`, { confirmed: form.get("confirmed") === "on", reason: text(form, "reason") }));
        }}>
          <label><span>Motivo</span><textarea name="reason" maxLength={200} /></label>
        </ActionDialog>
      )}
    </>
  );
}
