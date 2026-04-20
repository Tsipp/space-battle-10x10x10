"""Headless-симуляция одного матча Space Battle 10×10×10.

Запускает настоящую игровую логику (`GameServer.process_turn` и
`handle_gm_command`), минуя TCP и Tk: это гарантирует, что симуляция тестирует
ТОТ ЖЕ код, который работает в реальной игре, но без зависимости от сети и GUI.

На каждом ходу:
  * GM-бот посылает ``start_turn`` → сервер «разрешает» фазу планирования.
  * Каждая из 3-х команд-ботов принимает решения для своих кораблей (move/shoot/
    skip) на основе видимых врагов (сервер рассчитывает видимость через
    `get_visible_enemies`).
  * Собранные действия передаются в `process_turn`.
  * GM-бот при необходимости может сделать ``override_ship`` (например, чтобы
    воскресить корабль, который «нечестно» погиб, — тут не используется, просто
    показан механизм).

Полный лог (все решения ботов, попадания, состояние кораблей после каждого
хода) пишется в ``game_logs/game_<timestamp>.log``.

Запуск::

    python simulate_game.py

"""
from __future__ import annotations

import os
import random
import sys
import time
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from server_full_visibility import GameServer  # noqa: E402
from shared_simple import Action, ActionType, ShipType, Team  # noqa: E402


# ---------------------------------------------------------------------------
# Утилита: буфер лога
# ---------------------------------------------------------------------------
class TranscriptLogger:
    """Накапливает строки лога и умеет их сбрасывать в файл.

    Также служит "GUI-заглушкой" для GameServer: у него ожидается метод
    ``log(message, tag)``.
    """

    def __init__(self):
        self.lines: list[str] = []

    def log(self, message: str, tag: str = "info"):
        # Приписываем тег компактно в префикс — полезно для отладки.
        prefix = {
            'info': '',
            'success': '✓ ',
            'warning': '! ',
            'error': 'x ',
            'system': '# ',
        }.get(tag, '')
        self.lines.append(f"{prefix}{message}")

    def section(self, title: str):
        self.lines.append("")
        self.lines.append("=" * 70)
        self.lines.append(title)
        self.lines.append("=" * 70)

    def h(self, title: str):
        self.lines.append("")
        self.lines.append(f"--- {title} ---")

    def p(self, line: str = ""):
        self.lines.append(line)

    def dump(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(self.lines))
            f.write("\n")


