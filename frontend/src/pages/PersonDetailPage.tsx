import { useEffect, useState } from "react";
import { ApiError, apiRequest, postJson, sendJson } from "../api/client";
import type { AccountInfo, GrantInfo, Membership, PersonDetail, RoleOption, UnitOption } from "../api/types";
import { ActionDialog, text } from "../components/ActionDialog";
import { ErrorState, LoadingState } from "../components/Feedback";

type Dialog =
  | { kind: "edit" }
  | { kind: "person-status" }
  | { kind: "membership" }
  | { kind: "membership-status"; membership: Membership }
  | { kind: "account" }
  | { kind: "account-action"; account: AccountInfo; action: AccountAction }
  | { kind: "grant"; account: AccountInfo }
  | { kind: "grant-revoke"; grant: GrantInfo };

type AccountAction = "suspend" | "reactivate" | "revoke" | "end-sessions";

const ACCOUNT_STATUS: Record<AccountInfo["status"], { label: string; tone: string }> = {
  active: { label: "Ativa", tone: "success" },
  suspended: { label: "Suspensa", tone: "warning" },
  revoked: { label: "Revogada", tone: "danger" }
};

const ACCOUNT_ACTION_TEXT: Record<AccountAction, { title: string; description: string; label: string }> = {
  suspend: { title: "Suspender conta", description: "O acesso é bloqueado imediatamente. Pessoa, vínculos e histórico não mudam.", label: "Suspender" },
  reactivate: { title: "Reativar conta", description: "A conta volta a permitir acesso com a senha atual.", label: "Reativar" },
  revoke: { title: "Revogar conta", description: "A revogação é definitiva: a senha é invalidada e as concessões são revogadas. Uma nova conta poderá ser criada depois.", label: "Revogar" },
  "end-sessions": { title: "Encerrar sessões", description: "Todas as sessões abertas desta conta são encerradas; a conta continua ativa.", label: "Encerrar sessões" }
};

const SCOPE_LABEL = { organization: "Organização", unit: "Unidade" } as const;

