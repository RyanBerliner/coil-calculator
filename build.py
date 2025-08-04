#!/usr/bin/env python3

"""
Transforms and inlines bike data from the bikes.csv file into the html file.
Also move the rest of src to docs... but those are as is with no transformation
"""

import csv
import json
import os
import re
import shutil

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

html_file = open('src/index.html', 'r')
html_file_contents = html_file.read()
html_file.close()

bikes_variable = f'const bikesData = {json.dumps(output_object)};'

compiled_html_file_contents = \
        html_file_contents.replace('// BIKE_DATA', bikes_variable)

compiled_html_file = open('docs/index.html', 'w')
compiled_html_file.write(compiled_html_file_contents)

# move the rest of the files in src to docs, assume no other html files
other_files_pattern = re.compile('.+[^.html]$')

for file in os.listdir('src'):
    if other_files_pattern.match(file):
        shutil.copy(f'src/{file}', 'docs/')
