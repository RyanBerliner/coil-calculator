#!/usr/bin/env python3

"""
(WIP)
A geometric constraint solver to find leverage curves from pictures of bikes.
"""

import json
import math
import sys
import unittest


# NOTE: random thoughts
#       - need to be able to constrain joints on just x, y, and on some axis
#         (think about yetis with slider thing)


class Joint:
    def __init__(self, x, y, name):
        self.name = name
        self.x = x
        self.y = y
        self.constrained_coord = False

    def constrain_coord(self):
        self.constrained_coord = True

    def __str__(self):
        if not self.constrained_coord:
            return f'({self.name}, {self.x}, {self.y})'

        return f'({self.name}, ${self.x}, ${self.y})'

    @staticmethod
    def dist(j1, j2):
        return math.sqrt(math.pow(j2.x - j1.x, 2) + math.pow(j2.y - j1.y, 2))


class Linkage:
    def __init__(self, j1, j2, name):
        self.name = name
        self.j1 = j1
        self.j2 = j2
        self.constrained_length = None

    @property
    def current_length(self):
        return Joint.dist(self.j1, self.j2)

    def constrain_length(self, to=None):
        self.constrained_length = to

        if to is None:
            self.constrained_length = self.current_length

    @property
    def error(self):
        return self.constrained_length - self.current_length

    def adjust(self):
        constrained_joints = len(list(filter(
            bool,
            [
                self.j1.constrained_coord,
                self.j2.constrained_coord
            ]
        )))

        # nothing you can adjust
        if constrained_joints == 2:
            return

        error = self.error

        if error == 0:
            return

        # Find the angle that the linkage is as. Lets pull the joints in or
        # expand then out alongside the same angle by that adjustment

        rise = self.j2.y - self.j1.y
        run = self.j2.x - self.j1.x
        angle = math.atan(rise / run) if run != 0 else None
        adjustment = error / (2 if constrained_joints == 0 else 1)

        dy = abs(adjustment * math.sin(angle)) * (1 if error < 0 else -1) \
            if angle is not None \
            else adjustment * (1 if error < 0 else -1)

        dx = abs(adjustment * math.cos(angle)) * (1 if error < 0 else -1) \
            if angle is not None \
            else 0

        if self.j1.x < self.j2.x:
            if not self.j1.constrained_coord:
                self.j1.x += dx
            if not self.j2.constrained_coord:
                self.j2.x -= dx
        else:
            if not self.j1.constrained_coord:
                self.j1.x -= dx
            if not self.j2.constrained_coord:
                self.j2.x += dx

        if self.j1.y < self.j2.y:
            if not self.j1.constrained_coord:
                self.j1.y += dy
            if not self.j2.constrained_coord:
                self.j2.y -= dy
        else:
            if not self.j1.constrained_coord:
                self.j1.y -= dy
            if not self.j2.constrained_coord:
                self.j2.y += dy

    def __str__(self):
        length = f'{self.current_length}|??'

        if self.constrained_length is not None:
            length = f'{self.current_length}|{self.constrained_length}'

        return f'{self.name} {self.j1}---({length})---{self.j2}'


class Platform:
    """
    A platform is a system of constrained joints and linkages
    """

    def __init__(self):
        self.linkages = {}


    def add_linkage(self, j1, j2, name):
        assert self.linkages.get(name, None) is None, 'duplicate linkage'
        linkage = Linkage(j1, j2, name)
        self.linkages[name] = linkage
        return linkage

    def solve(self):
        for link in self.linkages.values():
            assert link.constrained_length is not None, \
                f'{link.name} must have constrained length'

        error = self.error
        count = 0
        while error > 0.00001:
            assert count < 1_000_000, 'unable to solve platform'

            for link in self.linkages.values():
                link.adjust()

            error = self.error
            count += 1

    @property
    def error(self):
        return sum([abs(link.error) for link in self.linkages.values()])

    def __str__(self):
        ret = ''

        for link in self.linkages.values():
            ret += str(link)
            ret += '\n'

        return ret


