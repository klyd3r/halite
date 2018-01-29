from . import collision, entity, constants, strategy
import logging


class Map:
    """
    Map which houses the current game information/metadata.
    
    :ivar my_id: Current player id associated with the map
    :ivar width: Map width
    :ivar height: Map height
    """

    def __init__(self, my_id, width, height):
        """
        :param my_id: User's id (tag)
        :param width: Map width
        :param height: Map height
        """
        self.my_id = my_id
        self.width = width
        self.height = height
        self._players = {}
        self._planets = {}
        # my parameters that I use to track the game
        # updated every turn..
        self.turn_num = 0
        self.corners_list = [entity.Position(0, 0),
                            entity.Position(self.width - 1, 0),
                            entity.Position(0, self.height - 1),
                            entity.Position(self.width - 1, self.height - 1)]
        self.my_ship_dict = {}
        self.my_clustered_ships_dict = {}
        self.MASTER_CLUSTER_ID = 0
        self.command_queue = []
        self.overall_top_target = None
        self.turn_timer = None


    def update_my_player_status(self, highest_ranked_enemy):
        self.corners_list = [entity.Position(0, 0),
                        entity.Position(self.width - 1, 0),
                        entity.Position(0, self.height - 1),
                        entity.Position(self.width - 1, self.height - 1)]
        self.turn_num += 1
        self.command_queue = []
        self.overall_top_target = None
        strategy.update_my_ship_status(self, highest_ranked_enemy, self.my_ship_dict, self.my_clustered_ships_dict)


    def get_me(self):
        """
        :return: The user's player
        :rtype: Player
        """
        return self._players.get(self.my_id)

    def get_player(self, player_id):
        """
        :param int player_id: The id of the desired player
        :return: The player associated with player_id
        :rtype: Player
        """
        return self._players.get(player_id)

    def all_players(self):
        """
        :return: List of all players
        :rtype: list[Player]
        """
        return list(self._players.values())

    def get_planet(self, planet_id):
        """
        :param int planet_id:
        :return: The planet associated with planet_id
        :rtype: entity.Planet
        """
        return self._planets.get(planet_id)

    def all_planets(self):
        """
        :return: List of all planets
        :rtype: list[entity.Planet]
        """
        return list(self._planets.values())

    def nearby_entities_by_distance(self, source_entity, exclude_ships=False, exclude_planets=False):
        """
        :param exclude_ships:
        :param exclude_planets:
        :return:
        :param source_entity: The source entity to find distances from
        :return: Dict containing all entities with their designated distances
        :rtype: dict
        """
        result = {}
        ships = self._all_ships() if not exclude_ships else []
        planets = self.all_planets() if not exclude_planets else []
        for foreign_entity in ships + planets:
            if source_entity == foreign_entity:
                continue
            result.setdefault(source_entity.calculate_min_distance2_between(foreign_entity), []).append(foreign_entity)
        return result

    def get_corners(self):
        return self.corners_list

    def get_mid_map(self):
        return entity.Position(self.width/2, self.height/2)

    def _link(self):
        """
        Updates all the entities with the correct ship and planet objects

        :return:
        """
        for celestial_object in self.all_planets() + self._all_ships():
            celestial_object._link(self._players, self._planets)

    def _parse(self, map_string):
        """
        Parse the map description from the game.

        :param map_string: The string which the Halite engine outputs
        :return: nothing
        """
        tokens = map_string.split()

        self._players, tokens = Player._parse(tokens)
        self._planets, tokens = entity.Planet._parse(tokens)

        assert(len(tokens) == 0)  # There should be no remaining tokens at this point
        self._link()

    def _all_ships(self):
        """
        Helper function to extract all ships from all players

        :return: List of ships
        :rtype: List[Ship]
        """
        all_ships = []
        for player in self.all_players():
            all_ships.extend(player.all_ships())
        return all_ships

    def _intersects_entity(self, target):
        """
        Check if the specified entity (x, y, r) intersects any planets. Entity is assumed to not be a planet.

        :param entity.Entity target: The entity to check intersections with.
        :return: The colliding entity if so, else None.
        :rtype: entity.Entity
        """
        for celestial_object in self._all_ships() + self.all_planets():
            if celestial_object is target:
                continue
            d = celestial_object.calculate_distance_between(target)
            if d <= celestial_object.radius + target.radius + 0.1:
                return celestial_object
        return None

    def obstacles_between(self, ship, target, position_to_move_to=None, ignore=(), additional_fudge=0.3):
        """
        Check whether there is a straight-line path to the given point, without planetary obstacles in between.

        :param entity.Ship ship: Source entity
        :param entity.Entity target: Target entity
        :param entity.Entity ignore: Which entity type to ignore
        :return: The list of obstacles between the ship and target
        :rtype: list[entity.Entity]
        """
        if not position_to_move_to:
            position_to_move_to = ship.closest_point_to(target)

        obstacles = {}
        entities = ([] if issubclass(entity.Planet, ignore) else self.all_planets()) \
            + ([] if issubclass(entity.Ship, ignore) else self._all_ships())
        for foreign_entity in entities:

            if foreign_entity == target:
                continue

            if isinstance(foreign_entity, entity.Ship):
                if (not isinstance(ship, entity.ShipCluster)) and (foreign_entity.id == ship.id):
                    continue
                if isinstance(target, entity.Ship) and foreign_entity.id == target.id:
                    continue
                if foreign_entity.owner != self.get_me():
                    if not foreign_entity.is_docked():
                        continue
                else:
                    #it's my ship
                    foreign_entity = self.my_ship_dict[foreign_entity.id]

            if isinstance(ship, entity.ShipCluster) and isinstance(foreign_entity, entity.Ship):
                if foreign_entity.id in [my_ship.id for my_ship in ship.ship_list]:
                    continue

            has_collided, collision_time = collision.does_moving_ship_intersect_obstacle(ship, position_to_move_to, foreign_entity, additional_fudge=additional_fudge)
            if ship.id == 15 and isinstance(foreign_entity, entity.Planet) and foreign_entity.id == 2:
                logging.debug('has_collided: {}, collision_time:{}'.format(has_collided, collision_time))

            #if collision.intersect_segment_circle(ship, position_to_move_to, foreign_entity, fudge=additional_fudge):
            if has_collided:
                obstacles.setdefault(collision_time, []).append(foreign_entity)
                continue

            if isinstance(foreign_entity, entity.Ship):

                if (foreign_entity.owner == self.get_me()) and foreign_entity.is_docked():
                    dist = foreign_entity.calculate_min_distance_between(foreign_entity.planet)
                    n_phony_entities = round(dist + 1)
                    for i in range(n_phony_entities):
                        position = foreign_entity.get_position(i, foreign_entity.calculate_angle_between(foreign_entity.planet))
                        phony_entity = entity.Entity(position.x, position.y, constants.SHIP_RADIUS, constants.BASE_SHIP_HEALTH, 0, -1)
                        has_collided, collision_time = collision.does_moving_ship_intersect_obstacle(ship, position_to_move_to, phony_entity, additional_fudge=additional_fudge)

                        if has_collided:
                            obstacles.setdefault(collision_time, []).append(foreign_entity)
                            break

        return obstacles

    def get_closest_obstacle(self, ship, target, position_to_move_to=None, ignore=(),
                             ignore_entities=[], additional_fudge=0.2):

        if not position_to_move_to:
            position_to_move_to = target

        obstacles_by_time = self.obstacles_between(ship, target, position_to_move_to, ignore, additional_fudge=additional_fudge)
        closest_obstacle = quickest_collision_time = None

        for collision_time in sorted(obstacles_by_time):
            for obstacle in obstacles_by_time[collision_time]:

                logging.debug('collision time:{}, quickest time:{}'.format(collision_time, quickest_collision_time))
                if obstacle in ignore_entities:
                    continue

                if not closest_obstacle:
                    quickest_collision_time = collision_time
                    closest_obstacle = obstacle

                elif quickest_collision_time > collision_time:
                    closest_obstacle = obstacle
                    quickest_collision_time = collision_time

        return closest_obstacle


