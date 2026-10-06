"""Debug mode: imitates a working energy storage by changing PARAMETERS.

Started with `python app/main.py --debug`. The model is simple but keeps the
values consistent with each other:

- the converter (БУП) goes through its states: init -> precharge -> idle ->
  charge -> idle -> discharge -> idle -> ...; БУНЭ requests every mode
  first, the converter follows on the next tick;
- SoC, storage voltage, currents, cell voltages follow the charge;
- current heats the cells, fans and shutters (СО) react to the temperature;
- every device answers with its states and link times;
- now and then a fault shows up and clears by itself: low insulation,
  converter overvoltage, a lost temperature sensor.
"""

import math
import random
import time

from nicegui import app

from parameters import DEVICES, NO_DATA
from settings import (
    CAN_BITRATE,
    CELL_TEMPERATURE_COUNT,
    CELL_VOLTAGE_COUNT,
)
from summary import update_summaries

# Seconds between two steps of the model
TICK = 0.5

# Converter states and how long they last, s.
# After the start-up the list repeats from REPEAT_FROM.
PHASES = [
    ("DC_INIT", 3),
    ("DC_PRECHARGE", 5),
    ("DC_IDLE", 8),
    ("DC_CHARGE", 45),
    ("DC_IDLE", 8),
    # Shorter than the charge: the discharge current is higher
    ("DC_DISCHARGE", 35),
]
REPEAT_FROM = 2

STORAGE_ENERGY_MAX = 19.5     # kWh
STORAGE_VOLTAGE_MIN = 560     # V at SoC 0
STORAGE_VOLTAGE_SPAN = 400    # V from SoC 0 to SoC 100
LINE_VOLTAGE = 780            # V, input of the converter
CHARGE_CURRENT = 600          # A
DISCHARGE_CURRENT = 780       # A
AMBIENT_TEMPERATURE = 22      # °C

