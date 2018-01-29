from . import constants, entity
from operator import attrgetter
import logging, math

def should_ship_micro(ship, current_strategy, game_map, combat_ratio):

    if ship.docking_status != ship.DockingStatus.UNDOCKED:
        return False

    if ship.has_command:
        return False

    if ship.aggress_flag:
        return False

    if not ship.nearby_enemies:
        return False

    if ship.health <= 0:
        return False

    if ship.nearby_enemies:
        if not get_nearest_enemy(ship, current_strategy, combat_ratio):
            return False
    else:
        return False

    return True

def get_nearest_enemy(ship, current_strategy, combat_ratio):
    for enemy in ship.nearby_enemies:
        enemy.distance_from_my_ship = ship.calculate_distance_sq_between(enemy)
    nearby_enemies = [enemy for enemy in ship.nearby_enemies if
                      not (enemy.is_fully_engaged(combat_ratio=combat_ratio) or enemy.health <= 0)]
    #nearby_docked_enemies = [enemy for enemy in ship.nearby_enemies if enemy.is_docked() and not (enemy.health <= 0)]

    #if nearby_docked_enemies:
    #    nearest_docked_enemy = min(nearby_docked_enemies, key=attrgetter('distance_from_my_ship'))
    #    if ship.is_target_nearer_than(nearest_docked_enemy, constants.MAX_SPEED):
    #        return nearest_docked_enemy

    if nearby_enemies:
        nearest_enemy = min(nearby_enemies, key=attrgetter('distance_from_my_ship'))
        return nearest_enemy


def can_friends_engage(ship, enemy, game_map, main_enemy):

    num_friends_ready_to_attack = 0
    cum_hp_friends = 0
    num_friends_required = 2
    for my_ship in enemy.friends_ready_to_attack:
        if (not my_ship.has_command) and my_ship.ready_to_attack():
            if enemy.weapon_cooldown or (my_ship.health >= constants.WEAPON_DAMAGE):
                if my_ship.last_engaged_target:
                    if my_ship.last_engaged_target.id == enemy.id:
                        if my_ship.last_engaged_target_hp >= enemy.health:
                            logging.info('ENGAGE: enemy {} jebaiting.. Not attacking.'.format(enemy.id))
                            return False
                #navi = my_ship.navigate_new(enemy, game_map, return_type='raw')
                #if navi:
                #    if my_ship.get_position(navi[0], navi[1]).is_target_nearer_than(enemy, constants.WEAPON_RADIUS):
                logging.debug('enemy:{}, ship ready to attack:{}'.format(enemy.id, my_ship.id))
                num_friends_ready_to_attack += 1
                cum_hp_friends += my_ship.health

    if enemy.attacking_my_docked_target:
        return True
    elif num_friends_ready_to_attack >= num_friends_required:
        return True
    elif num_friends_ready_to_attack < num_friends_required and cum_hp_friends > enemy.health:
        return True
    elif num_friends_ready_to_attack < num_friends_required and enemy.weapon_cooldown:
        return True
    elif num_friends_ready_to_attack < num_friends_required and enemy.is_docked():
        return True
    elif enemy.my_docked_target:
        if enemy.is_target_nearer_than(enemy.my_docked_target, constants.MAX_SPEED):
            return True
    else:
        return False


