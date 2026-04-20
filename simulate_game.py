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
        # ---- Способности нестандартных кораблей (только в advanced) --------
        # Тишина: вошёл в фазу, если ранен; выходит, когда полностью здоров.
        if getattr(ship, 'can_phase', False):
            if ship.is_phased and ship.hits == 0:
                return Action(ship.id, ActionType.PHASE)
            if not ship.is_phased and ship.hits > 0:
                return Action(ship.id, ActionType.PHASE)
            # Если ранен и уже в фазе — двигаемся к союзнику-Факелу.
            # Здоров и не в фазе — обычное поведение ниже.

        # Факел: лечит, если рядом есть раненый союзник (включая себя).
        if getattr(ship, 'heal_range', 0) > 0:
            has_wounded_ally = any(
                ally.alive and ally.hits > 0
                and max(abs(ally.x - ship.x), abs(ally.y - ship.y), abs(ally.z - ship.z))
                    <= ship.heal_range
                for ally in my_ships
            )
            if has_wounded_ally:
                return Action(ship.id, ActionType.HEAL)

        # Провокатор: ставит голограмму в соседнюю клетку в сторону ближайшего
        # врага, если враг в пределах 4 клеток и такая клетка свободна.
        if getattr(ship, 'can_create_hologram', False) and visible_ships:
            nearest = min(
                visible_ships,
                key=lambda e: max(
                    abs(e.x - ship.x), abs(e.y - ship.y), abs(e.z - ship.z)
                ),
            )
            dist = max(
                abs(nearest.x - ship.x),
                abs(nearest.y - ship.y),
                abs(nearest.z - ship.z),
            )
            if 1 <= dist <= 5:
                step = self._step_toward(
                    ship.x, ship.y, ship.z, nearest.x, nearest.y, nearest.z, reserved
                )
                if step is not None:
                    tx, ty, tz = step
                    return Action(
                        ship.id, ActionType.HOLOGRAM, tx, ty, tz
                    )

        # Паук: ставит мину в клетку между собой и ближайшим врагом.
        if getattr(ship, 'can_place_mine', False) and visible_ships:
            nearest = min(
                visible_ships,
                key=lambda e: max(
                    abs(e.x - ship.x), abs(e.y - ship.y), abs(e.z - ship.z)
                ),
            )
            dist = max(
                abs(nearest.x - ship.x),
                abs(nearest.y - ship.y),
                abs(nearest.z - ship.z),
            )
            if 1 <= dist <= 4:
                step = self._step_toward(
                    ship.x, ship.y, ship.z, nearest.x, nearest.y, nearest.z, reserved
                )
                if step is not None:
                    tx, ty, tz = step
                    return Action(
                        ship.id, ActionType.MINE, tx, ty, tz
                    )

        # Прыгун: если видит врага в радиусе jump_range — прыгает и убивает
        # его тараном.
        if getattr(ship, 'jump_range', 0) > 0 and visible_ships:
            for enemy in visible_ships:
                d = max(
                    abs(enemy.x - ship.x), abs(enemy.y - ship.y), abs(enemy.z - ship.z)
                )
                if 1 <= d <= ship.jump_range and not getattr(enemy, 'is_phased', False):
                    # Союзник в целевой клетке блокирует; редкий случай, но
                    # проверяем.
                    if (enemy.x, enemy.y, enemy.z) not in reserved:
                        return Action(
                            ship.id, ActionType.MOVE, enemy.x, enemy.y, enemy.z
                        )

        # Бурав: если видит врага по одной оси в радиусе drill_range —
        # движется тараном.
        if getattr(ship, 'drill_range', 0) > 0 and visible_ships:
            for enemy in visible_ships:
                axes = (
                    (1 if enemy.x != ship.x else 0)
                    + (1 if enemy.y != ship.y else 0)
                    + (1 if enemy.z != ship.z else 0)
                )
                d = max(
                    abs(enemy.x - ship.x), abs(enemy.y - ship.y), abs(enemy.z - ship.z)
                )
                if axes == 1 and 1 <= d <= ship.drill_range \
                        and not getattr(enemy, 'is_phased', False):
                    if (enemy.x, enemy.y, enemy.z) not in reserved:
                        return Action(
                            ship.id, ActionType.MOVE, enemy.x, enemy.y, enemy.z
                        )

        # ---- Классическая стратегия ---------------------------------------
        # 1) Стрельба
        target = self._pick_shoot_target(ship, visible_ships)
        if target is not None:
            return Action(
                ship_id=ship.id,
                action_type=ActionType.SHOOT,
                target_x=target.x, target_y=target.y, target_z=target.z,
            )

        # 2) Движение (учтём расширенный радиус у Прыгуна/Бурава).
        effective_move = max(
            ship.move_range,
            getattr(ship, 'jump_range', 0),
            getattr(ship, 'drill_range', 0),
        )
        if effective_move > 0:
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
                return None
            nx, ny, nz = step
            return Action(
                ship_id=ship.id,
                action_type=ActionType.MOVE,
                target_x=nx, target_y=ny, target_z=nz,
            )

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
    base = f"[{ship.team.value}] {ship.name} ({ship.x},{ship.y},{ship.z})"
    at = action.action_type
    if at == ActionType.MOVE:
        return f"{base} → MOVE ({action.target_x},{action.target_y},{action.target_z})"
    if at == ActionType.SHOOT:
        return f"{base} → SHOOT at ({action.target_x},{action.target_y},{action.target_z})"
    if at == ActionType.HEAL:
        return f"{base} → HEAL (AoE)"
    if at == ActionType.PHASE:
        return f"{base} → PHASE toggle"
    if at == ActionType.HOLOGRAM:
        return f"{base} → HOLOGRAM ({action.target_x},{action.target_y},{action.target_z})"
    if at == ActionType.MINE:
        return f"{base} → MINE ({action.target_x},{action.target_y},{action.target_z})"
    return f"{base} → {at}"


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
def _team_stats_zero() -> dict:
    return {
        'shoot_hits': 0,
        'damage_dealt': 0,
        'kills': 0,
        'heals': 0,
        'phases': 0,
        'holograms': 0,
        'mines_placed': 0,
        'mines_triggered': 0,
        'rams': 0,
        'shoot_actions': 0,
        'move_actions': 0,
        'heal_actions': 0,
        'phase_actions': 0,
        'hologram_actions': 0,
        'mine_actions': 0,
        'kills_by_ship_type': {},
        'deaths_by_ship_type': {},
    }


