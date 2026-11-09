export interface Session {
  user: { id: string; username: string };
  organization: { id: string; name: string };
  permissions: {
    can_manage_identity: boolean;
    can_manage_catalog: boolean;
    can_create_item: boolean;
    can_view_items: boolean;
    can_view_audit: boolean;
    can_checkout: boolean;
    can_use_self_service: boolean;
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
  items: Array<{ id: string; identifier: string; equipment_type: string; unit: string }>;
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
