#!/usr/bin/env python3

"""
(WIP)
A geometric constraint solver to find leverage curves from pictures of bikes.
"""

import math
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
            assert count < 100_000, 'unable to solve platform'

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
    starting_shock = shock.current_length;

    return platform, joints, shock, starting_shock


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
    starting_shock = shock.current_length;

    return platform, joints, shock, starting_shock


def draw(bike):
    import matplotlib.pyplot as plt
    import matplotlib.animation as animation

    platform, joints, shock, starting_shock = bike()

    fig, ax = plt.subplots()

    # this is an estimate duration, cause computation of each frame takes time
    animation_duration = 2_000
    fps = 30
    frames = int(animation_duration / fps)
    interval = int(1_000 / fps)

    def get_data(frame):
        max_percent = 60 / 205 * 100
        perc = max_percent * (frame / frames)
        shock_length = starting_shock * ((100 - perc)/100)
        shock.constrain_length(shock_length)
        platform.solve()
        js = joints.values()
        return [j.x for j in js], [j.y for j in js]

    plot = ax.plot(*get_data(0), 'o')[0]

    min_x = min(j.x for j in joints.values())
    max_x = max(j.x for j in joints.values())
    min_y = min(j.y for j in joints.values())
    max_y = max(j.y for j in joints.values())
    padding_x = (0.2 * (max_x - min_x));
    padding_y = (0.4 * (max_y - min_y));

    ax.set_xlim([min_x - padding_x, max_x + padding_x])
    ax.set_ylim([min_y - padding_y, max_y + padding_y])
    ax.set_aspect(1)

    def update(frame):
        plot.set_data(*get_data(frame))

    ani = animation.FuncAnimation(fig=fig, func=update, frames=frames, interval=interval)
    plt.show()


def leverage_curve(bike):
    travel = input('wheel travel (160): ')
    travel = int(travel) if travel else 160

    eye2eye = input('eye to eye (205): ')
    eye2eye = int(eye2eye) if eye2eye else 205

    stroke = input('stroke (60): ')
    stroke = int(stroke) if stroke else 60


    platform, joints, shock, starting_shock = bike()
    percent_change_shock = stroke / eye2eye / 100

    prev_shock_length = starting_shock
    prev_axle = Joint(joints['axle'].x, joints['axle'].y, 'prev')
    starting_axle = Joint(joints['axle'].x, joints['axle'].y, 'prev')
    x_data = []
    y_data = []

    for i in range(1, 101):
        remove = percent_change_shock * i * starting_shock
        shock.constrain_length(starting_shock - remove)
        platform.solve()

        delta_shock = shock.current_length - prev_shock_length
        delta_axle = Joint.dist(joints['axle'], prev_axle)
        delta_axle_total = Joint.dist(joints['axle'], starting_axle)
        leverage = abs(delta_axle / delta_shock)
        
        print(delta_axle_total, leverage)

        x_data.append(delta_axle_total)
        y_data.append(leverage)

        prev_shock_length = shock.current_length
        prev_axle = Joint(joints['axle'].x, joints['axle'].y, 'prev')

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

    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    ax.plot(x_data, y_data)
    plt.show()


if __name__ == '__main__':
    # unittest.main()
    # draw(firebird)
    leverage_curve(firebird)
