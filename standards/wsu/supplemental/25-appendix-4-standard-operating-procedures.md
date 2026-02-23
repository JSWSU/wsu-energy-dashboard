# 25-appendix-4-standard-operating-procedures

> **Title:** 25-appendix-4-standard-operating-procedures
> **Source:** WSU Facilities Services Design & Construction Standards (June 2025)
> **Category:** supplemental

---


DIVISION 25 ­ INTEGRATED AUTOMATION 25 50 00 INTEGRATED AUTOMATION FACILITY CONTROLS EXECUTION

D. EXECUTION ­ CONTINUED ­ APPENDIX 4 STANDARD OPERATING PROCEDURES

A. BAS SEQUENCE OF OPERATIONS (TYPICAL APPLICATION)

1. The following example illustrates the standards favored by WSU
Facilities Services. Specific Sequences of Operations for new construction shall be submitted and reviewed for approval by the WSU Integrated Engineering and Infrastructure Group (IEIG). Deviations from the standard operations will be reported to WSU Facilities Services Engineering by the design Engineering team with justifications for approval. The explanation and approval will both be recorded. Deviations lacking justifications will be automatically rejected.

2. Air Handling Units:
Note: Typical Air Handling unit diagrams for equipment to be used on the Washington State University Campus can be found under:
a) Appendix 9 ­ TYPICAL NON- RECIRCULATING AIR HANDLING SYSTEM
b) Appendix 10 ­RECIRCULATING AIR HANDLING SYSTEM
a. The BAS shall signal the starting sequence.
b. Warmup Cycle: Upon a start signal, in a mixed air system, the outside air and
exhaust air dampers shall remain closed and the return air dampers shall remain open and will slowly ramp into operation over a six (6) minute period allowing a controlled ease-in of operation. A reset schedule for the mixed air control loop will be based on the return or exhaust air temperature for the associated air handler unit.
i. Any variance from this standard requires specific approval from the WSU
IEIG.

ii. A typical reset schedule (mixed air system) is RA 72o MA 55o F and RA 68o
MA 65o F.
c. Pressurization and Volume Control:
i. The supply fan speed shall operate from a duct static pressure control
transmitter and a fan plenum static pressure high limit transmitter.

ii. The duct static pressure set point shall be established by the TAB and shall
be the lowest pressure required to meet airflow requirements. The duct static pressure control transmitter shall be located in a main duct, two-thirds of the total distance from the air handler.

June 22, 2021 WASHINGTON STATE UNIVERSITY

INTEGRATED AUTOMATION 25 50 00

Page 1

DIVISION 25 ­ INTEGRATED AUTOMATION 25 50 00 INTEGRATED AUTOMATION FACILITY CONTROLS EXECUTION

iii. A supply air flow monitoring station shall signal the BAS to modulate
exhaust fan speed to maintain the correct exhaust airflow. The air flow monitoring station shall be designed and installed in a location to measure the full air volume delivered by the AHU fan or blower assembly.
d. Mixed Air Operations
i. The mixed air control shall switch from economizer mode to minimum OSA
ventilation rate when the OSA temperature is above 76o F and the OSA-RA temperature difference is greater than 2o F.
ii. Use supply volume, return air temperature and outside air temperature to
calculate the mixed air set-point based on the required ventilation rate. This mixed air set-point will be a minimum ventilation rate setting in conjunction with the normal economizer control and CO2-Based Demand-controlled Ventilation or other occupancy strategy.
Example and further description:
Control scheme goals:
1. Eliminate fresh air entering the exhaust air plenum due to low mixed air plenum pressure not being counted as ventilation air.
2. Eliminate intake damper settings over driving the ventilation rate and tripping air handlers out on freezestat safeties or to avoid freezing conditions in the air handling unit.
The value of the % Required AHU Outside Air Quantity (or minimum ventilation rate) below may and probably should be adjustable related to variables like occupancy and areas that are shut down due to lack of occupancy.
i. The % Required AHU Outside Air Quantity (or minimum ventilation rate) will be set to a rate that will generally set the facility in a positive pressure state volumetrically. It will slightly exceed exhaust air, elevator shaft and other losses and will be adjustable in relation to occupancy and space requirements. Reference sample coding below:
1. % Required AHU Outside Air Quantity = (Required AHU Outside Air Quantity in CFM)/Actual AHU Supply Air Volume) (This can be overridden manually to adjust the air ventilation rate or biased by CO2 control or occupancy levels.)
2. Return Air Quantity = Actual AHU Return Air volume (or Actual AHU Supply Air Volume ­ Minimum Outside requirement. It would be best to have the Actual AHU Return Air volume.)

