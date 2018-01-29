"""
klyd3r bot for halite
uses a utility function for each target, and assigns ships and targets,
highest utility first.
"""
# Then let's import the logging module so we can print out information
import hlt
import logging

# Let's start by importing the Halite Starter Kit so we can interface with the Halite engine
from hlt import constants, entity, strategy, utilcalc, micro, macro
import time
from operator import attrgetter

#import hlt.display

# EARLYGAME STRATEGY settings/variables
rush_target = None
rushing_ships = []
initial_closest_enemy_id = None
initial_closest_enemy_location = None

# GAME START
game = hlt.Game("version292")
game_map = game.initial_map

current_strategy = constants.BotStrategy.NORMAL if len(game_map.all_players()) == 2 else constants.BotStrategy.FOUR_PLAYERS
planet_multiplier = docked_ship_aggression_multiplier = 1
mid_map_multiplier = constants.MID_MAP_MULTIPLIER[current_strategy.value]

while True:
    # TURN START
    # Update the map for the new turn and get the latest version
    game_map = game.update_map()

    # Display stuff - turn off before submission..
    #display = hlt.display.Display(game_map)
    #display.show()

    time_start = time.time()
    turn_timer = time.time()
    game_map.turn_timer = turn_timer


    turn_number = game_map.turn_num
    my_player = game_map.get_me()
    my_id = my_player.get_id()

    #########################################################################
    # PLANNING STRATEGY FOR TURN...
    #########################################################################

    list_enemies = strategy.calculate_player_score(game_map, game_map.my_ship_dict)
    current_closest_enemy = min(list_enemies, key=attrgetter('distance_from_me'))
    num_players_alive = len([player for player in game_map.all_players() if len(player.all_ships()) > 0])

    if turn_number == 0:
        initial_closest_enemy_id = current_closest_enemy.id
        initial_closest_enemy_location = entity.Position(current_closest_enemy.centroid_ship.x, current_closest_enemy.centroid_ship.y)
        if len(game_map.all_players()) == 2:
            mid_map_multiplier, planet_multiplier = strategy.calculate_utility_multipliers(game_map, current_closest_enemy)

    #mid_map_multiplier = constants.MID_MAP_MULTIPLIER[current_strategy.value]

    my_rank = 0
    for i in range(len(list_enemies)):
        enemy = list_enemies[i]
        if len(my_player.all_ships()) < len(enemy.all_ships()):
            my_rank += 1
        #logging.info("Rank {} score: {}, num ships: {}, pos: {},{}".format(i + 1, enemy.score, len(enemy.all_ships()), enemy.avg_x, enemy.avg_y))
    #logging.info("My rank: {}, My score: {}, num undocked ships: {}, pos: {},{}".format(my_rank, my_player.score, len(my_player.all_ships()), my_player.avg_x, my_player.avg_y))

    highest_ranked_enemy = list_enemies[0]
    game_map.update_my_player_status(highest_ranked_enemy)

    current_strategy, rush_target = strategy.get_turn_strategy(game_map, current_strategy, current_closest_enemy,initial_closest_enemy_id, rush_target, initial_closest_enemy_location)

    if rush_target:
        logging.debug('Rush target: {}'.format(rush_target))

    desertion_flag = strategy.desertion(my_rank, current_strategy, my_player, list_enemies, num_players_alive, turn_number)

    micro_flag = True
    if current_strategy != constants.BotStrategy.FOUR_PLAYERS:
        if strategy.health_advantage(game_map) >= 2000:
            micro_flag = False
            logging.debug('HP ADVANTAGE NOW - NOT MICROING')
    else:
        if desertion_flag:
            micro_flag = False
            logging.debug('LOSING! - NOT MICROING')
        elif strategy.health_advantage(game_map) >= 2500:
            micro_flag = False
            logging.debug('HP ADVANTAGE IN 4 PLAYER GAME NOW - NOT MICROING')

    combat_ratio = constants.COMBAT_RATIO[current_strategy.value] if len(my_player.all_ships()) > 5 else 1
    if not micro_flag:
        combat_ratio = 1.5
    time_end = time.time()
    logging.info('Turn {}, {}'.format(turn_number, current_strategy))
    logging.info("setup time: " + str(time_end - time_start))

    #########################################################################
    # REASSIGNMENT FIRST
    #########################################################################

    # CLUMP RUSHING STRATEGY
    if current_strategy == constants.BotStrategy.RUSH and rush_target:
        ships_to_clump = [s for s in game_map.my_ship_dict.values() if isinstance(s, entity.Ship) and not s.is_clumped]
        if ships_to_clump:
            logging.debug('Clumping ships for rush {}'.format(ships_to_clump))
            game_map.MASTER_CLUSTER_ID += 1
            ship_cluster = entity.ShipCluster(ships_to_clump, game_map.MASTER_CLUSTER_ID)
            game_map.my_clustered_ships_dict[game_map.MASTER_CLUSTER_ID] = ship_cluster
            navigate_commands = ship_cluster.clump_for_rush(rush_target, game_map)
            if navigate_commands:
                for navigate_command in navigate_commands:
                    game_map.command_queue.append(navigate_command)
                for ship in ships_to_clump:
                    ship.has_command = True

        else:
            for ship_cluster in game_map.my_clustered_ships_dict.values():
                if ship_cluster.is_clumped:
                    navi_list = ship_cluster.navigate_new(rush_target, game_map, return_type='raw')
                    logging.debug('Clump id: {}, navi_list:{}'.format(ship_cluster.id, navi_list))
                    if navi_list:
                        for clump_ship in ship_cluster.ship_list:
                            if clump_ship.clump_id == ship_cluster.id and not clump_ship.has_command:
                                navigate_command = clump_ship.thrust(navi_list[0], navi_list[1])
                                clump_ship.has_command = True
                                if navigate_command:
                                    game_map.command_queue.append(navigate_command)
                else:
                    navigate_commands = ship_cluster.clump_for_rush(rush_target, game_map)
                    if navigate_commands:
                        for navigate_command in navigate_commands:
                            game_map.command_queue.append(navigate_command)
                        for ship in ship_cluster.ship_list:
                            ship.has_command = True

    # AVOIDING RUSH IN 4 PLAYER MAPS
    #elif macro.should_avoid_rush(game_map, current_closest_enemy):
    #    if current_strategy == constants.BotStrategy.FOUR_PLAYERS:
    #        safest_planet = macro.get_best_survival_planet(game_map, current_closest_enemy, current_strategy)
    #        if safest_planet:
    #            logging.info('reassigning to safe planet: {}'.format(safest_planet))
    #            for ship in game_map.my_ship_dict.values():
    #                navigate_command = ship.navigate_new(safest_planet, game_map)
    #                if navigate_command:
    #                    ship.has_command = True
    #                    game_map.command_queue.append(navigate_command)

    #########################################################################
    # ASSIGN ACTIONS BY SHIP CLOSEST TO ENEMY
    #########################################################################
    time_start = time.time()

    max_iterations, docking_discount, overall_top_target, dock_check_distance = utilcalc.get_utility_parameters(
        game_map, list_enemies, micro_flag, desertion_flag)
    # pre-calc stuff if we don't have that many ships..
    if (game_map.turn_num <= 50) or (len(game_map.get_me().all_ships()) <= 130):
        utilcalc.set_ship_neighbours(game_map, current_strategy, dock_check_distance)
        #utilcalc.assign_ships_to_clusters(game_map)
        utilcalc.calculate_turn_utilities(game_map, current_strategy, game_map.my_ship_dict, list_enemies, turn_timer, micro_flag, combat_ratio=combat_ratio,
                                          desertion_flag=desertion_flag, planet_multiplier=planet_multiplier, docked_ship_aggression_multiplier=docked_ship_aggression_multiplier, mid_map_multiplier=mid_map_multiplier)
        sorted_ship_dict = sorted(game_map.my_ship_dict.values(), key=attrgetter('highest_utility'), reverse=True)
    else:
        sorted_ship_dict = [ship for ship in game_map.my_ship_dict.values() if ship.mission_target]
        sorted_ship_dict += sorted([ship for ship in game_map.my_ship_dict.values() if not ship.mission_target], key=attrgetter('distance_to_enemy'))

    for ship in sorted_ship_dict:

        # just to not make this complain later..
        if not isinstance(ship, entity.Ship):
            continue

        if ship.has_command:
            continue

        if (time.time() - turn_timer) >= 1.4:
            break

        target = None
        max_iterations, docking_discount, overall_top_target, dock_check_distance = utilcalc.get_utility_parameters(game_map, list_enemies, micro_flag, desertion_flag)
        if not ship.ship_neighbors_flag:
            utilcalc.set_ship_neighbor_single(ship, game_map, current_strategy, dock_check_radius=dock_check_distance)

        utilcalc.set_utilities_for_ship(ship, game_map, current_strategy, docking_discount, max_iterations, desertion_flag,
                                        planet_multiplier=planet_multiplier, docked_ship_aggression_multiplier=docked_ship_aggression_multiplier, mid_map_multiplier=mid_map_multiplier, combat_ratio=combat_ratio)

        # override top target if we have a preassigned target
        if ship.turn_assigned_target:
            ship.highest_utility_target = ship.turn_assigned_target

        #########################################################################
        # MICRO STRATEGIES
        #########################################################################

        logging.info('ASSIGNING SHIP: {}'.format(ship.id))

        if micro_flag:

            if micro.should_ship_micro(ship, current_strategy, game_map, combat_ratio):

                nearest_enemy = micro.get_nearest_enemy(ship, current_strategy, combat_ratio)
                #if overall_top_target in ship.nearby_enemies:
                #    if nearest_enemy != ship.highest_utility_target:
                #        nearest_enemy = overall_top_target

                logging.debug('MICRO: ship: {}, weapon_cd: {}, nearest enemy: {}, distance: {}, nearby_enemies:{}'.format(ship.id, ship.weapon_cooldown, nearest_enemy.id, nearest_enemy.distance_from_my_ship, ship.nearby_enemies))

                # BESPOKE RUSH MICRO
                if current_strategy == constants.BotStrategy.RUSH:

                    if not [ship for ship in current_closest_enemy.all_ships() if ship.is_docked()]:

                        if (nearest_enemy.distance_from_my_ship <= constants.NEARBY_RADIUS ** 2):
                            if micro.should_run(ship, current_strategy, nearest_enemy):
                                navigate_command = micro.run_away(ship, game_map.my_clustered_ships_dict, game_map)
                                if navigate_command:
                                    game_map.command_queue.append(navigate_command)
                                    continue

                        zone_radius = constants.MOVE_AND_FIRE_RADIUS if game_map.turn_num <= 15 else constants.WEAPON_RADIUS + 0.5
                        if (nearest_enemy.distance_from_my_ship <= zone_radius ** 2):
                            navigate_command = micro.zone_out(ship, nearest_enemy, game_map, game_map.my_clustered_ships_dict)
                            if navigate_command:
                                if type(navigate_command) == list:
                                    game_map.command_queue += navigate_command
                                else:
                                    game_map.command_queue.append(navigate_command)
                                continue

                        if (nearest_enemy.distance_from_my_ship <= constants.NEARBY_RADIUS ** 2):
                            navigate_command = micro.zone_in(ship, nearest_enemy, game_map, current_strategy)
                            if navigate_command:
                                if type(navigate_command) == list:
                                    game_map.command_queue += navigate_command
                                else:
                                    game_map.command_queue.append(navigate_command)
                                continue

                # NORMAL MICRO
                else:

                    # KAMIKAZE
                    #if ship.enemies_engaged:
                    #    if micro.get_kamikaze_target(ship):
                    #        navigate_command = micro.kamikaze(ship, micro.get_kamikaze_target(ship), game_map.my_clustered_ships_dict, game_map)
                    #        if navigate_command:
                    #            game_map.command_queue.append(navigate_command)
                    #            continue

                    # RUN
                    if (nearest_enemy.distance_from_my_ship <= constants.NEARBY_RADIUS ** 2):
                        if micro.should_run(ship, current_strategy, nearest_enemy):
                            navigate_command = micro.run_away(ship, game_map.my_clustered_ships_dict, game_map)
                            if navigate_command:
                                game_map.command_queue.append(navigate_command)
                                continue

                    # ENGAGE
                    #if nearest_enemy == ship.highest_utility_target:
                    if (nearest_enemy.distance_from_my_ship <= constants.MOVE_AND_FIRE_RADIUS ** 2):
                        if not(nearest_enemy.is_fully_engaged(game_map=game_map, my_ship=ship, combat_ratio=combat_ratio)):
                            if nearest_enemy.friends_ready_to_attack:
                                if micro.can_friends_engage(ship, nearest_enemy, game_map, highest_ranked_enemy):
                                    navigate_commands = micro.engage(nearest_enemy, game_map.my_clustered_ships_dict, game_map, overall_top_target)
                                    if nearest_enemy.clumped_enemies:
                                        for enemy in nearest_enemy.clumped_enemies:
                                            clumped_commands = micro.engage(enemy, game_map.my_clustered_ships_dict, game_map, overall_top_target)
                                            if clumped_commands:
                                                navigate_commands += clumped_commands
                                    if navigate_commands:
                                        game_map.command_queue += navigate_commands
                                        if ship.has_command:
                                            continue

                    # ZONE OUT / defend
                    if not nearest_enemy.is_docked():
                        if ship.is_target_nearer_than(game_map.get_mid_map(), 3.5 * constants.MAX_SPEED):
                            if nearest_enemy.distance_from_my_ship <= constants.MOVE_AND_FIRE_RADIUS ** 2:
                                if ship.highest_utility_target:
                                    if ship.highest_utility_target == nearest_enemy:
                                        navigate_command = micro.zone_out(ship, nearest_enemy, game_map, game_map.my_clustered_ships_dict)
                                        if navigate_command:
                                            if type(navigate_command) == list:
                                                game_map.command_queue += navigate_command
                                            else:
                                                game_map.command_queue.append(navigate_command)
                                            continue

                        # ROUND
                        if (nearest_enemy.distance_from_my_ship <= constants.NEARBY_RADIUS ** 2):
                            if ship.highest_utility_target:
                                if ship.highest_utility_target != nearest_enemy and not isinstance(ship.highest_utility_target, entity.Planet):
                                    navigate_command = micro.round_enemy(ship, nearest_enemy, game_map.my_clustered_ships_dict, game_map)
                                    if navigate_command:
                                        if type(navigate_command) == list:
                                            game_map.command_queue += navigate_command
                                        else:
                                            game_map.command_queue.append(navigate_command)
                                        continue

                            #if ship.nearby_docked_friends or ship.nearby_undocked_friends or ship.is_target_nearer_than(
                            #                    game_map.get_mid_map(), 3.5 * constants.MAX_SPEED):
                            # if we have more hp than enemy let's just go towards it don't zone in
                            if (ship.health < nearest_enemy.health) or (nearest_enemy.clumped_enemies):
                                navigate_command = micro.zone_in(ship, nearest_enemy, game_map, current_strategy)
                                if navigate_command:
                                    if type(navigate_command) == list:
                                        game_map.command_queue += navigate_command
                                    else:
                                        game_map.command_queue.append(navigate_command)
                                    continue



        #########################################################################
        # MACRO STRATEGIES
        #########################################################################

        if ship.turn_assigned_target:
            macro.assign_ship_to_target(ship, ship.turn_assigned_target, game_map)
            continue

        target = ship.highest_utility_target

        # first check if we want to dock
        dock_check_combat_ratio = 0.5 if len(game_map.get_me().all_ships()) > 5 else 1
        if isinstance(target, entity.Planet):
            if current_strategy != constants.BotStrategy.RUSH:
                if ship.can_dock(target) and not target.is_full():
                    if not ship.ship_neighbors_flag:
                        utilcalc.set_ship_neighbor_single(ship, game_map, current_strategy, dock_check_radius=dock_check_distance)
                    break_flag = False
                    if ship.dock_check_ships:
                        for enemy in ship.dock_check_ships:
                            if not enemy.is_fully_engaged(combat_ratio=dock_check_combat_ratio):
                                if macro.can_friend_defend(ship, enemy):
                                    continue
                                break_flag = True
                                target = enemy
                                break
                    if ship.nearest_enemy:
                        if len(my_player.all_ships()) <= 5:
                            logging.info('MACRO: dock check nearest enemy: {}'.format(ship.nearest_enemy))
                            if not ship.nearest_enemy.is_fully_engaged(combat_ratio=dock_check_combat_ratio):
                                if macro.can_friend_defend(ship, ship.nearest_enemy):
                                    continue
                                break_flag = True
                                target = ship.nearest_enemy
                    if ship.enemies_engaged:
                        break_flag = True

                    if not break_flag:
                        game_map.command_queue.append(ship.dock(target))
                        ship.docking_status = ship.DockingStatus.DOCKING
                        ship.planet = target
                        ship.has_command = True
                        target.add_approaching_friendly(ship)
                        logging.info('MACRO: docking! ship:{}'.format(ship))
                        if ship.dock_check_ships:
                            for enemy in ship.dock_check_ships:
                                utilcalc.set_proximity_discount(enemy, ship, current_strategy)
                        if ship.nearest_enemy:
                            utilcalc.set_proximity_discount(ship.nearest_enemy, ship, current_strategy)
                        if ship.is_clumped:
                            game_map.my_clustered_ships_dict[ship.clump_id].remove_ship_from_cluster(ship)

                    else:
                        if target != ship.highest_utility_target:
                            logging.debug(target)
                            logging.info('MACRO: NOT docking! ship: {} going for new target: {}'.format(ship, target))
                            macro.assign_ship_to_target(ship, target, game_map)
                            continue

        # Otherwise cycle through highest util targets and go to the first not fully engaged one
        for utility in sorted(ship.targets_by_utility, reverse=True):

            if ship.has_command:
                break

            for target in ship.targets_by_utility[utility]:
                if ship.has_command:
                    continue

                if target.is_fully_engaged(game_map=game_map, combat_ratio=combat_ratio):
                    continue

                macro.assign_ship_to_target(ship, target, game_map)

    time_macroing = time.time() - time_start
    logging.info("Time for finding target to move to: " + str(time_macroing))

    #########################################################################
    # ASSIGN UNASSIGNED SHIPS..
    #########################################################################
    unassigned_ships = [ship for ship_id, ship in game_map.my_ship_dict.items() if
                        not (ship.has_command or ship.is_docked())]

    if unassigned_ships:
        logging.info('unassigned ships: {}'.format(unassigned_ships))

        target = entity.Position(list_enemies[0].avg_x, list_enemies[0].avg_y)
        my_centroid = entity.Position(my_player.avg_x, my_player.avg_y)
        if overall_top_target:
            target = overall_top_target
        for ship in unassigned_ships:
            if (time.time() - turn_timer) >= 1.80:
                logging.warning('Turn time now: {}, breaking..'.format((time.time() - turn_timer)))
                break
            if ship.mission_target:
                if not ship.mission_target.is_fully_engaged(combat_ratio=combat_ratio):
                    macro.assign_ship_to_target(ship, ship.mission_target, game_map)
                    continue
            if target.is_fully_engaged(combat_ratio=20):
                break
            if ship.has_command:
                continue

            macro.assign_ship_to_target(ship, target, game_map)

    # Send our set of commands to the Halite engine for this turn
    logging.info(game_map.command_queue)
    game.send_command_queue(game_map.command_queue)
    for key in game_map.my_ship_dict:
        game_map.my_ship_dict[key].updated_this_turn = False

    logging.info("Total turn time: " + str(time.time() - turn_timer))
    # TURN END
# GAME END
