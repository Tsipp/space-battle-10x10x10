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
        
        # Настройка характеристик на основе типа
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
            self.scan_whole_z = True  # Сканирует всю плоскость Z
            
        else:  # Базовый
            self.max_hits = 2
            self.move_range = 1
            self.can_shoot = True
            self.shoot_range = 5
            self.shoot_anywhere = False
            
        self.hits = 0

    def move(self, x, y, z):
        if self.move_range > 0:
            # Проверяем, что перемещение не больше разрешённого
            dx = abs(x - self.x)
            dy = abs(y - self.y)
            dz = abs(z - self.z)
            
            if max(dx, dy, dz) <= self.move_range:
                self.x = max(0, min(9, x))
                self.y = max(0, min(9, y))
                self.z = max(0, min(9, z))
                return True
        return False

    def can_shoot_at(self, target_x, target_y, target_z):
        """Проверяет, может ли корабль выстрелить в указанную точку"""
        if not self.can_shoot or not self.alive:
            return False
        
        # Для артиллерии - стрельба в любую точку
        if self.ship_type == ShipType.ARTILLERY:
            # Проверяем дальность (макс 10 клеток по каждой оси)
            dx = abs(target_x - self.x)
            dy = abs(target_y - self.y)
            dz = abs(target_z - self.z)
            
            # Артиллерия может стрелять в любую точку в пределах 10 клеток
            return dx <= 10 and dy <= 10 and dz <= 10
        
        # Для обычных кораблей - только по прямой
        changed_axes = 0
        if target_x != self.x: changed_axes += 1
        if target_y != self.y: changed_axes += 1
        if target_z != self.z: changed_axes += 1
        
        if changed_axes != 1:
            return False
        
        # Проверка дальности
        distance = max(
            abs(target_x - self.x),
            abs(target_y - self.y),
            abs(target_z - self.z)
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
            'can_shoot': self.can_shoot if hasattr(self, 'can_shoot') else True,
            'ship_type': self.ship_type.value
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
            'target_z': self.target_z
        }