class Bike:
    def __init__(self,
                 platform,
                 joints,
                 shock,
                 travel=None,
                 eye2eye=None,
                 stroke=None,
                 shock_shadow=None,
            ):
        self.platform = platform
        self.joints = joints
        self.shock = shock
        self.shock_starting_length = shock.current_length
        self.travel = travel
        self.eye2eye = eye2eye
        self.stroke = stroke
        self.shock_shadow = shock_shadow
        self.shock_shadow_starting_length = None

        if shock_shadow:
            self.shock_shadow_starting_length = shock_shadow.current_length

    @staticmethod
    def from_datasheet(datasheet):
        file = open(datasheet)
        data = json.loads(file.read())
        file.close()

        joints = {}
        axle = None
        reverse_x = data['kinematics'].get('reverse_x', False)

        for joint in data['kinematics']['joints']:
            name = joint.get('name')
            x = joint.get('x')
            # subtract from som big number because the data we get is from the
            # 0,0 in top left cordinate system of the web
            y = 100000 - joint.get('y')
            x = joint.get('x')

            if reverse_x:
                x = 100000 - x

            assert name is not None, 'found unnamed joint'
            assert x is not None, f'{name} must have an x coord'
            assert y is not None, f'{name} must have an y coord'

            j = Joint(x, y, name)

            if joint.get('is_fixed'):
                j.constrain_coord()

            if joint.get('is_axle'):
                assert axle is None, 'more than one axle is defined'
                axle = j

            joints[name] = j

        assert axle is not None, 'no axle is defined'

        platform = Platform()
        shock = None
        # a shock_shadow is a link that adds and remove length along with the
        # shock when it moves through the travel. This is used for inline angle
        # restrictions
        shock_shadow = None

        for link in data['kinematics']['links']:
            name = link.get('name')
            j1 = link.get('j1')
            j2 = link.get('j2')

            assert name is not None, 'found unnamed link'
            assert j1 is not None, f'{name} must have j1 defined'
            assert j2 is not None, f'{name} must have j2 defined'
            assert j1 != j2, '{name} j1 and j2 cannot be the same'

            l = platform.add_linkage(joints[j1], joints[j2], name)
            l.constrain_length()

            if link.get('is_shock'):
                assert shock is None, 'more than one shock is defined'
                shock = l

            if link.get('is_shock_shadow'):
                shock_shadow = l

        assert shock is not None, 'no shock is defined'

        travel = data.get('wheel_travel')
        eye2eye = data.get('eyetoeye')
        stroke = data.get('stroke')

        assert travel is not None, 'wheel_travel not defined'
        assert eye2eye is not None, 'eyetoeye not defined'
        assert stroke is not None, 'stroke not defined'

        return Bike(
            platform,
            joints,
            shock,
            float(travel),
            float(eye2eye),
            float(stroke),
            shock_shadow,
        )