export function PersonDetailPage({ personId }: { personId: string }) {
  const [person, setPerson] = useState<PersonDetail | null>(null);
  const [units, setUnits] = useState<UnitOption[]>([]);
  const [roles, setRoles] = useState<RoleOption[]>([]);
  const [grantRoleId, setGrantRoleId] = useState("");
  const [grantScope, setGrantScope] = useState<"organization" | "unit">("organization");
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

  async function loadUnits(): Promise<boolean> {
    if (units.length > 0) return true;
    try {
      setUnits((await apiRequest<UnitOption[]>("/units/")).filter((unit) => unit.is_active));
      return true;
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "Erro inesperado.");
      return false;
    }
  }

  async function openMembershipDialog() {
    setSuccess("");
    if (await loadUnits()) setDialog({ kind: "membership" });
  }

  async function openGrantDialog(account: AccountInfo) {
    setSuccess("");
    if (!(await loadUnits())) return;
    try {
      const loaded = roles.length > 0 ? roles : await apiRequest<RoleOption[]>("/roles/");
      setRoles(loaded);
      setGrantRoleId("");
      setGrantScope("organization");
      setDialog({ kind: "grant", account });
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "Erro inesperado.");
    }
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
            {openAccount && openAccount.status !== "revoked" && (
              <>
                <h3>Papéis e escopo</h3>
                {openAccount.grants.length === 0 ? <p className="muted">Nenhuma concessão: a conta não tem permissão alguma.</p> : (
                  <ul className="sub-list">
                    {openAccount.grants.map((grant) => (
                      <li key={grant.id}>
                        <span><strong>{grant.role.name}</strong><small>{SCOPE_LABEL[grant.scope_type]}{grant.unit && ` · ${grant.unit.code}`}{grant.valid_until && ` · até ${new Intl.DateTimeFormat("pt-BR", { dateStyle: "short" }).format(new Date(grant.valid_until))}`}</small></span>
                        <button className="button button-quiet" onClick={() => open({ kind: "grant-revoke", grant })}>Revogar</button>
                      </li>
                    ))}
                  </ul>
                )}
              </>
            )}
            {pastAccounts.length > 0 && <p className="muted">{pastAccounts.length === 1 ? "1 conta revogada" : `${pastAccounts.length} contas revogadas`} no histórico.</p>}
            <div className="actions">
              {!openAccount && person.is_active && <button className="button button-secondary" onClick={() => open({ kind: "account" })}>Criar conta</button>}
              {openAccount?.status === "active" && <button className="button button-secondary" onClick={() => open({ kind: "account-action", account: openAccount, action: "suspend" })}>Suspender</button>}
              {openAccount?.status === "suspended" && <button className="button button-secondary" onClick={() => open({ kind: "account-action", account: openAccount, action: "reactivate" })}>Reativar</button>}
              {openAccount?.status === "active" && <button className="button button-secondary" onClick={() => void openGrantDialog(openAccount)}>Conceder papel</button>}
              {openAccount?.status === "active" && <button className="button button-quiet" onClick={() => open({ kind: "account-action", account: openAccount, action: "end-sessions" })}>Encerrar sessões</button>}
              {openAccount && <button className="button button-quiet" onClick={() => open({ kind: "account-action", account: openAccount, action: "revoke" })}>Revogar conta</button>}
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

      {dialog?.kind === "grant" && (
        <ActionDialog title="Conceder papel" description={`Conta ${dialog.account.username}. O motivo fica no histórico de perfil.`} submitLabel="Conceder" onClose={() => setDialog(null)} onSubmit={async (form) => {
          done("Papel concedido.")(await postJson<PersonDetail>(`/accounts/${dialog.account.id}/grants/`, {
            role_id: grantRoleId,
            scope_type: grantScope,
            unit_id: grantScope === "unit" ? text(form, "unit_id") : null,
            valid_until: text(form, "valid_until") ? new Date(text(form, "valid_until")).toISOString() : null,
            reason: text(form, "reason")
          }));
        }}>
          <label><span>Papel</span><select required value={grantRoleId} onChange={(event) => {
            const role = roles.find((candidate) => candidate.id === event.target.value);
            setGrantRoleId(event.target.value);
            if (role && !role.allowed_scopes.includes(grantScope)) setGrantScope(role.allowed_scopes[0]);
          }}><option value="" disabled>Selecione</option>{roles.map((role) => <option key={role.id} value={role.id}>{role.name}</option>)}</select></label>
          <label><span>Escopo</span><select value={grantScope} onChange={(event) => setGrantScope(event.target.value as "organization" | "unit")}>{(roles.find((role) => role.id === grantRoleId)?.allowed_scopes ?? ["organization", "unit"]).map((scope) => <option key={scope} value={scope}>{SCOPE_LABEL[scope]}</option>)}</select></label>
          {grantScope === "unit" && <label><span>Unidade</span><select name="unit_id" required defaultValue=""><option value="" disabled>Selecione</option>{units.map((unit) => <option key={unit.id} value={unit.id}>{unit.code} · {unit.name}</option>)}</select></label>}
          <label><span>Válido até (opcional)</span><input name="valid_until" type="datetime-local" /></label>
          <label><span>Motivo</span><textarea name="reason" maxLength={200} required /></label>
        </ActionDialog>
      )}

      {dialog?.kind === "grant-revoke" && (
        <ActionDialog title="Revogar papel" description={`${dialog.grant.role.name} · ${SCOPE_LABEL[dialog.grant.scope_type]}${dialog.grant.unit ? ` ${dialog.grant.unit.code}` : ""}.`} confirmation="Confirmo a revogação desta concessão." submitLabel="Revogar" onClose={() => setDialog(null)} onSubmit={async (form) => {
          done("Concessão revogada.")(await postJson<PersonDetail>(`/grants/${dialog.grant.id}/revoke/`, { confirmed: form.get("confirmed") === "on", reason: text(form, "reason") }));
        }}>
          <label><span>Motivo</span><textarea name="reason" maxLength={200} required /></label>
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