# ---------------------------------------------------------------------------
# Стратегия команды-бота
# ---------------------------------------------------------------------------
class TeamBot:
    """Простейшая детерминированная стратегия.

    Порядок принятия решения для каждого корабля:
      1. Если корабль видит хоть одного врага и может стрелять — стреляем в
         того, по кому реально проходит `can_shoot_at` (с учётом типа).
      2. Иначе, если корабль умеет двигаться — делаем шаг в сторону ближайшего
         видимого врага (или к центру куба, если никого не видно).
      3. Иначе (радиовышка, либо некуда идти) — пропуск хода.
    """

    def __init__(self, team: Team, rng: random.Random):
        self.team = team
        self.rng = rng

    def decide(self, server: GameServer) -> list[Action]:
        ships = server.game_state['ships']
        my_ships = [s for s in ships.values() if s.team == self.team and s.alive]
        # Видимые враги на уровне команды (радиовышка видит всю плоскость Z).
        visible = server.get_visible_enemies(self.team)
        # Преобразуем обратно из dict в объекты, чтобы оперировать позициями.
        visible_ships = [ships[sid] for sid in visible.keys() if sid in ships]

        actions: list[Action] = []
        # Зарезервированные целевые клетки для move на этом ходу — чтобы два
        # наших корабля не пытались влезть в одну и ту же клетку (коллизии
        # всё равно отсечёт сервер, но и так красивее).
        reserved_cells: set[tuple[int, int, int]] = {(s.x, s.y, s.z) for s in my_ships}

        for ship in my_ships:
            action = self._decide_ship(ship, visible_ships, my_ships, reserved_cells)
            if action is not None:
                actions.append(action)
                if action.action_type == ActionType.MOVE:
                    reserved_cells.add(
                        (action.target_x, action.target_y, action.target_z)
                    )
        return actions

    # --- shoot helpers -------------------------------------------------------

    def _pick_shoot_target(self, ship, enemies):
        """Ищет врага, по которому данный корабль реально может выстрелить.

        При равной дистанции выбор рандомизирован rng, чтобы партии
        с разными сидами ветвились по-разному.
        """
        if not ship.can_shoot or not enemies:
            return None

        def _dist(e):
            return max(abs(e.x - ship.x), abs(e.y - ship.y), abs(e.z - ship.z))

        shuffled = list(enemies)
        self.rng.shuffle(shuffled)
        ordered = sorted(shuffled, key=_dist)
        for enemy in ordered:
            if ship.can_shoot_at(enemy.x, enemy.y, enemy.z):
                return enemy
        return None

    # --- move helpers --------------------------------------------------------

    def _step_toward(self, sx, sy, sz, tx, ty, tz, reserved):
        """Один шаг на 1 клетку по каждой из осей в сторону (tx, ty, tz).
        Избегает занятых клеток из `reserved`."""
        def _sgn(a, b):
            if a < b:
                return 1
            if a > b:
                return -1
            return 0

        # Попробуем «жадный» вариант + несколько запасных, чтобы обойти
        # случай «клетка прямо впереди занята союзником».
        dx0, dy0, dz0 = _sgn(sx, tx), _sgn(sy, ty), _sgn(sz, tz)
        fallback = [
            (dx0, dy0, 0), (dx0, 0, dz0), (0, dy0, dz0),
            (dx0, 0, 0), (0, dy0, 0), (0, 0, dz0),
        ]
        # Подмешиваем рандомизацию: если есть несколько равнозначных
        # шагов — сид rng выбирает, куда пойдём, чтобы разные партии ветвились.
        self.rng.shuffle(fallback)
        candidates = [(dx0, dy0, dz0), *fallback]
        for (dx, dy, dz) in candidates:
            if dx == 0 and dy == 0 and dz == 0:
                continue
            nx, ny, nz = sx + dx, sy + dy, sz + dz
            if not (0 <= nx < 10 and 0 <= ny < 10 and 0 <= nz < 10):
                continue
            if (nx, ny, nz) in reserved:
                continue
            return nx, ny, nz
        return None

    def _decide_ship(self, ship, visible_ships, my_ships, reserved):
        # 1) Стрельба
        target = self._pick_shoot_target(ship, visible_ships)
        if target is not None:
            return Action(
                ship_id=ship.id,
                action_type=ActionType.SHOOT,
                target_x=target.x, target_y=target.y, target_z=target.z,
            )

        # 2) Движение
        if ship.move_range > 0:
            # Цель: ближайший видимый враг; если таких нет — центр карты.
            if visible_ships:
                anchor = min(
                    visible_ships,
                    key=lambda e: max(
                        abs(e.x - ship.x), abs(e.y - ship.y), abs(e.z - ship.z)
                    ),
                )
                tx, ty, tz = anchor.x, anchor.y, anchor.z
            else:
                tx, ty, tz = 5, 5, 5

            step = self._step_toward(
                ship.x, ship.y, ship.z, tx, ty, tz, reserved
            )
            if step is None:
                return None  # Некуда шагнуть — пропуск.
            nx, ny, nz = step
            return Action(
                ship_id=ship.id,
                action_type=ActionType.MOVE,
                target_x=nx, target_y=ny, target_z=nz,
            )

        # 3) Ни стрелять, ни двигаться — пропускаем.
        return None