class Player:
    """
    :ivar id: The player's unique id
    """
    def __init__(self, player_id, ships={}):
        """
        :param player_id: User's id
        :param ships: Ships user controls (optional)
        """
        self.id = player_id
        self._ships = ships
        self.score = 0
        self._planets = []
        self.rank = 0
        self.avg_x = 0
        self.avg_y = 0        
        self.num_undocked_ships = 0
        self.planet_avg_x = 0
        self.planet_avg_y = 0
        self.planet_docking_spots = 0
        self.planet_radius = 0
        self.centroid_ship = None
        self.centroid_planet = None

    def all_ships(self):
        """
        :return: A list of all ships which belong to the user
        :rtype: list[entity.Ship]
        """
        return list(self._ships.values())

    def get_ship(self, ship_id):
        """
        :param int ship_id: The ship id of the desired ship.
        :return: The ship designated by ship_id belonging to this user.
        :rtype: entity.Ship
        """
        return self._ships.get(ship_id)

    def get_id(self):
        return self.id

    def set_rank(self, rank):
        self.rank = rank

    def get_rank(self):
        return self.rank

    def ships_by_distance(self, entity):
        """
        :param entity: The source entity to find distances from
        :return: Dict containing all ships with their designated distances
        :rtype: dict
        """
        result = {}
        for foreign_entity in self.all_ships():
            if entity == foreign_entity:
                continue
            result.setdefault(entity.calculate_min_distance_between(foreign_entity), []).append(foreign_entity)
        return result

    @staticmethod
    def _parse_single(tokens):
        """
        Parse one user given an input string from the Halite engine.

        :param list[str] tokens: The input string as a list of str from the Halite engine.
        :return: The parsed player id, player object, and remaining tokens
        :rtype: (int, Player, list[str])
        """
        player_id, *remainder = tokens
        player_id = int(player_id)
        ships, remainder = entity.Ship._parse(player_id, remainder)
        player = Player(player_id, ships)
        return player_id, player, remainder

    @staticmethod
    def _parse(tokens):
        """
        Parse an entire user input string from the Halite engine for all users.

        :param list[str] tokens: The input string as a list of str from the Halite engine.
        :return: The parsed players in the form of player dict, and remaining tokens
        :rtype: (dict, list[str])
        """
        num_players, *remainder = tokens
        num_players = int(num_players)
        players = {}

        for _ in range(num_players):
            player, players[player], remainder = Player._parse_single(remainder)

        return players, remainder

    def __str__(self):
        return "Player {} with ships {}".format(self.id, self.score, self.all_ships())

    def __repr__(self):
        return self.__str__()
