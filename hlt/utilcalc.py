from . import constants, entity, strategy
import logging, time, math
from operator import attrgetter

def set_ship_neighbours(game_map, current_strategy, dock_check_distance):

    for player in game_map.all_players():
        for ship in player.all_ships():
            if (time.time() - game_map.turn_timer) >= 1.40:
                logging.warning('UTILITY: Turn time now: {}, breaking..'.format((time.time() - game_map.turn_timer)))
                break
            set_ship_neighbor_single(ship, game_map, current_strategy, dock_check_radius=dock_check_distance)


def set_ship_neighbor_single(ship, game_map, current_strategy, dock_check_radius=constants.DOCK_CHECK_RADIUS):

    my_ship_dict = game_map.my_ship_dict
    nearby_ships_by_distance = game_map.nearby_entities_by_distance(ship, exclude_planets=True)
    if ship.owner != game_map.get_me():
        ship.distance_to_my_centroid = game_map.get_me().centroid_ship.calculate_distance_between(ship)
        for distance2 in sorted(nearby_ships_by_distance):
            if (time.time() - game_map.turn_timer) >= 1.40:
                logging.warning('SHIP NEIGHBORS: Turn time now: {}, breaking..'.format((time.time() - game_map.turn_timer)))
                break
            if (distance2 / (constants.MAX_SPEED**2)) >= (constants.REVAL_TURN_HORIZON[current_strategy.value] ** 2):
                break
            for nearby_ship in nearby_ships_by_distance[distance2]:
                if nearby_ship.owner != game_map.get_me():
                    if distance2 <= (2**2) and not nearby_ship.is_docked():
                        ship.clumped_enemies.append(nearby_ship)
                else:
                    nearby_ship = my_ship_dict[nearby_ship.id]
                    if distance2 <= (constants.WEAPON_RADIUS ** 2):
                        if not ship.is_docked():
                            ship.friends_engaged_this_turn.append(nearby_ship)
                            logging.debug('UTILITY: enemy ship:{}, attacking my ship :{}'.format(ship.id, nearby_ship.id))

                    if nearby_ship.is_docked():
                        set_proximity_discount(ship, nearby_ship, current_strategy)

                    elif distance2 <= (constants.MOVE_AND_FIRE_RADIUS ** 2):
                        #if game_map.obstacles_between(ship, nearby_ship, ignore=entity.Ship):
                        #    continue
                        ship.friends_ready_to_attack.append(nearby_ship)
                        logging.debug('UTILITY: enemy ship:{}, friendly ready to attack:{}'.format(ship.id, nearby_ship.id))

        if ship.friends_engaged_this_turn:
            ship.weapon_cooldown = True
            for friendly in ship.friends_engaged_this_turn:
                friendly.health -= constants.WEAPON_DAMAGE / len(ship.friends_engaged_this_turn)
                if friendly.health <= 0:
                    friendly.has_command = True
                    logging.debug('UTILITY: friendly died this turn: {}'.format(friendly))
                    if friendly.is_docked():
                        friendly.planet.remove_docked_ship(friendly)

        ship.ship_neighbors_flag = True

    else:
        my_ship = my_ship_dict[ship.id]
        if my_ship.is_docked():
            return None
        for distance2 in sorted(nearby_ships_by_distance):
            if (distance2 / (constants.MAX_SPEED ** 2)) >= (constants.REVAL_TURN_HORIZON[current_strategy.value] ** 2):
                break
            if (time.time() - game_map.turn_timer) >= 1.40:
                logging.warning('SHIP NEIGHBORS: Turn time now: {}, breaking..'.format((time.time() - game_map.turn_timer)))
                break
            for nearby_ship in nearby_ships_by_distance[distance2]:
                if nearby_ship.owner == game_map.get_me():
                    # 2* MAX_SPEED because then our ships can move to each other
                    if distance2 <= (constants.MOVE_AND_FIRE_RADIUS ** 2) and not nearby_ship.is_docked():
                        my_ship.nearby_undocked_friends.append(my_ship_dict[nearby_ship.id])
                    # 1.5 distance away means is clumped
                    if distance2 <= (1.3 ** 2) and not nearby_ship.is_docked():
                        my_ship.clumpable_friends.append(my_ship_dict[nearby_ship.id])
                    # NEARBY docked ships that we can defend..
                    if distance2 <= (constants.NEARBY_RADIUS ** 2) and nearby_ship.is_docked():
                        my_ship.nearby_docked_friends.append(my_ship_dict[nearby_ship.id])
                elif nearby_ship.owner != game_map.get_me():
                    # nearby radius away..
                    if distance2 <= (constants.NEARBY_RADIUS ** 2):
                        my_ship.nearby_enemies.append(nearby_ship)
                    # nearby radius away..
                    if distance2 <= (constants.MOVE_AND_FIRE_RADIUS ** 2):
                        my_ship.nearby_enemies_to_fight.append(nearby_ship)
                    # Engaged are those we are already fighting
                    if distance2 <= (constants.WEAPON_RADIUS ** 2) and not nearby_ship.is_docked():
                        my_ship.enemies_engaged.append(nearby_ship)
                    # DOCK_CHECK_RADIUS is 3 * MAX_SPEED
                    if (not nearby_ship.is_docked()) and (distance2 <= (dock_check_radius ** 2)):
                        my_ship.dock_check_ships.append(nearby_ship)
                    # Fill this up with first ship
                    if (not nearby_ship.is_docked()) and not my_ship.nearest_enemy:
                        if distance2 <= (11 * constants.MAX_SPEED) ** 2:
                            my_ship.nearest_enemy = nearby_ship

        if my_ship.enemies_engaged:
            my_ship.weapon_cooldown = True
            for enemy in my_ship.enemies_engaged:
                enemy.health -= constants.WEAPON_DAMAGE / len(my_ship.enemies_engaged)
                if enemy.health <= 0:
                    logging.debug('enemy died this turn: {}'.format(enemy))
                    if enemy.is_docked():
                        enemy.planet.remove_docked_ship(enemy)

        my_ship.ship_neighbors_flag = True