# ---------------------------------------------------------------------------
# GM-бот
# ---------------------------------------------------------------------------
class GmBot:
    """Простейший GM-бот — просто просит сервер начинать каждый ход и даёт
    сигнал "end_planning" сразу после того, как боты сформировали действия.
    В будущем сюда можно добавить произвольные ``override_ship`` — сервер это
    умеет.
    """

    def start_turn(self, server: GameServer):
        server.handle_gm_command({'type': 'gm_command', 'command': 'start_turn'})

    def end_planning(self, server: GameServer):
        server.handle_gm_command({'type': 'gm_command', 'command': 'end_planning'})

    def stop(self, server: GameServer):
        server.handle_gm_command({'type': 'gm_command', 'command': 'stop'})


# ---------------------------------------------------------------------------
# Описание одного хода (для лога)
# ---------------------------------------------------------------------------
def describe_action(ship, action):
    if action.action_type == ActionType.MOVE:
        return (
            f"[{ship.team.value}] {ship.name} "
            f"({ship.x},{ship.y},{ship.z}) → MOVE "
            f"({action.target_x},{action.target_y},{action.target_z})"
        )
    if action.action_type == ActionType.SHOOT:
        return (
            f"[{ship.team.value}] {ship.name} "
            f"({ship.x},{ship.y},{ship.z}) → SHOOT at "
            f"({action.target_x},{action.target_y},{action.target_z})"
        )
    return f"[{ship.team.value}] {ship.name} → {action.action_type}"


def team_summary(server: GameServer) -> list[str]:
    lines = []
    ships = server.game_state['ships']
    for team in (Team.TEAM_A, Team.TEAM_B, Team.TEAM_C):
        alive = [s for s in ships.values() if s.team == team and s.alive]
        dead = [s for s in ships.values() if s.team == team and not s.alive]
        lines.append(
            f"  {team.value}: живых {len(alive)}/{len(alive)+len(dead)}"
        )
        for s in alive:
            lines.append(
                f"    ✓ {s.name:<18} @ ({s.x},{s.y},{s.z}) "
                f"hp={s.max_hits - s.hits}/{s.max_hits}"
            )
        for s in dead:
            lines.append(
                f"    ✗ {s.name:<18} @ ({s.x},{s.y},{s.z}) [уничтожен]"
            )
    return lines


