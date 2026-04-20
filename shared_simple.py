# shared_simple.py
from enum import Enum


class Team(Enum):
    TEAM_A = "Team A"
    TEAM_B = "Team B"
    TEAM_C = "Team C"


class ActionType(Enum):
    MOVE = "move"
    SHOOT = "shoot"


class ShipType(Enum):
    CRUISER = "Крейсер"
    ARTILLERY = "Артиллерия"
    RADIO = "Радиовышка"
    BASE = "Базовый"


class Ship:
    def __init__(self, ship_id, name, team, x, y, z, ship_type=ShipType.BASE):
        self.id = ship_id
        self.name = name
        self.team = team
        self.x = x
        self.y = y
        self.z = z
        self.alive = True
        self.ship_type = ship_type

        # Безопасные значения по умолчанию — заданы для ВСЕХ типов,
        # чтобы не было AttributeError при обращении к атрибуту вне зависимости
        # от типа корабля.
        self.max_hits = 2
        self.move_range = 1
        self.can_shoot = True
        self.shoot_range = 5
        self.shoot_anywhere = False
        self.scan_whole_z = False

        if ship_type == ShipType.CRUISER:
            self.max_hits = 1
            self.move_range = 1
            self.can_shoot = True
            self.shoot_range = 5
            self.shoot_anywhere = False  # Только по прямой

        elif ship_type == ShipType.ARTILLERY:
            self.max_hits = 3
            self.move_range = 0  # Артиллерия не двигается
            self.can_shoot = True
            self.shoot_range = 10  # Вся карта (макс 10 клеток)
            self.shoot_anywhere = True  # Может стрелять в любую точку

        elif ship_type == ShipType.RADIO:
            self.max_hits = 2
            self.move_range = 1
            self.can_shoot = False  # Радиовышка не стреляет
            self.shoot_range = 0
            self.scan_whole_z = True  # Сканирует всю плоскость Z

        else:  # Базовый
            self.max_hits = 2
            self.move_range = 1
            self.can_shoot = True
            self.shoot_range = 5
            self.shoot_anywhere = False

        self.hits = 0

    def move(self, x, y, z):
        """Переместить корабль в (x, y, z). Не проверяет коллизии —
        этим занимается сервер (`GameServer.process_turn`). Проверяет
        только границы карты и дальность хода."""
        if self.move_range <= 0:
            return False

        dx = abs(x - self.x)
        dy = abs(y - self.y)
        dz = abs(z - self.z)

        if max(dx, dy, dz) > self.move_range:
            return False

        # Проверка границ карты
        if not (0 <= x <= 9 and 0 <= y <= 9 and 0 <= z <= 9):
            return False

        self.x = x
        self.y = y
        self.z = z
        return True

    def can_shoot_at(self, target_x, target_y, target_z):
        """Проверяет, может ли корабль выстрелить в указанную точку."""
        if not self.can_shoot or not self.alive:
            return False

        # Для артиллерии - стрельба в любую точку в пределах диапазона
        if self.ship_type == ShipType.ARTILLERY:
            dx = abs(target_x - self.x)
            dy = abs(target_y - self.y)
            dz = abs(target_z - self.z)
            return dx <= self.shoot_range and dy <= self.shoot_range and dz <= self.shoot_range

        # Для обычных кораблей - только по одной оси (прямая линия)
        changed_axes = 0
        if target_x != self.x:
            changed_axes += 1
        if target_y != self.y:
            changed_axes += 1
        if target_z != self.z:
            changed_axes += 1

        if changed_axes != 1:
            return False

        distance = max(
            abs(target_x - self.x),
            abs(target_y - self.y),
            abs(target_z - self.z),
        )

        return distance <= self.shoot_range

    def take_hit(self):
        self.hits += 1
        if self.hits >= self.max_hits:
            self.alive = False
        return self.alive

    def to_dict(self):
        return {
            'id': self.id,
            'name': f"{self.ship_type.value} {self.id}",
            'team': self.team.value,
            'type': self.ship_type.value,
            'x': self.x, 'y': self.y, 'z': self.z,
            'alive': self.alive,
            'hits': self.hits,
            'max_hits': self.max_hits,
            'can_shoot': self.can_shoot,
            'ship_type': self.ship_type.value,
        }


class Action:
    def __init__(self, ship_id, action_type, target_x=None, target_y=None, target_z=None):
        self.ship_id = ship_id
        self.action_type = action_type
        self.target_x = target_x
        self.target_y = target_y
        self.target_z = target_z

    def to_dict(self):
        return {
            'ship_id': self.ship_id,
            'action_type': self.action_type.value,
            'target_x': self.target_x,
            'target_y': self.target_y,
            'target_z': self.target_z,
        }

    @classmethod
    def from_dict(cls, data):
        """Десериализация из словаря (обратная операция к to_dict)."""
        return cls(
            ship_id=data['ship_id'],
            action_type=ActionType(data['action_type']),
            target_x=data.get('target_x'),
            target_y=data.get('target_y'),
            target_z=data.get('target_z'),
        )