def assign_ships_to_clusters(game_map):
    for ship in game_map.my_ship_dict.values():
        ship.num_ships_to_cluster = len(ship.clumpable_friends)

    my_ship_list = sorted([ship for ship in game_map.my_ship_dict.values() if ship.clumpable_friends], key=attrgetter('num_ships_to_cluster'))
    for ship in my_ship_list:
        if ship.is_clumped:
            continue
        if ship.is_target_nearer_than(game_map.get_mid_map(), 3.5 * constants.MAX_SPEED):
            continue
        list_clumpable_friends = []
        for friendly in ship.clumpable_friends:
            if not friendly.is_clumped:
                list_clumpable_friends.append(friendly)
        if list_clumpable_friends:
            list_clumpable_friends.append(ship)
            game_map.MASTER_CLUSTER_ID += 1
            ship_cluster = entity.ShipCluster(list_clumpable_friends, game_map.MASTER_CLUSTER_ID, is_clumped=True)
            game_map.my_clustered_ships_dict[game_map.MASTER_CLUSTER_ID] = ship_cluster
            logging.info('CLUSTERING: new cluster: {}, ships: {}'.format(game_map.MASTER_CLUSTER_ID, list_clumpable_friends))


def set_proximity_discount(enemy_ship, my_docked_target, current_strategy):

    distance = enemy_ship.calculate_distance_between(my_docked_target)
    reval_horizon = constants.REVAL_TURN_HORIZON[current_strategy.value]
    if not enemy_ship.my_docked_target:
        enemy_ship.my_docked_target = my_docked_target
        enemy_ship.set_proximity_discount(distance, reval_horizon)
        #logging.debug('SET_PROX_DISC: ship:{}, my docked target:{}'.format(enemy_ship.id, enemy_ship.my_docked_target.id))
        if distance <= constants.WEAPON_RADIUS:
            enemy_ship.attacking_my_docked_target = True
            #logging.debug('SET_PROX_DISC: ship:{}, attacking my docked:{}'.format(enemy_ship.id, my_docked_target.id))
    elif enemy_ship.is_target_farther_than(enemy_ship.my_docked_target, distance):
        enemy_ship.my_docked_target = my_docked_target
        enemy_ship.set_proximity_discount(distance, reval_horizon)
        #logging.debug('SET_PROX_DISC: Closer docked target found: ship: {}, my docked: {}'.format(enemy_ship.id, my_docked_target.id))
        if distance <= constants.WEAPON_RADIUS:
            enemy_ship.attacking_my_docked_target = True
            #logging.debug('SET_PROX_DISC: ship:{}, attacking my docked:{}'.format(enemy_ship.id, my_docked_target.id))


