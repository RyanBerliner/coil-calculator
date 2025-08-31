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
#       - need to be able to constrain linkage angles with each other
#         (rigid arm with joint in the middle)


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
            return f'({self.x}, {self.y})'

        return f'(${self.x}, ${self.y})'

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

        # TODO: will hand to handle vertical line
        angle = math.atan((self.j2.y - self.j1.y) / (self.j2.x - self.j1.x))
        adjustment = error / (2 if constrained_joints == 0 else 1)
        y = adjustment * math.sin(angle)
        x = adjustment * math.cos(angle)

        if not self.j1.constrained_coord:
            self.j1.x -= x
            self.j1.y -= y

        if not self.j2.constrained_coord:
            self.j2.x += x
            self.j2.y += y

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
            assert count < 1000, 'unable to solve platform'

            for link in self.linkages.values():
                link.adjust()
            
            error = self.error
            count += 1

    @property
    def error(self):
        return abs(sum([link.error for link in self.linkages.values()]))

    def __str__(self):
        ret = ''

        for link in self.linkages.values():
            ret += str(link)
            ret += '\n'

        return ret


class PlatformTest(unittest.TestCase):
    def test_basic_platform(self):
        """

        Consider the *most basic* suspension platform where there is a giant shock
        attached directly to the axle up to the seatstay. There are just 2 linkages
        and 3 points of interest

            *
           /
          / 
         /  
        *---*

        / = shock (am considering this a linkage)
        - = swing arm
        axle = origin

        We want to understand how the axle position changes in relation to the shock
        length changing (ie shock compressing)

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

        # at this point it should arrive at the same solution at it stands currently
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

    def test_basic_platform_q2(self):
        """

        The same basic design but in the second quadrant

        *
         \
          \ 
           \ 
        *---*

        \ = shock (am considering this a linkage)
        - = swing arm
        axle = origin

        We want to understand how the axle position changes in relation to the shock
        length changing (ie shock compressing)

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

        # at this point it should arrive at the same solution at it stands currently
        platform.solve()
        self.assertEqual(j1.x, 0)
        self.assertEqual(j1.y, 0)
        self.assertEqual(j2.x, -10)
        self.assertEqual(j2.y, 0)
        self.assertEqual(j3.x, -10)
        self.assertEqual(j3.y, -10)

        # lets change the shock length and see the axle move
        shock.constrain_length(10)
        platform.solve()
        self.assertAlmostEqual(j1.x, -1.33975095)
        self.assertAlmostEqual(j1.y, -4.99999135)
        self.assertEqual(j2.x, -10)
        self.assertEqual(j2.y, 0)
        self.assertEqual(j3.x, -10)
        self.assertEqual(j3.y, -10)


if __name__ == '__main__':
    unittest.main()