Page 2

June 22, 2021 WASHINGTON STATE UNIVERSITY

INTEGRATED AUTOMATION 25 50 00

DIVISION 25 ­ INTEGRATED AUTOMATION 25 50 00 INTEGRATED AUTOMATION FACILITY CONTROLS EXECUTION
3. % AHU Return Air Quantity = Return Air Quantity/ Actual AHU Supply Air Volume
4. Mixed Air Setpoint = (Return Air temperature X % AHU Return Air Quantity)+(Outside Air Temperature X % Required AHU Outside Air Quantity
5. The minimum mixed air temperature set point setting will be 55 degrees.

iii. Only the temperature low limit (described above) shall override the
pressurization volume control.

iv. The TAB contractor shall provide a minimum ventilation rate damper setting
to be used only when the OSA and return air temperature sensors measure within 1o F of each other.

v. CO2 ­ Demand ­ Controlled Ventilation control will assume a maximum
background level of 400 PPM for air handling units including individual rooms with air handling units. Outdoor CO-2 level monitoring by the control system will only be applied to high occupancy spaces that have large variations in occupancy.

vi. CO2 ­ Demand ­ Controlled Ventilation control as applied to individual
rooms with air handling units with mixed air will assume a maximum background level of 400 PPM. The control will not need to monitor outdoor CO-2 levels and will only be applied to spaces that are used at a high occupancy levels and that have in turn large variations in occupancy.

vii. The mixed air sensor shall be placed in a manner that promotes accuracy,
despite stratification. More than one sensor may be used.

viii. The mixed air temperature control shall be controlled from a temperature
sensor located beyond air filters to control mixed air directly.
e. Air Handler Coil Controls:
i. An analog temperature sensor in the discharge air stream of each coil shall
signal the BAS to modulate the preheat coil and chilled water coil valves in order to maintain the correct discharge temperature set points.

ii. The preheat coil discharge set point shall be 2o F lower than the mixed air
temperature control set point, and no lower than 52o. The preheat coil circulating pump shall start operating at a call for heating, and shall run at least 15 minutes after the call for heat has been satisfied.

Page 3

iii. The cooling set point shall be 2o F higher than the mixed air temperature
control set point. The chilled water coil circulating pump shall start

June 22, 2021 WASHINGTON STATE UNIVERSITY

INTEGRATED AUTOMATION 25 50 00

DIVISION 25 ­ INTEGRATED AUTOMATION 25 50 00 INTEGRATED AUTOMATION FACILITY CONTROLS EXECUTION
operating at a call for cooling, and shall run at least 15 minutes after the call for cooling has been satisfied.
f. Exhaust Air:
i. BAS analog temperature sensors in the inlet and discharge air streams
shall monitor the heat recovery system.
ii. Design and install an air flow monitoring station in a location to measure the
full air volume delivered by the exhaust fan or blower assembly.
iii. If fume-hoods or other safety ventilation devices are included in a combined
general exhaust, use duct static control to maintain the ventilation rates of those devices.
iv. For general exhaust (not including safety ventilation devices), modulate the
exhaust volume in sequence with the supply air volume to maintain building pressurization.
v. Designers shall make provisions for Supply Fan failure by reducing Exhaust
Air volume.
g. Heat Recovery:
i. The heat recovery set point shall be 2o higher than the mixed air set point.
ii. If the heat recovery device is located upstream of the mixed air plenum, the
heat recovery device discharge air temperature shall be accounted for in any mixed air calculations as the OSA temperature would be.
h. Freeze Stats: Low limit manual reset protecting thermostats shall be physically
wired in series in the AHU start string. If preheat discharge temperature decreases below 40o F, these thermostats shall stop the fan and close the outside air dampers. A secondary contact shall show the status of the low limit thermostat, alarming the BAS under these conditions.
i. Smoke Detection: If products of combustion are detected, duct mounted smoke
detectors shall stop the fan and close the outside air dampers. The Electrical Contractor responsible for the fire alarm system shall provide and install the necessary duct smoke detectors. Smoke detectors shall not be located in a path directly affected by steam injection or other humidification systems.
j. Boiler Hot Water Systems: These systems shall be controlled in accordance
with the boiler manufacturer's recommendations. Sequence of Operations shall not include a reset schedule through the BAS control system.
3. Heating Converter - Steam to Hot Water:

Page 4

June 22, 2021 WASHINGTON STATE UNIVERSITY

INTEGRATED AUTOMATION 25 50 00

DIVISION 25 ­ INTEGRATED AUTOMATION 25 50 00 INTEGRATED AUTOMATION FACILITY CONTROLS EXECUTION
a. An immersion temperature sensor with well in the HWS line shall signal the
BAS to modulate the 1/3 - 2/3 valve arrangements in order to maintain a reset schedule based on Outside Air Temperature.
4. VAV Terminal Boxes and Fin Tube Heaters:

a. Utilizing direct digital control, room sensors shall control VAV boxes and fin
tube radiators in sequence.
i. On a call for cooling, the VAV box damper shall modulate open. Both the
radiator and reheat coil valves shall be closed.

ii. On a call for heating, the VAV box damper shall modulate closed to
minimum position. The VAV reheat valve and fin tube shall then begin to modulate open.

iii. Occupied / unoccupied logic shall be applied. VAV reheat valve shall close
when supply fan is off.

5. Toilet and Other Exhaust Fans:

a. Exhaust fans serving toilet areas shall be start/stop/proofed and scheduled by
time of day scheduling through the BAS. Start/Stop time schedule shall be provided to Contractor by the WSU PM and will be adjustable from the WSU Controls Shop.

6. Computer Room HVAC Units:

a. BAS shall monitor and enable control packaged computer room units; alarm
and report & record any alarm/failures to WSU Facilities Services Operations Center for response.

7. 100 Percent Outside Air HVAC Systems:

a. Dampers shall be provided with an end switch on the damper blades to shut
down the fan if the outside air dampers close for any reason. Adjustment of the end switch will allow the dampers to be open 50 percent before fan shall startup.

8. Domestic and Laboratory Hot Water Heater:

a. Instantaneous water heaters shall be DDC controlled and the control valve
shall be sized and supplied by the BAS contractor. Reference the specific requirements of WSU Design Standard 23 22 00.
b. The re-circulation pump(s) shall be operated and scheduled from the BAS.
The WSU PM will provide this schedule to the BAS Contractor.

9. Snowmelt Systems:

June 22, 2021 WASHINGTON STATE UNIVERSITY

INTEGRATED AUTOMATION 25 50 00

Page 5

DIVISION 25 ­ INTEGRATED AUTOMATION 25 50 00 INTEGRATED AUTOMATION FACILITY CONTROLS EXECUTION
a. Snowmelt for all campus exterior stairs and walkways shall be single point
controlled through the WSU Facilities Services Procedures Panel. See also sections 32 17 43 26 (Electric) and 32 17 43 60 (Hydronic) Pavement Snow Melting Systems.
b. When the snowmelt system is in operation the system shall include a
notification to the dispatch sensor every 2 hours.
10. Laboratory Fume Hoods:
a. Fume hoods shall incorporate VAV function through the use of a Venturi valve.
Measuring the open area via sash position will control the fume hood volume and then setting the air volume to the value required to maintain 100 FPM; the action time will be less than 3 seconds.
b. The fume hood controller will incorporate an alarm that will indicate low / high
velocity alarms and will display the airflow in feet per minute. The alarm will be a locally audible indicated alarm, with a local silence, and will report alarm condition to the BAS Operations center.
c. The makeup air requirements will be controlled by the lab room controller to
provide the correct laboratory pressure and ventilation rates.
11. Meter systems-
All network metrics and systems listed below will be attached to both the WSU FS BAS via MSTP network and onboarded into the SkySpark system via ethernet connection to the WSU FS Meter network.Chilled Water Metering:
a. The BAS system shall query and display the following points from the building chilled water meter, accessible at the BAS Operations Center through BACnet MSTP Connection:
i. Supply and return temperature (degrees Fahrenheit) ii. Flow rate (GPM) iii. Totalized flow (gallons) iv. Instantaneous BTU value (tons) v. Totalized tons
B. Steam Metering, Pressure Monitoring, and Condensate Conductivity:
a. The BAS system shall query and display the following points from the
building steam meter, accessible at the BAS Operations Center through BACnet MSTP Connection:
i. Temperature (degrees Fahrenheit) ii. Flow rate (pounds/hour) iii. Pressure (psi)
b. The BAS system shall query and display the following points from the
building condensate meter, accessible at the BAS Operations Center:

Page 6

June 22, 2021 WASHINGTON STATE UNIVERSITY

INTEGRATED AUTOMATION 25 50 00

DIVISION 25 ­ INTEGRATED AUTOMATION 25 50 00 INTEGRATED AUTOMATION FACILITY CONTROLS EXECUTION
i. Flow rate (pounds/hour) ii. Conductivity (microOhms)
C. Heating Hot Water Metering (as it relates to the WSU BAS)
a. The BAS system shall query and display the following points from the Heating HW energy meter, accessible at the BAS Operations Center through BACnet MSTP Connection:
i. Temperature (degrees Fahrenheit) ii. Flow rate (GPM) iii. Totalized flow (gallons) iv. Instantaneous BTU value (BTU) v. Totalized BTUs
D. Domestic Water Metering (as it relates to the WSU BAS)
a. The BAS system shall query and display the following points from the building water meter(s), accessible at the BAS Operations Center through BACnet MSTP Connection:
i. Flow rate (GPM) ii. Totalized flow (gallons)
B. FIELD DEVICES
i. Provide instrumentation as required for monitoring, control or optimization functions.
ii. Temperature Sensors:
1. Digital room sensors shall have LCD display, day / night override button, and setpoint adjustment override options. The setpoint adjustment can be software limited by the automation system to limit the amount of room adjustment.
iii. Liquid Differential Pressure Transmitter:
1. Meters will be provided with a 3-way valve manifold
iv. Differential pressure:
1. Unit for fluid flow proof shall be Penn P74.
2. Unit for airflow shall be Siemens Building Technologies SW141.
v. Insertion Flow Meters shall be equal to or better than Onicon Series F-1210 or Sparling Tiger Mag FM 656):
vi. Control Valves:

Page 7

June 22, 2021 WASHINGTON STATE UNIVERSITY

INTEGRATED AUTOMATION 25 50 00

DIVISION 25 ­ INTEGRATED AUTOMATION 25 50 00 INTEGRATED AUTOMATION FACILITY CONTROLS EXECUTION
1. Steam applications: Control Valves shall be Normally Open (N/O); Fail State shall be N/O.
a. Belimo or Siemens Globe Valve with stainless steel trim.
2. Floor-level Control: Specify Siemens Pressure-Independent Control Valves (PICV); no exceptions.
3. Energy Valves: Specify ONICON, including temperature and flow sensing to calculate BTU/h, inlet and outlet temperature, delta T, and water flow rates.
4. Automatic Temperature Control Valves in water lines: Specify Siemens PressureIndependent Control Valves (PICV), sized for minimum 25% of the system pressure drop or 5 psi, whichever is less.
C. MISCELLANEOUS DEVICES
i. Current Sensing Relay:
1. Adjust the relay switch point so that the relay responds to motor operation under load as an "on" state and so that the relay responds to an unloaded running motor as an "off" state. A motor with a broken belt is considered an unloaded motor.
ii. CO2 sensors
1. Provide space or duct type as required. Outdoor units shall be provided with heater or proper temperature compensation. Provide visible display.
iii. VFD Control:
1. See Section 26 29 23 "Variable-Frequency Motor Controllers."
D. LABORATORY ROOM CONTROLLER
i. Siemens Building Technologies laboratory room controllers:
1. Room airflow tracking shall be accomplished via actual measurement of terminal unit airflow. Controllers, which track within a range of airflow's versus actual airflow setpoints shall not be acceptable.
2. Each laboratory room controller shall be specifically designed for control of laboratory temperature, (humidity and differential pressure monitoring where applicable) and room ventilation. Each controller shall be a microprocessor-based, multi-tasking, real-time digital control processor. Control sequences shall be included as part of the factory supplied software. These sequences shall be field customized by adjusting parameters such as control loop algorithm gains, temperature setpoint, alarm limits, airflow differential setpoint, and pressurization mode. Closed loop Proportional Integral Derivative (PID) control algorithms shall be used to maintain temperature and airflow offset set points.

