#!/usr/bin/env python3

import os
import json
import sys
import webbrowser


def update_kinematics(args):
    assert len(args) == 1, 'Supply a datasheet file'

    with open(args[0]) as file:
        data = json.loads(file.read())
        assert data.get('kinematics') is not None, 'kinematics not found in datasheet'
        assert data['kinematics'].get('img') is not None, 'no reference image found'

        simhtml = os.path.abspath('sim.html')
        webbrowser.open(f'file://{simhtml}?img={data['kinematics']['img']}', new=2)

        data = input('Update kinematics in browser, paste output here: ')
        print(data)


if __name__ == '__main__':
    assert len(sys.argv) >= 2, 'Supply a command (ie "update_kin")'
    command, args = sys.argv[1], sys.argv[2:]

    if command == 'update_kin':
        update_kinematics(args)
    else:
        print(f'Invalid command {sys.argv[1]}')

