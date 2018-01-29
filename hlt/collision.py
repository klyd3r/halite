from .entity import Position, Entity, Ship, Planet
from . import constants
import logging, math

def intersect_segment_circle_amount(start, end, circle, *, fudge=0.2, return_time=False):
    """
    Test whether a line segment and circle intersect.

    :param Entity start: The start of the line segment. (Needs x, y attributes)
    :param Entity end: The end of the line segment. (Needs x, y attributes)
    :param Entity circle: The circle to test against. (Needs x, y, r attributes)
    :param float fudge: A fudge factor; additional distance to leave between the segment and circle. (Probably set this to the ship radius, 0.5.)
    :return: True if intersects, False otherwise
    :rtype: bool
    """
    # Derived with SymPy
    # Parameterize the segment as start + t * (end - start),
    # and substitute into the equation of a circle
    # Solve for t
    dx = end.x - start.x
    dy = end.y - start.y

    a = dx**2 + dy**2
    b = -2 * (start.x**2 - start.x*end.x - start.x*circle.x + end.x*circle.x +
              start.y**2 - start.y*end.y - start.y*circle.y + end.y*circle.y)
    c = (start.x - circle.x)**2 + (start.y - circle.y)**2

    if a == 0.0:
        # Start and end are the same point
        return start.calculate_distance_between(circle) <= circle.radius + fudge

    # Time along segment when closest to the circle (vertex of the quadratic)
    t = min(-b / (2 * a), 1.0)
    if t < 0:
        return False

    closest_x = start.x + dx * t
    closest_y = start.y + dy * t
    closest_distance = Position(closest_x, closest_y).calculate_distance_between(circle)

    return closest_distance - (circle.radius + start.radius + fudge)

def intersect_segment_circle(start, end, circle, *, fudge=0.2):
    """
    Test whether a line segment and circle intersect.

    :param Entity start: The start of the line segment. (Needs x, y attributes)
    :param Entity end: The end of the line segment. (Needs x, y attributes)
    :param Entity circle: The circle to test against. (Needs x, y, r attributes)
    :param float fudge: A fudge factor; additional distance to leave between the segment and circle. (Probably set this to the ship radius, 0.5.)
    :return: True if intersects, False otherwise
    :rtype: bool
    """
    # Derived with SymPy
    # Parameterize the segment as start + t * (end - start),
    # and substitute into the equation of a circle
    # Solve for t

    return intersect_segment_circle_amount(start,end,circle,fudge=fudge) < 0


def are_ships_moving_toward_each_other(ship, target, moved_ship):
    if not moved_ship.pos_eot:
        return False
    ship_movement_angle = ship.calculate_angle_between(target)
    moved_ship_angle = moved_ship.calculate_angle_between(moved_ship.pos_eot)
    angle1 = (ship_movement_angle - moved_ship_angle) % 360
    angle2 = (moved_ship_angle - ship_movement_angle) % 360
    if (180 - min(angle1,angle2)) <= 20:
        logging.info('COLLISION: ships moving towards each other! {} and {}'.format(ship.id, moved_ship.id))
        logging.info('COLLISION: ship angle {} moved_ship angle {}'.format(ship_movement_angle, moved_ship_angle))
        return True
    else:
        return False


def are_ships_moving_in_same_direction(ship, target, moved_ship):
    if not moved_ship.pos_eot:
        return False
    ship_movement_angle = ship.calculate_angle_between(target)
    moved_ship_angle = moved_ship.calculate_angle_between(moved_ship.pos_eot)
    angle1 = (ship_movement_angle - moved_ship_angle) % 360
    angle2 = (moved_ship_angle - ship_movement_angle) % 360
    if (min(angle1,angle2)) <= 20:
        logging.info('COLLISION: ships moving parallel to each other! {} and {}'.format(ship.id, moved_ship.id))
        logging.info('COLLISION: ship angle {} moved_ship angle {}'.format(ship_movement_angle, moved_ship_angle))
        return True
    else:
        return False


