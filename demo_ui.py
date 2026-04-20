"""Быстрый демо-рендер UI-компонентов клиента без сервера.

Запуск:  ``python demo_ui.py map``
Пока умеет показывать MapWindow с реалистичным набором кораблей на поле.
Нужно для валидации визуала (скриншоты) без полной сетевой сессии.
"""
from __future__ import annotations

import sys
from tkinter import Tk, Toplevel, LabelFrame, BOTH, X

from client_player_fixed import MapWindow, GameClientGUI
from ui_theme import TEAM_COLORS, apply_theme, Palette


def _demo_ships():
    """Возвращает (ships_of_player, enemies_visible) с разнообразным составом."""
    # Свои — Team A (синий), разные типы, разный HP, фаза у Тишины.
    ships = {}
    for sid, (name, typ, x, y, z, hits, maxh, extra) in enumerate([
        ("Артиллерия A1", "Артиллерия", 2, 3, 4, 0, 1, {"can_shoot": True, "shoot_range": 10, "damage": 1, "shoot_anywhere": True, "move_range": 0}),
        ("Прыгун A2", "Прыгун", 3, 3, 4, 0, 2, {"jump_range": 2, "move_range": 2, "can_shoot": True, "shoot_range": 1, "damage": 1}),
        ("Факел A3", "Факел", 4, 3, 4, 1, 6, {"heal_range": 2, "move_range": 2, "can_shoot": True, "shoot_range": 1, "damage": 1}),
        ("Тишина A4", "Тишина", 5, 3, 4, 0, 2, {"is_phased": True, "phase_cooldown": 3, "can_phase": True, "move_range": 2}),
        ("Бурав A5", "Бурав", 6, 3, 4, 0, 2, {"drill_range": 3, "move_range": 3}),
        ("Провокатор A6", "Провокатор", 7, 3, 4, 0, 2, {"can_create_hologram": True, "can_shoot": True, "shoot_range": 1, "damage": 1, "move_range": 2}),
        ("Паук A7", "Паук", 8, 3, 4, 2, 3, {"can_place_mine": True, "mine_damage": 2, "move_range": 2}),
        ("Радиовышка A8", "Радиовышка", 3, 4, 4, 0, 2, {"scan_whole_z": True, "move_range": 2}),
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


def run_cards():
    """Демо: рендер панелей карточек кораблей (свои + враги) без сервера."""
    root = Tk()
    apply_theme(root)
    root.title("demo: карточки кораблей")
    root.configure(bg=Palette().bg_root)
    root.geometry("720x1400")

    # Привязываем render-методы к простому mock-объекту вместо полного
    # GameClientGUI (без сетевой логики).  Мы используем сам GameClientGUI
    # ровно настолько, насколько нужны его _render_* методы — передаём
    # его же на created panel'ы.
    ships, enemies = _demo_ships()
    # Добавляем один «мёртвый» корабль, чтобы было видно, как он рендерится.
    ships["dead"] = {
        "id": "dead", "name": "Бурав A9", "type": "Бурав", "team": "Team A",
        "x": 5, "y": 5, "z": 4, "alive": False, "hits": 2, "max_hits": 2,
        "drill_range": 3, "move_range": 3,
    }

    class _MockGui:
        colors = {
            'panel': Palette().bg_panel,
            'accent1': Palette().accent_info,
            'accent2': Palette().accent_danger,
            'accent3': Palette().accent_success,
        }
        root = None  # set below
        _make_scrollable_cards = GameClientGUI._make_scrollable_cards
        _render_hp_bar = GameClientGUI._render_hp_bar
        _render_ship_card = GameClientGUI._render_ship_card
        create_ships_panel = GameClientGUI.create_ships_panel
        create_enemies_panel = GameClientGUI.create_enemies_panel
        update_ships_list = GameClientGUI.update_ships_list
        update_enemies_list = GameClientGUI.update_enemies_list

    gui = _MockGui()
    gui.root = root
    gui.create_ships_panel()
    gui.create_enemies_panel()
    gui.update_ships_list({"my_ships": ships})
    gui.update_enemies_list({"visible_enemies": enemies})
    root.mainloop()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "map"
    if cmd == "map":
        run_map()
    elif cmd == "cards":
        run_cards()
    else:
        print(f"unknown demo '{cmd}'", file=sys.stderr)
        sys.exit(2)
