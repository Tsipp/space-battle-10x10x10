"""Проводит серию симуляций и формирует `game_logs/summary.md`.

Использование::

    python run_tournament.py --games 20 --mode advanced --max-turns 30

По умолчанию — 20 партий с сидами 1..20 в advanced-режиме.
"""
from __future__ import annotations

import argparse
import os
from collections import Counter

from simulate_game import simulate


TEAMS = ("Team A", "Team B", "Team C")


def _fmt_bytype(d: dict) -> str:
    if not d:
        return "—"
    return "; ".join(f"{k}:{v}" for k, v in sorted(d.items(), key=lambda kv: -kv[1]))


def run_tournament(
    games: int = 20,
    mode: str = "advanced",
    max_turns: int = 30,
    start_seed: int = 1,
) -> str:
    results = []
    for i in range(games):
        seed = start_seed + i
        r = simulate(max_turns=max_turns, seed=seed, game_mode=mode, write_log=True)
        results.append(r)
        print(
            f"[{i + 1:>2}/{games}] seed={seed:>3} winner={r['winner']:>6} "
            f"turns={r['turns']:>2} damage={r['total_damage']:>3}"
        )

    lines = []
    lines.append(f"# Турнир: {games} игр ({mode}, max_turns={max_turns})")
    lines.append("")
    lines.append(
        "Симуляции headless (3 бота-команды + GM-бот), детерминированные по сиду. "
        "Действия каждого бота используют все 6 способностей (HEAL / PHASE / "
        "HOLOGRAM / MINE / jump-ram / drill-ram) плюс стандартные MOVE/SHOOT."
    )
    lines.append("")

    # ---- Сводная таблица по партиям ---------------------------------------
    lines.append("## Таблица по партиям")
    lines.append("")
    header = [
        "Seed", "Winner", "Turns",
        "A живых", "B живых", "C живых",
        "A hp", "B hp", "C hp",
        "A урон", "B урон", "C урон",
        "A хиты", "B хиты", "C хиты",
        "A тараны", "B тараны", "C тараны",
        "A мины(×)", "B мины(×)", "C мины(×)",
        "A heal", "B heal", "C heal",
        "A phase", "B phase", "C phase",
        "A holo", "B holo", "C holo",
        "A mine(пост)", "B mine(пост)", "C mine(пост)",
        "A kills", "B kills", "C kills",
        "A move", "B move", "C move",
        "A shoot", "B shoot", "C shoot",
        "Σ урон", "Σ урон/ход",
    ]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "|".join(["---"] * len(header)) + "|")
    for r in results:
        st = r["stats"]
        row = [
            str(r["seed"]), r["winner"] or "—", str(r["turns"]),
            *(str(r["survivors"][t]) for t in TEAMS),
            *(str(r["remaining_hp"][t]) for t in TEAMS),
            *(str(st[t]["damage_dealt"]) for t in TEAMS),
            *(str(st[t]["shoot_hits"]) for t in TEAMS),
            *(str(st[t]["rams"]) for t in TEAMS),
            *(str(st[t]["mines_triggered"]) for t in TEAMS),
            *(str(st[t]["heals"]) for t in TEAMS),
            *(str(st[t]["phase_actions"]) for t in TEAMS),
            *(str(st[t]["hologram_actions"]) for t in TEAMS),
            *(str(st[t]["mines_placed"]) for t in TEAMS),
            *(str(st[t]["kills"]) for t in TEAMS),
            *(str(st[t]["move_actions"]) for t in TEAMS),
            *(str(st[t]["shoot_actions"]) for t in TEAMS),
            str(r["total_damage"]),
            f"{r['avg_damage_per_turn']:.2f}",
        ]
        lines.append("| " + " | ".join(row) + " |")

    # ---- Агрегаты ---------------------------------------------------------
    lines.append("")
    lines.append("## Агрегированная статистика (по всем играм)")
    lines.append("")
    wins = Counter(r["winner"] for r in results)
    total_turns = sum(r["turns"] for r in results)
    total_damage = sum(r["total_damage"] for r in results)

    lines.append(f"- Всего партий: **{games}**")
    lines.append(
        "- Победителей: "
        + ", ".join(f"{w}: {c}" for w, c in sorted(wins.items()))
    )
    lines.append(f"- Суммарно ходов: **{total_turns}**, среднее: **{total_turns / games:.2f}**")
    lines.append(f"- Суммарный урон: **{total_damage}**, среднее/партия: **{total_damage / games:.2f}**")
    lines.append("")

    lines.append("### Вклад команд (суммарно по всем играм)")
    lines.append("")
    header2 = [
        "Команда",
        "Урон", "Хиты", "Тараны", "Мины(сработ)",
        "Heal", "Phase", "Hologram", "Mine(поставл)",
        "Убийств", "Шагов MOVE", "Выстрелов",
        "Убитые типы", "Потерянные типы",
    ]
    lines.append("| " + " | ".join(header2) + " |")
    lines.append("|" + "|".join(["---"] * len(header2)) + "|")
    for t in TEAMS:
        dmg = sum(r["stats"][t]["damage_dealt"] for r in results)
        hits = sum(r["stats"][t]["shoot_hits"] for r in results)
        rams = sum(r["stats"][t]["rams"] for r in results)
        mt = sum(r["stats"][t]["mines_triggered"] for r in results)
        he = sum(r["stats"][t]["heals"] for r in results)
        ph = sum(r["stats"][t]["phase_actions"] for r in results)
        ho = sum(r["stats"][t]["hologram_actions"] for r in results)
        mp = sum(r["stats"][t]["mines_placed"] for r in results)
        kl = sum(r["stats"][t]["kills"] for r in results)
        mv = sum(r["stats"][t]["move_actions"] for r in results)
        sh = sum(r["stats"][t]["shoot_actions"] for r in results)
        kbt = Counter()
        dbt = Counter()
        for r in results:
            for k, v in r["stats"][t]["kills_by_ship_type"].items():
                kbt[k] += v
            for k, v in r["stats"][t]["deaths_by_ship_type"].items():
                dbt[k] += v
        row = [
            t, str(dmg), str(hits), str(rams), str(mt),
            str(he), str(ph), str(ho), str(mp),
            str(kl), str(mv), str(sh),
            _fmt_bytype(kbt), _fmt_bytype(dbt),
        ]
        lines.append("| " + " | ".join(row) + " |")

    # ---- Побочные метрики -------------------------------------------------
    lines.append("")
    lines.append("### Дополнительно")
    lines.append("")

    decisive = [r for r in results if r["winner"] in TEAMS]
    draws = [r for r in results if r["winner"] not in TEAMS]
    lines.append(f"- Победы до лимита ходов: **{len(decisive)}** / ничьих/патов: **{len(draws)}**")
    if decisive:
        avg_turns_decisive = sum(r["turns"] for r in decisive) / len(decisive)
        lines.append(f"- Ср. ходов в результативных играх: **{avg_turns_decisive:.2f}**")
    # Топ-3 самых «боевых» партий по суммарному урону
    top_dmg = sorted(results, key=lambda r: r["total_damage"], reverse=True)[:3]
    lines.append(
        "- Самые боевые партии (урон/сид/победитель): "
        + ", ".join(f"{r['total_damage']}@seed={r['seed']}→{r['winner']}" for r in top_dmg)
    )
    quiet = sorted(results, key=lambda r: r["total_damage"])[:3]
    lines.append(
        "- Самые «тихие» партии (мин. урон): "
        + ", ".join(f"{r['total_damage']}@seed={r['seed']}→{r['winner']}" for r in quiet)
    )

    # ---- Путь к логам -----------------------------------------------------
    lines.append("")
    lines.append("## Логи партий")
    lines.append("")
    for r in results:
        rel = os.path.relpath(r["log_path"], start=os.path.dirname(os.path.abspath(__file__)))
        lines.append(f"- seed={r['seed']}: `{rel}`")

    out_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "game_logs", "summary.md"
    )
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", type=int, default=20)
    parser.add_argument("--mode", choices=("advanced", "basic"), default="advanced")
    parser.add_argument("--max-turns", type=int, default=30)
    parser.add_argument("--start-seed", type=int, default=1)
    args = parser.parse_args()

    path = run_tournament(
        games=args.games,
        mode=args.mode,
        max_turns=args.max_turns,
        start_seed=args.start_seed,
    )
    print("\nSummary:", path)
