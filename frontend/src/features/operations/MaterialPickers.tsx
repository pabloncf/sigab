import { KeyboardEvent, useId, useState } from "react";
import { formatQuantity } from "../../components/format";

export interface RegisteredOption {
  id: string;
  identifier: string;
  codes?: string[];
  equipment_type: string;
  unit: string;
}

function onEnter(action: () => void) {
  // Os seletores ficam dentro do formulário da operação: Enter adiciona, não confirma.
  return (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter") { event.preventDefault(); action(); }
  };
}

/** Material com registro: o operador digita o número de série ou patrimônio. */
export function RegisteredPicker({ options, onAdd }: { options: RegisteredOption[]; onAdd: (id: string) => void }) {
  const list = useId();
  const [value, setValue] = useState("");
  const [error, setError] = useState("");

  function add() {
    const term = value.trim().toLowerCase();
    if (!term) return;
    const match = options.find((option) => [option.identifier, ...(option.codes ?? [])].some((code) => code.toLowerCase() === term));
    if (!match) {
      setError(`Nenhum material com registro disponível com o número "${value.trim()}".`);
      return;
    }
    onAdd(match.id);
    setValue("");
    setError("");
  }

  return (
    <div className="material-picker">
      <label><span>Número do material (série ou patrimônio)</span>
        <input value={value} list={list} autoComplete="off" onChange={(event) => { setValue(event.target.value); setError(""); }} onKeyDown={onEnter(add)} />
      </label>
      <datalist id={list}>{options.map((option) => <option key={option.id} value={option.identifier}>{option.equipment_type} · {option.unit}</option>)}</datalist>
      <button className="button button-secondary" type="button" aria-label="Adicionar material com registro" onClick={add}>Adicionar</button>
      {error && <p className="field-error" role="alert">{error}</p>}
    </div>
  );
}

export interface UnregisteredOption {
  id: string;
  name: string;
  detail: string;
  max: string;
}

/** Material sem registro: o operador digita o nome do material e a quantidade. */
export function UnregisteredPicker({ options, onAdd }: { options: UnregisteredOption[]; onAdd: (id: string, quantity: string) => void }) {
  const list = useId();
  const [value, setValue] = useState("");
  const [quantity, setQuantity] = useState("");
  const [error, setError] = useState("");
  const label = (option: UnregisteredOption) => `${option.name} · ${option.detail}`;

  function add() {
    const term = value.trim().toLowerCase();
    if (!term) return;
    const exact = options.filter((option) => label(option).toLowerCase() === term);
    const byName = options.filter((option) => option.name.toLowerCase() === term);
    const partial = options.filter((option) => option.name.toLowerCase().includes(term));
    const matches = exact.length ? exact : byName.length ? byName : partial;
    if (matches.length === 0) { setError(`Nenhum material sem registro disponível com o nome "${value.trim()}".`); return; }
    if (matches.length > 1) { setError("Mais de um material corresponde. Escolha nas sugestões o local desejado."); return; }
    const amount = Number(quantity);
    if (!quantity.trim() || !(amount > 0)) { setError("Informe a quantidade."); return; }
    if (amount > Number(matches[0].max)) { setError(`Quantidade acima do disponível (${formatQuantity(matches[0].max)}).`); return; }
    onAdd(matches[0].id, quantity.trim());
    setValue("");
    setQuantity("");
    setError("");
  }

  return (
    <div className="material-picker">
      <label><span>Nome do material</span>
        <input value={value} list={list} autoComplete="off" onChange={(event) => { setValue(event.target.value); setError(""); }} onKeyDown={onEnter(add)} />
      </label>
      <datalist id={list}>{options.map((option) => <option key={option.id} value={label(option)}>disponível {formatQuantity(option.max)}</option>)}</datalist>
      <label className="quantity"><span>Quantidade</span>
        <input type="number" min="0" step="0.001" value={quantity} onChange={(event) => { setQuantity(event.target.value); setError(""); }} onKeyDown={onEnter(add)} />
      </label>
      <button className="button button-secondary" type="button" aria-label="Adicionar material sem registro" onClick={add}>Adicionar</button>
      {error && <p className="field-error" role="alert">{error}</p>}
    </div>
  );
}