class PlatformTest(unittest.TestCase):
    def test_basic_platform(self):
        """
        Most basic suspension platform possible (single pivot shock on axle)

            *
           /
          /
         /
        *---*

        / = shock (am considering this a linkage)
        - = swing arm
        axle = origin

        We want to understand how the axle position changes in relation to the
        shock length changing (ie shock compressing)

        """

        j1 = Joint(0, 0, 'axle')

        j2 = Joint(10, 0, 'pivot')
        j2.constrain_coord()

        j3 = Joint(10, 10, 'shock_mount')
        j3.constrain_coord()

        platform = Platform()

        swing_arm = platform.add_linkage(j1, j2, name='swing_arm')
        swing_arm.constrain_length()

        shock = platform.add_linkage(j1, j3, name='shock')
        shock.constrain_length()

        # at this point it should arrive at the same solution at it stands
        # currently
        platform.solve()
        self.assertEqual(j1.x, 0)
        self.assertEqual(j1.y, 0)
        self.assertEqual(j2.x, 10)
        self.assertEqual(j2.y, 0)
        self.assertEqual(j3.x, 10)
        self.assertEqual(j3.y, 10)

        # lets change the shock length and see the axle move
        shock.constrain_length(10)
        platform.solve()
        self.assertAlmostEqual(j1.x, 1.33975095)
        self.assertAlmostEqual(j1.y, 4.99999135)
        self.assertEqual(j2.x, 10)
        self.assertEqual(j2.y, 0)
        self.assertEqual(j3.x, 10)
        self.assertEqual(j3.y, 10)

        # make sure it can grow too
        shock.constrain_length(15)
        platform.solve()
        self.assertAlmostEqual(j1.x, 0.07842415)
        self.assertAlmostEqual(j1.y, -1.24999256)
        self.assertEqual(j2.x, 10)
        self.assertEqual(j2.y, 0)
        self.assertEqual(j3.x, 10)
        self.assertEqual(j3.y, 10)

    def test_basic_platform_q2(self):
        """
        The same basic platform design but in the second quadrant with the axle
        at the origin again
        """

        j1 = Joint(0, 0, 'axle')

        j2 = Joint(-10, 0, 'pivot')
        j2.constrain_coord()

        j3 = Joint(-10, 10, 'shock_mount')
        j3.constrain_coord()

        platform = Platform()

        swing_arm = platform.add_linkage(j1, j2, name='swing_arm')
        swing_arm.constrain_length()

        shock = platform.add_linkage(j1, j3, name='shock')
        shock.constrain_length()

        platform.solve()
        self.assertEqual(j1.x, 0)
        self.assertEqual(j1.y, 0)
        self.assertEqual(j2.x, -10)
        self.assertEqual(j2.y, 0)
        self.assertEqual(j3.x, -10)
        self.assertEqual(j3.y, 10)

        shock.constrain_length(10)
        platform.solve()
        self.assertAlmostEqual(j1.x, -1.33975095)
        self.assertAlmostEqual(j1.y, 4.99999135)
        self.assertEqual(j2.x, -10)
        self.assertEqual(j2.y, 0)
        self.assertEqual(j3.x, -10)
        self.assertEqual(j3.y, 10)

        shock.constrain_length(15)
        platform.solve()
        self.assertAlmostEqual(j1.x, -0.07842415)
        self.assertAlmostEqual(j1.y, -1.24999256)
        self.assertEqual(j2.x, -10)
        self.assertEqual(j2.y, 0)
        self.assertEqual(j3.x, -10)
        self.assertEqual(j3.y, 10)

    def test_basic_platform_q3(self):
        """
        The same basic platform design but in the third quadrant with the axle
        at the origin again
        """

        j1 = Joint(0, 0, 'axle')

        j2 = Joint(-10, 0, 'pivot')
        j2.constrain_coord()

        j3 = Joint(-10, -10, 'shock_mount')
        j3.constrain_coord()

        platform = Platform()

        swing_arm = platform.add_linkage(j1, j2, name='swing_arm')
        swing_arm.constrain_length()

        shock = platform.add_linkage(j1, j3, name='shock')
        shock.constrain_length()

        platform.solve()
        self.assertEqual(j1.x, 0)
        self.assertEqual(j1.y, 0)
        self.assertEqual(j2.x, -10)
        self.assertEqual(j2.y, 0)
        self.assertEqual(j3.x, -10)
        self.assertEqual(j3.y, -10)

        shock.constrain_length(10)
        platform.solve()
        self.assertAlmostEqual(j1.x, -1.33975095)
        self.assertAlmostEqual(j1.y, -4.99999135)
        self.assertEqual(j2.x, -10)
        self.assertEqual(j2.y, 0)
        self.assertEqual(j3.x, -10)
        self.assertEqual(j3.y, -10)

        shock.constrain_length(15)
        platform.solve()
        self.assertAlmostEqual(j1.x, -0.07842415)
        self.assertAlmostEqual(j1.y, 1.24999256)
        self.assertEqual(j2.x, -10)
        self.assertEqual(j2.y, 0)
        self.assertEqual(j3.x, -10)
        self.assertEqual(j3.y, -10)

    def test_basic_platform_q4(self):
        """
        The same basic platform design but in the fourth quadrant with the axle
        at the origin again
        """

        j1 = Joint(0, 0, 'axle')

        j2 = Joint(10, 0, 'pivot')
        j2.constrain_coord()

        j3 = Joint(10, -10, 'shock_mount')
        j3.constrain_coord()

        platform = Platform()

        swing_arm = platform.add_linkage(j1, j2, name='swing_arm')
        swing_arm.constrain_length()

        shock = platform.add_linkage(j1, j3, name='shock')
        shock.constrain_length()

        platform.solve()
        self.assertEqual(j1.x, 0)
        self.assertEqual(j1.y, 0)
        self.assertEqual(j2.x, 10)
        self.assertEqual(j2.y, 0)
        self.assertEqual(j3.x, 10)
        self.assertEqual(j3.y, -10)

        shock.constrain_length(10)
        platform.solve()
        self.assertAlmostEqual(j1.x, 1.33975095)
        self.assertAlmostEqual(j1.y, -4.99999135)
        self.assertEqual(j2.x, 10)
        self.assertEqual(j2.y, 0)
        self.assertEqual(j3.x, 10)
        self.assertEqual(j3.y, -10)

        shock.constrain_length(15)
        platform.solve()
        self.assertAlmostEqual(j1.x, 0.07842415)
        self.assertAlmostEqual(j1.y, 1.24999256)
        self.assertEqual(j2.x, 10)
        self.assertEqual(j2.y, 0)
        self.assertEqual(j3.x, 10)
        self.assertEqual(j3.y, -10)

    def test_vertical_linkage(self):
        """
        When the linkage we want to grow or shrink is vertical our slope is
        inf, so we need to make sure this is handled properly
        """

        j1 = Joint(0, 10, 'top')
        j1.constrain_coord()

        j2 = Joint(0, 0, 'bottom')

        platform = Platform()

        link = platform.add_linkage(j1, j2, name='link')
        link.constrain_length(15)
        platform.solve()

        self.assertEqual(j1.x, 0)
        self.assertEqual(j1.y, 10)
        self.assertEqual(j2.x, 0)
        self.assertAlmostEqual(j2.y, -5)

    def test_horizontal_linkage(self):
        # no special case here, just pairs well with vertical test
        j1 = Joint(0, 0, 'left')
        j1.constrain_coord()

        j2 = Joint(10, 0, 'right')

        platform = Platform()

        link = platform.add_linkage(j1, j2, name='link')
        link.constrain_length(15)
        platform.solve()

        self.assertEqual(j1.x, 0)
        self.assertEqual(j1.y, 0)
        self.assertAlmostEqual(j2.x, 15)
        self.assertEqual(j2.y, 0)

    def test_transition_patrol_like_platform(self):
        a = Joint(0, 0, 'a')
        b = Joint(5, 5, 'b')
        c = Joint(7, 4, 'c')
        c.constrain_coord()
        d = Joint(9, 5, 'd')
        e = Joint(7, 1, 'e')
        e.constrain_coord()
        f = Joint(9, 1, 'f')
        f.constrain_coord()

        platform = Platform()

        chainstay = platform.add_linkage(a, e, name='chainstay')
        chainstay_length = chainstay.current_length
        chainstay.constrain_length()

        seatstay = platform.add_linkage(a, b, name='seatstay')
        seatstay_length = seatstay.current_length
        seatstay.constrain_length()

        ttop = platform.add_linkage(b, d, name='ttop')
        ttop.constrain_length()
        tleft = platform.add_linkage(b, c, name='tleft')
        tleft.constrain_length()
        tright = platform.add_linkage(c, d, name='tright')
        tright.constrain_length()

        shock = platform.add_linkage(d, f, name='shock')

        starting_shock = shock.current_length
        starting_axle_x, starting_axle_y = a.x, a.y
        self.assertEqual(starting_shock, 4)
        self.assertEqual(starting_axle_x, 0)
        self.assertEqual(starting_axle_y, 0)

        shock.constrain_length(2)
        platform.solve()

        self.assertAlmostEqual(shock.current_length, 2)

        self.assertAlmostEqual(
            chainstay.current_length,
            chainstay_length,
            places=5
        )

        self.assertAlmostEqual(
            seatstay.current_length,
            seatstay_length,
            places=5
        )


