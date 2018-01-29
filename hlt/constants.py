from enum import Enum

#: Max number of units of distance a ship can travel in a turn
MAX_SPEED = 7
#: Radius of a ship
SHIP_RADIUS = 0.5
#: Starting health of ship, also its max
MAX_SHIP_HEALTH = 255
#: Starting health of ship, also its max
BASE_SHIP_HEALTH = 255
#: Weapon cooldown period
WEAPON_COOLDOWN = 1
#: Weapon damage radius
WEAPON_RADIUS = 5.0
#: Weapon damage
WEAPON_DAMAGE = 64
#: Radius in which explosions affect other entities
EXPLOSION_RADIUS = 10.0
#: Distance from the edge of the planet at which ships can try to dock
DOCK_RADIUS = 4.0
#: Number of turns it takes to dock a ship
DOCK_TURNS = 5
#: Number of production units per turn contributed by each docked ship
BASE_PRODUCTIVITY = 6
#: Distance from the planets edge at which new ships are created
SPAWN_RADIUS = 2.0
#: Move and Fire radius - can engage this turn
MOVE_AND_FIRE_RADIUS = WEAPON_RADIUS + MAX_SPEED
#: Nearby radius - potential to clash next turn
NEARBY_RADIUS = WEAPON_RADIUS + 2 * MAX_SPEED
#: Docking check radius
DOCK_CHECK_RADIUS = 3 * MAX_SPEED

# Defines how we want to play this turn
class BotStrategy(Enum):
    NORMAL = 0
    FOUR_PLAYERS = 1
    RUSH = 2


# These are the parameters that drive the bot behavior
#: Max number of ships we send to an enemy ship
COMBAT_RATIO = [1, 1, 1]

#: discount on stuff far away from rest of us..
MASS_PROXIMITY_DISCOUNT = [0, .25, 0]

#: The factor we use to discount utility by travel time
#: This is percentage of the average of the 2 game dimensions
#: (1 - min(travel time,REVAL_TURN_HORIZON)/REVAL_TURN_HORIZON)
REVAL_TURN_HORIZON = [20, 15, 35]
MID_MAP_MULTIPLIER = [1.4, 0.5, 1.4]

#: Ship and planet utility based on game state
UTILITY_UNDOCKED_SHIP = [9, 11, 5]
UTILITY_ENEMY_DOCKED_SHIP = [6.5, 5, 15]
UTILITY_NOT_ENEMY_PLANET = [4.8, 5.7, 1]

MIN_UTILITY_EMPTY_PLANET = 0

# DESERTION
CORNER_UTILITY = 20

# RUSH STRATEGY settings/variables
RUSH_BREAK_DISTANCE = 35