def engage(enemy, my_clustered_ships_dict, game_map, highest_utility_target):
    list_commands = []
    friendly_ships = [friend for friend in enemy.friends_ready_to_attack if friend.ready_to_attack()]
    enemy_clumped_hp = enemy.health + sum([e.health for e in enemy.clumped_enemies])
    max_engaged_num = 1 + int(enemy_clumped_hp / (constants.WEAPON_DAMAGE))

    counter = 0
    logging.debug('need {} to engage enemy: {}'.format(max_engaged_num, enemy))
    logging.debug('friends attacking:{}'.format(friendly_ships))
    for my_ship in friendly_ships:
        my_ship.distance_from_target = my_ship.calculate_distance_between(enemy)

    logging.debug('engaging enemy:{}'.format(enemy))

    for my_ship in sorted(friendly_ships, key=attrgetter('distance_from_target')):

        logging.debug('counter:{}, max_engaged_num:{}, has_command:{}'.format(counter, max_engaged_num, my_ship.has_command))

        if counter >= max_engaged_num:
            break

        if my_ship.has_command:
            continue

        if (not enemy.weapon_cooldown) and (my_ship.health <= constants.WEAPON_DAMAGE):
            continue

        # ship is definitely attacking.. friends around cannot run
        if my_ship.nearby_undocked_friends:
            for friendly in my_ship.nearby_undocked_friends:
                logging.debug('friendly {} aggress flag true'.format(friendly))
                friendly.aggress_flag = True


        if len(my_ship.nearby_undocked_friends) > 4:
            logging.debug('ENGAGE: adjusting angle to get closer to top enemy')
            target = enemy.get_position(4.5, enemy.calculate_angle_between(highest_utility_target))
        elif my_ship.nearby_docked_friends:
            docked_x = sum([friendly.x for friendly in my_ship.nearby_docked_friends]) / len(my_ship.nearby_docked_friends)
            docked_y = sum([friendly.y for friendly in my_ship.nearby_docked_friends]) / len(my_ship.nearby_docked_friends)
            docked_avg = entity.Position(docked_x, docked_y)
            target = enemy.get_position(4.5, enemy.calculate_angle_between(docked_avg))
        #elif (my_ship.highest_utility_target in my_ship.nearby_enemies)\
        #        and (my_ship.highest_utility_target != enemy):
        #    logging.debug('ENGAGE: adjusting angle to get closer to highest util target: {}'.format(my_ship.highest_utility_target))
        #    target = enemy.get_position(4.5, enemy.calculate_angle_between(my_ship.highest_utility_target))

        else:
            target = enemy


        if my_ship.is_clumped:
            navi_list = my_clustered_ships_dict[my_ship.clump_id].navigate_new(target, game_map, is_engage=True, return_type='raw')
            if navi_list:
                for clumped_ship in my_clustered_ships_dict[my_ship.clump_id].ship_list:
                    if not clumped_ship.has_command:
                        navigate_command = clumped_ship.thrust(navi_list[0], navi_list[1])
                        if navigate_command:
                            list_commands.append(navigate_command)
                            clumped_ship.has_command = True
                            if clumped_ship.pos_eot:
                                if clumped_ship.pos_eot.is_target_nearer_than(enemy, constants.WEAPON_RADIUS):
                                    clumped_ship.last_engaged_target = enemy
                                    clumped_ship.last_engaged_target_hp = enemy.health
                                    enemy.add_approaching_friendly(my_ship)
                                    counter += 1
                            logging.info('clumped ship: {}, engaging ship: {}'.format(clumped_ship.id, enemy.id))
            continue

        navigate_command = my_ship.navigate_new(target, game_map, is_engage=True)
        if navigate_command:
            list_commands.append(navigate_command)
            my_ship.has_command = True
            logging.debug('attacking ship:{}'.format(my_ship))
            if my_ship.pos_eot:
                if my_ship.pos_eot.is_target_nearer_than(enemy, constants.WEAPON_RADIUS):
                    my_ship.last_engaged_target = enemy
                    my_ship.last_engaged_target_hp = enemy.health
                    enemy.add_approaching_friendly(my_ship)
                    counter += 1
    return list_commands


