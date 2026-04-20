"""Быстрый демо-рендер UI-компонентов клиента без сервера.

Запуск:  ``python demo_ui.py map``
Пока умеет показывать MapWindow с реалистичным набором кораблей на поле.
Нужно для валидации визуала (скриншоты) без полной сетевой сессии.
"""
from __future__ import annotations

import sys
from tkinter import Tk

from client_player_fixed import MapWindow
from ui_theme import TEAM_COLORS, apply_theme


def _demo_ships():
    """Возвращает (ships_of_player, enemies_visible) с разнообразным составом."""
    # Свои — Team A (синий), разные типы, разный HP, фаза у Тишины.
    ships = {}
    for sid, (name, typ, x, y, z, hits, maxh, extra) in enumerate([
        ("Артиллерия A1", "Артиллерия", 2, 3, 4, 0, 1, {"can_shoot": True, "shoot_range": 10}),
        ("Прыгун A2", "Прыгун", 3, 3, 4, 0, 2, {"jump_range": 2, "move_range": 2}),
        ("Факел A3", "Факел", 4, 3, 4, 1, 6, {"heal_range": 2}),
        ("Тишина A4", "Тишина", 5, 3, 4, 0, 2, {"is_phased": True, "phase_cooldown": 3}),
        ("Бурав A5", "Бурав", 6, 3, 4, 0, 2, {"drill_range": 3, "move_range": 3}),
        ("Провокатор A6", "Провокатор", 7, 3, 4, 0, 2, {}),
        ("Паук A7", "Паук", 8, 3, 4, 2, 3, {}),
        ("Радиовышка A8", "Радиовышка", 3, 4, 4, 0, 2, {"scan_whole_z": True}),
    ]):
        ships[str(sid)] = {
            "id": str(sid), "name": name, "type": typ, "team": "Team A",
            "x": x, "y": y, "z": z, "alive": True,
            "hits": hits, "max_hits": maxh,
            **extra,
        }
    # Враги — по одному из Team B (красный) и Team C (мятный) в поле видимости.
    enemies = {}
    for sid, (name, typ, x, y, z, team, hits, maxh, extra) in enumerate([
        ("Прыгун B1", "Прыгун", 4, 6, 4, "Team B", 0, 2, {"jump_range": 2}),
        ("Артиллерия B2", "Артиллерия", 3, 7, 4, "Team B", 0, 1, {"can_shoot": True}),
        ("Тишина B3", "Тишина", 6, 6, 4, "Team B", 0, 2, {"is_phased": True}),
        ("Бурав C1", "Бурав", 7, 5, 4, "Team C", 1, 2, {"drill_range": 3}),
        ("Провокатор C2", "Провокатор", 8, 6, 4, "Team C", 0, 2, {}),
    ], start=100):
        enemies[str(sid)] = {
            "id": str(sid), "name": name, "type": typ, "team": team,
            "x": x, "y": y, "z": z, "alive": True,
            "hits": hits, "max_hits": maxh,
            **extra,
        }
    return ships, enemies


def run_map():
    root = Tk()
    apply_theme(root)
    # Корневое окно скрываем — визуализируем только MapWindow (Toplevel).
    root.withdraw()
    mw = MapWindow(root, "Team A", TEAM_COLORS["Team A"])
    # Когда пользователь закрывает карту — завершаем процесс целиком.
    mw.window.protocol("WM_DELETE_WINDOW", root.destroy)
    ships, enemies = _demo_ships()
    mw.update_data(ships, enemies)
    # Симулируем ситуацию: выбрали Прыгун A2, планируем таран — легальные клетки.
    legal = set()
    sx, sy, sz = 3, 3, 4
    # Примерная логика для Прыгуна jump_range=2: все клетки в кубе 2 вокруг.
    for dx in range(-2, 3):
        for dy in range(-2, 3):
            for dz in range(-2, 3):
                if dx == dy == dz == 0:
                    continue
                nx, ny, nz = sx + dx, sy + dy, sz + dz
                if 0 <= nx < 10 and 0 <= ny < 10 and 0 <= nz < 10:
                    legal.add((nx, ny, nz))
    mw.set_targeting(legal, selected=(4, 6, 4), mode="shoot")
    mw.current_layer.set(4)
    root.mainloop()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "map"
    if cmd == "map":
        run_map()
    else:
        print(f"unknown demo '{cmd}'", file=sys.stderr)
        sys.exit(2)
