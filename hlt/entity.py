import logging
import abc
import math
from enum import Enum
from operator import attrgetter
from . import constants, collision


class Entity:
    """
    Then entity abstract base-class represents all game entities possible. As a base all entities possess
    a position, radius, health, an owner and an id. Note that ease of interoperability, Position inherits from
    Entity.

    :ivar id: The entity ID
    :ivar x: The entity x-coordinate.
    :ivar y: The entity y-coordinate.
    :ivar radius: The radius of the entity (may be 0)
    :ivar health: The entity's health.
    :ivar owner: The player ID of the owner, if any. If None, Entity is not owned.
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self, x, y, radius, health, player, entity_id):
        self.x = x
        self.y = y
        self.radius = radius
        self.health = health
        self.owner = player 
        self.id = entity_id
        self.num_approaching_friendlies = 0
        self.approaching_ship_health = 0

    def calculate_distance_between(self, target):
        """
        Calculates the distance between this object and the target.

        :param Entity target: The target to get distance to.
        :return: distance
        :rtype: float
        """
        return math.sqrt((target.x - self.x) ** 2 + (target.y - self.y) ** 2)

    def calculate_distance_sq_between(self,target):
        return (target.x - self.x) ** 2 + (target.y - self.y) ** 2

    def is_target1_nearer(self, target1, target2):
        dist_target1 = (target1.x - self.x) ** 2 + (target1.y - self.y) ** 2
        dist_target2 = (target2.x - self.x) ** 2 + (target2.y - self.y) ** 2
        return dist_target1 < dist_target2


    def is_target_nearer_than(self, target, distance):
        target_dist_square = (target.x - self.x) ** 2 + (target.y - self.y) ** 2
        distance_square = distance ** 2
        return target_dist_square <= distance_square


    def is_target_farther_than(self, target, distance):
        target_dist_square = (target.x - self.x) ** 2 + (target.y - self.y) ** 2
        distance_square = distance ** 2
        return target_dist_square >= distance_square


    def calculate_distance_from_coords(self, x, y):
        """
        Calculates the distance between this object and the target.

        :param float x: x coord of target
        :param float y: y coord of target
        :return: distance
        :rtype: float
        """
        return math.sqrt((x - self.x) ** 2 + (y - self.y) ** 2)

    def calculate_min_distance_between(self, target):
        """
        Calculates the distance between 2 objects excluding radiuses.
        """
        if isinstance(target, Ship):
            if target.pos_eot:
                if self.is_target1_nearer(target.pos_eot, target):
                    return self.calculate_distance_between(target.pos_eot) - self.radius - target.radius
        return self.calculate_distance_between(target) - self.radius - target.radius


    def calculate_min_distance2_between(self, target):
        """
        Calculates the distance between 2 objects excluding radiuses.
        """
        if isinstance(target, Ship):
            if target.pos_eot:
                if self.is_target1_nearer(target.pos_eot, target):
                    return self.calculate_distance_sq_between(self.closest_point_to(target.pos_eot, min_distance=1))
        return self.calculate_distance_sq_between(self.closest_point_to(target, min_distance=0.5, shortest_dist=True))


    def calculate_angle_between(self, target):
        """
        Calculates the angle between this object and the target in degrees.

        :param Entity target: The target to get the angle between.
        :return: Angle between entities in degrees
        :rtype: float
        """
        return math.degrees(math.atan2(target.y - self.y, target.x - self.x)) % 360

    def closest_point_to(self, target, min_distance=0.5, shortest_dist=False):
        """
        Find the closest point to the given ship near the given target, outside its given radius,
        with an added fudge of min_distance.

        :param Entity target: The target to compare against
        :param int min_distance: Minimum distance specified from the object's outer radius
        :return: The closest point's coordinates
        :rtype: Position
        """
        angle = target.calculate_angle_between(self)
        if not shortest_dist:
            if isinstance(target, Ship):
                if target.is_docked():
                    angle = (target.calculate_angle_between(target.planet) + 180) % 360
        radius = target.radius + min_distance
        x = target.x + radius * math.cos(math.radians(angle))
        y = target.y + radius * math.sin(math.radians(angle))

        return Position(x, y)

    def get_anticipated_position(self, ship, speed):
        """
        Shift the position of the target ship by it's velocity. If we can
        reach the ship in a turn we'll not adjust speed
        """
        distance = self.calculate_distance_between(ship)
        if distance <= speed:
            return Position(ship.x, ship.y)
        else:
            x = ship.x + ship.vel_x
            y = ship.y + ship.vel_y
            return Position(x, y)

    def get_position(self, speed, angle, rounded=False):
        """
        Get the final position of this ship moving at that speed and angle

        :rtype: Position
        """
        dx = math.cos(math.radians(angle)) * speed
        dy = math.sin(math.radians(angle)) * speed
        if rounded:
            return Position(round(self.x + dx), round(self.y + dy))
        return Position((self.x + dx), (self.y + dy))

    def add_approaching_friendly(self, ship, set_full=False):
        """
        Increment num_approaching_friendly
        """
        #if isinstance(self, Ship):
        #    if self.clumped_enemies:
        #        for e in self.clumped_enemies:
        #            e.num_approaching_friendlies = self.num_approaching_friendlies + 1

        self.num_approaching_friendlies += 1
        if not isinstance(self, Position):
            if set_full:
                self.approaching_ship_health += self.health
            else:
                self.approaching_ship_health += ship.health


    def is_fully_engaged(self, my_ship=None, game_map=None, combat_ratio=1):
        """
        if we have sent enough ships at this enemy
        """
        if game_map:
            if self.is_target_nearer_than(game_map.get_mid_map(), 3.5 * constants.MAX_SPEED):
                combat_ratio = combat_ratio * 1.5

        if type(self) == Ship:
            if self.highest_utility_target == self:
                combat_ratio = combat_ratio * 10
            elif self.is_docked():
                combat_ratio = combat_ratio * 3

        if isinstance(self, Planet):
            return self.is_full()

        if isinstance(self, Position):
            return 0 < self.num_approaching_friendlies

        #if my_ship:
        #    if self.is_target_nearer_than(my_ship, constants.MAX_SPEED + 2):
        #        return (combat_ratio * self.health) <= self.num_approaching_friendlies * constants.WEAPON_DAMAGE
        return (combat_ratio * self.health) <= self.approaching_ship_health

    @abc.abstractmethod
    def _link(self, players, planets):
        pass

    def __str__(self):
        return "Entity {} (id: {}) at position: (x = {}, y = {}), hp = {}, with radius = {}"\
            .format(self.__class__.__name__, self.id, self.x, self.y, self.health, self.radius)

    def __repr__(self):
        return self.__str__()


class Planet(Entity):
    """
    A planet on the game map.

    :ivar id: The planet ID.
    :ivar x: The planet x-coordinate.
    :ivar y: The planet y-coordinate.
    :ivar radius: The planet radius.
    :ivar num_docking_spots: The max number of ships that can be docked.
    :ivar current_production: How much production the planet has generated at the moment.
    Once it reaches the threshold, a ship will spawn and this will be reset.
    :ivar remaining_resources: The remaining production capacity of the planet.
    :ivar health: The planet's health.
    :ivar owner: The player ID of the owner, if any. If None, Entity is not owned.

    """

    def __init__(self, planet_id, x, y, hp, radius, docking_spots, current,
                 remaining, owned, owner, docked_ships):
        self.id = planet_id
        self.x = x
        self.y = y
        self.radius = radius
        self.num_docking_spots = docking_spots
        self.current_production = current
        self.remaining_resources = remaining
        self.health = hp
        self.owner = owner if bool(int(owned)) else None
        self._docked_ship_ids = docked_ships
        self._docked_ships = {}
        self.num_approaching_friendlies = 0
        self.approaching_ship_health = 0
        self.is_mine = False
        self.is_enemy = False
        self.distance_from_me = None
        self.distance_from_enemy = None

    def set_mine(self):
        self.is_mine = True

    def set_enemy(self):
        self.is_enemy = True

    def get_docked_ship(self, ship_id):
        """
        Return the docked ship designated by its id.

        :param int ship_id: The id of the ship to be returned.
        :return: The Ship object representing that id or None if not docked.
        :rtype: Ship
        """
        return self._docked_ships.get(ship_id)

    def all_docked_ships(self):
        """
        The list of all ships docked into the planet

        :return: The list of all ships docked
        :rtype: list[Ship]
        """
        return list(self._docked_ships.values())

    def is_owned(self):
        """
        Determines if the planet has an owner.
        :return: True if owned, False otherwise
        :rtype: bool
        """
        return self.owner is not None

    def is_owned_by(self, player_id):
        """
        Determines if the planet has an owner.
        :return: True if owned, False otherwise
        :rtype: bool
        """
        if not self.is_owned():
            return False
        else:
            return self.owner.get_id() == player_id

    def is_full(self):
        """
        Determines if the planet has been fully occupied (all possible ships are docked)

        :return: True if full, False otherwise.
        :rtype: bool
        """
        if self.is_owned():        
            if self.is_mine:
                return (self.num_approaching_friendlies + len(self._docked_ship_ids)) >= self.num_docking_spots
            return True
        return self.num_approaching_friendlies >= self.num_docking_spots

    def remove_docked_ship(self, ship):
        if ship.id in self._docked_ship_ids:
            self._docked_ship_ids.remove(ship.id)
            del self._docked_ships[ship.id]
        if len(self._docked_ship_ids) == 0:
            self.owner = None


    def _link(self, players, planets):
        """
        This function serves to take the id values set in the parse function and use it to populate the planet
        owner and docked_ships params with the actual objects representing each, rather than IDs

        :param dict[int, gane_map.Player] players: A dictionary of player objects keyed by id
        :return: nothing
        """
        if self.owner is not None:
            self.owner = players.get(self.owner)
            for ship in self._docked_ship_ids:
                self._docked_ships[ship] = self.owner.get_ship(ship)

    @staticmethod
    def _parse_single(tokens):
        """
        Parse a single planet given tokenized input from the game environment.

        :return: The planet ID, planet object, and unused tokens.
        :rtype: (int, Planet, list[str])
        """
        (plid, x, y, hp, r, docking, current, remaining,
         owned, owner, num_docked_ships, *remainder) = tokens

        plid = int(plid)
        docked_ships = []

        for _ in range(int(num_docked_ships)):
            ship_id, *remainder = remainder
            docked_ships.append(int(ship_id))

        planet = Planet(int(plid),
                        float(x), float(y),
                        int(hp), float(r), int(docking),
                        int(current), int(remaining),
                        bool(int(owned)), int(owner),
                        docked_ships)

        return plid, planet, remainder

    @staticmethod
    def _parse(tokens):
        """
        Parse planet data given a tokenized input.

        :param list[str] tokens: The tokenized input
        :return: the populated planet dict and the unused tokens.
        :rtype: (dict, list[str])
        """
        num_planets, *remainder = tokens
        num_planets = int(num_planets)
        planets = {}

        for _ in range(num_planets):
            plid, planet, remainder = Planet._parse_single(remainder)
            planets[plid] = planet

        return planets, remainder


class Ship(Entity):
    """
    A ship in the game.
    
    :ivar id: The ship ID.
    :ivar x: The ship x-coordinate.
    :ivar y: The ship y-coordinate.
    :ivar radius: The ship radius.
    :ivar health: The ship's remaining health.
    :ivar DockingStatus docking_status: The docking status (UNDOCKED, DOCKED, DOCKING, UNDOCKING)
    :ivar planet: The ID of the planet the ship is docked to, if applicable.
    :ivar owner: The player ID of the owner, if any. If None, Entity is not owned.
    """

    class DockingStatus(Enum):
        UNDOCKED = 0
        DOCKING = 1
        DOCKED = 2
        UNDOCKING = 3

    def __init__(self, player_id, ship_id, x, y, hp, vel_x, vel_y,
                 docking_status, planet, progress, cooldown):
        self.id = ship_id
        self.x = x
        self.y = y
        self.vel_x = vel_x
        self.vel_y = vel_y
        self.owner = player_id
        self.radius = constants.SHIP_RADIUS
        self.health = hp
        self.docking_status = docking_status
        self.planet = planet if (docking_status is not Ship.DockingStatus.UNDOCKED) else None
        self._docking_progress = progress
        self.weapon_cooldown = False
        # for BOTH
        self.ship_neighbors_flag = False
        # FOR ENEMIES
        self.is_enemy = False
        self.num_approaching_friendlies = 0
        self.approaching_ship_health = 0
        self.proximity_discount = 0
        self.my_docked_target = None
        self.attacking_my_docked_target = False
        self.docked_ship_multiplier = 1
        self.clumped_enemies = []
        self.friends_ready_to_attack = []
        self.friends_engaged_this_turn = []
        self.distance_to_my_centroid = 10000
        self.is_top_target = False
        # FOR FRIENDLIES
        self.updated_this_turn = True
        self.is_mine = False
        self.is_clumped = False
        self.clump_id = None
        self.mission_target = None
        self.distance_to_enemy = None
        self.aggress_flag = False
        self.turn_assigned_target = None
        self.speed = None
        self.angle = None
        self.last_engaged_target = None
        self.last_engaged_target_hp = None
        self.last_ship_target = None
        self.last_ship_target_sq_dist = None
        self.reset_turn_calculations()
        # PATHING CACHING
        self.obs_avoid_direction = None
        self.target = None

    def update_ship(self, ship):
        """
        Update our cached ship with new ship stuff from game_map
        :param ship: ship from game_map
        :return: nothing
        """
        self.reset_turn_calculations()
        self.id = ship.id
        self.x = ship.x
        self.y = ship.y
        self.vel_x = ship.vel_x
        self.vel_y = ship.vel_y
        self.owner = ship.owner
        self.health = ship.health
        self.docking_status = ship.docking_status
        self.planet = ship.planet if (ship.docking_status is not Ship.DockingStatus.UNDOCKED) else None
        self._docking_progress = ship._docking_progress
        self.weapon_cooldown = False
        self.updated_this_turn = True
        self.distance_to_enemy = ship.distance_to_enemy
        self.turn_assigned_target = None

    def reset_turn_calculations(self):
        # FOR FRIENDLIES
        self.distance_to_enemy = None
        self.has_target = False
        self.has_command = False
        self.nearest_enemy = None
        self.nearby_undocked_friends = []
        self.clumpable_friends = []
        self.nearby_docked_friends = []
        self.nearby_enemies = []
        self.nearby_enemies_to_fight = []
        self.dock_check_ships = []
        self.enemies_engaged = []
        self.pos_eot = None
        self.highest_utility_target = None
        self.highest_utility = 0
        self.targets_by_utility = {}
        self.ship_neighbors_flag = False
        self.aggress_flag = False
        self.speed = None
        self.angle = None

    def set_mine(self):
        self.is_mine = True

    def set_enemy(self):
        self.is_enemy = True

    def ready_to_attack(self):
        return (self.health > 0) and (not self.weapon_cooldown)

    def set_proximity_discount(self, distance, reval_horizon):
        """
        Determines how much we want to discount utility of this enemy ship
        by. Ships that are farther away from our docked ships aren't
        threats
        """
        num_turns_away = distance / constants.MAX_SPEED
        if num_turns_away <= 10:
            self.proximity_discount = max(0, 1 - min(num_turns_away, reval_horizon) / reval_horizon)

    def thrust(self, magnitude, angle, force_zero=False):
        """
        Generate a command to accelerate this ship.

        :param int magnitude: The speed through which to move the ship
        :param int angle: The angle to move the ship in
        :return: The command string to be passed to the Halite engine.
        :rtype: str
        """
        # we want to round angle to nearest integer, but we want to round
        # magnitude down to prevent overshooting and unintended collisions
        magnitude = max(0, magnitude)
        magnitude = int(min(constants.MAX_SPEED, magnitude))
        angle = round(angle)
        if magnitude > 0:
            self.pos_eot = self.get_position(magnitude, angle)
            self.speed = magnitude
            self.angle = angle
            return "t {} {} {}".format(self.id, magnitude, angle)
        elif force_zero:
            return "t {} {} {}".format(self.id, magnitude, angle)

    def dock(self, planet):
        """
        Generate a command to dock to a planet.

        :param Planet planet: The planet object to dock to
        :return: The command string to be passed to the Halite engine.
        :rtype: str
        """
        return "d {} {}".format(self.id, planet.id)

    def undock(self):
        """
        Generate a command to undock from the current planet.

        :return: The command trying to be passed to the Halite engine.
        :rtype: str
        """
        return "u {}".format(self.id)

    def navigate(self, target, speed):
        """
        Simple navigate function that doesn't care about obstacles and everything - assume
        that those are already accounted for..
        :param target: Entity to move to
        :param speed: Speed to move at
        :return:
        """
        distance_from_target = self.calculate_distance_between(target)
        speed = min(speed, distance_from_target)
        angle = self.calculate_angle_between(target)
        return self.thrust(speed, angle)


    def navigate_new(self, target, game_map, ignore_ships=False, ignore_planets=False, return_type='default',
                ignore_entities=[], additional_fudge=0.2, ignore_enemies=False, min_speed=None, force_zero=False, is_engage=False):
        """
        Navigate to a certain target (Entity). Decide what to do based on what entity it is.
        If we hit obstacles we navigate around on either tangents - if we still hit an obstacle
        after that we give up.
        """
        if isinstance(target, Planet):
            min_dist = 1 if not ignore_planets else 0
        elif isinstance(target, Position):
            min_dist = 0
        elif target.is_mine:
            min_dist = 1
        elif ignore_enemies:
            min_dist = 0
        else:
            if isinstance(self, ShipCluster):
                min_dist = 2.0 if target.is_docked() else 4.5
            else:
                if target.is_docked():
                    min_dist = 1.5
                elif is_engage:
                    min_dist = 4.5
                else:
                    min_dist = 2.0

        self.target = target
        if isinstance(target, Ship):
            if (not target.is_docked()) and target.my_docked_target:
                distance_from_my_docked = target.calculate_distance_sq_between(target.my_docked_target)
                if (distance_from_my_docked > constants.WEAPON_RADIUS ** 2) and (distance_from_my_docked <= 8 * constants.MAX_SPEED):
                    angle_from_my_docked = target.my_docked_target.calculate_angle_between(target)
                    if (len(game_map.get_me().all_ships()) <= 5):
                        logging.info('NAVIGATION: intercepting enemy ship {}, my docked {}'.format(target, target.my_docked_target))
                        target = target.my_docked_target.get_position(1.2, angle_from_my_docked)
                        #target = self.closest_point_to(target.my_docked_target)
                    else:
                        if not self.is_target_nearer_than(target, constants.MOVE_AND_FIRE_RADIUS):
                            target = target.my_docked_target.get_position(0.85 * math.sqrt(distance_from_my_docked), angle_from_my_docked)

        distance = self.calculate_distance_between(self.closest_point_to(target, min_dist))
        angle = self.calculate_angle_between(self.closest_point_to(target, min_dist))
        if distance <= 1.005:
            force_zero = True

        ignore = () if not (ignore_ships or ignore_planets) \
            else Ship if (ignore_ships and not ignore_planets) \
            else Planet if (ignore_planets and not ignore_ships) \
            else Entity

        logging.info('NAVIGATION: self: {}, target: {}, angle: {}, distance: {}'.format(self,target,angle,distance))

        speed = min(distance, constants.MAX_SPEED)
        look_ahead = min(distance, 2.5 * speed)

        position_to_move_to = self.get_position(look_ahead, angle)

        obstacle = game_map.get_closest_obstacle(self, target, position_to_move_to, ignore,
                                                 ignore_entities = ignore_entities, additional_fudge=additional_fudge)
        if obstacle:
            logging.info('NAVIGATION: obstacle: {}'.format(obstacle))
            speed, angle, force_zero = self.get_adjusted_angle_thrust(position_to_move_to, obstacle, game_map, initial_target=target, additional_fudge=additional_fudge)
            logging.info('NAVIGATION: got adjusted speed {} and angle {} around obstacle'.format(speed, angle))
            if angle == None:
                return None

        # corner correction
        final_target = self.get_position(speed, angle)
        radius = (0.5 + self.radius) if isinstance(self, ShipCluster) else 0
        if((final_target.x < radius) or (final_target.x > (game_map.width - radius)) or
                (final_target.y < radius) or (final_target.y > (game_map.height - radius))):
            #logging.debug('Going out of map.. {}'.format(final_target))
            corners_list = [Position(radius, radius),
                            Position(game_map.width - radius, radius),
                            Position(radius, game_map.height - radius),
                            Position(game_map.width - radius, game_map.height - radius)]
            corners_by_dist = {}
            for position in corners_list:
                if not position.is_target_nearer_than(target, 1.3 * constants.MAX_SPEED):
                    angle1 = (self.calculate_angle_between(final_target) - self.calculate_angle_between(position)) % 360
                    angle2 = (self.calculate_angle_between(position) - self.calculate_angle_between(final_target)) % 360
                    angular_diff = min(angle1, angle2)
                    corners_by_dist.setdefault(angular_diff, []).append(position)
            for angular_diff in sorted(corners_by_dist):
                final_target = corners_by_dist[angular_diff][0]
                #if self.is_target_nearer_than(final_target, constants.MAX_SPEED):
                #    continue
                angle = self.calculate_angle_between(final_target)
                logging.debug('adjusted_angle {}, corner: {}'.format(angle, final_target))
                break

        if min_speed:
            speed = max(min_speed, speed)
        logging.info('NAVIGATION END: ship_id:{}, x:{}, y:{}, speed:{}, angle:{}'.format(self.id, self.x, self.y, speed, angle))
        if (return_type == 'default'):
            if obstacle:
                return self.thrust(speed, angle, force_zero=force_zero)
            else:
                return self.thrust(speed, angle, force_zero=force_zero)
        else:
            return [speed, angle]


    def get_adjusted_angle_thrust(self, target, obstacle, game_map, initial_target=None,
                                  ignore_entities=[], recursive_call=False, additional_fudge=0.2):

        if not initial_target:
            initial_target = target
        #ignore_entities.append(initial_target)
        distance_to_obstacle = self.calculate_distance_between(obstacle)
        angle_to_obstacle = self.calculate_angle_between(obstacle)
        distance_to_target = self.calculate_min_distance_between(target)
        angle_to_target = self.calculate_angle_between(target)
        obs_radius = obstacle.radius + self.radius + additional_fudge
        #logging.info('dist_to_target: {}, angle_to_target: {}'.format(distance_to_target, angle_to_target))
        #logging.info('dist_to_obstacle: {}, angle_to_obstacle: {}, obs_radius: {}, adj_speed: {}'.format(distance_to_obstacle, angle_to_obstacle, obs_radius, adjusted_speed))

        # in this case just move away from obstacle
        if obs_radius >= distance_to_obstacle:
            #logging.info('ADJ_ANGLE: ship: {} distance < obs radius + fudges'.format(self.id, obstacle))
            obs_radius = distance_to_obstacle
            #return min(obs_radius, constants.MAX_SPEED), (180 + angle_to_obstacle) % 360

        # calculate all relevant angles..
        tangent_angle = 1 + math.degrees(math.asin(obs_radius / distance_to_obstacle))
        clockwise_angle = (round(angle_to_obstacle - tangent_angle + 0.5) % 360)
        anticlockwise_angle = (round(angle_to_obstacle + tangent_angle - 0.5)) % 360
        if ((angle_to_target - angle_to_obstacle) % 360) < 180: # force it to go one angle if it's tight
            close_angle = anticlockwise_angle
        else:
            close_angle = clockwise_angle
        #logging.info('tangent_angle: {}, clockwise_angle: {}, anticlockwise_angle: {}, close_angle: {}'.format(tangent_angle, clockwise_angle, anticlockwise_angle, close_angle))

        if isinstance(obstacle, Planet):
            logging.info('ADJ_ANGLE: ship: {} avoiding planet: {}'.format(self.id, obstacle.id))
            angle = close_angle
            angular_diff = abs(angle_to_target - angle)
            angular_diff = min(abs(angular_diff - 360), angular_diff)
            # increase speed more if angular correction is big
            adjusted_speed = max(1, min(distance_to_target / math.cos(math.radians(min(angular_diff, 90))),
                                        constants.MAX_SPEED))
            #logging.info('angle: {}, angle_to_target: {}, distance_to_target: {}, adjusted_speed: {}'.format(angle, angle_to_target, distance_to_target, adjusted_speed))

        else:
            if obstacle.is_docked() and \
                    not(obstacle.planet == initial_target):
                logging.info('ADJ_ANGLE: ship: {} avoiding docked ship: {} docked to :{}'.format(self.id, obstacle.id, obstacle.planet))
                obstacle_angle_to_planet = obstacle.calculate_angle_between(obstacle.planet)
                ship_angle_to_planet = self.calculate_angle_between(obstacle.planet)
                angle = anticlockwise_angle if ((ship_angle_to_planet - obstacle_angle_to_planet) % 360) <= 180 else clockwise_angle
                angular_diff = abs(angle - ship_angle_to_planet)
                angular_diff = min(abs(angular_diff - 360), angular_diff)
                adjusted_speed = max(1, min(distance_to_target / math.cos(math.radians(min(angular_diff, 90))),
                                            constants.MAX_SPEED))
                #logging.info('angular diff:{}, angle:{}, angle to planet:{}, adjusted speed:{}'.format(angular_diff, angle, ship_angle_to_planet, adjusted_speed))
            else:
                if obstacle.owner == game_map.get_me():
                    obstacle = game_map.my_ship_dict[obstacle.id]
                    if obstacle.pos_eot:
                        logging.info('ADJ_ANGLE: ship: {} avoiding moving friendly: {}'.format(self.id, obstacle.id))
                        adjusted_speed, angle = collision.get_speed_and_angle_around_moving_ship(self, target, obstacle)
                        if angle == None:
                            return 0,0,True

                    else:
                        logging.info('ADJ_ANGLE: ship: {} avoiding friendly'.format(self.id))
                        angle = close_angle
                        angular_diff = abs(angle_to_target - angle)
                        angular_diff = min(abs(angular_diff - 360), angular_diff)
                        # increase speed more if angular correction is big
                        adjusted_speed = max(1, min(distance_to_target / math.cos(math.radians(min(angular_diff, 90))),
                                                    constants.MAX_SPEED))

                else:
                    angle = angle_to_target
                    adjusted_speed = min(distance_to_target, constants.MAX_SPEED)

        adjusted_speed = int(adjusted_speed)
        new_target = self.get_position(adjusted_speed, angle)
        additional_obstacle = game_map.get_closest_obstacle(self, obstacle, new_target, ignore_entities=ignore_entities, additional_fudge=additional_fudge)
        if not additional_obstacle:
            return adjusted_speed, angle, False
        else:
            if not recursive_call:
                return self.get_adjusted_angle_thrust(new_target, additional_obstacle, game_map, initial_target=target, recursive_call=True, additional_fudge=additional_fudge)

            logging.info('ADJ_ANGLE: new obstacle: {}'.format(additional_obstacle))
            if isinstance(self, ShipCluster):
                has_collision, collision_time = collision.does_moving_ship_intersect_obstacle(self, new_target, additional_obstacle)
                if has_collision:
                    slower_speed = int(collision_time * adjusted_speed)
                    return slower_speed, angle, False
            else:
                if isinstance(additional_obstacle, Ship) and (additional_obstacle.owner == game_map.get_me()):
                    additional_obstacle = game_map.my_ship_dict[additional_obstacle.id]
                    #logging.debug(additional_obstacle.pos_eot)
                    if additional_obstacle.pos_eot: #if it's my moving ship let's not move at all
                        return 0,0,True
                angle_diff = abs(self.calculate_angle_between(additional_obstacle) - angle)
                return min(self.calculate_min_distance_between(additional_obstacle)/ math.cos(math.radians(angle_diff)), constants.MAX_SPEED), angle, False


    def can_dock(self, planet):
        """
        Determine whether a ship can dock to a planet

        :param Planet planet: The planet wherein you wish to dock
        :return: True if can dock, False otherwise
        :rtype: bool
        """
        return self.calculate_distance_between(planet) <= planet.radius + constants.DOCK_RADIUS

    def is_docked(self):
        """
        Determine whether a ship is docked or is docking

        :return: True if Docking or docked
        :rtype: bool
        """
        if self.docking_status != Ship.DockingStatus.UNDOCKED:
            return True
        else:
            return False

    def _link(self, players, planets):
        """
        This function serves to take the id values set in the parse function and use it to populate the ship
        owner and docked_ships params with the actual objects representing each, rather than IDs

        :param dict[int, game_map.Player] players: A dictionary of player objects keyed by id
        :param dict[int, Planet] players: A dictionary of planet objects keyed by id
        :return: nothing
        """
        self.owner = players.get(self.owner)  # All ships should have an owner. If not, this will just reset to None
        self.planet = planets.get(self.planet)  # If not will just reset to none

    @staticmethod
    def _parse_single(player_id, tokens):
        """
        Parse a single ship given tokenized input from the game environment.

        :param int player_id: The id of the player who controls the ships
        :param list[tokens]: The remaining tokens
        :return: The ship ID, ship object, and unused tokens.
        :rtype: int, Ship, list[str]
        """
        (sid, x, y, hp, vel_x, vel_y,
         docked, docked_planet, progress, cooldown, *remainder) = tokens

        sid = int(sid)
        docked = Ship.DockingStatus(int(docked))

        ship = Ship(player_id,
                    sid,
                    float(x), float(y),
                    int(hp),
                    float(vel_x), float(vel_y),
                    docked, int(docked_planet),
                    int(progress), int(cooldown))

        return sid, ship, remainder

    @staticmethod
    def _parse(player_id, tokens):
        """
        Parse ship data given a tokenized input.

        :param int player_id: The id of the player who owns the ships
        :param list[str] tokens: The tokenized input
        :return: The dict of Players and unused tokens.
        :rtype: (dict, list[str])
        """
        ships = {}
        num_ships, *remainder = tokens
        for _ in range(int(num_ships)):
            ship_id, ships[ship_id], remainder = Ship._parse_single(player_id, remainder)
        return ships, remainder

class ShipCluster(Ship):

    def __init__(self, ship_list, id, is_clumped=False):
        Ship.__init__(self,None,id,None,None,None,0,0,Ship.DockingStatus.UNDOCKED, None, None,None)
        self.owner = None
        self.id = id
        self.ship_list = ship_list
        for ship in self.ship_list:
            ship.is_clumped = True
            ship.clump_id = id
        self.is_clumped = is_clumped
        self.update_state()

    def clump(self, target):
        """
        Clumps in direction of a specific target
        :param target: target we're going to
        :return: list of commands for each ship in the cluster
        """
        spacing = constants.SHIP_RADIUS + .5
        position_list = [Position(self.x + spacing, self.y + spacing), Position(self.x + spacing, self.y - spacing),
                         Position(self.x - spacing, self.y + spacing), Position(self.x - spacing, self.y - spacing)]

        for position in position_list:
            position.dist_from_target = position.calculate_distance_between(target)

        position_list = sorted(position_list, key=attrgetter('dist_from_target'))
        logging.debug(position_list)
        for ship in self.ship_list:
            ship.distance_from_clump_positions = [ship.calculate_distance_between(position) for position in position_list]

        my_ship_list = list(self.ship_list)
        thrust_list = []
        for i in range(len(self.ship_list)):
            assigned_ship = min(my_ship_list, key=lambda a_obj: a_obj.distance_from_clump_positions[i])
            assigned_ship.is_clumped = True
            assigned_ship.clump_id = self.id
            thrust_list.append(assigned_ship.navigate(position_list[i], constants.MAX_SPEED))
            my_ship_list.remove(assigned_ship)

        self.is_clumped = True
        self.update_state()
        return thrust_list


    def clump_for_rush(self, target, game_map):
        if (abs(target.y - self.y)) <= 5:
            return self.clump_for_rush_horizontal_2(target, game_map)
        #elif len(game_map.all_players()) == 2:
        return self.clump_for_rush_vert_2(target, game_map)
        #else:
        #    return self.clump_for_rush_vertical(target)


    def clump_for_rush_horizontal_2(self, target, game_map):
        if game_map.turn_num == 1:
            x_move = 7
            spacing = 2
        else:
            x_move = 8
            spacing = 1.05

        if target.x > self.x:
            position_list = [Position(self.x + x_move, self.y),
                             Position(self.x + x_move, self.y + spacing),
                             Position(self.x + x_move, self.y - spacing)]
        else:
            position_list = [Position(self.x - x_move, self.y),
                             Position(self.x - x_move, self.y + spacing),
                             Position(self.x - x_move, self.y - spacing)]

        logging.info('RUSH: self:{}'.format(self))
        logging.info('RUSH: position_list:{}'.format(position_list))
        #assign by furthest ship..
        thrust_list = []
        for ship in self.ship_list:
            ship.distance_from_clump_positions = [ship.calculate_distance_between(position) for position in
                                                  position_list]
        my_ship_list = list(self.ship_list)
        for i in range(len(self.ship_list)):
            assigned_ship = min(my_ship_list, key=lambda a_obj: a_obj.distance_from_clump_positions[i])
            assigned_ship.is_clumped = True
            assigned_ship.clump_id = self.id
            thrust_list.append(assigned_ship.navigate(position_list[i], constants.MAX_SPEED))
            my_ship_list.remove(assigned_ship)

        if game_map.turn_num > 1:
            self.is_clumped = True

        return thrust_list


    def clump_for_rush_vert_2(self, target, game_map):
        if game_map.turn_num == 1:
            y_move = 4
            spacing = 1.7
        else:
            y_move = 7
            spacing = 1.05

        if target.y > self.y:
            position_list = [Position(self.x + 0.5, self.y + y_move),
                             Position(self.x + 0.5 + spacing, self.y + y_move),
                             Position(self.x + 0.5 - spacing, self.y + y_move)]
            self.ship_list = sorted(self.ship_list, key=attrgetter('y'))
        else:
            position_list = [Position(self.x + 0.5, self.y - y_move),
                             Position(self.x + 0.5 + spacing, self.y - y_move),
                             Position(self.x + 0.5 - spacing, self.y - y_move)]
            self.ship_list = sorted(self.ship_list, key=attrgetter('y'), reverse=True)

        logging.info('RUSH: self:{}'.format(self))
        logging.info('RUSH: position_list:{}'.format(position_list))
        #assign by furthest ship..
        thrust_list = []
        if game_map.turn_num == 1:
            for i in range(len(self.ship_list)):
                thrust_list.append(self.ship_list[i].navigate(position_list[i], constants.MAX_SPEED))
                self.ship_list[i].is_clumped = True
                self.ship_list[i].clump_id = self.id

        else:
            for ship in self.ship_list:
                ship.distance_from_clump_positions = [ship.calculate_distance_between(position) for position in
                                                      position_list]
            my_ship_list = list(self.ship_list)
            for i in range(len(self.ship_list)):
                assigned_ship = min(my_ship_list, key=lambda a_obj: a_obj.distance_from_clump_positions[i])
                assigned_ship.is_clumped = True
                assigned_ship.clump_id = self.id
                thrust_list.append(assigned_ship.navigate(position_list[i], constants.MAX_SPEED))
                my_ship_list.remove(assigned_ship)

            self.is_clumped = True

        return thrust_list

    def clump_for_rush_vertical(self, target):
        """
        Clumps for rush - try to make the front two ships on the same plane
        Assigns from top to bottom (sort by y)
        :param target: target we're going to
        :return: list of commands for each ship in the cluster
        """

        for ship in self.ship_list:
            ship.distance_to_rush_target = ship.calculate_distance_between(target)
        closest_ships = sorted(self.ship_list, key=attrgetter('distance_to_rush_target'))[0:2]
        closest_x = sum([ship.x for ship in closest_ships]) / 2
        closest_y = sum([ship.y for ship in closest_ships]) / 2

        point = Position(closest_x, closest_y)
        spacing = constants.SHIP_RADIUS + .1
        position_list = [Position(point.x + spacing, point.y + spacing), Position(point.x + spacing, point.y - spacing),
                         Position(point.x - spacing, point.y + spacing), Position(point.x - spacing, point.y - spacing)]

        for position in position_list:
            position.dist_from_target = position.calculate_distance_between(target)

        position_list = sorted(position_list, key=attrgetter('dist_from_target'))
        logging.debug(position_list)
        for ship in self.ship_list:
            ship.distance_from_clump_positions = [ship.calculate_distance_between(position) for position in position_list]

        my_ship_list = list(self.ship_list)
        thrust_list = []
        for i in range(len(self.ship_list)):
            assigned_ship = min(my_ship_list, key=lambda a_obj: a_obj.distance_from_clump_positions[i])
            assigned_ship.is_clumped = True
            assigned_ship.clump_id = self.id
            thrust_list.append(assigned_ship.navigate(position_list[i], constants.MAX_SPEED))
            my_ship_list.remove(assigned_ship)

        self.is_clumped = True
        self.update_state()
        logging.debug(
            'clumping for rush, ships {}'.format(self.ship_list))
        return thrust_list


    def clump_in_line(self):
        spacing = constants.SHIP_RADIUS + .5
        angle_between_ships = self.ship_list[0].calculate_angle_between(self.ship_list[1])
        position_list = [Position(self.x, self.y).get_position(spacing, angle_between_ships),
                         Position(self.x, self.y).get_position(spacing, (angle_between_ships + 180) % 360)]

        logging.debug(position_list)
        for ship in self.ship_list:
            ship.distance_from_clump_positions = [ship.calculate_distance_between(position) for position in position_list]

        my_ship_list = list(self.ship_list)
        thrust_list = []
        for i in range(len(self.ship_list)):
            assigned_ship = min(my_ship_list, key=lambda a_obj: a_obj.distance_from_clump_positions[i])
            assigned_ship.is_clumped = True
            assigned_ship.clump_id = self.id
            thrust_list.append(assigned_ship.navigate(position_list[i], constants.MAX_SPEED))
            my_ship_list.remove(assigned_ship)

        self.is_clumped = True
        self.update_state()
        return thrust_list

    def update_state(self):
        """
        Update internal params - update radius and location
        :return: nothing
        """
        if not len(self.ship_list):
            return False
        if len(self.ship_list) == 1:
            self.remove_ship_from_cluster(next(iter(self.ship_list)))
            return False
        avg_x = sum([ship.x for ship in self.ship_list]) / len(self.ship_list)
        avg_y = sum([ship.y for ship in self.ship_list]) / len(self.ship_list)
        self.x = avg_x
        self.y = avg_y
        self.radius = 1.2 + max([ship.calculate_distance_from_coords(avg_x,avg_y) for ship in self.ship_list])
        self.health = sum([ship.health for ship in self.ship_list])
        return True

    def remove_ship_from_cluster(self, ship):
        ship.is_clumped = False
        ship.clump_id = None
        if ship in self.ship_list:
            self.ship_list.remove(ship)
            logging.debug('Ship id: {} removed from clump {}'.format(ship.id, self.id))
            self.update_state()

class Position(Entity):
    """
    A simple wrapper for a coordinate. Intended to be passed to some functions in place of a ship or planet.

    :ivar id: Unused
    :ivar x: The x-coordinate.
    :ivar y: The y-coordinate.
    :ivar radius: The position's radius (should be 0).
    :ivar health: Unused.
    :ivar owner: Unused.
    """

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = 0
        self.health = None
        self.owner = None
        self.id = None
        self.num_approaching_friendlies = 0

    def _link(self, players, planets):
        raise NotImplementedError("Position should not have link attributes.")