def zone_out(ship, enemy, game_map, my_clustered_ships_dict):
    logging.info('trying to zone out enemy:{}'.format(enemy.id))

    distance_to_safety = max(1.1, 1 + constants.MOVE_AND_FIRE_RADIUS - ship.calculate_distance_between(enemy))

    angle = (180 + ship.calculate_angle_between(enemy)) % 360

    #if ship.nearby_docked_friends:
    #   for friendly in ship.nearby_docked_friends:
    #       friendly.distance_from_my_ship = ship.calculate_distance_between(friendly)
    #       closest_docked_friend = sorted(ship.nearby_docked_friends, key=attrgetter('distance_from_my_ship'))[0]

    if enemy.my_docked_target:
        closest_docked_friend = enemy.my_docked_target
        logging.info('ship: {} going to closest docked friend:{}'.format(ship.id, closest_docked_friend.id))
        spot_in_front_of_ship = closest_docked_friend.get_position(1.2, closest_docked_friend.calculate_angle_between(enemy))
        #spot_in_front_of_ship = ship.closest_point_to(closest_docked_friend)
        angle = ship.calculate_angle_between(spot_in_front_of_ship)
        distance_to_safety = min(constants.MAX_SPEED, ship.calculate_min_distance_between(spot_in_front_of_ship))

    if ship.is_clumped:
        clump_radius = my_clustered_ships_dict[ship.clump_id].radius
        distance_to_safety = distance_to_safety - clump_radius - 0.2
    target = ship.get_position(min(distance_to_safety, constants.MAX_SPEED),angle)

    if ship.is_clumped:
        list_commands = []
        navi_list = my_clustered_ships_dict[ship.clump_id].navigate_new(target, game_map, return_type='raw')
        if navi_list:
            logging.info('clumped navi:{}'.format(navi_list))
            enemy.add_approaching_friendly(ship)
            if enemy.clumped_enemies and game_map.turn_num >= 20:
                for e in enemy.clumped_enemies:
                    e.add_approaching_friendly(ship)
            for clumped_ship in my_clustered_ships_dict[ship.clump_id].ship_list:
                if not clumped_ship.has_command:
                    navigate_command = clumped_ship.thrust(navi_list[0], navi_list[1])
                    if navigate_command:
                        list_commands.append(navigate_command)
                        clumped_ship.has_command = True
                        logging.info('clumped ship: {}, zoning out'.format(clumped_ship.id, enemy.id))
        return list_commands

    navigate_command = ship.navigate_new(target, game_map)
    if navigate_command:
        logging.debug('zoning out ship:{}, enemy:{}'.format(ship.id, enemy.id))
        enemy.add_approaching_friendly(ship)
        if enemy.clumped_enemies and game_map.turn_num >= 20:
            for e in enemy.clumped_enemies:
                e.add_approaching_friendly(ship)
        ship.has_command = True
        return navigate_command
    return None


def zone_in(ship, enemy, game_map, current_strategy):
    logging.info('trying to zone in {}'.format(enemy.id))
    my_clustered_ships_dict = game_map.my_clustered_ships_dict
    zone_dist = constants.WEAPON_RADIUS if current_strategy == constants.BotStrategy.RUSH else (constants.MOVE_AND_FIRE_RADIUS)
    if ship.is_clumped:
        zone_dist = zone_dist - my_clustered_ships_dict[ship.clump_id].radius
        logging.info('dist from enemy: {}, clump radi: {}'.format(ship.calculate_distance_between(enemy),
                                                                  my_clustered_ships_dict[ship.clump_id].radius))
    distance_to_safety = ship.calculate_distance_between(enemy) - zone_dist + 0.5
    angle = ship.calculate_angle_between(enemy)

    if distance_to_safety <= 0:
        distance_to_safety = abs(distance_to_safety)
        angle = (180 + angle) % 360
    distance_to_safety = max(1.1 ,abs(distance_to_safety))
    if ship.is_clumped:
        logging.info('dist from enemy: {}, clump radi: {}'.format(ship.calculate_distance_between(enemy),
                                                                  my_clustered_ships_dict[ship.clump_id].radius))

    target = ship.get_position(min(distance_to_safety, constants.MAX_SPEED),angle)

    #if enemy.my_docked_target:
    #    if enemy.is_target_nearer_than(enemy.my_docked_target, constants.MOVE_AND_FIRE_RADIUS):
    #        target = ship.closest_point_to(enemy.my_docked_target)

    if ship.is_clumped:
        list_commands = []
        navi_list = my_clustered_ships_dict[ship.clump_id].navigate_new(target, game_map, return_type='raw')
        if navi_list:
            logging.info('clumped navi:{}'.format(navi_list))
            for clumped_ship in my_clustered_ships_dict[ship.clump_id].ship_list:
                if not clumped_ship.has_command:
                    navigate_command = clumped_ship.thrust(navi_list[0], navi_list[1])
                    if navigate_command:
                        list_commands.append(navigate_command)
                        clumped_ship.has_command = True
                        logging.info('clumped ship: {}, zoning in'.format(clumped_ship.id, enemy.id))
        logging.debug(list_commands)
        return list_commands

    navigate_command = ship.navigate_new(target, game_map, force_zero=True)
    if navigate_command:
        logging.debug('zoning in ship:{}, enemy:{}'.format(ship.id, enemy.id))
        ship.has_command = True
        enemy.add_approaching_friendly(ship)
        if enemy.clumped_enemies and game_map.turn_num >= 20:
            for e in enemy.clumped_enemies:
                e.add_approaching_friendly(ship)
        return navigate_command
    return None


