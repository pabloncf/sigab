import type { EquipmentTypeInfo } from "../../api/types";

type Classification = EquipmentTypeInfo["classification"];

/** Rótulos de interface; a API mantém os valores individual/quantitative (SIGAB-080). */
export const classificationLabels: Record<Classification, string> = {
  individual: "Com registro",
  quantitative: "Sem registro"
};

export const classificationHints: Record<Classification, string> = {
  individual: "controle item a item, com número de série ou patrimônio",
  quantitative: "controle por quantidade em estoque, como munição"
};