# ---------------------------------------------------------------------------
# Главный цикл
# ---------------------------------------------------------------------------
def simulate(
    max_turns: int = 30,
    seed: int = 42,
    game_mode: str = 'advanced',
) -> str:
    """Проводит один матч и возвращает путь к лог-файлу."""
    rng = random.Random(seed)
    transcript = TranscriptLogger()

    server = GameServer(
        host='127.0.0.1', port=0, game_mode=game_mode, gui=transcript
    )
    # GameServer в __init__ уже сделал create_ships и залогировал в gui.

    bots = {
        Team.TEAM_A: TeamBot(Team.TEAM_A, rng),
        Team.TEAM_B: TeamBot(Team.TEAM_B, rng),
        Team.TEAM_C: TeamBot(Team.TEAM_C, rng),
    }
    gm = GmBot()

    # Шапка.
    transcript.lines.insert(0, f"Seed: {seed}")
    transcript.lines.insert(0, f"Game mode: {game_mode}")
    transcript.lines.insert(
        0, f"Space Battle 10×10×10 — simulation run at "
           f"{datetime.now(timezone.utc).isoformat(timespec='seconds')}"
    )
    transcript.lines.insert(0, "=" * 70)
    transcript.lines.append("")  # пустая строка перед турнирными ходами

    transcript.h("СТАРТОВАЯ РАССТАНОВКА")
    for line in team_summary(server):
        transcript.p(line)

    turn = 0
    while turn < max_turns and not server.game_state['game_over']:
        turn += 1
        transcript.section(f"ХОД {turn}")

        # 1. GM сигналит "начать ход".
        gm.start_turn(server)
        transcript.p("GM: start_turn")

        # 2. Каждая команда собирает действия.
        actions_by_team: dict[Team, list[Action]] = {}
        for team, bot in bots.items():
            actions_by_team[team] = bot.decide(server)

        # 3. Логируем принятые решения.
        transcript.h("Решения ботов")
        ships = server.game_state['ships']
        for team in (Team.TEAM_A, Team.TEAM_B, Team.TEAM_C):
            team_actions = actions_by_team[team]
            if not team_actions:
                transcript.p(f"  [{team.value}] все корабли пропускают ход")
                continue
            for action in team_actions:
                ship = ships.get(action.ship_id)
                if ship is None:
                    continue
                transcript.p(f"  {describe_action(ship, action)}")
            # Корабли без явного действия = пропуск.
            passed = {s.id for s in ships.values() if s.team == team and s.alive} \
                - {a.ship_id for a in team_actions}
            for sid in passed:
                s = ships[sid]
                transcript.p(f"  [{team.value}] {s.name} → SKIP")

        # 4. GM сигналит "end_planning".
        gm.end_planning(server)
        transcript.p("GM: end_planning")

        # 5. Загружаем actions_received и процессим ход.
        server.actions_received = actions_by_team
        turn_before_hits = len(server.game_state['hit_history'])
        server.process_turn()

        # 6. Записываем результаты хода.
        new_hits = server.game_state['hit_history'][turn_before_hits:]
        transcript.h("Результаты хода")
        if not new_hits:
            transcript.p("  Попаданий нет")
        else:
            for h in new_hits:
                marker = "УБИТ" if h['killed'] else "ранен"
                transcript.p(
                    f"  {h['attacker']} / {h['attacker_name']:<18} → "
                    f"{h['target']} / {h['target_name']:<18} "
                    f"@ {h['position']}  ({marker})"
                )

        transcript.h("Состояние команд после хода")
        for line in team_summary(server):
            transcript.p(line)

    # --- конец матча -------------------------------------------------------
    transcript.section("ИТОГ")
    if server.game_state['game_over']:
        winner = server.game_state.get('winner') or '—'
        transcript.p(f"Игра окончена. Победитель: {winner}")
        transcript.p(f"Ходов сыграно: {turn}")
    else:
        transcript.p(f"Лимит ходов ({max_turns}) исчерпан, ничья/пат.")

    # Статистика по командам.
    ships = server.game_state['ships']
    transcript.h("Сводка по командам")
    for team in (Team.TEAM_A, Team.TEAM_B, Team.TEAM_C):
        alive = sum(1 for s in ships.values() if s.team == team and s.alive)
        total = sum(1 for s in ships.values() if s.team == team)
        transcript.p(f"  {team.value}: {alive}/{total} живых кораблей")

    transcript.h("Сводка по попаданиям")
    history = server.game_state['hit_history']
    kills = sum(1 for h in history if h['killed'])
    transcript.p(f"  Всего попаданий: {len(history)}")
    transcript.p(f"  Уничтожено кораблей: {kills}")
    by_team: dict[str, int] = {}
    for h in history:
        by_team[h['attacker']] = by_team.get(h['attacker'], 0) + 1
    for team_name, count in sorted(by_team.items()):
        transcript.p(f"  Попаданий от {team_name}: {count}")

    # GM-бот завершает игру.
    gm.stop(server)

    # --- дамп ----------------------------------------------------------------
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")
    out_path = os.path.join(
        ROOT, "game_logs", f"game_{ts}_{game_mode}_seed{seed}.log"
    )
    transcript.dump(out_path)

    # Закрыть сокет, чтобы не оставался открытый файловый дескриптор.
    try:
        server.server.close()
    except Exception:
        pass

    return out_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Headless Space Battle simulation")
    parser.add_argument("--seed", type=int, default=42,
                        help="RNG seed (для детерминированности)")
    parser.add_argument("--max-turns", type=int, default=30,
                        help="Максимум ходов до объявления ничьей")
    parser.add_argument("--mode", choices=("advanced", "basic"), default="advanced",
                        help="Режим игры: advanced (разные типы) или basic (только крейсеры)")
    args = parser.parse_args()

    path = simulate(
        max_turns=args.max_turns,
        seed=args.seed,
        game_mode=args.mode,
    )
    print(f"Simulation complete. Log written to:\n  {path}")