def patrol():
    # a dump from sim.html of a transition patrol
    # (complete bike image)
    # patrol_dump = [
    #     {"name":"axle","x":143,"y":292},
    #     {"name":"chainstay left","x":167,"y":296},
    #     {"name":"chainstay right","x":297,"y":270},
    #     {"name":"seatstay top","x":282,"y":204},
    #     {"name":"triangle bottom","x":315,"y":210},
    #     {"name":"shock top","x":333,"y":193},
    #     {"name":"shock bottom","x":336,"y":265}
    # ]

    # (just the frame image)
    patrol_dump = [
        {"name":"axle","x":32,"y":284},
        {"name":"chainstay left","x":55,"y":290},
        {"name":"chainstay right","x":184,"y":276},
        {"name":"seatstay top","x":175,"y":206},
        {"name":"triangle bottom","x":207,"y":216},
        {"name":"shock top","x":226,"y":200},
        {"name":"shock bottom","x":223,"y":272}
    ]

    # the 1000 is just a random big number to make it bottom left coord from top left
    joints = {j['name']: Joint(j['x'], 1000 - j['y'], j['name']) for j in patrol_dump}
    joints['chainstay right'].constrain_coord()
    joints['triangle bottom'].constrain_coord()
    joints['shock bottom'].constrain_coord()

    platform = Platform()

    chainstay = platform.add_linkage(joints['chainstay left'], joints['chainstay right'], name='chainstay')
    chainstay.constrain_length()

    seatstay = platform.add_linkage(joints['axle'], joints['seatstay top'], name='seatstay')
    seatstay.constrain_length()

    # now make a triangle to make the full seatstay rigid
    seatstay_bottom = platform.add_linkage(joints['axle'], joints['chainstay left'], name='seatstay bottom')
    seatstay_bottom.constrain_length()
    seatstay_brace = platform.add_linkage(joints['seatstay top'], joints['chainstay left'], name='seatstay brace')
    seatstay_brace.constrain_length()

    ttop = platform.add_linkage(joints['shock top'], joints['seatstay top'], name='ttop')
    ttop.constrain_length()

    tleft = platform.add_linkage(joints['triangle bottom'], joints['seatstay top'], name='tleft')
    tleft.constrain_length()

    tright = platform.add_linkage(joints['triangle bottom'], joints['shock top'], name='tright')
    tright.constrain_length()

    shock = platform.add_linkage(joints['shock top'], joints['shock bottom'], name='shock')

    return Bike(
        platform,
        joints,
        shock,
        160, 205, 60
    )


