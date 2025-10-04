#!/usr/bin/env python3

import os
import json
import sys
import webbrowser

from sim import Bike, quantized_leverage_curve


def update_kinematics(args):
    assert len(args) == 1, 'Supply a datasheet file'

    with open(args[0]) as file:
        data = json.loads(file.read())

        assert data.get('kinematics') is not None, \
            'kinematics not found in datasheet'

        assert data['kinematics'].get('img') is not None, \
            'no reference image found'

        joints = ','.join([j['name'] for j in data['kinematics']['joints']])

        simhtml = os.path.abspath('sim.html')
        url = f'file://{simhtml}?img={data["kinematics"]["img"]}&js={joints}'
        webbrowser.open(url, new=2)

        kin_data = input('Update kinematics in browser, paste output here: ')
        kin_data = json.loads(kin_data)

        for i, joint in enumerate(data['kinematics']['joints']):
            name = joint['name']

            match = next(
                (kin_d for kin_d in kin_data if kin_d['name'] == name),
                None
            )

            data['kinematics']['joints'][i]['x'] = match['x']
            data['kinematics']['joints'][i]['y'] = match['y']

    with open(args[0], 'w') as file:
        json.dump(data, file, indent=2)


def update_leverage_curve(args):
    assert len(args) == 1, 'Supply a datasheet file'
    datasheet_file = args[0]
    bike = Bike.from_datasheet(datasheet_file)
    leverage_data = quantized_leverage_curve(bike, resolution=6, normalized=True)

    with open(datasheet_file) as file:
        data = json.loads(file.read())

    data['leverage_curve'] = leverage_data[1]

    with open(args[0], 'w') as file:
        json.dump(data, file, indent=2)


if __name__ == '__main__':
    assert len(sys.argv) >= 2, 'Supply a command (ie "update_kin")'
    command, args = sys.argv[1], sys.argv[2:]

    if command == 'update_kin':
        update_kinematics(args)
    elif command == 'update_lev':
        update_leverage_curve(args)
    else:
        print(f'Invalid command {sys.argv[1]}')
