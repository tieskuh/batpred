# -----------------------------------------------------------------------------
# Predbat Home Battery System
# Copyright Trefor Southwell 2026 - All Rights Reserved
# This application maybe used for personal use only and not for commercial use
# -----------------------------------------------------------------------------
# fmt off
# pylint: disable=consider-using-f-string
# pylint: disable=line-too-long
# pylint: disable=attribute-defined-outside-init
"""
Opportunistic solar car charging (car_charging_solar) against the car_charging_now model.

A car that reports charging now outside any slot is modelled at its full charging rate until the end
of the current plan interval (dynamic_load_car_charging_now). A car on opportunistic solar charging
with no plan draws PV surplus that the prediction's solar diversion already models, so a charging-now
slot for it would count the same energy twice. These tests pin that the charging-now slot is skipped
for such a car only, and that every other case keeps the full-rate model.
"""
import copy

MISSING = object()
STATE_FIELDS = (
    "num_cars",
    "minutes_now",
    "car_charging_now",
    "car_charging_planned",
    "car_charging_rate",
    "car_charging_slots",
    "car_charging_now_slots",
    "car_charging_solar",
)
NOW = 12 * 60 + 10
END = 12 * 60 + 30
RATE = 8.5


def _check(name, condition, detail=""):
    """
    Print an error for a failed condition and return whether it failed.
    """
    if not condition:
        print("ERROR: {} {}".format(name, detail))
        return True
    return False


def _setup(my_predbat, solar, planned):
    """
    One car charging now at 12:10, mid-way through the 12:00-12:30 interval, with no slot covering now.
    solar is the car_charging_solar value, or MISSING to remove the attribute as a bare mock would lack it.
    """
    my_predbat.num_cars = 1
    my_predbat.minutes_now = NOW
    my_predbat.car_charging_now = [True]
    my_predbat.car_charging_planned = [planned]
    my_predbat.car_charging_rate = [RATE]
    my_predbat.car_charging_slots = [[]]
    my_predbat.car_charging_now_slots = [[]]
    if solar is MISSING:
        if hasattr(my_predbat, "car_charging_solar"):
            delattr(my_predbat, "car_charging_solar")
    else:
        my_predbat.car_charging_solar = [solar]


def _full_rate_slot(my_predbat):
    """
    Whether car 0 got exactly one charging-now slot at its full rate for the rest of the interval.
    """
    slots = my_predbat.car_charging_now_slots[0]
    expected_kwh = RATE * (END - NOW) / 60
    return len(slots) == 1 and slots[0]["start"] == NOW and slots[0]["end"] == END and abs(slots[0]["kwh"] - expected_kwh) < 0.001


def _run(my_predbat):
    """
    Run the car_charging_solar against car_charging_now scenarios.
    """
    failed = False

    print("Test 1: a solar-only car charging now gets no full-rate charging-now slot")
    _setup(my_predbat, True, False)
    my_predbat.dynamic_load_car_charging_now(END)
    failed |= _check("t1 no now-slot", my_predbat.car_charging_now_slots == [[]], "slots {}".format(my_predbat.car_charging_now_slots))
    failed |= _check("t1 prediction model empty", my_predbat.car_charging_slots_model() == [[]], "model {}".format(my_predbat.car_charging_slots_model()))

    print("Test 2: a solar car with an active plan keeps the full-rate charging-now slot")
    _setup(my_predbat, True, True)
    my_predbat.dynamic_load_car_charging_now(END)
    failed |= _check("t2 full-rate slot", _full_rate_slot(my_predbat), "slots {}".format(my_predbat.car_charging_now_slots))

    print("Test 3: a car without solar charging keeps the full-rate charging-now slot")
    _setup(my_predbat, False, False)
    my_predbat.dynamic_load_car_charging_now(END)
    failed |= _check("t3 full-rate slot", _full_rate_slot(my_predbat), "slots {}".format(my_predbat.car_charging_now_slots))

    print("Test 4: without the car_charging_solar attribute the full-rate model is kept and nothing crashes")
    _setup(my_predbat, MISSING, False)
    my_predbat.dynamic_load_car_charging_now(END)
    failed |= _check("t4 full-rate slot", _full_rate_slot(my_predbat), "slots {}".format(my_predbat.car_charging_now_slots))
    return failed


def run_car_solar_now_tests(my_predbat):
    """
    car_charging_solar suppresses the full-rate car_charging_now model for a solar-only car, and nothing else.
    """
    print("*** Running test: car_solar_now")
    saved_state = {}
    for field in STATE_FIELDS:
        value = getattr(my_predbat, field, MISSING)
        # The sentinel itself, never a deep copy of it, so the restore below can recognise it
        saved_state[field] = value if value is MISSING else copy.deepcopy(value)
    try:
        failed = _run(my_predbat)
    finally:
        for field, value in saved_state.items():
            if value is MISSING:
                if hasattr(my_predbat, field):
                    delattr(my_predbat, field)
            else:
                setattr(my_predbat, field, value)
    print("*** car_solar_now test {}".format("FAILED" if failed else "PASSED"))
    return failed