def firebird():
    firebird_dump = [
        {"name":"axle","x":26,"y":408},
        {"name":"bb joint","x":285,"y":380},
        {"name":"chainstay","x":253,"y":384},
        {"name":"seatstay","x":281,"y":265},
        {"name":"shock bottom","x":335,"y":400},
        {"name":"triangle bottom","x":295,"y":302},
        {"name":"triangle right","x":325,"y":283}
    ]

    # the 1000 is just a random big number to make it bottom left coord from top left
    joints = {j['name']: Joint(j['x'], 1000 - j['y'], j['name']) for j in firebird_dump}
    joints['shock bottom'].constrain_coord()
    joints['triangle bottom'].constrain_coord()
    joints['bb joint'].constrain_coord()

    platform = Platform()

    chainstay = platform.add_linkage(joints['axle'], joints['chainstay'], name='chainstay')
    chainstay.constrain_length()

    seatstay = platform.add_linkage(joints['axle'], joints['seatstay'], name='seatstay')
    seatstay.constrain_length()

    rear_triangle = platform.add_linkage(joints['chainstay'], joints['seatstay'], name='rear_triangle')
    rear_triangle.constrain_length()

    bb_link = platform.add_linkage(joints['chainstay'], joints['bb joint'], name='bb link')
    bb_link.constrain_length()

    ttop = platform.add_linkage(joints['triangle right'], joints['seatstay'], name='ttop')
    ttop.constrain_length()

    tleft = platform.add_linkage(joints['triangle bottom'], joints['seatstay'], name='tleft')
    tleft.constrain_length()

    tright = platform.add_linkage(joints['triangle bottom'], joints['triangle right'], name='tright')
    tright.constrain_length()

    shock = platform.add_linkage(joints['triangle right'], joints['shock bottom'], name='shock')

    return Bike(
        platform,
        joints,
        shock,
        165, 205, 65
    )