def does_moving_ship_intersect_obstacle(ship, target, obstacle, additional_fudge=0.2, ship_speed=None, ship_angle=None):

    R = ship.radius + obstacle.radius + additional_fudge

    # ship stuff..
    ax0 = ship.x
    ay0 = ship.y
    if ship_speed:
        speed_a = ship_speed
    else:
        if ship.is_target_nearer_than(target, constants.MAX_SPEED):
            speed_a = ship.calculate_distance_between(target)
        else:
            speed_a = constants.MAX_SPEED
    if ship_angle:
        angle_a = ship_angle
    else:
        angle_a = ship.calculate_angle_between(target)
    avx = speed_a*math.cos(math.radians(angle_a))
    avy = speed_a*math.sin(math.radians(angle_a))

    # assume obstacle doesn't move
    bx0 = obstacle.x
    by0 = obstacle.y
    bvx = 0
    bvy = 0
    if isinstance(obstacle, Ship):
        if obstacle.pos_eot:
            speed_b = obstacle.speed
            angle_b = obstacle.angle
            bvx = speed_b*math.cos(math.radians(angle_b))
            bvy = speed_b*math.sin(math.radians(angle_b))
            R += additional_fudge / 2

    a = ((bvx - avx) ** 2) + ((bvy - avy) ** 2)
    b = 2*(avx - bvx)*(ax0 - bx0) + 2*(avy - bvy)*(ay0 - by0)
    c = ((ax0 - bx0) ** 2) + ((ay0 - by0) ** 2) - (R ** 2)


    if ship.id == 15 and isinstance(obstacle, Planet) and obstacle.id == 2:
        logging.debug('INTERSECTION CALC HERE')

    # moving in the same direction same speed
    if (a == 0):
        return False, None

    min_t = min(-b / (2*a), 1.0)

    if ship.id == 15 and isinstance(obstacle, Planet) and obstacle.id == 2:
        logging.debug('INTERSECTION CALC')
        logging.debug('min_t: {}, a: {}, b: {}, c: {}'.format(min_t, a,b,c))
        logging.debug('ax0: {}, ay0: {}, speed_a: {}, angle_a: {}'.format(ax0,ay0,speed_a,angle_a))

    # moving away from each other
    if min_t < 0:
        return False, None

    # min between 0 and 1
    ax = ax0 + avx * min_t
    ay = ay0 + avy * min_t
    bx = bx0 + bvx * min_t
    by = by0 + bvy * min_t
    D_sq = ((ax - bx) ** 2) + ((ay - by) ** 2)
    if D_sq > R ** 2:
        return False, None
    return True, min_t

    # if we reached here we need to find roots
    #t1 = ((-b) + math.sqrt((b ** 2) - 4*a*c)) / (2*a)
    #t2 = ((-b) - math.sqrt((b ** 2) - 4*a*c)) / (2*a)
    #min_t = max(0,min(t1,t2))
    #return True, min_t

    #if (c == 0):
    #    return True

    #if (4*a*c) > (b ** 2):
    #    return False, 2


