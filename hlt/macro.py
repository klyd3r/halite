from . import constants, entity, utilcalc
import logging
from operator import attrgetter

def should_avoid_rush(game_map, current_closest_enemy):
    if game_map.turn_num <= 3 and current_closest_enemy.centroid_ship.calculate_distance_between(game_map.get_me().centroid_ship) <= 125:
        return True
    return False


def get_best_survival_planet(game_map, current_closest_enemy, current_strategy):
    """
    Get a planet that's at least 3 docking spots, and close enough to me,
    while far enough from the enemy
    :param game_map:
    :param current_closest_enemy:
    :return:
    """
    planets_by_utility = {}
    guide_ship = game_map.get_me().all_ships()[0]
    min_utility = 0.7 * constants.UTILITY_NOT_ENEMY_PLANET[current_strategy.value]
    for planet in game_map.all_planets():
        if planet.num_docking_spots < 3:
            continue
        utility = utilcalc.get_utility(guide_ship, planet, game_map, current_strategy,
                                       game_map.get_me().centroid_ship.calculate_min_distance_between(planet))
        enemy_turns_away = current_closest_enemy.centroid_ship.calculate_distance_between(planet) / constants.MAX_SPEED
        enemy_discount = min(1, (enemy_turns_away) / constants.REVAL_TURN_HORIZON[current_strategy.value])
        utility = enemy_discount * utility
        logging.info('AVOID RUSH: utility: {} planet: {} enemy_turns_away: {}'.format(utility, planet.id,enemy_discount ))
        if utility >= min_utility:
            planets_by_utility.setdefault(utility, []).append(planet)

    if planets_by_utility:
        return next(p_list for util, p_list in sorted(planets_by_utility.items(), reverse=True))[0]


def can_friend_defend(ship, enemy):
    for friendly in ship.nearby_undocked_friends:
        if friendly.has_command or friendly.turn_assigned_target:
            continue
        if enemy.is_target1_nearer(ship, friendly):
            continue
        friendly.turn_assigned_target = enemy
        enemy.add_approaching_friendly(friendly)
        return True
    return False

def assign_ship_to_target(ship, target, game_map):

    if isinstance(target, entity.Planet):
        if ship.is_clumped:
            clump_id = ship.clump_id
            logging.debug('clump_id: {}, ship: {}'.format(clump_id, ship))
            logging.debug(game_map.my_clustered_ships_dict)

            game_map.my_clustered_ships_dict[clump_id].remove_ship_from_cluster(ship)

    if ship.is_clumped:
        clump_id = ship.clump_id
        navi_list = game_map.my_clustered_ships_dict[clump_id].navigate_new(target, game_map,
                                                                            return_type='raw')
        logging.debug('Clump id: {}, navi_list:{}'.format(clump_id, navi_list))
        if navi_list:
            for clump_ship in game_map.my_clustered_ships_dict[clump_id].ship_list:
                if clump_ship.clump_id == clump_id and not clump_ship.has_command:
                    navigate_command = clump_ship.thrust(navi_list[0], navi_list[1])
                    clump_ship.has_command = True
                    clump_ship.last_ship_target = target
                    clump_ship.last_ship_target_sq_dist = ship.calculate_distance_sq_between(target)
                    if navigate_command:
                        game_map.command_queue.append(navigate_command)
                        if target != ship.turn_assigned_target:
                            target.add_approaching_friendly(ship)
            return None
        else:
            game_map.my_clustered_ships_dict[clump_id].remove_ship_from_cluster(ship)

    navigate_command = ship.navigate_new(target, game_map)
    if navigate_command:
        logging.info('MACRO: ship: {} going for target: {}'.format(ship, target))
        ship.mission_target = target
        ship.has_command = True
        game_map.command_queue.append(navigate_command)
        ship.last_ship_target = target
        ship.last_ship_target_sq_dist = ship.calculate_distance_sq_between(target)
        if target != ship.turn_assigned_target:
            target.add_approaching_friendly(ship)