def draw(bike):
    import matplotlib.pyplot as plt
    import matplotlib.animation as animation

    fig, ax = plt.subplots()

    # this is an estimate duration, cause computation of each frame takes time
    animation_duration = 2_000
    fps = 30
    frames = int(animation_duration / fps)
    interval = int(1_000 / fps)

    def get_data(frame):
        max_percent = bike.stroke / bike.travel * 100 * .8
        perc = max_percent * (frame / frames)
        shock_length = bike.shock_starting_length * ((100 - perc)/100)
        bike.shock.constrain_length(shock_length)

        total_shock_delta = bike.shock_starting_length - shock_length

        if bike.shock_shadow:
            new_shock_shadow = bike.shock_shadow_starting_length - total_shock_delta
            bike.shock_shadow.constrain_length(new_shock_shadow)

        bike.platform.solve()
        js = bike.joints.values()
        return [j.x for j in js], [j.y for j in js]

    plot = ax.plot(*get_data(0), 'o')[0]

    min_x = min(j.x for j in bike.joints.values())
    max_x = max(j.x for j in bike.joints.values())
    min_y = min(j.y for j in bike.joints.values())
    max_y = max(j.y for j in bike.joints.values())
    padding_x = (0.2 * (max_x - min_x));
    padding_y = (0.4 * (max_y - min_y));

    ax.set_xlim([min_x - padding_x, max_x + padding_x])
    ax.set_ylim([min_y - padding_y, max_y + padding_y])
    ax.set_aspect(1)

    def update(frame):
        plot.set_data(*get_data(frame))

    ani = animation.FuncAnimation(fig=fig, func=update, frames=frames, interval=interval)
    plt.show()


