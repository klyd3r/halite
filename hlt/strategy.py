from . import constants, entity, utilcalc
import logging
from operator import attrgetter


def calculate_player_score(game_map, my_ship_dict):
    """
    Determine who's in the lead and who's closest
    :param game_map:
    :param my_ship_dict:
    :return: list of enemy player objects
    """

    # Get stats of enemies
    list_enemies = []

    my_id = game_map.get_me().get_id()

    for player in game_map.all_players():
        running_x = running_y = 0
        for ship in player.all_ships():
            player.score += 2.2 if ship.is_docked() else 1.0
            running_x += ship.x
            running_y += ship.y
            ship.set_mine() if player.get_id() == my_id else ship.set_enemy()

        if len(player.all_ships()) > 0:
            player.avg_x = running_x / len(player.all_ships())
            player.avg_y = running_y / len(player.all_ships())

        player.centroid_ship = entity.Position(player.avg_x, player.avg_y)

        if player.get_id() == my_id:
            continue
        else:
            list_enemies.append(player)

    list_enemies = sorted(list_enemies, key=attrgetter('score'), reverse=True)

    for i in range(len(list_enemies)):
        enemy = list_enemies[i]
        enemy.distance_from_me = enemy.centroid_ship.calculate_distance_between(game_map.get_me().centroid_ship)

    # set planets
    for planet in game_map.all_planets():
        if planet.is_owned():
            if planet.owner == game_map.get_me():
                planet.set_mine()
            else:
                planet.set_enemy()

    return list_enemies


def update_my_ship_status(game_map, closest_enemy, my_ship_dict, my_clustered_ships_dict):
    """
    Updates my ship and cluster statuses
    :param game_map:
    :param my_ship_dict:
    :param my_clustered_ships_dict:
    :return:  nothing
    """

    my_player = game_map.get_me()

    for ship in my_player.all_ships():
        ship.distance_to_enemy = ship.calculate_distance_between(closest_enemy.centroid_ship)
        my_ship = my_ship_dict.get(ship.id)
        if not my_ship:
            my_ship_dict[ship.id] = ship
        else:
            my_ship.update_ship(ship)
            #if (my_ship.health < constants.BASE_SHIP_HEALTH / 3) and my_ship.is_clumped:
            #    my_clustered_ships_dict[my_ship.clump_id].remove_ship_from_cluster(my_ship)
            if game_map.turn_num >= 5:
                if my_ship.is_clumped:
                    if not my_ship.clump_id == 1:
                        game_map.my_clustered_ships_dict[my_ship.clump_id].remove_ship_from_cluster(my_ship)

    list_ids_not_updated = [my_ship_dict[ship_id].id for ship_id in my_ship_dict if not my_ship_dict[ship_id].updated_this_turn]

    for ship_id in list_ids_not_updated:
        dead_ship = my_ship_dict[ship_id]
        if dead_ship.is_clumped:
            my_clustered_ships_dict[dead_ship.clump_id].ship_list.remove(dead_ship)
        del my_ship_dict[ship_id]

    logging.info('TURN UPDATE: ships alive: {}'.format(list(my_ship_dict.keys())))

    list_cluster_ids_not_updated = [cluster_id for cluster_id, ship_cluster in my_clustered_ships_dict.items() if
                                    not ship_cluster.update_state()]

    logging.debug('my clusters:{}'.format(my_clustered_ships_dict))

    for cluster_id, cluster in my_clustered_ships_dict.items():
        logging.debug('cluster: {}'.format(cluster))
        logging.debug('ships: {}'.format(cluster.ship_list))

    logging.debug('my clusters not updated:{}'.format(list_cluster_ids_not_updated))
    for cluster_id in list_cluster_ids_not_updated:
        del my_clustered_ships_dict[cluster_id]

    return None


