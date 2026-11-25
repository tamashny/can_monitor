"""Debug mode: imitates a working energy storage by changing PARAMETERS.

Started with `python app/main.py --debug`. The model is simple but keeps the
values consistent with each other:

- the converter (БУП) goes through its states: INIT -> READY (precharge) ->
  STANDBY -> RUN charge -> STANDBY -> RUN discharge -> STANDBY -> ...;
  БУНЭ requests every mode first, the converter follows on the next tick;
- ПУЭР closes K2 that shunts the precharge circuit (K1 is switched by БУНЭ);
- SoC, storage voltage, currents, group voltages follow the charge;
- current heats the cells, the fans of БУСТ-А and the shutter of БУСТ-Б react;
- every device answers with its states and link times;
- now and then a fault shows up and clears by itself: low insulation,
  storage overvoltage, a lost temperature sensor, sensors with an unknown
  ROM code, a lost reserve bus.
"""

import math
import random
import time

from nicegui import app

from canmap import FRAMES, temperature_sensor
from parameters import DEVICES, NO_DATA
from settings import (
    CAN_BITRATE,
    CELL_TEMPERATURE_COUNT,
    CELL_VOLTAGE_COUNT,
)
from summary import update_summaries

# Seconds between two steps of the model
TICK = 0.5

# (БУП state, БУП mode, БУНЭ state, how long it lasts, s).
# After the start-up the list repeats from REPEAT_FROM.
PHASES = [
    ("INIT", "IDLE", "INIT", 3),
    ("READY", "IDLE", "STARTING", 5),
    ("STANDBY", "IDLE", "STANDBY", 8),
    ("RUN", "CHARGE_SET_V", "RUN", 45),
    ("STANDBY", "IDLE", "STANDBY", 8),
    # Shorter than the charge: the discharge current is higher
    ("RUN", "DISCHARGE_SET_I", "RUN", 35),
]
REPEAT_FROM = 2

STORAGE_ENERGY_MAX = 19.5     # kWh
STORAGE_CAPACITY = 25.0       # Ah
STORAGE_VOLTAGE_MIN = 560     # V at SoC 0
STORAGE_VOLTAGE_SPAN = 400    # V from SoC 0 to SoC 100
LINE_VOLTAGE = 780            # V, bus side of the converter
CHARGE_CURRENT = 600          # A
DISCHARGE_CURRENT = 780       # A
AMBIENT_TEMPERATURE = 22      # °C

# Chance per tick that a fault starts, and how long it lasts, s
FAULT_CHANCE = 1 / 200
FAULT_DURATION = (6, 15)
FAULTS = ("insulation", "overvoltage", "sensor", "free_sensors", "reserve_bus")

# How many sensors get an unknown ROM code in the "free_sensors" fault
FREE_SENSORS = 3

# Devices with a heartbeat frame (СКИ has none)
HEARTBEAT_DEVICES = ("bune", "puer", "bem", "bup", "cc", "bust_a", "bust_b", "plod")


def noise(span):

    return random.uniform(-span, span)