def leverage_curve(bike, draw=False):
    travel, eye2eye, stroke = bike.travel, bike.eye2eye, bike.stroke

    percent_change_shock = stroke / eye2eye / 100

    prev_shock_length = bike.shock_starting_length
    prev_axle = Joint(bike.joints['axle'].x, bike.joints['axle'].y, 'prev')
    starting_axle = Joint(bike.joints['axle'].x, bike.joints['axle'].y, 'prev')
    x_data = []
    y_data = []

    i = 1
    while i <= 100:
        remove = percent_change_shock * i * bike.shock_starting_length
        bike.shock.constrain_length(bike.shock_starting_length - remove)

        if bike.shock_shadow:
            bike.shock_shadow.constrain_length(bike.shock_shadow_starting_length - remove)

        bike.platform.solve()

        delta_shock = bike.shock.current_length - prev_shock_length

        # we don't actually want to do the full delta of the axle, but rather
        # just the delta y ... because when companies say "160mm travel" they
        # really mean "160mm *vertical* travel" ... not "the wheel travels 160mm"
        #
        # this is what "the wheel travels 160mm" would look like
        # delta_axle = Joint.dist(bike.joints['axle'], prev_axle)
        # delta_axle_total = Joint.dist(bike.joints['axle'], starting_axle)

        # and this is "160mm *vertical* travel
        delta_axle = bike.joints['axle'].y - prev_axle.y
        delta_axle_total = bike.joints['axle'].y - starting_axle.y

        leverage = abs(delta_axle / delta_shock)
        
        print(i, leverage)

        x_data.append(delta_axle_total)
        y_data.append(leverage)

        prev_shock_length = bike.shock.current_length
        prev_axle = Joint(bike.joints['axle'].x, bike.joints['axle'].y, 'prev')

        # TODO: make more precise
        i += 1

    # convert x axis to wheel travel scale
    x_data = [x/x_data[-1]*travel for x in x_data]

    # do error correction based on the area under the reciprical (integral) and
    # edge it towards to correct solution

    y_recip = [1/y for y in y_data]
    x_deltas = [d[1] - d[0] for d in zip(x_data[:-1], x_data[1:])]
    area = sum(d[0]*d[1] for d in zip(x_deltas, y_recip))
    error = (area - stroke) / stroke
    og_error = error
    corrections = 0
    print('applying error correction...')

    while abs(error) > 1e-5 and corrections < 10_000:
        y_min = min(y_data)
        adjustment = y_min * 1e-5

        if error < 0:
            y_data = [d - adjustment for d in y_data]
        else:
            y_data = [d + adjustment for d in y_data]

        y_recip = [1/y for y in y_data]
        x_deltas = [d[1] - d[0] for d in zip(x_data[:-1], x_data[1:])]
        area = sum(d[0]*d[1] for d in zip(x_deltas, y_recip))
        error = (area - stroke) / stroke
        corrections += 1

    print('original error: ', og_error)
    print(f'new error ({corrections} corrections): ', error)

    if not draw:
        return x_data, y_data

    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    ax.plot(x_data, y_data)
    plt.show()


def quantized_leverage_curve(bike, draw=False, resolution=6, normalized=False):
    assert resolution >= 2, 'resolution must be 2 or greater'

    raw_x_data, raw_y_data = leverage_curve(bike)
    travel, stroke = bike.travel, bike.stroke

    deltas = raw_x_data[-1] / (resolution-1)
    x_data = [x*deltas for x in range(0, resolution)]

    # need to find the closest data points we have to our desired x_data
    y_data = []
    for i in range(resolution):
        x = x_data[i]
        closest_i = None
        closest_i_dist = float('inf')

        for i, raw_x in enumerate(raw_x_data):
            dist = abs(raw_x - x)
            if dist < closest_i_dist:
                closest_i_dist = dist
                closest_i = i

        y_data.append(raw_y_data[closest_i])

    # do error correction
    # area under recip should be stroke
    recip_y = [1/y for y in y_data]
    area = sum([
        ((recip_y[i]*deltas)+(recip_y[i+1]*deltas))/2
        for i in range(resolution-1)
    ])
    diff = stroke - area
    change = diff / (resolution-1) / deltas

    recip_y = [y+change for y in recip_y]
    y_data = [1/y for y in recip_y]

    if normalized:
        leverage = travel / stroke
        y_data = [y / leverage for y in y_data]

    if not draw:
        return x_data, y_data

    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    ax.plot(x_data, y_data)
    plt.show()


if __name__ == '__main__':
    unittest.main()
    # draw(firebird())
    # leverage_curve(firebird(), draw=True)
    # quantized_leverage_curve(patrol(), draw=True, resolution=6, normalized=True)
    # x_data, y_data = quantized_leverage_curve(patrol(), resolution=6, normalized=True)
    # print(','.join([str(y) for y in y_data]))

    # datasheet = sys.argv[1]
    # bike = Bike.from_datasheet(datasheet)
    # draw(bike)
