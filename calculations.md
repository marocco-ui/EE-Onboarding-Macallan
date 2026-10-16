# Required calculations

Board: basic sensor interface PCB, ESP32-S3-WROOM-1 module, 5 V USB-C input, 3.3 V LDO.

All datasheet numbers are cited at the bottom.

## 1. Voltage regulator and capacitors

### Load the regulator has to supply

The ESP32-S3-WROOM-1 datasheet asks for a 3.0 V to 3.6 V supply that can deliver at least 0.5 A. Its worst-case current is Wi-Fi transmit (802.11b, 1 Mbps, 20.5 dBm):

    I_ESP(peak) = 355 mA
    I_ESP(RX)   = 95 mA

### Part chosen: Diodes Inc. AP7361C-33E-13 (3.3 V fixed LDO, SOT-223)

| Spec | Value | Why it matters |
|---|---|---|
| Output current | 1 A rated, 1.1 A min current limit | 2x the 0.5 A the module asks for |
| Input range | 2.2 V to 6.0 V (6.5 V abs max) | USB VBUS is 4.75 V to 5.25 V |
| Dropout | 90 mV typ / 140 mV max at 300 mA, 360 mV at 1 A | Plenty of headroom from 5 V |
| Quiescent current | 60 uA typ, 80 uA max | Negligible |
| Thermal resistance | 110 °C/W (SOT-223) | Sets the heat limit, see below |
| Thermal shutdown | 150 °C | Upper limit for the heat check |
| Pinout | 1 = IN, 2 = GND, 3 = OUT, tab on pin 2 | Matches KiCad footprint SOT-223-3_TabPin2 |

Why an LDO and not a buck converter: the current is under 0.5 A and the voltage drop is only 1.7 V, so the heat is manageable. An LDO is one part plus a few caps, has no switching noise near the ADC, and is easier to lay out on a 60 × 60 mm board. The cost is efficiency:

    efficiency = V_out / V_in
               = 3.3 V / 5.0 V
               = 66 %

### Dropout check

Using the 1 A dropout figure as a safe upper bound:

    V_in(min) = V_out + V_dropout
              = 3.3 V + 0.36 V
              = 3.66 V

USB VBUS minimum is 4.75 V, so there is about 1.1 V of margin.

### Heat check (worst case, Wi-Fi TX)

Total 3.3 V load at peak is 357 mA (see section 3).

    P_LDO = (V_in − V_out) × I_load
          = (5.0 V − 3.3 V) × 0.357 A
          = 0.61 W

    ΔT = P_LDO × θJA
       = 0.61 W × 110 °C/W
       = 67 °C

    T_junction = 25 °C + 67 °C
               = 92 °C

With VBUS at its 5.25 V maximum:

    P_LDO = (5.25 V − 3.3 V) × 0.357 A
          = 0.70 W

    ΔT = 0.70 W × 110 °C/W
       = 77 °C

    T_junction = 25 °C + 77 °C
               = 102 °C

Both stay under the 150 °C thermal shutdown. TX current comes in bursts, so the average will be lower. The layout gives the SOT-223 tab a copper pour to keep θJA at or below the datasheet figure.

### Capacitors

| Ref | Value | Location | Reason |
|---|---|---|---|
| C1 | 4.7 uF X5R, 10 V, 0805 | LDO input | Datasheet minimum is 1 uF ceramic, and its application circuit uses 4.7 uF. USB 2.0 limits a device to 10 uF on VBUS at plug-in. |
| C2 | 100 nF X7R, 0603 | LDO input | High-frequency bypass |
| C3 | 10 uF X5R, 10 V, 0805 | LDO output | Datasheet minimum is 2.2 uF, ceramic recommended. Larger improves the response to Wi-Fi current bursts. |
| C4 | 22 uF X5R, 10 V, 0805 | Module 3V3 pin | Local bulk for TX bursts, matching the 22 uF in Espressif's peripheral schematic |
| C5 | 100 nF X7R, 0603 | Module 3V3 pin | High-frequency bypass, per the same schematic |

Ceramic caps lose capacitance under DC bias. A 10 V rated part on a 3.3 V or 5 V rail keeps most of its value.

## 2. LED current-limiting resistor

D1 is a power indicator on the 3.3 V rail.

Part: Lite-On LTST-C191KGKT (green, 0603). Datasheet: V_F = 1.9 V min, 2.4 V max at 20 mA, 30 mA absolute max.

20 mA is far brighter than an indicator needs. Target about 2 mA, using V_F ≈ 2.0 V (V_F drops at low current).

    R = (V_supply − V_F) / I_LED
      = (3.3 V − 2.0 V) / 0.002 A
      = 650 Ω

Next standard E12 value up: 680 Ω.