def get_turn_strategy(game_map, prev_turn_strategy, closest_enemy, initial_closest_enemy_id, rush_target, initial_closest_enemy_location):

    # Determine what strategy to use..
    num_players = len([player for player in game_map.all_players() if len(player.all_ships()) > 0])
    current_strategy = prev_turn_strategy

    # Should we rush?
    if game_map.turn_num == 1:

        # First situation if enemy is going to a planet close enough to us
        planets_by_utility = {}
        guide_ship = closest_enemy.all_ships()[0]
        for planet in game_map.all_planets():
            utility = utilcalc.get_utility(guide_ship, planet, game_map, current_strategy,
                                           guide_ship.calculate_min_distance_between(planet), exclude_mid_multiplier=True)
            planets_by_utility.setdefault(utility, []).append(planet)

        enemy_nearest_planet = next(p_list for util, p_list in sorted(planets_by_utility.items(), reverse=True))[0]
        closest_point_enemy_nearest_planet = guide_ship.closest_point_to(enemy_nearest_planet)
        closest_point_enemy_nearest_planet.distance_from_me = game_map.get_me().centroid_ship.calculate_distance_between(enemy_nearest_planet)
        closest_point_enemy_nearest_planet.distance_from_enemy = closest_enemy.centroid_ship.calculate_distance_between(enemy_nearest_planet)

        buffer_turns = 11 if enemy_nearest_planet.num_docking_spots >= 3 else 16
        if num_players > 2:
            buffer_turns = 9.5 if enemy_nearest_planet.num_docking_spots >= 3 else 12.5
        logging.debug('Turns to get to target: {}'.format(closest_point_enemy_nearest_planet.distance_from_me / constants.MAX_SPEED))
        logging.debug('Enemy turns to get to target: {}, buffer: {}'.format((closest_point_enemy_nearest_planet.distance_from_enemy / constants.MAX_SPEED), buffer_turns))

        if (closest_point_enemy_nearest_planet.distance_from_me / constants.MAX_SPEED) <= \
                (closest_point_enemy_nearest_planet.distance_from_enemy / constants.MAX_SPEED) + buffer_turns:
            if num_players > 2:
                logging.info('Rush target: {}'.format(closest_point_enemy_nearest_planet))
                return constants.BotStrategy.RUSH, closest_point_enemy_nearest_planet
            logging.info('Rush target: {}'.format(closest_enemy.centroid_ship))
            return constants.BotStrategy.RUSH, closest_enemy.centroid_ship

        # 2nd situation if we are going mid.. we'll clump and move to mid_map
        guide_ship = sorted(game_map.get_me().all_ships(), key=attrgetter('y'))[1]  # get middle ship
        for planet in game_map.all_planets():
            utility = utilcalc.get_utility(guide_ship, planet, game_map, current_strategy,
                                           guide_ship.calculate_min_distance_between(planet))
            planets_by_utility.setdefault(utility, []).append(planet)
            logging.debug('mid planet deflection planet utility: {}, planet: {}'.format(utility, planet))

        highest_utility_planet = next(p_list for util, p_list in sorted(planets_by_utility.items(), reverse=True))[0]
        if highest_utility_planet.id <= 3:
            logging.info('my centroid: {}'.format(game_map.get_me().centroid_ship))
            logging.info('Rush target mid map: {}'.format(game_map.get_mid_map()))
            return constants.BotStrategy.RUSH, game_map.get_mid_map()

    # 4 player game?
    if num_players > 2:
        logging.debug('current closest enemy:{}, ships: {}'.format(closest_enemy, len(closest_enemy.all_ships())))
        if current_strategy != constants.BotStrategy.RUSH:
            return constants.BotStrategy.FOUR_PLAYERS, None

    if current_strategy == constants.BotStrategy.RUSH:
        if rush_target:
            # do we break out of rush target?
            enemy_ships = [s for s in closest_enemy.all_ships()]
            if [enemy for enemy in enemy_ships if enemy.is_docked()]:
                logging.info('Rush broken')
                return constants.BotStrategy.RUSH, None
            if closest_enemy.all_ships():
                for ship in enemy_ships:
                    ship.distance_from_me = ship.calculate_min_distance_between(game_map.get_me().centroid_ship)
                closest_ship = min(enemy_ships, key=attrgetter('distance_from_me'))
                if closest_ship.distance_from_me <= constants.RUSH_BREAK_DISTANCE:
                    logging.info('Rush broken')
                    return constants.BotStrategy.RUSH, None

            all_ship_distance = game_map.get_me().centroid_ship.calculate_distance_between(closest_enemy.centroid_ship)
            if all_ship_distance <= constants.RUSH_BREAK_DISTANCE:
                logging.info('Rush broken')
                logging.info('{} away from enemy ships'.format(all_ship_distance))
                return constants.BotStrategy.RUSH, None

            rush_distance = game_map.get_me().centroid_ship.calculate_distance_between(rush_target)
            logging.info('{} away from rush target'.format(rush_distance))
            if rush_distance <= constants.RUSH_BREAK_DISTANCE:
                logging.info('Rush broken')
                # if we did mid rush and enemy is too far
                if all_ship_distance >= 12 * constants.MAX_SPEED:
                    if num_players == 2:
                        for ship in game_map.my_ship_dict.values():
                            if ship.is_clumped:
                                game_map.my_clustered_ships_dict[ship.clump_id].remove_ship_from_cluster(ship)
                        return constants.BotStrategy.NORMAL, None
                return constants.BotStrategy.RUSH, None

            return constants.BotStrategy.RUSH, rush_target

        else:
            break_flag = False
            # if they have docked ships we continue rushing..
            if closest_enemy.id == initial_closest_enemy_id:
                if [enemy_ship for enemy_ship in closest_enemy.all_ships() if enemy_ship.is_docked()]:
                    return constants.BotStrategy.RUSH, None

            # do we break out of rush strategy?
            if game_map.get_me().score >= 2 * closest_enemy.score:
                break_flag = True

            if closest_enemy.id != initial_closest_enemy_id:
                break_flag = True

            if len(closest_enemy.all_ships()) == 1:
                break_flag = True

            if (2 * sum([ship.health for ship in closest_enemy.all_ships()])) <= \
                    sum([ship.health for ship in game_map.get_me().all_ships()]):
                break_flag = True

            # ebretel strat
            if are_we_baited(closest_enemy, game_map):
                break_flag = True

            # 4 player bait
            if (num_players > 2) and \
                    closest_enemy.centroid_ship.calculate_distance_between(initial_closest_enemy_location) >= 7 * constants.MAX_SPEED:
                break_flag = True

            if break_flag:
                for ship in game_map.my_ship_dict.values():
                    if ship.is_clumped:
                        game_map.my_clustered_ships_dict[ship.clump_id].remove_ship_from_cluster(ship)
                if num_players > 2:
                    return constants.BotStrategy.FOUR_PLAYERS, None
                else:
                    return constants.BotStrategy.NORMAL, None

            return constants.BotStrategy.RUSH, None

    # if got till here just return two player..
    return constants.BotStrategy.NORMAL, None


