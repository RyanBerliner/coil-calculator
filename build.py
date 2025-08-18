#!/usr/bin/env python3

"""
Transforms and inlines bike data from the bikes.csv file into the html file.

The bike data is transformed into an data structures for quick searching out of
the box without any client side indexing required. This is done by making an
inverted index on the terms (anything we want searchable about a bike... make,
model, year, etc) and then a radix tree of the terms themselves to do partial
term matching.

Also move the rest of src files to dist... but those are as is with no
transformation done to them.
"""

import csv
import json
import os
import re
import shutil


class TrieNode:
    def __init__(self, character):
        self.character = character
        self.object_ids = []
        self.children_nodes = []

    def add(self, string, object_id):
        if len(string) == 0:
            if object_id not in self.object_ids:
                self.object_ids.append(object_id)

            return

        added = False

        for node in self.children_nodes:
            if node.character == string[0]:
                node.add(string[1:], object_id)
                added = True

        if not added:
            node = TrieNode(string[0])
            node.add(string[1:], object_id)
            self.children_nodes.append(node)

    def __dict__(self):
        return {
            'object_ids': self.object_ids,
            'children': {
                child.character: child.__dict__()
                for child in self.children_nodes
            }
        }


class Trie:
    def __init__(self):
        self.root = TrieNode(None)

    def add(self, term, object_id):
        self.root.add(term, object_id)

    def __dict__(self):
        return self.root.__dict__()


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

output_object = {
    # bikes can be an array with constant time lookup because the "ids" we
    # store in our search structures are just the indexes of the bikes
    'bikes': [],
    'terms': {},
    'terms_trie': None,
}

terms_trie = Trie()

for i, bike in enumerate(bikes):
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

    searchable_terms = [str(f).lower() for f in [
        bike_data['make'],
        bike_data['model'],
        # TODO: interpolate between years and sizes by filling in the blanks
        bike_data['year_start'],
        bike_data['year_end'],
        bike_data['size_start'],
        bike_data['size_end'],
    ]]

    # seems dumb to join then split, but some of these fields may be multiple
    # terms themselves and this is just an easy way to do it
    for term in ' '.join(searchable_terms).split(' '):
        if output_object['terms'].get(term, None) is None:
            output_object['terms'][term] = []

        # dedupe, could use a set by then we'd have to convert back to list i
        # at some point and ordering would no longer be preserved... this is
        # the lesser evil
        if len(output_object['terms'][term]) and \
                output_object['terms'][term][-1] == i:
            continue

        output_object['terms'][term].append(i)

        # IDEA: if we wanted to add some common mispellings we could add
        #       support for this just in our terms trie, without bothering to
        #       create more indexes in the inverted index
        terms_trie.add(term, i)


output_object['terms_trie'] = terms_trie.__dict__()

html_file = open('src/index.html', 'r')
html_file_contents = html_file.read()
html_file.close()

bikes_variable = f'const bikesData = {json.dumps(output_object)};'

compiled_html_file_contents = \
        html_file_contents.replace('// BIKE_DATA', bikes_variable)

compiled_html_file = open('dist/index.html', 'w')
compiled_html_file.write(compiled_html_file_contents)

# move the rest of the files in src to dist, assume no other html files
other_files_pattern = re.compile('.+[^.html]$')

for file in os.listdir('src'):
    if other_files_pattern.match(file):
        shutil.copy(f'src/{file}', 'dist/')
