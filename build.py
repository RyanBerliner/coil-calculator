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
import hashlib
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


# Importantly, these are in ascending order. This matters because we
# interpolate between size ranges when constructing inverted index
size_map_traditional = [
    ('XXS', 'Extra Extra Small'),
    ('XS', 'Extra Small'),
    ('SM', 'Small'),
    ('MD', 'Medium'),
    ('LG', 'Large'),
    ('XL', 'Extra Large'),
    ('XXL', 'Extra Extra Large'),
]

size_map_alt1 = [
    ('S0', 'Size 0'),
    ('S1', 'Size 1'),
    ('S2', 'Size 2'),
    ('S3', 'Size 3'),
    ('S4', 'Size 4'),
    ('S5', 'Size 5'),
    ('S6', 'Size 6'),
]

size_map_alt2 = [
    ('S/M', 'Small'),
    ('M/L', 'Medium'),
    ('L/XL', 'Large'),
]

size_map_alt3 = [
    ('R1', 'R1'),
    ('R2', 'R2'),
    ('R3', 'R3'),
]

size_map_alt4 = [('Custom', 'Custom')]

def get_size_map(s):
    maps = [
        size_map_traditional,
        size_map_alt1,
        size_map_alt2,
        size_map_alt3,
        size_map_alt4,
    ]

    for size_map in maps:
        sizes = [size[0] for size in size_map]

        if s in sizes:
            return size_map

    raise Exception('unable to find size map')


fields = {
    'make',
    'model',
    'wheel_travel',
    'stroke',
    'year_start',
    'year_end',
    'size_start',
    'size_end',
    'curve',
}

bikes = []

with os.scandir('datasheets') as items:
    for item in items:
        if not item.is_file():
            continue

        if not item.name.endswith('.json'):
            continue

        if item.name == 'reference.json':
            continue

        with open(item.path, 'r') as datasheet_file:
            full_data = json.loads(datasheet_file.read())
            trimmed_data = {field: full_data[field] for field in fields}
            bikes.append(trimmed_data)

output_object = {
    # bikes can be an array with constant time lookup because the "ids" we
    # store in our search structures are just the indexes of the bikes
    'bikes': [],
    'terms': {},
    'terms_trie': None,
}

terms_trie = Trie()

for i, bike_data in enumerate(bikes):
    output_object['bikes'].append(bike_data)

    searchable_terms = [str(f).lower() for f in [
        bike_data['make'],
        bike_data['model'],
        bike_data['year_start'],
        bike_data['year_end'],
        # we'll add sizes separately cause we have to provide alternate
        # spellings and interpolate anyway
    ]]

    # interpolate between years if they are different
    if bike_data['year_start'] != bike_data['year_end']:
        start, end = int(bike_data['year_start']), int(bike_data['year_end'])

        for year in range(start + 1, end):
            searchable_terms.append(str(year))

    # expand size abreviation to alternative name, interpolate between them

    # BUG: for bikes with size ranges like XS-LG someone could search
    #      "extra large" and this would match since we break on space and that
    #      matches both "extra" and "large". This is really a generic bug with
    #      how I'm matching all terms, but its particularly appearent here

    size_map = get_size_map(bike_data['size_start'])

    bounds = [
        size_i for size_i in range(len(size_map)) if size_map[size_i][0] in
        [bike_data['size_start'], bike_data['size_end']]
    ]

    if len(bounds) == 1:
        searchable_terms.append(size_map[bounds[0]][0].lower())
        searchable_terms.append(size_map[bounds[0]][1].lower())
    elif len(bounds) > 1:
        for b in range(bounds[0], bounds[1] + 1):
            searchable_terms.append(size_map[b][0].lower())
            searchable_terms.append(size_map[b][1].lower())
    else:
        raise Exception('Unable to find size in sizes map ' +
                        f'start={bike_data["size_start"]} ' +
                        f'end={bike_data["size_end"]}')

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

# To build the site we take the src files, put there contents into a map, and
# apply tranformations to the file contents. When we are done, we will write the
# file contents to new files in the dist dir
#
# Transformations are:
#
# 1. Insert html partials into root html pages
# 2. Insert data into root html pages
# 3. Generate assets checksums
# 4. Swap asset references with new filenames (which include checksums)

built_files = {}
partial_files = {}

html_pattern = re.compile('.+.html$')
asset_pattern = re.compile('.+.(css|js)$')

for filename in os.listdir('src'):
    if not html_pattern.match(filename):
        continue

    with open(f'src/{filename}', 'r') as file:
        built_files[filename] = file.read()

for filename in os.listdir('src/partials'):
    if not html_pattern.match(filename):
        continue

    with open(f'src/partials/{filename}', 'r') as file:
        partial_files[filename] = file.read()

for filename in os.listdir('src/assets'):
    if not asset_pattern.match(filename):
        continue

    with open(f'src/assets/{filename}', 'r') as file:
        built_files[f'assets/{filename}'] = file.read()

for name in built_files.keys():
    if not html_pattern.match(name):
        continue

    for partial_name, partial_contents in partial_files.items():
        built_files[name] = built_files[name].replace(
            f'<!-- {partial_name} -->',
            partial_contents
        )

for name, contents in built_files.items():
    if not html_pattern.match(name):
        continue

    bikes_variable = f'const bikesData = {json.dumps(output_object)};'
    built_files[name] = contents.replace('// BIKE_DATA', bikes_variable)

for name, contents in list(built_files.items()):
    if not asset_pattern.match(name):
        continue

    parts = name.split('.')
    checksum = hashlib.md5(bytes(contents, 'utf-8')).hexdigest()
    new_name = f'{".".join(parts[0:-1])}.{checksum}.{parts[-1]}'

    built_files[new_name] = contents
    del built_files[name]

    for html_name, html_contents in built_files.items():
        if not html_pattern.match(html_name):
            continue

        html_contents = html_contents.replace(f'src="{name}"', f'src="{new_name}"')
        built_files[html_name] = html_contents.replace(f'href="{name}"', f'href="{new_name}"')

# Before writing to the dist/ dir, clean up everything that is there already

for filename in os.listdir('dist'):
    if filename == '.keep':
        continue

    try:
        os.remove(f'dist/{filename}')
    except OSError:
        shutil.rmtree(f'dist/{filename}')

for name, content in built_files.items():
    os.makedirs(os.path.dirname(f'dist/{name}'), exist_ok=True)

    with open(f'dist/{name}', 'x') as file:
        file.write(content)