Check the current across the V_F range:

    I(V_F = 1.9 V) = (3.3 V − 1.9 V) / 680 Ω
                   = 2.06 mA

    I(V_F = 2.0 V) = (3.3 V − 2.0 V) / 680 Ω
                   = 1.91 mA

    I(V_F = 2.4 V) = (3.3 V − 2.4 V) / 680 Ω
                   = 1.32 mA

All are visible and far under the 30 mA limit.

Resistor power, worst case:

    P_R = (3.3 V − 1.9 V)² / 680 Ω
        = 1.96 V² / 680 Ω
        = 2.9 mW

A 0603 resistor (1/10 W) is more than enough.

## 3. Board power consumption

Supply is 5 V from USB-C. Every load on the 3.3 V rail passes through the LDO, so input current equals the 3.3 V load plus the LDO's quiescent current.

| Load | Current |
|---|---|
| ESP32-S3-WROOM-1, Wi-Fi TX peak | 355 mA |
| ESP32-S3-WROOM-1, Wi-Fi RX | 95 mA |
| Power LED (D1) | 1.9 mA |
| Sensor divider (R5 + R6) | 3.3 V / 40 kΩ = 0.08 mA |
| LDO quiescent (max) | 0.08 mA |
| Button or BOOT pull-up (only while pressed) | 3.3 V / 10 kΩ = 0.33 mA |

The external sensor's own current is not included because it is unknown. Add it once a sensor is chosen.

### Worst case (Wi-Fi transmitting)

    I_in = 355 + 1.9 + 0.08 + 0.08 mA
         = 357 mA

    P_in = 5.0 V × 0.357 A
         = 1.79 W

### Typical (Wi-Fi connected, receiving)

    I_in = 95 + 1.9 + 0.08 + 0.08 mA
         = 97 mA

    P_in = 5.0 V × 0.097 A
         = 0.49 W

A standard USB 2.0 port supplies 500 mA, so the board fits with 143 mA of margin at worst case.

## 4. Trace widths

IPC-2221 current capacity for an outer-layer trace, 1 oz copper (1.378 mil thick), 10 °C allowed rise:

    I = k × ΔT⁰·⁴⁴ × A⁰·⁷²⁵
    k = 0.048 (outer layer),  ΔT in °C,  A in mil²

Power class, 0.4 mm (15.75 mil):

    A = 15.75 mil × 1.378 mil
      = 21.7 mil²

    I = 0.048 × 10⁰·⁴⁴ × 21.7⁰·⁷²⁵
      = 0.048 × 2.754 × 9.31
      = 1.23 A

Ground class, 0.3 mm (11.81 mil):

    A = 11.81 mil × 1.378 mil
      = 16.3 mil²

    I = 0.048 × 2.754 × 7.55
      = 1.0 A

Worst-case load is 357 mA (section 3), so 0.4 mm has 3.4 times margin and 0.3 mm has 2.8 times margin. Ground mostly returns through the bottom pour, so the 0.3 mm ground tracks are only short stubs to vias.

## Supporting values

ADC input divider. The ESP32-S3 ADC reads 0 to 3.1 V at its highest attenuation, so a 3.3 V signal would clip without scaling:

    V_ADC = V_sensor × R6 / (R5 + R6)
          = 3.3 V × 30 kΩ / (10 kΩ + 30 kΩ)
          = 2.475 V

That leaves 0.6 V of margin below the 3.1 V limit for resistor tolerance and sensor overshoot.

ADC filter corner (Thevenin resistance of the divider with C7 = 100 nF):

    R_th = R5 × R6 / (R5 + R6)
         = (10 kΩ × 30 kΩ) / 40 kΩ
         = 7.5 kΩ

    f_c = 1 / (2π × R_th × C7)
        = 1 / (2π × 7500 Ω × 100 nF)
        = 212 Hz

Button debounce (R7 = 10 kΩ, C8 = 100 nF):

    τ = R7 × C8
      = 10 kΩ × 100 nF
      = 1 ms

EN power-on delay (R1 = 10 kΩ, C6 = 1 uF, the values Espressif recommends):

    τ = 10 kΩ × 1 uF
      = 10 ms

## Sources

- ESP32-S3-WROOM-1 datasheet (Espressif): https://documentation.espressif.com/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf
- ESP-IDF ADC docs, ESP32-S3: https://docs.espressif.com/projects/esp-idf/en/v4.4.5/esp32s3/api-reference/peripherals/adc.html
- AP7361C datasheet (Diodes Inc., DS37274): https://static.chipdip.ru/lib/709/DOC017709829.pdf
- LTST-C191KGKT datasheet (Lite-On): https://docs.rs-online.com/18fd/0900766b80dc02b1.pdf
- IPC-2221 trace width formula and constants (NextPCB summary): https://www.nextpcb.com/blog/pcb-trace-width-calculator-ipc-2221-guide