class Simulator:

    def __init__(self, parameters):

        self.p = parameters

        self.phase = 0
        self.phase_started = time.monotonic()

        self.soc = 55.0
        self.temperature = 24.0
        self.current = 0.0
        self.charge = 0.0

        # Groups differ a little, one is weaker, one sensor sits on a hot spot
        self.cell_offsets = [noise(0.1) for _ in range(CELL_VOLTAGE_COUNT)]
        self.cell_offsets[random.randrange(CELL_VOLTAGE_COUNT)] -= 0.5
        self.sensor_offsets = [noise(2.0) for _ in range(CELL_TEMPERATURE_COUNT)]
        self.sensor_offsets[random.randrange(CELL_TEMPERATURE_COUNT)] += 7

        self.resistance = [4200.0, 3900.0]   # kOhm, plus and minus

        self.fault = None
        self.fault_until = 0.0
        self.fault_object = None
        self.free_places = []

        self.setup()

    # =================================================
    # VALUES THAT DO NOT CHANGE
    # =================================================

    def setup(self):

        self.p["bus"].update(
            bitrate=CAN_BITRATE,
            port="имитация",
            state="SIMULATION",
            reserve_port="имитация",
            reserve_state="SIMULATION",
        )

        for key in HEARTBEAT_DEVICES:
            self.p[key]["nmt_state"] = "OPERATIONAL"

        # Nothing is wrong at the start
        for key, *_ in DEVICES:

            device = self.p[key]

            for name in device:

                if name.startswith(("fault.", "warn.", "internal_error.")):
                    device[name] = "OK"

            for name in ("warn", "fault"):

                if device.get(name) == NO_DATA:
                    device[name] = 0

        self.p["bune"].update(soh=92, i_chg_max=700, i_dch_max=800)
        self.p["imd"].update({"cmd.allow_work": "ALLOW", "cmd.force_selftest": "AUTO"})
        self.p["plod"].update(state="RUN", mode="LOGGING")
        self.p["cc"].update(state="RUN", mode=0)
        self.p["bem"].update(state="RUN", mode=0)
        self.p["puer"]["state"] = "RUN"
        self.p["bust_a"]["state"] = "RUN"
        self.p["bust_b"]["state"] = "RUN"

    # =================================================
    # ONE STEP
    # =================================================

    def tick(self):

        now = time.monotonic()

        state, mode, system, requested = self.step_phase(now)
        self.step_fault(now)

        self.step_storage(state, mode, system)
        self.step_converter(state, mode, requested)
        self.step_contactors(state)
        self.step_temperature()
        self.step_isolation(state)
        self.step_capacitors()
        self.step_cooling()
        self.step_summary()

    def step_phase(self, now):
        """
        State and mode of the converter, state of БУНЭ, the mode БУНЭ asks for.
        """

        state, mode, system, duration = PHASES[self.phase]

        # Stop charging / discharging early at the limits of SoC
        limit_reached = (
            (mode == "CHARGE_SET_V" and self.soc >= 97)
            or (mode == "DISCHARGE_SET_I" and self.soc <= 12)
        )

        if now - self.phase_started >= duration or limit_reached:

            self.phase += 1

            if self.phase >= len(PHASES):
                self.phase = REPEAT_FROM

            self.phase_started = now

            # The request goes out now, the converter follows on the next tick
            return state, mode, system, PHASES[self.phase][1]

        return state, mode, system, mode

    def step_fault(self, now):

        if self.fault and now >= self.fault_until:
            self.fault = None

        if self.fault is None and random.random() < FAULT_CHANCE:
            self.fault = random.choice(FAULTS)
            self.fault_until = now + random.uniform(*FAULT_DURATION)
            self.fault_object = random.randrange(CELL_TEMPERATURE_COUNT)
            self.free_places = sorted(
                random.sample(range(CELL_TEMPERATURE_COUNT), FREE_SENSORS)
            )

    def step_storage(self, state, mode, system):

        target = {
            "CHARGE_SET_V": CHARGE_CURRENT,
            "DISCHARGE_SET_I": -DISCHARGE_CURRENT,
        }.get(mode, 0)

        # Current ramps up and down, with some ripple. + charge, - discharge
        self.current += (target - self.current) * 0.3
        current = self.current + (noise(15) if target else 0)

        if not target and abs(self.current) < 1:
            current = 0.0

        voltage = STORAGE_VOLTAGE_MIN + STORAGE_VOLTAGE_SPAN * math.sqrt(self.soc / 100)

        # Energy that went in or out during the tick, in % of SoC
        power = voltage * current / 1000                       # kW
        delta = power * TICK / 3600 / STORAGE_ENERGY_MAX * 100

        if target:
            self.soc = min(100.0, max(0.0, self.soc + delta))
            self.charge += current * TICK / 3600

        self.p["bune"].update(
            state=system,
            mode=1 if target > 0 else 2 if target < 0 else 0,
            soc=round(self.soc),
        )

        self.p["bem"].update(
            i=round(current, 3),
            u=round(voltage + noise(2), 1),
            q=round(self.charge, 3),
            t=round(self.temperature),
        )

    def step_converter(self, state, mode, requested):

        bup = self.p["bup"]
        bem = self.p["bem"]

        storage_voltage = bem["u"]
        storage_current = bem["i"]
        line_voltage = LINE_VOLTAGE + noise(12)

        # Bus side current from the power balance, 97% efficiency.
        # + taken from the bus (charge), - given to the bus (discharge)
        line_current = storage_current * storage_voltage / line_voltage

        if storage_current > 0:
            line_current /= 0.97
        else:
            line_current *= 0.97

        overvoltage = self.fault == "overvoltage"
        running = state == "RUN"

        bup.update({
            "state": state,
            "mode": mode,
            "u_dc": round(line_voltage, 1),
            "u_ess": round(storage_voltage + (60 if overvoltage else 0), 1),
            "i_dc": round(line_current, 1),
            "i_ess": round(storage_current, 1),
            "fault.u_ess_high": "ALARM" if overvoltage else "OK",
            "flags.voltages_in_window": "OFF",
            "flags.dc_link_charged": "ON" if state in ("STANDBY", "RUN") else "OFF",
            "flags.pulses_enabled": "ON" if running else "OFF",
            "cmd.req_mode": requested,
            "cmd.set": {
                "CHARGE_SET_V": 950,
                "DISCHARGE_SET_I": DISCHARGE_CURRENT,
            }.get(requested, 0),
        })

    def step_contactors(self, state):

        k2 = state in ("STANDBY", "RUN")

        reserve = "WARNING" if self.fault == "reserve_bus" else "OK"

        self.p["puer"].update({
            "warn.can_res_w": reserve,
            "mode.k2": "CLOSED" if k2 else "OPENED",
            "cmd.req_mode.k2": "CLOSE" if k2 else "OPEN",
        })

    def step_temperature(self):

        # Current heats the storage, the air and the fans cool it down
        fans_on = is_running(self.p["bust_a"])
        heating = (self.current / 1000) ** 2 * 0.5
        cooling = (self.temperature - AMBIENT_TEMPERATURE) * (0.012 if fans_on else 0.006)

        self.temperature += (heating - cooling) * TICK

    def step_isolation(self, state):

        imd = self.p["imd"]

        calculated = "NOT_CALCULATED" if state == "INIT" else "CALCULATED"

        # Insulation resistance wanders around; a fault pulls it down
        for i in (0, 1):
            self.resistance[i] += noise(40)
            self.resistance[i] = min(6000.0, max(2500.0, self.resistance[i]))

        plus, minus = self.resistance

        if self.fault == "insulation":
            plus = 220 + noise(20)

        if plus < 50:
            status = "ALARM"
        elif plus < 300:
            status = "WARNING"
        else:
            status = "OK"

        imd.update(
            state="WORK",
            insulation_status=status if calculated == "CALCULATED" else "NO_DATA",
            resistance_calculated=calculated,
            resistance_plus=round(plus),
            resistance_minus=round(minus),
            bus_voltage_calculated=calculated,
            bus_voltage=round(self.p["bup"]["u_ess"] + noise(1), 1),
        )

    def step_capacitors(self):

        cc = self.p["cc"]

        group_voltage = self.p["bem"]["u"] / CELL_VOLTAGE_COUNT

        cc["cell_voltages"][:] = [
            round(group_voltage + offset + noise(0.02), 3)
            for offset in self.cell_offsets
        ]

        temperatures = [
            round(self.temperature + offset + noise(0.3), 2)
            for offset in self.sensor_offsets
        ]

        # Five sensors inside the storage, 1 °C per unit
        for i in range(1, 6):
            cc[f"t_storage_{i}"] = round(self.temperature + noise(1))

        sensor_lost = self.fault == "sensor"

        if sensor_lost:
            temperatures[self.fault_object] = NO_DATA

        # An unknown sensor takes the place of a known one, which then has
        # no data. The last of them does not know its bus either
        free = {}

        if self.fault == "free_sensors":

            for place in self.free_places:

                bus = None if place == self.free_places[-1] else temperature_sensor(place)[0]

                free[place] = (bus, temperatures[place])
                temperatures[place] = NO_DATA

        cc["cell_temperatures"][:] = temperatures

        cc["free_temperatures"].clear()
        cc["free_temperatures"].update(free)

        numbers = [value for value in temperatures if value != NO_DATA]

        cc.update({
            "warn.t_high_w": "WARNING" if max(numbers) > 60 else "OK",
            "warn.t_sens_w": "WARNING" if sensor_lost or free else "OK",
            "warn.can_res_w": "WARNING" if self.fault == "reserve_bus" else "OK",
        })

    def step_cooling(self):

        bust_a = self.p["bust_a"]
        bust_b = self.p["bust_b"]

        # Fans start above 28 °C and speed up with the temperature;
        # the shutter opens with them
        if self.temperature < 28:
            power = 0
        else:
            power = round(min(100, 30 + (self.temperature - 28) * 5))

        bust_a["cmd.fan_set"] = power

        for i in range(1, 7):
            bust_a[f"fan_{i}_fb"] = max(0, round(power + noise(2))) if power else 0

        bust_b.update({
            "cmd.conv_fan_set": power,
            "cmd.damper_set.open": "ON" if power else "OFF",
            "conv_fan_fb": max(0, round(power + noise(2))) if power else 0,
            "damper_fb.open": "ON" if power else "OFF",
            "damper_fb.closed": "OFF" if power else "ON",
        })

    def step_summary(self):
        """
        Every device answers in time; states come from summary.py,
        the same way as for the real bus.
        """

        reserve_lost = self.fault == "reserve_bus"

        for key, _, _, link_max in DEVICES:

            device = self.p[key]

            # Between two contacts: the fastest frame of the device, with jitter
            device["link"] = fastest_cycle(key) + random.randint(0, 2)

            device["link_main"] = random.randint(5, int(link_max * 0.8))
            device["link_reserve"] = (
                NO_DATA if reserve_lost else random.randint(5, int(link_max * 0.8))
            )

        update_summaries(self.p)


def fastest_cycle(device):
    """
    Shortest period of the frames the device sends, ms.
    """

    return min(
        frame["cycle_ms"]
        for frame in FRAMES.values()
        if frame["sender"] == device and "cycle_ms" in frame
    )


def is_running(bust_a):

    return isinstance(bust_a["fan_1_fb"], (int, float)) and bust_a["fan_1_fb"] > 0


def start_simulator(parameters):

    simulator = Simulator(parameters)

    simulator.tick()

    app.timer(TICK, simulator.tick)

    return simulator
