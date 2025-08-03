#!/usr/bin/env python3

"""
Takes the bikes.csv file and converts it to a JSON file to be read directly by
the calculator with no alterations nessescary
"""

import csv
import json

input_filename = 'bikes.csv'
header = None
bikes = []


with open(input_filename) as bikes_csv:
    reader = csv.reader(bikes_csv)
    rows = [row for row in reader]
    header = rows[0]
    bikes = rows[1:]

field_transformation = {
    'make': lambda x: x,
    'model': lambda x: x,
    'wheel_travel': lambda x: int(x),
    'stroke': lambda x: float(x),
    'year_start': lambda x: int(x),
    'year_end': lambda x: int(x),
    'size_start': lambda x: x,
    'size_end': lambda x: x,
}

output_filename = 'docs/bikes.json'
output_object = {'bikes': []}

for bike in bikes:
    all_data = list(zip(header, bike))
    bike_data = {}
    curve_data = []

    for data in all_data:
        name, value = data

        if name.startswith('curve_'):
            curve_data.append(float(value))
        elif name in field_transformation.keys():
            bike_data[name] = field_transformation[name](value)

    bike_data['curve'] = curve_data
    output_object['bikes'].append(bike_data)

with open(output_filename, 'w') as bikes_json:
    bikes_json.write(json.dumps(output_object))