def round_enemy(ship, enemy, my_clustered_ships_dict, game_map):
    distance_to_enemy = ship.calculate_distance_between(enemy)
    angle = ship.calculate_angle_between(enemy)
    tangent_angle = 90 if distance_to_enemy <= constants.NEARBY_RADIUS else math.degrees(math.asin(constants.MAX_SPEED / distance_to_enemy))
    if ship.is_target_nearer_than(game_map.get_mid_map(), 2.5 * constants.MAX_SPEED):
        tangent_angle = math.degrees(math.asin(min(3, distance_to_enemy) / distance_to_enemy))

    target1 = ship.get_position(constants.MAX_SPEED, (angle + tangent_angle) % 360)
    target2 = ship.get_position(constants.MAX_SPEED, (angle - tangent_angle) % 360)

    if ship.highest_utility_target:
        if ship.highest_utility_target.is_target1_nearer(ship, enemy):
            target = ship.highest_utility_target
        else:
            target = target1 if ship.highest_utility_target.is_target1_nearer(target1, target2) else target2

    else:
        enemy_avg_x = enemy.x
        enemy_avg_y = enemy.y
        enemy_avg_x += sum([e.x for e in enemy.clumped_enemies])
        enemy_avg_y += sum([e.y for e in enemy.clumped_enemies])
        enemy_avg_x = enemy_avg_x / (1 + len(enemy.clumped_enemies))
        enemy_avg_y = enemy_avg_y / (1 + len(enemy.clumped_enemies))
        enemy_centroid = entity.Position(enemy_avg_x, enemy_avg_y)
        target = target1 if enemy_centroid.is_target1_nearer(target2, target1) else target2

    if ship.is_clumped:
        list_commands = []
        navi_list = my_clustered_ships_dict[ship.clump_id].navigate_new(target, game_map, return_type='raw')
        if navi_list:
            logging.info('clumped navi:{}'.format(navi_list))
            for clumped_ship in my_clustered_ships_dict[ship.clump_id].ship_list:
                if not clumped_ship.has_command:
                    navigate_command = clumped_ship.thrust(navi_list[0], navi_list[1])
                    if navigate_command:
                        list_commands.append(navigate_command)
                        clumped_ship.has_command = True
                        logging.info('clumped ship: {}, rounding'.format(clumped_ship.id, enemy.id))
        return list_commands

    navigate_command = ship.navigate_new(target, game_map)
    if navigate_command:
        logging.debug('rounding ship:{}, enemy:{}'.format(ship.id, enemy.id))
        ship.has_command = True
        return navigate_command
    return None


def should_run(ship, current_strategy, nearest_enemy):
    num_enemies = len([enemy for enemy in ship.nearby_enemies if \
                       not (enemy.is_docked() or enemy.is_fully_engaged(combat_ratio=constants.COMBAT_RATIO[current_strategy.value]))])
    if ship.nearby_docked_friends:
        return False
    if ship.is_clumped:
        return False
    #if ship.highest_utility_target:
    #    if ship.highest_utility_target.is_target1_nearer(ship, nearest_enemy):
    #        return False
    #if (2 * num_enemies * constants.WEAPON_DAMAGE) >= ship.health:
    #    return True
    if (len(ship.nearby_undocked_friends)) >= 1.25 * num_enemies:
        return False
    if (num_enemies * constants.WEAPON_DAMAGE) >= ship.health:
        return True
    return False