def calculate_turn_utilities(game_map, current_strategy, my_ship_dict, list_enemies, turn_timer, micro_flag, combat_ratio=1,
                             desertion_flag=False, planet_multiplier=1, docked_ship_aggression_multiplier=1, mid_map_multiplier=1.3):

    # Return a dictionary with key utilities and target/ship pair dictionary value..
    targets_by_utility = {}

    max_iterations, docking_discount, overall_top_target, dock_check_distance = get_utility_parameters(game_map, list_enemies, micro_flag, desertion_flag)

    for ship_id, ship in my_ship_dict.items():

        if (time.time() - turn_timer) >= 1.50:
            logging.warning('UTILITY: Turn time now: {}, breaking..'.format((time.time() - turn_timer)))
            break

        set_utilities_for_ship(ship, game_map, current_strategy, docking_discount, max_iterations, desertion_flag,
                               combat_ratio=combat_ratio, planet_multiplier=planet_multiplier,
                               docked_ship_aggression_multiplier=docked_ship_aggression_multiplier,
                               mid_map_multiplier=mid_map_multiplier)

    return targets_by_utility


def get_utility_parameters(game_map, list_enemies, micro_flag, desertion_flag):
    """
    Utility parameters for individual ship utilities
    Calculations I only want to do once per turn
    :param game_map:
    :param list_enemies:
    :return:
    """
    enemy_num_docked_ships = enemy_num_undocked_ships = 0
    for enemy_player in list_enemies:
        enemy_num_docked_ships += len([ship for ship in enemy_player.all_ships() if ship.is_docked()])
        enemy_num_undocked_ships += len([ship for ship in enemy_player.all_ships() if not ship.is_docked()])
    my_num_docked_ships = len([ship for ship_id, ship in game_map.my_ship_dict.items() if ship.is_docked()])
    my_num_undocked_ships = len([ship for ship_id, ship in game_map.my_ship_dict.items() if not ship.is_docked()])

    max_iterations = 3 if my_num_undocked_ships >= 100 else 15

    docking_discount = .5 if (my_num_docked_ships > max(2,enemy_num_docked_ships) * 1.05) and (
            my_num_undocked_ships <= enemy_num_undocked_ships + 3) else 1
    if (not micro_flag) and (not desertion_flag):
        docking_discount = .5
    if (game_map.turn_num >= 5) and len([enemy_ship for enemy_ship in list_enemies[0].all_ships() if enemy_ship.is_docked()]) == 0:
        logging.debug('DOCKING DISCOUNT: EARLY GAME OPPONENT RUSH PENALTY')
        docking_discount = .5

    dock_check_distance = constants.MAX_SPEED * (3 if len(game_map.get_me().all_ships()) > 5 else 8)

    docked_enemies = []
    undocked_enemies = []
    for player in game_map.all_players():
        if player != game_map.get_me():
            docked_enemies += [ship for ship in player.all_ships() if ship.is_docked()]
            undocked_enemies += [ship for ship in player.all_ships() if not ship.is_docked()]

    if docked_enemies:
        overall_top_target = min(docked_enemies, key=attrgetter('distance_to_my_centroid'))
    else:
        overall_top_target = min(undocked_enemies, key=attrgetter('distance_to_my_centroid'))

    if isinstance(overall_top_target, entity.Ship):
        overall_top_target.is_top_target = True
        game_map.overall_top_target = overall_top_target
        logging.info('UTILITY: highest util target: {}, distance from centroid: {}'.format(overall_top_target, overall_top_target.distance_to_my_centroid))

    return max_iterations, docking_discount, overall_top_target, dock_check_distance

def set_utilities_for_ship(ship, game_map, current_strategy, docking_discount, max_iterations, desertion_flag, combat_ratio=1,
                           planet_multiplier=1, docked_ship_aggression_multiplier=1, mid_map_multiplier=1.4):

    # If the ship is docked
    if ship.docking_status != ship.DockingStatus.UNDOCKED:
        return None

    entities_by_distance = game_map.nearby_entities_by_distance(ship)
    if desertion_flag:
        logging.debug('UTILITY: deserting! adding corners to targets')
        for corner in game_map.get_corners():
            logging.debug('corner: {}'.format(corner))
            entities_by_distance.setdefault(ship.calculate_min_distance2_between(corner) / 100, []).append(corner)

    counter = 0
    highest_utility = 0

    for distance2 in sorted(entities_by_distance):

        if (distance2 / (constants.MAX_SPEED ** 2)) >= (constants.REVAL_TURN_HORIZON[current_strategy.value] ** 2):
            continue

        for current_entity in entities_by_distance[distance2]:

            distance = math.sqrt(distance2)

            utility = get_utility(ship, current_entity, game_map, current_strategy, distance=distance,
                                  docking_discount=docking_discount, planet_multiplier=planet_multiplier,
                                  docked_ship_aggression_multiplier=docked_ship_aggression_multiplier,
                                  mid_map_multiplier=mid_map_multiplier, combat_ratio=combat_ratio)

            if utility > 0:
                ship.targets_by_utility.setdefault(utility, []).append(current_entity)
                counter += 1
                if ship.id == 14:
                    logging.debug('ship: {}, utility: {}, counter: {}, target:{}'.format(ship.id, utility, counter,
                                                                                         current_entity))
                if utility >= highest_utility:
                    highest_utility = utility
                    ship.highest_utility_target = current_entity
                    ship.highest_utility = highest_utility

        if counter >= max_iterations:
            #logging.info('UTILITY: Too many targets')
            break