def intersection_two_moving_ships(ship, target, moved_ship):

    if moved_ship.pos_eot.x > moved_ship.x:
        b1 = moved_ship.pos_eot
        b0 = Position(moved_ship.x, moved_ship.y)
    else:
        b0 = moved_ship.pos_eot
        b1 = Position(moved_ship.x, moved_ship.y)

    if target.x > ship.x:
        a1 = Position(target.x, target.y)
        a0 = Position(ship.x, ship.y)
    else:
        a0 = Position(target.x, target.y)
        a1 = Position(ship.x, ship.y)

    if b1.x == b0.x:
        if a1.x != a0.x:
            x = b0.x
            grad_a = ((a1.y - a0.y) / (a1.x - a0.x))
            y = a0.y + grad_a * (x - a0.x)
        else:
            logging.info('INTERSECTING SHIPS: EDGE CASE returning own position!')
            return Position(ship.x, ship.y)

    elif a1.x == a0.x:
        if b1.x != b0.x:
            x = a0.x
            grad_b = ((b1.y - b0.y) / (b1.x - b0.x))
            y = b0.y + grad_b * (x - b0.x)
        else:
            logging.info('INTERSECTING SHIPS: EDGE CASE returning own position!')
            return Position(ship.x, ship.y)
    else:
        grad_b = (b1.y - b0.y) / (b1.x - b0.x)
        grad_a = (a1.y - a0.y) / (a1.x - a0.x)
        if grad_a != grad_b:
            x = (b0.y - a0.y + (grad_a*a0.x) - (grad_b*b0.x)) / (grad_a - grad_b)
            y = a0.y + grad_a * (x - a0.x)
        else:
            logging.info('INTERSECTING SHIPS: EDGE CASE returning own position!')
            return Position(ship.x, ship.y)
    intersection = Position(x, y)

    logging.info('ship: {}'.format(ship))
    logging.info('target: {}'.format(target))
    logging.info('moved_ship: {}'.format(moved_ship))
    logging.info('moved_ship eot: {}'.format(moved_ship.pos_eot))
    logging.info('a0:{}, a1:{}'.format(a0,a1))
    logging.info('b0:{}, b1:{}'.format(b0,b1))
    logging.info('intersection:{}'.format(intersection))

    if x <= b0.x:
        intersection = b0
        angle = intersection.calculate_angle_between(b1)
        logging.info('adj intersection:{}'.format(intersection))
    elif x >= b1.x:
        intersection = b1
        angle = intersection.calculate_angle_between(b0)
        logging.info('adj intersection:{}'.format(intersection))
    else:
        angle = intersection.calculate_angle_between(b0)

    target1 = intersection.get_position(1.3, (angle + 90) % 360)
    target2 = intersection.get_position(1.3, (angle - 90) % 360)
    if ship.is_target1_nearer(target1, target2):
        logging.info('target:{}'.format(target1))
        return target1
    else:
        logging.info('target:{}'.format(target2))
        return target2


def get_speed_and_angle_around_moving_ship(ship, target, moving_ship):

    distance_to_target = ship.calculate_distance_between(target)
    angle_to_target = ship.calculate_angle_between(target)

    # first try moving //
    if are_ships_moving_in_same_direction(ship, target, moving_ship):
        angle = moving_ship.calculate_angle_between(moving_ship.pos_eot)
        adjusted_speed = int(min(constants.MAX_SPEED, distance_to_target))
        has_collided, collision_time = does_moving_ship_intersect_obstacle(ship, target, moving_ship,
                                                                           ship_speed=adjusted_speed, ship_angle=angle)
        if not has_collided:
            logging.info('AVOID MOVING SHIP: ship moving parallel with new angle {}'.format(angle))
            return adjusted_speed, angle

    # try moving to intersection
    new_target = intersection_two_moving_ships(ship, target, moving_ship)
    angle = round(ship.calculate_angle_between(new_target))
    adjusted_speed = int(min(constants.MAX_SPEED, ship.calculate_distance_between(new_target)))
    has_collided, collision_time = does_moving_ship_intersect_obstacle(ship, target, moving_ship, ship_speed=adjusted_speed, ship_angle=angle)
    if not has_collided:
        logging.info('AVOID MOVING SHIP: ship moving to intersection {}'.format(new_target))
        return adjusted_speed, angle

    # get collision time
    has_collided, collision_time = does_moving_ship_intersect_obstacle(ship, target, moving_ship)

    # try slowing down
    slower_speed = int(collision_time * min(distance_to_target, constants.MAX_SPEED))
    has_collided, collision_time = does_moving_ship_intersect_obstacle(ship, target, moving_ship, ship_speed=slower_speed)
    if not has_collided:
        logging.info('AVOID MOVING SHIP: ship slowing down to {}'.format(slower_speed))
        return slower_speed, angle_to_target

    if are_ships_moving_toward_each_other(ship, target, moving_ship):
        distance_to_eot = ship.calculate_distance_between(moving_ship.pos_eot)
        angle = ship.calculate_angle_between(moving_ship.pos_eot)
        angular_diff = abs(angle_to_target - angle)
        angular_diff = min(abs(angular_diff - 360), angular_diff)
        if angular_diff >= 30:
            return 0, None
        else:
            adjusted_speed = min(distance_to_eot - 1 - 0.3, constants.MAX_SPEED)
            return adjusted_speed, angle

    # give up if we get here
    return 0, None
