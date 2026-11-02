import { useEffect, useMemo, useState } from "react";
import { ApiError, apiRequest, postJson } from "../api/client";
import type { EquipmentTypeInfo, ItemDetail, UnitInfo } from "../api/types";
import { ActionDialog, text } from "./ActionDialog";

export function IncorporateItemDialog({ onClose, onCreated }: { onClose: () => void; onCreated: (item: ItemDetail) => void }) {
  const [units, setUnits] = useState<UnitInfo[]>([]);
  const [types, setTypes] = useState<EquipmentTypeInfo[]>([]);
  const [unitId, setUnitId] = useState("");
  const [condition, setCondition] = useState("fit");
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    Promise.all([apiRequest<UnitInfo[]>("/units/"), apiRequest<EquipmentTypeInfo[]>("/equipment-types/")])
      .then(([loadedUnits, loadedTypes]) => {
        setUnits(loadedUnits.filter((unit) => unit.is_active));
        setTypes(loadedTypes.filter((type) => type.is_active && type.classification === "individual"));
      })
      .catch((requestError) => setLoadError(requestError instanceof ApiError ? requestError.message : "Erro inesperado."));
  }, []);

  const locations = useMemo(
    () => units.find((unit) => unit.id === unitId)?.locations.filter((location) => location.is_active) ?? [],
    [units, unitId]
  );

  return (
    <ActionDialog
      title="Incorporar item"
      description={loadError || "O item entra na reserva com a condição declarada. Informe ao menos série ou patrimônio."}
      confirmation="Confirmo a incorporação após conferir o item e seus números."
      submitLabel="Incorporar"
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
      <label><span>Tipo de equipamento</span><select name="equipment_type_id" required defaultValue=""><option value="" disabled>Selecione</option>{types.map((type) => <option key={type.id} value={type.id}>{type.name}</option>)}</select></label>
      <label><span>Unidade</span><select name="unit_id" required value={unitId} onChange={(event) => setUnitId(event.target.value)}><option value="" disabled>Selecione</option>{units.map((unit) => <option key={unit.id} value={unit.id}>{unit.code} · {unit.name}</option>)}</select></label>
      <label><span>Local de guarda</span><select name="storage_location_id" required defaultValue="" key={unitId} disabled={!unitId}><option value="" disabled>{unitId ? "Selecione" : "Escolha a unidade"}</option>{locations.map((location) => <option key={location.id} value={location.id}>{location.code} · {location.name}</option>)}</select></label>
      <label><span>Número de série</span><input name="serial_number" maxLength={100} autoComplete="off" /></label>
      <label><span>Patrimônio</span><input name="asset_number" maxLength={100} autoComplete="off" /></label>
      <label><span>Registro oficial (opcional)</span><input name="official_identifier" maxLength={100} autoComplete="off" /></label>
      <label><span>Condição na incorporação</span><select name="condition" value={condition} onChange={(event) => setCondition(event.target.value)}><option value="fit">Apto</option><option value="unfit">Inapto</option></select></label>
      {condition === "unfit" && <label><span>Motivo de inapto</span><textarea name="condition_reason" maxLength={200} required /></label>}
    </ActionDialog>
  );
}