def simulate(
    max_turns: int = 30,
    seed: int = 42,
    game_mode: str = 'advanced',
    write_log: bool = True,
) -> dict:
    """Проводит один матч и возвращает dict со статистикой (в т.ч. путь
    к лог-файлу под ключом ``log_path``).
    """
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

    # Статистика по командам (заполняется по ходу игры).
    stats: dict[str, dict] = {
        Team.TEAM_A.value: _team_stats_zero(),
        Team.TEAM_B.value: _team_stats_zero(),
        Team.TEAM_C.value: _team_stats_zero(),
    }

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

        # 3. Логируем принятые решения + считаем действия по типам.
        transcript.h("Решения ботов")
        ships = server.game_state['ships']
        for team in (Team.TEAM_A, Team.TEAM_B, Team.TEAM_C):
            tstats = stats[team.value]
            team_actions = actions_by_team[team]
            if not team_actions:
                transcript.p(f"  [{team.value}] все корабли пропускают ход")
                continue
            for action in team_actions:
                ship = ships.get(action.ship_id)
                if ship is None:
                    continue
                transcript.p(f"  {describe_action(ship, action)}")
                at = action.action_type
                if at == ActionType.SHOOT:
                    tstats['shoot_actions'] += 1
                elif at == ActionType.MOVE:
                    tstats['move_actions'] += 1
                elif at == ActionType.HEAL:
                    tstats['heal_actions'] += 1
                elif at == ActionType.PHASE:
                    tstats['phase_actions'] += 1
                elif at == ActionType.HOLOGRAM:
                    tstats['hologram_actions'] += 1
                elif at == ActionType.MINE:
                    tstats['mine_actions'] += 1
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
        # Запомним раненых до хода, чтобы посчитать heals.
        hits_before = {s.id: s.hits for s in ships.values() if s.alive}
        server.process_turn()
        # После хода: heals = раненые, у которых hits уменьшились.
        for sid, before in hits_before.items():
            s = ships.get(sid)
            if s is None or not s.alive:
                continue
            if s.hits < before:
                stats[s.team.value]['heals'] += (before - s.hits)

        # 6. Разбираем новые события hit_history и обновляем статы.
        new_events = server.game_state['hit_history'][turn_before_hits:]
        transcript.h("Результаты хода")
        if not new_events:
            transcript.p("  Попаданий нет")
        else:
            for h in new_events:
                marker = "УБИТ" if h.get('killed') else "ранен"
                transcript.p(
                    f"  {h.get('attacker','?')} / {h.get('attacker_name','?'):<18} → "
                    f"{h.get('target','?')} / {h.get('target_name','?'):<18} "
                    f"@ {h.get('position','?')}  ({marker})"
                )

        for h in new_events:
            attacker = h.get('attacker')
            target = h.get('target')
            damage = h.get('damage', 0) or 0
            is_ram = bool(h.get('ram'))
            is_mine = h.get('type') == 'mine_detonated'
            killed = bool(h.get('killed'))
            if is_mine:
                owner = h.get('owner')
                if owner and owner in stats:
                    stats[owner]['mines_triggered'] += 1
                    stats[owner]['damage_dealt'] += damage
                    if killed:
                        stats[owner]['kills'] += 1
                        tname = h.get('target_name', '').split()[0] if h.get('target_name') else '?'
                        stats[owner]['kills_by_ship_type'][tname] = \
                            stats[owner]['kills_by_ship_type'].get(tname, 0) + 1
                if target and target in stats:
                    tname = h.get('target_name', '').split()[0] if h.get('target_name') else '?'
                    if killed:
                        stats[target]['deaths_by_ship_type'][tname] = \
                            stats[target]['deaths_by_ship_type'].get(tname, 0) + 1
                continue
            if attacker and attacker in stats:
                if is_ram:
                    stats[attacker]['rams'] += 1
                else:
                    stats[attacker]['shoot_hits'] += 1
                stats[attacker]['damage_dealt'] += damage
                if killed:
                    stats[attacker]['kills'] += 1
                    tname = h.get('target_name', '').split()[0] if h.get('target_name') else '?'
                    stats[attacker]['kills_by_ship_type'][tname] = \
                        stats[attacker]['kills_by_ship_type'].get(tname, 0) + 1
            if target and target in stats and killed:
                tname = h.get('target_name', '').split()[0] if h.get('target_name') else '?'
                stats[target]['deaths_by_ship_type'][tname] = \
                    stats[target]['deaths_by_ship_type'].get(tname, 0) + 1

        # Голограммы/мины в state: посчитаем placements.
        for team_value in stats:
            stats[team_value]['phases'] = sum(
                1 for s in ships.values()
                if s.team.value == team_value and getattr(s, 'is_phased', False)
            ) + stats[team_value].get('phases_latched', 0)
        # Проще: количество «поставленных» мин/голограмм — это просто действия этого типа.
        stats[Team.TEAM_A.value]['mines_placed'] = stats[Team.TEAM_A.value]['mine_actions']
        stats[Team.TEAM_B.value]['mines_placed'] = stats[Team.TEAM_B.value]['mine_actions']
        stats[Team.TEAM_C.value]['mines_placed'] = stats[Team.TEAM_C.value]['mine_actions']
        stats[Team.TEAM_A.value]['holograms'] = stats[Team.TEAM_A.value]['hologram_actions']
        stats[Team.TEAM_B.value]['holograms'] = stats[Team.TEAM_B.value]['hologram_actions']
        stats[Team.TEAM_C.value]['holograms'] = stats[Team.TEAM_C.value]['hologram_actions']
        stats[Team.TEAM_A.value]['phases'] = stats[Team.TEAM_A.value]['phase_actions']
        stats[Team.TEAM_B.value]['phases'] = stats[Team.TEAM_B.value]['phase_actions']
        stats[Team.TEAM_C.value]['phases'] = stats[Team.TEAM_C.value]['phase_actions']

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
        winner = '—'
        transcript.p(f"Лимит ходов ({max_turns}) исчерпан, ничья/пат.")

    # Финальные выжившие и агрегаты.
    ships = server.game_state['ships']
    survivors = {t.value: 0 for t in (Team.TEAM_A, Team.TEAM_B, Team.TEAM_C)}
    totals = {t.value: 0 for t in (Team.TEAM_A, Team.TEAM_B, Team.TEAM_C)}
    remaining_hp = {t.value: 0 for t in (Team.TEAM_A, Team.TEAM_B, Team.TEAM_C)}
    for s in ships.values():
        totals[s.team.value] += 1
        if s.alive:
            survivors[s.team.value] += 1
            remaining_hp[s.team.value] += (s.max_hits - s.hits)

    transcript.h("Сводка по командам")
    for team in (Team.TEAM_A, Team.TEAM_B, Team.TEAM_C):
        transcript.p(
            f"  {team.value}: {survivors[team.value]}/{totals[team.value]} живых; "
            f"hp={remaining_hp[team.value]}"
        )

    transcript.h("Сводка по попаданиям")
    history = server.game_state['hit_history']
    kills = sum(1 for h in history if h.get('killed'))
    transcript.p(f"  Всего событий (шоты+тараны+мины): {len(history)}")
    transcript.p(f"  Уничтожено кораблей всего: {kills}")
    for team_name in (Team.TEAM_A.value, Team.TEAM_B.value, Team.TEAM_C.value):
        ts = stats[team_name]
        transcript.p(
            f"  {team_name}: урон={ts['damage_dealt']} хиты={ts['shoot_hits']} "
            f"тараны={ts['rams']} мины(сработало)={ts['mines_triggered']} "
            f"убийств={ts['kills']}"
        )

    # GM-бот завершает игру.
    gm.stop(server)

    # --- дамп ----------------------------------------------------------------
    out_path = None
    if write_log:
        ts_stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")
        out_path = os.path.join(
            ROOT, "game_logs", f"game_{ts_stamp}_{game_mode}_seed{seed}.log"
        )
        transcript.dump(out_path)

    # Закрыть сокет, чтобы не оставался открытый файловый дескриптор.
    try:
        server.server.close()
    except Exception:
        pass

    total_damage = sum(stats[t]['damage_dealt'] for t in stats)
    return {
        'seed': seed,
        'mode': game_mode,
        'turns': turn,
        'winner': winner,
        'survivors': survivors,
        'totals': totals,
        'remaining_hp': remaining_hp,
        'stats': stats,
        'total_damage': total_damage,
        'avg_damage_per_turn': round(total_damage / turn, 2) if turn else 0,
        'log_path': out_path,
    }


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
