export interface Session {
  user: { id: string; username: string };
  organization: { id: string; name: string };
  /** Unidades cujo acervo a conta consulta; nomeia o escopo nas telas em vez de "seu escopo". */
  item_scope?: { all_units: boolean; units: Array<{ id: string; code: string; name: string }> };
  permissions: {
    can_manage_identity: boolean;
    can_manage_catalog: boolean;
    can_create_item: boolean;
    can_view_items: boolean;
    can_view_audit: boolean;
    can_checkout: boolean;
    can_return: boolean;
    can_use_stock: boolean;
    can_receive_stock: boolean;
    can_manage_restrictions: boolean;
    can_use_self_service: boolean;
    can_manage_biometrics?: boolean;
    can_approve_identity_exceptions?: boolean;
    /** ADR 0008: retirada e devolução exigem biometria facial ou termo aprovado. */
    identity_check_required?: boolean;
  };
}

export interface PossessionEntry {
  kind: "individual" | "quantitative";
  id: string;
  equipment_type: string;
  identifier?: string;
  quantity?: string;
  unit: string;
  due_at?: string | null;
  overdue?: boolean;
}

export interface MyPossessions {
  person: { id: string; name: string };
  possessions: PossessionEntry[];
}

export interface PersonalHistoryEntry {
  id: string;
  type: string;
  equipment_type: string;
  identifier?: string;
  quantity?: string;
  occurred_at: string;
}

export interface PersonalHistory {
  individual: PersonalHistoryEntry[];
  quantitative: PersonalHistoryEntry[];
  receipts: Array<{ id: string; code: string; confirmed_at: string }>;
}

export interface PersonalReceipt {
  receipt_code: string;
  confirmed_at: string;
  recipient: { id: string; name: string };
  operator: { id: string; username: string };
  custody_mode: string;
  due_at: string | null;
  items: Array<{ id: string; identifier: string; equipment_type: string }>;
  stock: Array<{ loan_id: string; equipment_type: string; quantity: string; open_quantity: string }>;
}

export interface ServiceBatchResult {
  id: string;
  receipt_code: string;
  custody_mode: "shift" | "fixed_term" | "indefinite";
  due_at: string | null;
}

export interface ServiceBatchOptions {
  people: Array<{ id: string; name: string }>;
  items: Array<{ id: string; identifier: string; codes?: string[]; equipment_type: string; unit: string }>;
  stock: Array<{
    id: string;
    equipment_type_id: string;
    equipment_type: string;
    unit_id: string;
    unit: string;
    storage_location_id: string;
    storage_location: string;
    quantity: string;
  }>;
}

export interface Page<T> {
  rows: T[];
  count: number;
}

export interface ItemSummary {
  id: string;
  identifier: string;
  equipment_type: string;
  administrative_status: string;
  administrative_status_label: string;
  condition: "fit" | "unfit";
  condition_label: string;
  condition_reason: string;
  availability: "available" | "in_custody" | "unavailable";
  availability_label: string;
  current_holder: { id: string; name: string } | null;
}

export interface ItemDetail extends ItemSummary {
  unit: { id: string; code: string; name: string };
  storage_location: { id: string; code: string; name: string };
  serial_number: string;
  asset_number: string;
  official_identifier: string;
  reversible_movement_id: string | null;
  permissions: { can_checkout: boolean; can_return: boolean; can_reverse: boolean; can_set_condition: boolean };
}

export interface ItemEvent {
  id: string;
  type: string;
  occurred_at: string;
  actor: string;
  movement: {
    id: string;
    type: string;
    recipient: { id: string; name: string } | null;
    condition: "fit" | "unfit" | null;
    reason: string;
    reverses: string | null;
    reversed: boolean;
    origin: "system" | "contingency";
    paper_reference: string;
    recorded_at: string;
  };
}

export interface ActivityEvent extends ItemEvent {
  item: { id: string; identifier: string; equipment_type: string };
}

export interface PersonMatch {
  id: string;
  name: string;
  is_active: boolean;
  registrations: string[];
}

export interface Recipient {
  id: string;
  name: string;
}

export interface MovementResult {
  movement_id: string;
  created: boolean;
  item: ItemSummary;
}

export interface PersonSummary {
  id: string;
  name: string;
  functional_name: string;
  is_active: boolean;
  registrations: string[];
  has_account: boolean;
}

export interface Membership {
  id: string;
  registration: string;
  rank: string;
  is_active: boolean;
  main_unit: { id: string; code: string; name: string };
}

export interface GrantInfo {
  id: string;
  role: { id: string; name: string };
  scope_type: "organization" | "unit";
  unit: { id: string; code: string; name: string } | null;
  valid_from: string | null;
  valid_until: string | null;
  active: boolean;
}

export interface AccountInfo {
  id: string;
  username: string;
  email: string;
  status: "active" | "suspended" | "revoked";
  last_login: string | null;
  revoked_at: string | null;
  grants: GrantInfo[];
}

export interface RoleOption {
  id: string;
  name: string;
  permissions: string[];
  allowed_scopes: Array<"organization" | "unit">;
}

export interface LocationInfo {
  id: string;
  code: string;
  name: string;
  is_active: boolean;
}

