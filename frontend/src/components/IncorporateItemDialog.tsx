import { useEffect, useMemo, useState } from "react";
import { apiRequest, postJson, describeError } from "../api/client";
import type { EquipmentTypeInfo, ItemDetail, UnitInfo } from "../api/types";
import { ActionDialog, text } from "./ActionDialog";
import { Field } from "./Field";

interface IncorporateItemDialogProps {
  onClose: () => void;
  onCreated: (item: ItemDetail) => void;
  /** Tipo com registro pré-selecionado quando o cadastro parte do módulo Equipamentos. */
  typeId?: string;
}

export function IncorporateItemDialog({ onClose, onCreated, typeId: initialTypeId = "" }: IncorporateItemDialogProps) {
  const [units, setUnits] = useState<UnitInfo[]>([]);
  const [types, setTypes] = useState<EquipmentTypeInfo[]>([]);
  const [typeId, setTypeId] = useState(initialTypeId);
  const [unitId, setUnitId] = useState("");
  const [condition, setCondition] = useState("fit");
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    Promise.all([apiRequest<UnitInfo[]>("/units/"), apiRequest<EquipmentTypeInfo[]>("/equipment-types/")])
      .then(([loadedUnits, loadedTypes]) => {
        setUnits(loadedUnits.filter((unit) => unit.is_active));
        setTypes(loadedTypes.filter((type) => type.is_active && type.classification === "individual"));
      })
      .catch((requestError) => setLoadError(describeError(requestError)));
  }, []);

  const locations = useMemo(
    () => units.find((unit) => unit.id === unitId)?.locations.filter((location) => location.is_active) ?? [],
    [units, unitId]
  );

  return (
    <ActionDialog
      title="Cadastrar item com registro"
      description={loadError ? `Não foi possível carregar tipos e unidades: ${loadError}` : "O item entra na reserva com a condição declarada. Informe ao menos série ou patrimônio."}
      confirmation="Confirmo a incorporação após conferir o item e seus números."
      submitLabel="Incorporar"
      size="wide"
      onClose={onClose}
      onSubmit={async (form) => {
        onCreated(await postJson<ItemDetail>("/items/", {
          equipment_type_id: text(form, "equipment_type_id"),
          unit_id: text(form, "unit_id"),
          storage_location_id: text(form, "storage_location_id"),
          serial_number: text(form, "serial_number"),
          asset_number: text(form, "asset_number"),
          official_identifier: text(form, "official_identifier"),
          condition: text(form, "condition"),
          condition_reason: text(form, "condition_reason"),
          confirmed: form.get("confirmed") === "on"
        }));
      }}
    >
      <Field label="Tipo de equipamento"><select name="equipment_type_id" required value={typeId} onChange={(event) => setTypeId(event.target.value)}><option value="" disabled>Selecione</option>{types.map((type) => <option key={type.id} value={type.id}>{type.name}</option>)}</select></Field>
      <Field label="Unidade"><select name="unit_id" required value={unitId} onChange={(event) => setUnitId(event.target.value)}><option value="" disabled>Selecione</option>{units.map((unit) => <option key={unit.id} value={unit.id}>{unit.code} · {unit.name}</option>)}</select></Field>
      <Field label="Local de guarda"><select name="storage_location_id" required defaultValue="" key={unitId} disabled={!unitId}><option value="" disabled>{unitId ? "Selecione" : "Escolha a unidade"}</option>{locations.map((location) => <option key={location.id} value={location.id}>{location.code} · {location.name}</option>)}</select></Field>
      <Field label="Número de série" hint="Informe série, patrimônio ou ambos."><input name="serial_number" maxLength={100} autoComplete="off" /></Field>
      <Field label="Patrimônio"><input name="asset_number" maxLength={100} autoComplete="off" /></Field>
      <Field label="Registro oficial" optional><input name="official_identifier" maxLength={100} autoComplete="off" /></Field>
      <Field label="Condição na incorporação"><select name="condition" value={condition} onChange={(event) => setCondition(event.target.value)}><option value="fit">Apto</option><option value="unfit">Inapto</option></select></Field>
      {condition === "unfit" && <Field label="Motivo de inapto" name="condition_reason"><textarea name="condition_reason" maxLength={200} required /></Field>}
    </ActionDialog>
  );
}
