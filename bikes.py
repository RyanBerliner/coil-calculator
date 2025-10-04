#!/usr/bin/env python3

import os
import json
import sys
import webbrowser

from sim import Bike, quantized_leverage_curve


def add_bike(_args):
    with open('datasheets/reference.json') as file:
        reference_data = json.loads(file.read())

    exclude = ['kinematics', 'curve']

    for data_name in reference_data.keys():
        if data_name in exclude:
            continue

        default_value = reference_data[data_name]
        default_type = type(default_value)
        is_list = default_type == list

        if is_list:
            default_value = default_value[0]
            default_type = type(default_value)

        value = None

        while not value:
            if default_value:
                value = input(f'{data_name} ({default_value}): ')
            else:
                value = input(f'{data_name}: ')

            value = default_type(value) if value else default_value

        if is_list:
            reference_data[data_name] = [value]
        else:
            reference_data[data_name] = value

    default_datasheet_name = f'{reference_data["make"]}-{reference_data["model"]}-{reference_data["year_start"]}'
    datasheet_name = input(f'datasheet name ({default_datasheet_name}): ')
    datasheet_name = datasheet_name if datasheet_name else default_datasheet_name
    datasheet_name = f'datasheets/{datasheet_name}.json'

    with open(datasheet_name, 'w') as file:
        json.dump(reference_data, file, indent=2)

    print(f'Bike added, open {datasheet_name} to add kinematic or curve data')


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

    data['curve'] = leverage_data[1]

    with open(args[0], 'w') as file:
        json.dump(data, file, indent=2)


if __name__ == '__main__':
    valid_commands = {
        'add_bike': (add_bike, 'add a new datasheet file for a bike'),
        'update_kin': (update_kinematics, 'update kinematics for an existing bike'),
        'update_lev': (update_leverage_curve, 'update curve based on existing kinematics'),
    }

    def show_commands(_args):
        print('Available commands are:')
        [print(f'  {c} - {valid_commands[c][1]}') for c in valid_commands.keys()]

    valid_commands['help'] = (show_commands, 'display available commands')

    assert len(sys.argv) >= 2, 'Command missing, run help command for options'
    command, args = sys.argv[1], sys.argv[2:]

    assert command in valid_commands.keys(), \
        'Invalid command, run help command for options'

    valid_commands[command][0](args)