export interface UnitInfo {
  id: string;
  code: string;
  name: string;
  is_active: boolean;
  locations: LocationInfo[];
}

export interface EquipmentTypeInfo {
  id: string;
  name: string;
  description: string;
  classification: "individual" | "quantitative";
  classification_label: string;
  is_active: boolean;
  /** Itens com registro ativos no escopo de consulta; null para sem registro ou sem escopo. */
  item_count?: number | null;
  /** Total (reserva + em posse) de material sem registro no escopo; null caso contrário. */
  stock_quantity?: string | null;
}

export interface PersonDetail {
  id: string;
  name: string;
  functional_name: string;
  phone: string;
  cpf_masked: string;
  is_active: boolean;
  memberships: Membership[];
  accounts: AccountInfo[];
}

export type UnitOption = UnitInfo;

export interface OverviewRecent {
  kind: "individual" | "quantitative";
  id: string;
  type: string;
  type_label: string;
  equipment_type: string;
  identifier: string | null;
  item_id: string | null;
  quantity: string | null;
  unit: string;
  operator: string;
  recipient: string | null;
  occurred_at: string;
  receipt_code?: string | null;
}

export interface QuantitativeTotals {
  equipment_type_id: string;
  equipment_type: string;
  reserve: string;
  in_custody: string;
  total: string;
}

export interface Overview {
  individual: {
    totals: { available: number; in_custody: number; unavailable: number; total: number };
    by_type: Array<{ equipment_type_id: string; equipment_type: string; available: number; in_custody: number; unavailable: number }>;
  };
  quantitative: QuantitativeTotals[];
  pending: { individual_in_custody: number; quantitative_open: number; quantitative_overdue: number };
  recent: OverviewRecent[];
}

export interface StockSummaryRow {
  id: string;
  equipment_type: { id: string; name: string };
  unit: { id: string; name: string };
  storage_location: { id: string; name: string };
  reserve: string;
  in_custody: string;
  total: string;
}

export interface StockHistoryEntry {
  id: string;
  type: string;
  type_label: string;
  equipment_type: string;
  quantity: string;
  balance_delta: string;
  unit: string;
  storage_location: string;
  operator: string;
  recipient: string | null;
  reason: string;
  reverses: string | null;
  occurred_at: string;
}

export interface ReturnOptions {
  people: Array<{ id: string; name: string }>;
  items?: Array<{ id: string; identifier: string; codes?: string[]; equipment_type: string; unit: string; awaiting_approval?: boolean }>;
  stock?: Array<{ loan_id: string; equipment_type: string; unit: string; open_quantity: string; due_at: string | null; awaiting_approval?: boolean }>;
}

export interface ReturnBatchResult {
  id: string;
  receipt_code: string;
  person: { id: string; name: string };
  operator: { id: string; username: string };
  confirmed_at: string;
  items: Array<{ id: string; identifier: string; equipment_type: string; condition: "fit" | "unfit" }>;
  stock: Array<{ loan_id: string; equipment_type: string; quantity: string }>;
}

export interface RegisterRow {
  kind: "individual" | "quantitative";
  id: string;
  type: "checkout" | "return" | "consume";
  type_label: string;
  equipment_type: string;
  identifier: string | null;
  item_id: string | null;
  quantity: string | null;
  condition: "fit" | "unfit" | null;
  unit: string;
  operator: string;
  recipient: string | null;
  recipient_id: string | null;
  receipt_code: string | null;
  origin: "system" | "contingency";
  identity_method: "facial" | "signed_term" | "not_required" | "paper_contingency" | null;
  occurred_at: string;
}

export interface RegisterOptions {
  people: Array<{ id: string; name: string }>;
  operators: Array<{ id: string; username: string }>;
  equipment_types: Array<{ id: string; name: string }>;
}

export interface BiometricStatus {
  enrolled: boolean;
  enrolled_at: string | null;
  engine_version: string | null;
}

/** Pessoa identificada no balcão pela matrícula exata (entrada e saída). */
export interface CounterIdentity {
  id: string;
  name: string;
  registration: string;
  biometric_enrolled: boolean;
  open_possessions: number;
  /** Matrícula do próprio operador: outro operador precisa atender. */
  own: boolean;
  operations: { checkout: boolean; return: boolean };
}

export interface FaceVerificationResult {
  id: string;
  result: "approved" | "rejected";
  expires_at: string;
}

export type IdentityExceptionStatus = "pending_signature" | "pending_approval" | "approved" | "rejected" | "cancelled";

export interface IdentityExceptionTerm {
  id: string;
  code: string;
  operation: "checkout" | "return";
  operation_label: string;
  status: IdentityExceptionStatus;
  status_label: string;
  person: { id: string; name: string; registration: string | null };
  requested_by: string;
  requested_at: string;
  reason_code: string;
  reason_label: string;
  reason: string;
  custody_mode: string | null;
  due_at: string | null;
  items: Array<{ id: string; identifier: string; equipment_type: string; unit: string; condition: "fit" | "unfit" | null; reason?: string }>;
  stock: Array<{ equipment_type: string; unit: string; quantity: string }>;
  signed_collected_at: string | null;
  decided_by: string | null;
  decided_at: string | null;
  decision_reason: string;
  permissions: { can_register_signature: boolean; can_cancel: boolean; can_decide: boolean };
}