def run_away(ship, my_clustered_ships_dict, game_map):

    num_enemies = len([enemy for enemy in ship.nearby_enemies if not enemy.is_docked()])
    avg_x = sum([enemy.x for enemy in ship.nearby_enemies if not enemy.is_docked()]) / num_enemies
    avg_y = sum([enemy.y for enemy in ship.nearby_enemies if not enemy.is_docked()]) / num_enemies
    angle1 = (145 + ship.calculate_angle_between(entity.Position(avg_x, avg_y))) % 360
    angle2 = (215 + ship.calculate_angle_between(entity.Position(avg_x, avg_y))) % 360
    target1 = ship.get_position(constants.MAX_SPEED + 1, angle1)
    target2 = ship.get_position(constants.MAX_SPEED + 1, angle2)
    if ship.nearby_undocked_friends + ship.nearby_docked_friends:
        num_friendlies = len(ship.nearby_undocked_friends + ship.nearby_docked_friends)
        avg_x = sum([s.x for s in ship.nearby_undocked_friends + ship.nearby_docked_friends]) / num_friendlies
        avg_y = sum([s.y for s in ship.nearby_undocked_friends + ship.nearby_docked_friends]) / num_friendlies
        my_center = entity.Position(avg_x, avg_y)
    else:
        my_center = game_map.get_me().centroid_ship

    if my_center.is_target1_nearer(target2,target1):
        target = target1
        navi_list = ship.navigate_new(target, game_map, return_type='raw')
        if navi_list:
            new_target = ship.get_position(navi_list[0], navi_list[1])
            for enemy in ship.nearby_enemies:
                if new_target.is_target_nearer_than(enemy, constants.WEAPON_RADIUS):
                    target = target2
                    break
        else:
            target = target2
    else:
        target = target2
        navi_list = ship.navigate_new(target, game_map, return_type='raw')
        if navi_list:
            new_target = ship.get_position(navi_list[0], navi_list[1])
            for enemy in ship.nearby_enemies:
                if new_target.is_target_nearer_than(enemy, constants.WEAPON_RADIUS):
                    target = target1
                    break
        else:
            target = target1

    for enemy in ship.nearby_enemies:
        if target.is_target_nearer_than(enemy, constants.WEAPON_RADIUS):
            target = ship.get_position(constants.MAX_SPEED + 1, (180 + ship.calculate_angle_between(entity.Position(avg_x, avg_y))) % 360)

    if ship.is_clumped:
        my_clustered_ships_dict[ship.clump_id].remove_ship_from_cluster(ship)
    navigate_command = ship.navigate_new(target, game_map)
    if navigate_command:
        logging.debug('running away! ship:{}, num_enemies:{}'.format(ship, num_enemies))
        ship.has_command = True
        return navigate_command
    return None


def get_kamikaze_target(ship):
    if ship.is_clumped:
        return None
    if ship.nearby_undocked_friends:
        return None
    nearby_enemies = [enemy for enemy in ship.nearby_enemies if (enemy.health > 0) and
                      ship.is_target_nearer_than(enemy, constants.MAX_SPEED)]
    docked_enemies = [enemy for enemy in nearby_enemies if enemy.is_docked()]
    if docked_enemies:
        nearby_enemies = docked_enemies

    if nearby_enemies and ship.enemies_engaged:
        if ship.health <= (len(ship.enemies_engaged) * constants.WEAPON_DAMAGE):
            highest_hp_enemy = max(nearby_enemies, key=attrgetter('health'))
            #if highest_hp_enemy.health >= 2.0 * ship.health:
            #    return highest_hp_enemy
            if (highest_hp_enemy.health > 1.5 * ship.health) and highest_hp_enemy.is_docked():
                return highest_hp_enemy
    return None


def kamikaze(ship, highest_hp_enemy, my_clustered_ships_dict, game_map):
    navigate_command = ship.navigate_new(highest_hp_enemy, game_map, ignore_enemies=True)
    if navigate_command:
        logging.debug('Kamikaze! ship:{}, enemy:{}'.format(ship, highest_hp_enemy))
        ship.has_command = True
        highest_hp_enemy.add_approaching_friendly(ship, set_full=True)
        if ship.is_clumped:
            my_clustered_ships_dict[ship.clump_id].remove_ship_from_cluster(ship)
        return navigate_command