def are_we_baited(closest_enemy, game_map):
    if game_map.turn_num >= 15:
        for enemy_ship in closest_enemy.all_ships():
            if enemy_ship.calculate_distance_between(game_map.get_me().centroid_ship) >= 11 * constants.MAX_SPEED:
                return True
    return False

def desertion(my_rank, current_strategy, my_player, list_enemies, num_players_alive, turn_number):
    if current_strategy == constants.BotStrategy.FOUR_PLAYERS:
        if turn_number >= 75:
            if my_rank == num_players_alive - 1:
                logging.info('desertion threshold reached.. My rank:{}'.format(my_rank))
                return True
            elif my_player.score <= list_enemies[0].score - 30:
                logging.info('desertion threshold reached.. My score:{}'.format(my_player.score))
                return True
    else:
        return False


def health_advantage(game_map):
    mid_entities_by_distance = game_map.nearby_entities_by_distance(game_map.get_mid_map(),exclude_planets=True)
    my_ship_hp = 0
    enemy_ship_hp = 0
    for distance in sorted(mid_entities_by_distance):
        for entity in mid_entities_by_distance[distance]:
            if entity.is_docked():
                continue
            if entity.owner == game_map.get_me():
                my_ship_hp += entity.health
            else:
                enemy_ship_hp += entity.health
    return my_ship_hp - enemy_ship_hp

def calculate_utility_multipliers_old(game_map):
    mid_docking_spots = game_map.all_planets()[0].num_docking_spots
    total_docking_spots = sum([planet.num_docking_spots for planet in game_map.all_planets() if planet.id > 3])
    if (mid_docking_spots == 3) and (total_docking_spots > 30):
        planet_multiplier = 1.25
    else:
        planet_multiplier = 1
    docked_ship_aggression_multiplier = 1.0 if mid_docking_spots == 3 else 1.0

    """
    total_planet_area = sum([(planet.radius ** 2) for planet in game_map.all_planets()])
    total_area = game_map.width * game_map.height
    planet_area_ratio = total_planet_area / total_area
    if mid_docking_spots == 2:
        if planet_area_ratio <= 0.0108:
            mid_map_multiplier = 1.4
        elif planet_area_ratio <= 0.016:
            mid_map_multiplier = 1.3
        else:
            mid_map_multiplier = 1.2
    else:
        if planet_area_ratio <= 0.015:
            mid_map_multiplier = 1.4
        else:
            mid_map_multiplier = 1.3
    """

    logging.info('UTILITY MULTIPLIERS: mid_spots: {}, total_docking_spots: {}'.format(mid_docking_spots, total_docking_spots))
    return planet_multiplier, docked_ship_aggression_multiplier

def calculate_utility_multipliers(game_map, closest_enemy):
    rush_distance = game_map.get_me().centroid_ship.calculate_distance_between(closest_enemy.centroid_ship)
    #if rush_distance <= 140:
    #    mid_map_multiplier = 1.4
    #else:
    #    mid_map_multiplier = 1.5

    mid_docking_spots = game_map.all_planets()[0].num_docking_spots
    if (mid_docking_spots == 3):
        mid_map_multiplier = 1.4
        if (rush_distance <= 140):
            planet_multiplier = 1.25
        else:
            planet_multiplier = 1
    else:
        planet_multiplier = 1
        mid_map_multiplier = 1.4
    return mid_map_multiplier, planet_multiplier