# Chance per tick that a fault starts, and how long it lasts, s
FAULT_CHANCE = 1 / 200
FAULT_DURATION = (6, 15)
FAULTS = ("insulation", "overvoltage", "sensor")


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
        self.cycles = 1530
        self.charged = False

        # Cells differ a little, one is weaker, one sensor sits on a hot spot
        self.cell_offsets = [noise(0.2) for _ in range(CELL_VOLTAGE_COUNT)]
        self.cell_offsets[random.randrange(CELL_VOLTAGE_COUNT)] -= 0.8
        self.sensor_offsets = [noise(2.0) for _ in range(CELL_TEMPERATURE_COUNT)]
        self.sensor_offsets[random.randrange(CELL_TEMPERATURE_COUNT)] += 7

        self.resistance = [4200.0, 3900.0]   # kOhm, plus and minus

        self.fault = None
        self.fault_until = 0.0
        self.fault_object = None

        self.setup()

    # =================================================
    # VALUES THAT DO NOT CHANGE
    # =================================================

    def setup(self):

        self.p["bus"].update(
            source="simulation",
            bitrate=CAN_BITRATE,
            state="SIMULATION",
        )

        bune = self.p["bune"]

        bune.update(
            imd_allow_work="ALLOW",
            imd_force_selftest="AUTO",
            imd_alarm_resistance=50,
            imd_warning_resistance=300,
            cc_data_request="FULL_PARSING",
            cc_frame_request=0,
            soh=91.7,
            storage_energy_max=STORAGE_ENERGY_MAX,
        )

        self.p["imd"].update(
            imd_status="WORKING",
            low_bus_voltage_error="OK",
            timeout_error="OK",
            anomaly_error="OK",
            self_test_error="OK",
        )

        self.p["cc"].update(
            cell_overvoltage="OK",
            cell_undervoltage="OK",
            cell_overcooling="OK",
            voltage_sensor_connection="OK",
        )

        self.p["bup"].update(
            dc_undervoltage="OK",
            dc_overcurrent="OK",
            dc_igbt_driver_error="OK",
        )

    # =================================================
    # ONE STEP
    # =================================================

    def tick(self):

        now = time.monotonic()

        mode, requested = self.step_phase(now)
        self.step_fault(now)

        self.step_storage(mode)
        self.step_converter(mode, requested)
        self.step_temperature()
        self.step_isolation(mode)
        self.step_capacitors()
        self.step_cooling()
        self.step_summary()

    def step_phase(self, now):
        """
        Current converter mode and the mode БУНЭ asks for.
        """

        name, duration = PHASES[self.phase]

        # Stop charging / discharging early at the limits of SoC
        limit_reached = (
            (name == "DC_CHARGE" and self.soc >= 97)
            or (name == "DC_DISCHARGE" and self.soc <= 12)
        )

        if now - self.phase_started >= duration or limit_reached:

            if name == "DC_CHARGE":
                self.charged = True

            # A full cycle: charged, then discharged
            if name == "DC_DISCHARGE" and self.charged:
                self.cycles += 1
                self.charged = False

            self.phase += 1

            if self.phase >= len(PHASES):
                self.phase = REPEAT_FROM

            self.phase_started = now

            # The request goes out now, the converter follows on the next tick
            return name, PHASES[self.phase][0]

        return name, name

    def step_fault(self, now):

        if self.fault and now >= self.fault_until:
            self.fault = None

        if self.fault is None and random.random() < FAULT_CHANCE:
            self.fault = random.choice(FAULTS)
            self.fault_until = now + random.uniform(*FAULT_DURATION)
            self.fault_object = random.randrange(CELL_TEMPERATURE_COUNT)

    def step_storage(self, mode):

        bune = self.p["bune"]

        target = {
            "DC_CHARGE": CHARGE_CURRENT,
            "DC_DISCHARGE": DISCHARGE_CURRENT,
        }.get(mode, 0)

        # Current ramps up and down, with some ripple
        self.current += (target - self.current) * 0.3
        current = max(0.0, self.current + (noise(15) if target else 0))

        voltage = STORAGE_VOLTAGE_MIN + STORAGE_VOLTAGE_SPAN * math.sqrt(self.soc / 100)

        # Energy that went in or out during the tick, in % of SoC
        power = voltage * current / 1000                       # kW
        delta = power * TICK / 3600 / STORAGE_ENERGY_MAX * 100

        if mode == "DC_CHARGE":
            self.soc = min(100.0, self.soc + delta)
        elif mode == "DC_DISCHARGE":
            self.soc = max(0.0, self.soc - delta)

        contactors = "OPEN" if mode == "DC_INIT" else "CLOSED"

        bune.update(
            soc=round(self.soc, 1),
            storage_energy=round(STORAGE_ENERGY_MAX * self.soc / 100, 1),
            voltage=round(voltage + noise(2), 1),
            current=round(current, 1),
            cycles=self.cycles,
            contactor1=contactors,
            # The second contactor closes after the precharge
            contactor2="OPEN" if mode in ("DC_INIT", "DC_PRECHARGE") else "CLOSED",
            converter_contactor=contactors,
        )

    def step_converter(self, mode, requested):

        bup = self.p["bup"]
        bune = self.p["bune"]

        storage_voltage = bune["voltage"]
        line_voltage = LINE_VOLTAGE + noise(12)

        # Line side current from the power balance, 97% efficiency
        storage_current = bune["current"]
        line_current = storage_current * storage_voltage / line_voltage

        if mode == "DC_CHARGE":
            line_current /= 0.97
        else:
            line_current *= 0.97

        overvoltage = self.fault == "overvoltage"

        bup.update(
            dc_status=mode,
            dc_input_voltage=round(line_voltage),
            dc_output_voltage=round(storage_voltage + (60 if overvoltage else 0)),
            dc_input_current=round(line_current),
            dc_output_current=round(storage_current),
            dc_overvoltage="ALARM" if overvoltage else "OK",
            dc_error_none="NO" if overvoltage else "YES",
        )

        bune.update(
            bup_requested_mode=requested,
            bup_target_voltage={
                "DC_CHARGE": 950,
                "DC_DISCHARGE": 650,
            }.get(requested, round(storage_voltage)),
        )

    def step_temperature(self):

        bune = self.p["bune"]
        so = self.p["so"]

        # Current heats the storage, the air and the fans cool it down
        fans_on = is_running(so)
        heating = (self.current / 1000) ** 2 * 0.5
        cooling = (self.temperature - AMBIENT_TEMPERATURE) * (0.012 if fans_on else 0.006)

        self.temperature += (heating - cooling) * TICK

        bune["temperature"] = round(self.temperature + noise(0.2), 1)

    def step_isolation(self, mode):

        imd = self.p["imd"]
        bup = self.p["bup"]

        calculated = "NOT" if mode == "DC_INIT" else "YES"

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
            insulation_status=status if calculated == "YES" else "NO_DATA",
            resistance_calculated=calculated,
            resistance_plus=round(plus),
            resistance_minus=round(minus),
            bus_voltage_calculated=calculated,
            bus_voltage=round(bup["dc_output_voltage"] + noise(1), 1),
        )

    def step_capacitors(self):

        cc = self.p["cc"]
        bune = self.p["bune"]

        # 1 V and 1 °C per unit in the 0x297 frames, so whole numbers
        cell_voltage = bune["voltage"] / CELL_VOLTAGE_COUNT

        cc["cell_voltages"][:] = [
            round(cell_voltage + offset + noise(0.1))
            for offset in self.cell_offsets
        ]

        temperatures = [
            round(self.temperature + offset + noise(0.3))
            for offset in self.sensor_offsets
        ]

        sensor_lost = self.fault == "sensor"

        if sensor_lost:
            temperatures[self.fault_object] = NO_DATA

        cc["cell_temperatures"][:] = temperatures

        numbers = [value for value in temperatures if value != NO_DATA]
        voltages = cc["cell_voltages"]

        disbalance = max(voltages) - min(voltages) >= 3
        overheat = max(numbers) > 60

        cc.update(
            cell_disbalance="ALARM" if disbalance else "OK",
            cell_overheat="ALARM" if overheat else "OK",
            temperature_sensor_connection="ALARM" if sensor_lost else "OK",
        )

        if sensor_lost:
            cc.update(
                event_type="TEMPERATURE_SENSOR_CONNECTION",
                event_source="TEMPERATURE_SENSORS",
                event_object=self.fault_object + 1,
            )

        alarms = disbalance or overheat or sensor_lost
        cc["cc_status"] = "WARNING" if alarms else "OK"

    def step_cooling(self):

        so = self.p["so"]

        # Fans start above 28 °C and speed up with the temperature
        if self.temperature < 28:
            speed = 0
        else:
            speed = min(3000, 900 + (self.temperature - 28) * 150)

        for i in range(1, 7):
            so[f"fan{i}_rpm"] = round(speed + noise(25)) if speed else 0

        so["shutters"] = "OPEN" if speed else "CLOSED"

    def step_summary(self):
        """
        Every device answers in time; states come from summary.py,
        the same way as for the real bus.
        """

        for key, _, _, link_max in DEVICES:
            self.p[key]["link"] = random.randint(5, int(link_max * 0.8))

        update_summaries(self.p)


def is_running(so):

    return isinstance(so["fan1_rpm"], (int, float)) and so["fan1_rpm"] > 0


def start_simulator(parameters):

    simulator = Simulator(parameters)

    simulator.tick()

    app.timer(TICK, simulator.tick)

    return simulator