Page 8

June 22, 2021 WASHINGTON STATE UNIVERSITY

INTEGRATED AUTOMATION 25 50 00

DIVISION 25 ­ INTEGRATED AUTOMATION 25 50 00 INTEGRATED AUTOMATION FACILITY CONTROLS EXECUTION
3. All databases and programs shall be stored in non-volatile EEPROM, EPROM and PROM memory, or a minimum of 72-hour battery backup shall be provided. All controllers shall return to full normal operation without any need for manual intervention after a power failure of unlimited duration.
ii. Alerton / Phoenix Lab Controls provided laboratory room controllers:
1. Only for use in air flow applications > 100 CFM.
2. The airflow control device shall be a microprocessor-based design and shall use closed loop control to linearly regulate airflow based on a digital control signal. The device shall generate a digital feedback signal that represents its airflow.
3. The airflow control device shall store its control algorithms in non-volatile, rewriteable memory. The device shall be able to stand-alone or to be networked with other room-level digital airflow control devices using an industry standard protocol.
4. Room-level control functions shall be embedded in and carried out by the airflow device controller using distributed control architecture. Critical control functions shall be implemented locally; no room-level controller shall be required.
5. The airflow control device shall use industry standard 24 VAC power.
6. The airflow control device shall have provisions to connect a notebook PC commissioning tool and every node on the network shall be accessible from any point in the system.
7. The airflow control device shall have built-in integral input/output connections that address fume hood control, temperature control, humidity control occupancy control, emergency control, and non-network sensors switches and control devices. At a minimum, the airflow controller shall have:
a. Three universal inputs capable of accepting 0 to 10 VDC, 4 to 20 mA, 0 to 65 K ohms, or Type 2 or Type 3 10 K ohm @ 25 degree C thermistor temperature sensors.
b. One digital input capable of accepting a dry contact or logic level signal input.
c. Two analog outputs capable of developing either a 0 to 10 VDC or 4 to 20 mA linear control signal.
d. One Form C (SPDT) relay output capable of driving up to 1 A @ 24 VAC/VAC.
8. The airflow control device shall meet FCC Part 15 Subpart J Class A, CE, and CSA Listed per file #228219.
E. VARIABLE AIR VOLUME FUME HOOD CONTROLLER
i. Siemens Building Technologies variable air volume fume hood controller:

Page 9

June 22, 2021 WASHINGTON STATE UNIVERSITY

INTEGRATED AUTOMATION 25 50 00

DIVISION 25 ­ INTEGRATED AUTOMATION 25 50 00 INTEGRATED AUTOMATION FACILITY CONTROLS EXECUTION
1. In operation, the VAV fume hood control process consists of calculating the fume hood exhaust flow necessary to provide the required average face velocity at any sash position based upon actual sash position and total fume hood open area. The controller shall then position the fume hood exhaust terminal damper to attain the required exhaust airflow in conjunction with constant feedback from an integral exhaust airflow sensor. The controller shall perform this exhaust airflow calculation ten times per second to ensure maximum speed of response to changes in sash position. Even when no change has occurred in sash position since the previous calculation, the controller shall continue to position the exhaust terminal damper in response to its airflow measurement feedback to ensure that the required fume hood exhaust is always maintained independently of variations in exhaust system static pressure or room conditions that could otherwise affect fume hood exhaust airflow.
a. The VAV fume hood controller shall initiate corrective action immediately upon sash movement and be completed when sash movement stops so as to restore the required average face velocity within 3 seconds after completion of sash movement.
b. A "Sash Alert" feature shall provide periodic beeps at the Operator Display Panel when the sash remains open above the recommended safe working height (adjustable) for an adjustable period of time. This feature shall enhance fume hood safety operation and energy efficiency. This feature shall include a beep interval and be capable of being implemented on individual fume hoods as desired by authorized owner personnel.
END OF SECTION

Page10

June 22, 2021 WASHINGTON STATE UNIVERSITY

INTEGRATED AUTOMATION 25 50 00