def get_utility(ship, current_entity, game_map, current_strategy, distance, combat_ratio=1,
                docking_discount=1, planet_multiplier=1, docked_ship_aggression_multiplier=1,
                exclude_mid_multiplier=False, mid_map_multiplier=1.4):
    reval_horizon = constants.REVAL_TURN_HORIZON[current_strategy.value]
    ship_distance_discount = 1 - min(distance / constants.MAX_SPEED, reval_horizon) / reval_horizon
    distance_from_me_overall = current_entity.calculate_distance_between(game_map.get_me().centroid_ship)
    mass_proximity_discount = 1 - constants.MASS_PROXIMITY_DISCOUNT[current_strategy.value] * min(
        distance_from_me_overall / constants.MAX_SPEED, reval_horizon) / reval_horizon
    mid_multiplier = mid_map_multiplier
    distance_from_mid = current_entity.calculate_distance_between(game_map.get_mid_map())
    if current_strategy == constants.BotStrategy.FOUR_PLAYERS:
        planet_multiplier = 1
        #distance_from_mid = current_entity.calculate_distance_between(entity.Position(game_map.get_mid_map().x, current_entity.y))
    mid_multiplier = mid_multiplier + (1 - mid_multiplier) * (distance_from_mid / (0.5 * game_map.width))
    if exclude_mid_multiplier:
        mid_multiplier = 1
    overall_discount = mass_proximity_discount * ship_distance_discount * mid_multiplier

    if current_entity.is_fully_engaged(game_map, combat_ratio=combat_ratio):
        utility = 0

    elif isinstance(current_entity, entity.Planet):
        utility = overall_discount * docking_discount * constants.UTILITY_NOT_ENEMY_PLANET[
            current_strategy.value]
        utility = utility * planet_multiplier
        if (current_entity.num_approaching_friendlies > 1) or len(current_entity.all_docked_ships()) >= 1:
            utility = utility * 1.1
        utility = max(utility, constants.MIN_UTILITY_EMPTY_PLANET)
        utility = utility if not current_entity.is_full() else 0

    elif isinstance(current_entity, entity.Ship):
        if current_entity.is_enemy and not current_entity.health <= 0:
            if not current_entity.ship_neighbors_flag:
                    set_ship_neighbor_single(current_entity, game_map, current_strategy)
            proximity_discount = current_entity.proximity_discount
            if (current_strategy == constants.BotStrategy.RUSH):
                proximity_discount = 1
            #elif proximity_discount == 0:
            #    proximity_discount = ship_distance_discount

            undocked_utility = proximity_discount * constants.UTILITY_UNDOCKED_SHIP[current_strategy.value]
            docked_utility = constants.UTILITY_ENEMY_DOCKED_SHIP[current_strategy.value] * docked_ship_aggression_multiplier
            if not current_entity.is_docked():
                utility = undocked_utility
                if ship.last_ship_target:
                    if current_entity.id == ship.last_ship_target.id:
                        if ship.calculate_distance_sq_between(current_entity) >= ship.last_ship_target_sq_dist:
                            utility = 0
            else:
                utility = docked_utility * (1.5 if ship.is_clumped else 1)
            utility = overall_discount * utility

        else:
            utility = 0

    elif isinstance(current_entity, entity.Position):
        if current_entity.num_approaching_friendlies > 0:
            utility = 0
        else:
            utility = constants.CORNER_UTILITY

    else:
        utility = 0


    if ship.mission_target:
        if type(ship.mission_target) == type(current_entity):
            if current_entity.id == ship.mission_target.id:
                utility = utility

    return utility