export interface Session {
  user: { id: string; username: string };
  organization: { id: string; name: string };
  permissions: { can_manage_identity: boolean };
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
  permissions: { can_move: boolean; can_set_condition: boolean };
  events: Array<{
    id: string;
    type: string;
    occurred_at: string;
    actor: string;
  }>;
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

export interface AccountInfo {
  id: string;
  username: string;
  email: string;
  status: "active" | "suspended" | "revoked";
  last_login: string | null;
  revoked_at: string | null;
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

export interface UnitOption {
  id: string;
  code: string;
  name: string;
}
