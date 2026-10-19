#!/usr/bin/env python3
"""Convert the SIGAB product backlog to a Jira Cloud import CSV."""

import argparse
import csv
import re
import unicodedata
from pathlib import Path

REQUIRED_COLUMNS = {
    "id",
    "epico",
    "tipo",
    "tarefa",
    "descricao",
    "prioridade",
    "status_inicial",
    "sprint_sugerida",
    "responsavel_sugerido",
    "dependencias",
    "entregavel",
    "criterio_de_aceite",
    "requisitos_relacionados",
    "observacoes",
}

STATUS = {
    "pronto": "Done",
    "pendente": "To Do",
    "pendente_decisao": "To Do",
    "bloqueado": "To Do",
    "backlog": "To Do",
}

PRIORITY = {"P0": "Highest", "P1": "High", "P2": "Medium"}


def slug(value: str) -> str:
    normalized = "".join(
        character
        for character in unicodedata.normalize("NFKD", value.lower())
        if not unicodedata.combining(character)
    )
    return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")


def numeric_id(external_id: str) -> str:
    return str(int(external_id.rsplit("-", 1)[1]))


def description(row: dict[str, str]) -> str:
    sections = [
        row["descricao"],
        f"ID original: {row['id']}",
        f"Tipo original: {row['tipo']}",
        f"Sprint sugerida: {row['sprint_sugerida']}",
        f"Responsável sugerido: {row['responsavel_sugerido']}",
        f"Entregável: {row['entregavel']}",
        f"Critério de aceite: {row['criterio_de_aceite']}",
        f"Requisitos relacionados: {row['requisitos_relacionados']}",
    ]
    if row["dependencias"]:
        sections.append(f"Dependências originais: {row['dependencias']}")
    if row["observacoes"]:
        sections.append(f"Observações: {row['observacoes']}")
    return "\n\n".join(sections)


def convert(source: Path, destination: Path) -> None:
    with source.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not REQUIRED_COLUMNS.issubset(reader.fieldnames):
            raise SystemExit("O arquivo de origem não possui o formato original do backlog SIGAB.")
        tasks = list(reader)

    epics = list(dict.fromkeys(row["epico"] for row in tasks))
    epic_ids = {name: str(1000 + index) for index, name in enumerate(epics, start=1)}
    max_dependencies = max(
        (len([item for item in row["dependencias"].split(";") if item]) for row in tasks),
        default=0,
    )
    headers = [
        "Work Type",
        "Status",
        "Summary",
        "Description",
        "Priority",
        "Labels",
        "Labels",
        "Labels",
        "Labels",
        "Component",
        "Work item ID",
        "Parent",
        *(["Is Blocked By"] * max_dependencies),
    ]

    rows: list[list[str]] = []
    for epic in epics:
        rows.append(
            [
                "Epic",
                "To Do",
                f"SIGAB — {epic}",
                f"Agrupa as tarefas do épico {epic} do backlog inicial do SIGAB.",
                "Highest",
                "sigab",
                "epic",
                f"epic-{slug(epic)}",
                "",
                epic,
                epic_ids[epic],
                "",
                *([""] * max_dependencies),
            ]
        )

    for task in tasks:
        dependencies = [
            numeric_id(item.strip()) for item in task["dependencias"].split(";") if item.strip()
        ]
        rows.append(
            [
                "Task",
                STATUS.get(task["status_inicial"], "To Do"),
                f"[{task['id']}] {task['tarefa']}",
                description(task),
                PRIORITY.get(task["prioridade"], "Medium"),
                "sigab",
                f"tipo-{slug(task['tipo'])}",
                f"origem-{slug(task['status_inicial'])}",
                f"sprint-{slug(task['sprint_sugerida'])}",
                task["epico"],
                numeric_id(task["id"]),
                epic_ids[task["epico"]],
                *dependencies,
                *([""] * (max_dependencies - len(dependencies))),
            ]
        )

    temporary = destination.with_suffix(destination.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
        writer.writerow(headers)
        writer.writerows(rows)
    temporary.replace(destination)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path, nargs="?")
    args = parser.parse_args()
    convert(args.source, args.destination or args.source)


if __name__ == "__main__":
    main()
