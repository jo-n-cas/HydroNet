#!/usr/bin/env python3
"""Group sites within 250 m and select repeated biological measurements."""
import argparse
import ast
import csv
from collections import defaultdict
from datetime import date
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'structural_subset'


def parameter_counts(value):
    counts = ast.literal_eval(re.sub(r'np\.int64\((-?\d+)\)', r'\1', value))
    if not isinstance(counts, dict) or any(not isinstance(k, str) or type(v) is not int or v < 0
                                           for k, v in counts.items()):
        raise ValueError('Invalid GeoJSON parameter_counts')
    return counts


def group_locations(positions, radius):
    """Create groups whose members are all pairwise within radius metres."""
    groups = []
    location_of = {}
    for code in sorted(positions, key=lambda site: (*positions[site], site)):
        x, y = positions[code]
        best = None
        for group in reversed(groups):
            ax, ay = positions[group[0]]
            if x - ax > radius:
                break
            distance = math.hypot(x - ax, y - ay)
            if (distance <= radius and
                    all(math.hypot(x - positions[member][0], y - positions[member][1]) <= radius
                        for member in group) and
                    (best is None or distance < best[0])):
                best = (distance, group)
        group = best[1] if best else [code]
        if best is None:
            groups.append(group)
        else:
            group.append(code)
        location_of[code] = f'LOC_{group[0]}'
    assert len(location_of) == len(positions)
    assert all(math.hypot(positions[a][0] - positions[b][0],
                          positions[a][1] - positions[b][1]) <= radius
               for group in groups for i, a in enumerate(group) for b in group[i + 1:])
    return groups, location_of


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--min-dates', type=int, default=4)
    parser.add_argument('--min-years', type=int, default=2)
    parser.add_argument('--radius-m', type=int, default=250)
    parser.add_argument('--min-chem-count', type=int, default=5)
    args = parser.parse_args()
    if min(args.min_dates, args.min_years, args.radius_m, args.min_chem_count) < 1:
        parser.error('all thresholds must be positive')

    bio = json.loads((ROOT / 'HB_unique_locations_with_measurements.geojson').read_text(encoding='utf-8'))
    chem = json.loads((ROOT / 'FYCHEM_unique_locations_with_measurements.geojson').read_text(encoding='utf-8'))
    positions = {}
    sources = defaultdict(set)
    feature_by_code = {}
    for label, data in [('HB', bio), ('FYCHEM', chem)]:
        for feature in data['features']:
            p = feature['properties']
            code = p['locatiecode']
            point = (p['rd_x_original'], p['rd_y_original'])
            if code in positions and positions[code] != point:
                raise ValueError(f'Conflicting coordinates for {code}')
            positions[code] = point
            sources[code].add(label)
            feature_by_code.setdefault(code, feature)

    with (ROOT / 'HB_sampled50locations.csv').open(encoding='utf-8-sig', newline='') as source:
        reader = csv.DictReader(source, delimiter=';')
        fields = reader.fieldnames
        rows = list(reader)
    for row in rows:
        code = row['locatiecode']
        if not code or not row['fewsparameter']:
            raise ValueError('Biological row without locatiecode or fewsparameter')
        if code not in positions or positions[code] != (int(row['locatie x']), int(row['locatie y'])):
            raise ValueError(f'Biological CSV and GeoJSON coordinates disagree at {code}')
        sources[code].add('HB_sampled50')

    groups, location_of = group_locations(positions, args.radius_m)
    members = {f'LOC_{group[0]}': group for group in groups}
    series = defaultdict(list)
    for row in rows:
        day = date.fromisoformat(row['datum'].split()[0])
        series[(location_of[row['locatiecode']], row['fewsparameter'])].append((day, row))
    eligible = {key: records for key, records in series.items()
                if len({day for day, _ in records}) >= args.min_dates
                and len({day.year for day, _ in records}) >= args.min_years}
    structural_ids = {location for location, _ in eligible}
    selected_rows = [dict(row, structural_location_id=location_of[row['locatiecode']])
                     for row in rows if (location_of[row['locatiecode']], row['fewsparameter']) in eligible]

    bio_features = []
    for feature in bio['features']:
        location = location_of[feature['properties']['locatiecode']]
        if location in structural_ids:
            feature['properties']['structural_location_id'] = location
            bio_features.append(feature)
    chem_features = []
    for feature in chem['features']:
        location = location_of[feature['properties']['locatiecode']]
        if (location in structural_ids and
                any(count >= args.min_chem_count for count in
                    parameter_counts(feature['properties']['parameter_counts']).values())):
            feature['properties']['structural_location_id'] = location
            chem_features.append(feature)

    OUT.mkdir(exist_ok=True)
    with (OUT / 'HB_sampled50locations_structural.csv').open('w', encoding='utf-8', newline='') as target:
        writer = csv.DictWriter(target, fieldnames=fields + ['structural_location_id'], delimiter=';')
        writer.writeheader()
        writer.writerows(selected_rows)
    bio['features'] = bio_features
    (OUT / 'HB_unique_locations_structural.geojson').write_text(json.dumps(bio, ensure_ascii=False), encoding='utf-8')
    chem['features'] = chem_features
    (OUT / 'FYCHEM_near_structural_HB_candidates.geojson').write_text(
        json.dumps(chem, ensure_ascii=False), encoding='utf-8')

    with (OUT / 'location_groups.csv').open('w', encoding='utf-8', newline='') as target:
        writer = csv.writer(target)
        writer.writerow(['structural_location_id', 'locatiecode', 'rd_x', 'rd_y', 'sources', 'structural'])
        for code in sorted(positions):
            x, y = positions[code]
            location = location_of[code]
            writer.writerow([location, code, x, y, ','.join(sorted(sources[code])), location in structural_ids])
    with (OUT / 'structural_series.csv').open('w', encoding='utf-8', newline='') as target:
        writer = csv.writer(target)
        writer.writerow(['structural_location_id', 'fewsparameter', 'source_locatiecodes',
                         'rows', 'distinct_dates', 'distinct_years', 'first_date', 'last_date'])
        for (location, parameter), records in sorted(eligible.items()):
            days = {day for day, _ in records}
            writer.writerow([location, parameter,
                             ','.join(sorted({row['locatiecode'] for _, row in records})),
                             len(records), len(days), len({day.year for day in days}), min(days), max(days)])

    locations = {'type': 'FeatureCollection', 'features': []}
    for location in sorted(structural_ids):
        records = [record for (key, _), values in eligible.items() if key == location for record in values]
        days = {day for day, _ in records}
        p = {'structural_location_id': location,
             'source_locatiecodes': members[location],
             'qualifying_parameters': sorted({parameter for (key, parameter) in eligible if key == location}),
             'distinct_dates': len(days), 'distinct_years': len({day.year for day in days}),
             'chemistry_candidate_codes': sorted(feature['properties']['locatiecode']
                                                 for feature in chem_features
                                                 if feature['properties']['structural_location_id'] == location)}
        locations['features'].append({'type': 'Feature',
                                      'geometry': feature_by_code[members[location][0]]['geometry'],
                                      'properties': p})
    (OUT / 'structural_locations.geojson').write_text(json.dumps(locations, ensure_ascii=False), encoding='utf-8')

    summary = [
        '# Structural monitoring locations', '',
        f'Sites from all three input files are grouped when **every pair** of RD-coordinate '
        f'points is within {args.radius_m} metres. Each group gets one `structural_location_id`; '
        'original `locatiecode` values remain available. A chain wider than the threshold is split.', '',
        f'A grouped location is structural when at least one biological parameter has observations '
        f'on {args.min_dates} distinct dates in {args.min_years} calendar years. Dates from different '
        'site codes in a group are combined; multiple rows on one date count as one visit. '
        'Only rows for qualifying group/parameter series are retained.', '',
        f'Across all inputs, {len(positions):,} unique site codes form {len(groups):,} groups; '
        f'{sum(len(group) > 1 for group in groups):,} groups contain multiple codes.', '',
        f'**Result:** {len(structural_ids)} structural grouped locations, {len(eligible)} qualifying '
        f'parameter series, and {len(selected_rows):,} of {len(rows):,} biological CSV rows retained. '
        f'They contain {len(bio_features)} original HB site features.', '',
        f'The FYCHEM subset has {len(chem_features)} sites in those groups with at least '
        f'{args.min_chem_count} aggregate observations for one parameter. These are chemistry '
        '**candidates**: FYCHEM has no measurement dates, so its counts do not establish '
        'repeated measurements over time. Original GeoJSON aggregate counts describe the full inventory.', '',
        '`location_groups.csv` maps every source code to a grouped location and source files. '
        '`structural_series.csv` gives dates and source codes for qualifying series. '
        '`structural_locations.geojson` has one point per group, placed at its first source site. '
        'The other GeoJSON outputs retain source points and add `structural_location_id`.', '',
        '| Structural location | Source site codes | Qualifying parameters | Dates | Years | Chemistry candidates |',
        '| --- | --- | ---: | ---: | ---: | --- |',
    ]
    for feature in locations['features']:
        p = feature['properties']
        summary.append(f"| `{p['structural_location_id']}` | "
                       f"{', '.join('`' + code + '`' for code in p['source_locatiecodes'])} | "
                       f"{len(p['qualifying_parameters'])} | {p['distinct_dates']} | "
                       f"{p['distinct_years']} | "
                       f"{', '.join('`' + code + '`' for code in p['chemistry_candidate_codes']) or 'none'} |")
    summary.extend(['', 'The daily water-level/flow CSVs have no `locatiecode` link to these sites. '
                    'Proximity alone does not establish whether a group lies on the Amstel river '
                    'or represents the same water body.', ''])
    (OUT / 'README.md').write_text('\n'.join(summary), encoding='utf-8')
    print(f'{len(structural_ids)} structural grouped locations, {len(eligible)} parameter series, '
          f'{len(selected_rows):,} biological rows, {len(chem_features)} chemistry candidates')
    print(f'Wrote {OUT}')


if __name__ == '__main__':
    main()
