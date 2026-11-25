# SPDX-License-Identifier: Apache-2.0
"""Validate producer-defined observation shapes without converting their bytes.

Source: livingproof-sim-mujoco v3.9.7, observations.py observe/observe_route,
commit 727d8706598e8ac706324ca87edd0973fdbb3485. These adapters validate evidence;
Health observations still come exclusively from bounded MCAP replay.
"""

import math

COLUMNS = ["t", "x", "y", "z", "wall_distance", "wall_intrusion"]


def require(ok, field):
    if not ok:
        raise ValueError(f"Malformed observation: {field}")


def number(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def timed_value(value, field):
    require(isinstance(value, dict), field)
    require(number(value.get("value")), field + ".value")
    require(number(value.get("time")) and value["time"] >= 0, field + ".time")


def common(doc, departure, distance):
    required = {
        "end",
        "duration_s",
        "exit_time",
        departure,
        distance,
        "min_base_height",
        "wall_contacts",
        "wall_distance",
        "wall_intrusion",
        "trace",
    }
    require(required <= doc.keys(), "missing required producer fields")
    require(doc["end"] in ("crossed_exit", "time_limit", "non_finite_state", departure), "end")
    require(number(doc["duration_s"]) and doc["duration_s"] >= 0, "duration_s")
    require(
        doc["exit_time"] is None
        or (number(doc["exit_time"]) and 0 <= doc["exit_time"] <= doc["duration_s"]),
        "exit_time",
    )
    timed_value(doc[distance], distance)
    timed_value(doc["min_base_height"], "min_base_height")
    left = doc[departure]
    if left is not None:
        require(isinstance(left, dict), departure)
        require(all(number(left.get(k)) for k in ("time", "x", "y")), departure)
        require(isinstance(left.get("via"), str) and bool(left["via"]), departure + ".via")
    contacts = doc["wall_contacts"]
    require(isinstance(contacts, list), "wall_contacts")
    for contact in contacts:
        require(isinstance(contact, dict), "wall contact")
        require(isinstance(contact.get("wall"), str), "wall contact.wall")
        require(all(number(contact.get(k)) for k in ("start", "end", "depth")), "wall contact")
        require(0 <= contact["start"] <= contact["end"], "wall contact interval")
    wall_distance = doc["wall_distance"]
    require(isinstance(wall_distance, dict), "wall_distance")
    require(
        isinstance(wall_distance.get("method"), str) and number(wall_distance.get("distmax")),
        "wall_distance fields",
    )
    intrusion = doc["wall_intrusion"]
    require(isinstance(intrusion, dict), "wall_intrusion")
    require(
        isinstance(intrusion.get("method"), str)
        and isinstance(intrusion.get("walls"), dict)
        and isinstance(intrusion.get("geometry"), dict),
        "wall_intrusion fields",
    )
    trace = doc["trace"]
    require(isinstance(trace, dict) and trace.get("columns") == COLUMNS, "trace.columns")
    samples = trace.get("samples")
    require(isinstance(samples, list) and bool(samples), "trace.samples")
    previous = -1
    for row in samples:
        require(isinstance(row, list) and len(row) == len(COLUMNS), "trace row width")
        require(
            all(number(v) for v in row[:5]) and (row[5] is None or number(row[5])),
            "trace row values",
        )
        require(row[0] >= 0 and row[0] >= previous, "trace time order")
        previous = row[0]
    require(previous == doc["duration_s"], "trace duration")


def hallway(doc):
    require(
        not {"left_world", "max_route_distance", "places", "places_entered"} & doc.keys(),
        "route fields in hallway observation",
    )
    common(doc, "left_hallway", "max_abs_lateral")
    intrusion = doc["wall_intrusion"]
    require(
        "half_width" in intrusion
        and (intrusion["half_width"] is None or number(intrusion["half_width"])),
        "half_width",
    )


def route(doc):
    require(
        not {"left_hallway", "max_abs_lateral"} & doc.keys(), "hallway fields in route observation"
    )
    common(doc, "left_world", "max_route_distance")
    require(isinstance(doc.get("places_entered"), dict), "places_entered")
    require(all(number(t) and t >= 0 for t in doc["places_entered"].values()), "place times")
    places = doc.get("places")
    require(isinstance(places, dict), "places")
    require(all(isinstance(places.get(k), str) for k in ("route", "exit")), "places names")
    require(
        isinstance(places.get("through"), list)
        and all(isinstance(v, str) for v in places["through"]),
        "places.through",
    )


def validate_observation(doc):
    adapters = {
        "livingproof-hallway-observation/2.0.0": hallway,
        "livingproof-route-observation/0.1.0": route,
    }
    fmt = doc.get("format")
    if not isinstance(fmt, str) or fmt not in adapters:
        raise ValueError("Unsupported observation format")
    adapters[fmt](doc)
