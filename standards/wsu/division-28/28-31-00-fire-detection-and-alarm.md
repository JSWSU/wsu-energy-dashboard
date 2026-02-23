# CSI 28 31 00 - Fire Detection and Alarm

> **Division:** 28
> **CSI Code:** 28 31 00
> **Title:** Fire Detection and Alarm
> **Date:** 1-8-16
> **Source:** WSU Facilities Services Design & Construction Standards (June 2025)

---

DIVISION 28 ­ ELECTRONIC SAFETY AND SECURITY 28 31 00 FIRE DETECTION AND ALARM

PART 1 - GENERAL
1.01 SCOPE
A. Background: Washington State University has agreements with SimplexGrinnell and Siemens Industry, Inc. to provide Fire Detection and Alarm (FDA) systems for the WSU Pullman Campus. As such, the Consultants shall retain Simplex-Grinnell or Siemens Industry, Inc. to design and provide the complete coordinated FDA system as described in this section.
B. Fire Detection and Alarm Monitoring Network:
1. Buildings on the Pullman campus are monitored by a Simplex 4120 FDA Network or a Siemens XLS Network.
2. Provide communications in the Fire Alarm Control Panel (FACP) for connection to the appropriate fire alarm network. Provide all network components for a complete peer-to-peer token ring style connection, viewable from a proprietary UL-listed Graphical Command Center.
3. Provide connection to the campus Simplex 4120 Network or Siemens XLS Network in a dedicated 1-inch conduit from the FACP to the building's MDF room, using one of the following methods:
i. Two #22 twisted shielded pair cables (up to 500 ft inter-building cable provided by WSU)
ii. Four strands 62.5/125 multimode optical fiber red-jacketed cable (with ST connectors at the FACP end and SC connectors at the MDF end)
iii. Two strands single mode fiber red-jacketed cable (per Telecommunications Specifications)
4. Programming of the network, central reporting to Whitcom, the fire alarm Graphical Command Center, and the fire alarm network system shall be updated to include each new fire alarm system. FDA system record drawing floor plans shall be visible at the Graphical Command Center(s).
C. System Description:
1. Systems may include but not be limited to:
i. FACP
ii. Manual pull stations
iii. Automatic fire detectors
iv. Speaker/strobes for voice annunciation

JANUARY 8, 2016 WASHINGTON STATE UNIVERSITY

FIRE DETECTION AND ALARM 28 31 00

DIVISION 28 ­ ELECTRONIC SAFETY AND SECURITY 28 31 00 FIRE DETECTION AND ALARM
v. Remote annunciator panel
vi. Remote microphone
vii. Remote control devices
2. Use closed loop initiating device circuits with individual zone supervision, indicating appliance circuit supervision and incoming and standby power supervision as required.
3. Provide a system that communicates with all initiating and control devices individually over a signaling line circuit. Annunciate all initiating and control devices individually at the FACP. Include the following annunciation conditions for each point:
i. Alarm
ii. Trouble
iii. Short
iv. Ground
v. Device Fail or Incorrect Device
4. Configure all devices to allow for the addition of devices on circuit after the initial installation.
5. Provide 25% spare capacity for all addressable circuits and 25% spare capacity on all notification circuits.
6. Provide a system capable of multi-dropping up to 250 addressable devices in any combination of device types from a single pair of wires. Provide 25% spare capacity for all addressable circuits and 25% spare capacity on all indicating circuits.
7. Provide a system capable of having software programming modified and initiating or control devices added or deleted in the field. Systems that require factory reprogramming to add or delete devices are unacceptable.
8. Provide a system with a completely digital, poll/response protocol communications format. System is to use parity data bit error-checking routines for address codes and check sum routines for the data transmission protocol to achieve a high degree of communication reliability. Systems that do not utilize full digital transmission protocol (i.e., that may use time pulse width methods) to transmit data are not acceptable.

JANUARY 8, 2016 WASHINGTON STATE UNIVERSITY

FIRE DETECTION AND ALARM 28 31 00

DIVISION 28 ­ ELECTRONIC SAFETY AND SECURITY 28 31 00 FIRE DETECTION AND ALARM
9. Provide a system where each addressable device is uniquely identified by an address code.
10. Provide a system capable of supporting up to 10,000 feet wire length of 18 AWG or smaller for each initiating circuit loop, or for each signaling line circuit.
D. Allow for loading or editing special instructions and operating sequences in the FACP as required. Provide a system capable of onsite programming to accommodate and facilitate expansion, building parameter changes or changes as required by the Owner, authorities having jurisdiction and code requirements. Provide storage for all fire alarm system software operations in a non-volatile, programmable memory within the FACP. Loss of primary and secondary power will not erase the instructions stored in memory.
E. Incorporate in the resident software programming of the system the full ability for selective input/output control functions based on ANDing, ORing, NOTing, timing and special coded operations, logical operations involving lists of points, and unlimited grouping of input and output points. The resident software shall support two separate operating programs. Only one program shall be operable at one time.
1.02 SUPERVISION
A. Provide an addressable Fire Detection and Alarm (FDA) system with Class "B" independently supervised initiating circuits. As such, a fault in any one zone (or device) shall not affect any other zone (or device) and an alarm activation of any initiating circuit shall not prevent the subsequent alarm operation of any other initiating circuit.
B. Provide sprinkler supervisory initiation device circuits for connection of all sprinkler valve tamper switches. These circuits shall be clearly labeled as Supervisory Service.
C. Provide independently supervised and independently fused indicating appliance circuits for horn (or speaker) and strobe devices.
D. Provide supervision of all auxiliary manual controls so that all switches must be returned to their normal automatic position to clear a system trouble.
E. Provide unique FACP readouts for each independently supervised circuit to indicate disarrangement conditions per circuit.
F. Provide supervision of the incoming power to the system so that any power failure will be audibly and visually indicated at the FACP. A green "power on" LED shall be displayed continuously while incoming power is present.

JANUARY 8, 2016 WASHINGTON STATE UNIVERSITY

FIRE DETECTION AND ALARM 28 31 00

DIVISION 28 ­ ELECTRONIC SAFETY AND SECURITY 28 31 00 FIRE DETECTION AND ALARM
1. Provide supervision of the system batteries so that a low battery condition or disconnection of the battery will be audibly and visually indicated at the FACP.
2. Provide supervision of any system expansion modules for module placement. In the event a module becomes disconnected from the controls, the system trouble indicator shall illuminate and audible trouble signal shall sound.
3. Provide a unique Annunciator trouble readout, illuminated LED and sound an audible trouble signal at the FACP upon the detection of an open or ground connection.
4. Provide discrete trouble panel readout per output circuit for indication. Provide indication of a common ground trouble on the FACP in the presence of a ground condition of the air handling control output wiring.
5. Provide supervision of all module LEDs for burnout or disarrangement conditions. In the event of burnout or disarrangement the FACP shall display the module and the LED location numbers.
1.03 POWER REQUIREMENTS
A. Provide 120 VAC power via a dedicated circuit to the Fire Alarm Control Panel. Use a branch circuit from Feeder 13/EB-13 where available.
B. Provide battery backup to the system with sufficient capacity to operate the entire system upon loss of normal power in supervisory mode for a period of twenty-four (24) hours followed by fifteen (15) minutes of alarm operation at full output load. The system shall automatically transfer to backup power upon primary power failure. All battery charging and recharging operations shall be automatic.
C. Provide DC power from the FACP to all circuits requiring system operating power. Each circuit shall be individually fused and supervised by the FACP.
D. Coordinate any and all communications, addressable, SCU/RCU, initiating, indicating and signaling lines (including shields) extending beyond the main structure of the facility to be installed with Isolated Loop Circuit Protectors (ICLP).
E. All doors held open by door control devices shall release upon loss of normal power after a thirty (30) second delay.
F. Fire/Smoke dampers shall be on the same power source as their associated air handler and monitored for position (i.e., the same WSU feeder or same Avista feeder).

JANUARY 8, 2016 WASHINGTON STATE UNIVERSITY

FIRE DETECTION AND ALARM 28 31 00

DIVISION 28 ­ ELECTRONIC SAFETY AND SECURITY 28 31 00 FIRE DETECTION AND ALARM
G. Furnish and install Simplex #2081-9028, #2081-9044, or Siemens HLIM Isolated Loop Circuit Protectors (ICLP) on all communication, addressable, initiating, indicating, and signaling lines, including shields, on all circuits that extend beyond the building by any means.
H. Provide a single connection to the WSU Building Automation System (BAS). The connection shall provide an indication of the alarm status of the fire alarm system.
1.04 DESIGN REQUIREMENTS
A. General:
1. Design for selective detection coverage at the following locations at a minimum (in addition to requirements of NFPA 72): means of egress, Electrical Closets/Rooms, Telecommunications Closets/Rooms, Custodial Closets, conference rooms and places of assembly (500 SF and larger), rooms housing electrical power distribution equipment, and top of stairwells.
i. Detection coverage is generally not required in laboratories. Discuss lab detection requirements with WSU Project Manager and Engineering Services.
ii. Design selective coverage to minimize requirements for in-ceiling duct smoke detectors. These are expensive to inspect and maintain; WSU prefers to minimize these where possible.
2. Individual bypass switches located at the main control panel shall provide a bypass for each type of controlled device to accommodate testing with minimal interruptions. WSU Facilities Services personnel must be able to perform comprehensive system tests with minimum disruption to facility occupants.
3. The Fire Alarm Control Panel (FACP) shall be addressable with analog sensor and remote station monitoring capability.
4. The FDA system shall include voice notification with manual override.
i. The alarm signal shall consist of the selected alarm tone for 10 seconds followed by a custom message set selected by WSU. At the end of the voice message, the alarm tone shall resume.
5. For renovation projects, provide devices compatible with the existing system and listed to function as a single networked system. When a system cannot be expanded, provide and install a new FACP for the entire facility.

JANUARY 8, 2016 WASHINGTON STATE UNIVERSITY

FIRE DETECTION AND ALARM 28 31 00

DIVISION 28 ­ ELECTRONIC SAFETY AND SECURITY 28 31 00 FIRE DETECTION AND ALARM
6. Where a fire command center is not required by code, the FACP, extender panels, terminal cabinets, etc. shall generally be located in the Electrical Room. FACP installation in the building Telecommunications Room requires specific approval from the WSU PM and Information Technology Services (ITS).
B. Remote Annunciator:
1. If a Remote Annunciator is required it shall be provided at the main fire department entrance to the building.
C. Circuit and Raceway:
1. Raceway layout shall consist of at least one vertical riser of terminal cabinets located on each floor.
2. Circuits shall be laid out to serve a specific geographical area, smoke control zone or floor.
3. Where appropriate, field-located transponders and power supply panels are acceptable.
4. Regardless of code exceptions, the FDA System shall be designed with all wire in raceway appropriate for the application.
D. Smoke Detection:
1. Smoke detectors shall be located a minimum of 3 feet away from any HVAC diffuser or return.
E. Heat Detection:
1. Heat detection is preferred in lieu of smoke detection in certain dirty environments where allowed by code such as: exit stairs, laboratories, kitchens, mechanical rooms, janitor closets, elevator control rooms and elevator shafts.
F. Auxiliary Controls:
1. Coordinate auxiliary controls for fans, smoke dampers, fire suppression systems, elevator and door control with other divisions. Include all necessary components and relays to make a fully operational system.
2. For campus consistency the preferred method of fan control is from the FACP via addressable relay modules located within three (3) feet of the fan control. For low voltage/low current the addressable relay module may perform the control function. For switching higher voltage (120VAC)

JANUARY 8, 2016 WASHINGTON STATE UNIVERSITY

FIRE DETECTION AND ALARM 28 31 00

DIVISION 28 ­ ELECTRONIC SAFETY AND SECURITY 28 31 00 FIRE DETECTION AND ALARM
an interposing MR101 shall be included between the module and the magnetic starter.
3. Fire smoke dampers shall be controlled from the FACP via one addressable relay with the sensing input to monitor open and closed end switches operated by the damper blades.
4. Power for damper actuators shall not be provided from the FACP. Dedicated 120 volt circuits (minimum of one per floor) shall be provided to power the fire/smoke dampers. These circuits shall be labeled in the panel boards as damper power and identify the area served.
5. Damper interface from the FACP may include a thirty (30) second delay programmed into the FACP to allow the fans to cease rotation before closing the dampers.
6. Exterior waterflow bells shall be 24 VDC supervised and powered by the FDA system.
7. Coordinate door hold open requirements with the Project Architect. All door hold open devices shall release on a general alarm. Door holders shall be powered from a dedicated 120 VAC circuit(s) and shall be labeled as door holder circuits in the panel. The corridor smoke detection system shall provide the code required detection for the door holder operation.
8. FDA circuits and four (4) supervised relays shall be supplied to each elevator control room, and other modules necessary for elevator acceptance.
G. Fan Control:
1. Dedicated fans in lieu of environmental fans for smoke control are preferred particularly for elevator and stair shaft pressurization and atriums. These fans shall be controlled by the FACP.
2. When environmental fans are used for smoke control, the Building Automation System (BAS) shall be listed for that purpose. Consult with the WSU Project Manager as early as possible during the design phase to identify design options.
3. Where the alarm indicator on any duct smoke detector is not readily visible from the floor, a remote test and indicator for that detector shall be installed at a minimum of five (5) feet and a maximum of six (6) feet above the finish floor height.
H. Fire Smoke Damper Control:

JANUARY 8, 2016 WASHINGTON STATE UNIVERSITY

FIRE DETECTION AND ALARM 28 31 00

DIVISION 28 ­ ELECTRONIC SAFETY AND SECURITY 28 31 00 FIRE DETECTION AND ALARM
1. Provide an addressable relay which by the use of multiple end-of-line resistors is capable of monitoring the change of state of two separate switches and which also provides a built-in Form C relay capable of operating the damper motor.
2. Provide one (1) such device for each fire/smoke damper.
1.05 QUALITY ASSURANCE
A. All items of the Fire Alarm System shall be listed under the appropriate category by Underwriters Laboratories, Inc. (UL) and bearing the "UL" label. Provide control equipment that is all listed under UL category UOJZ as a single control unit including voice notification.
B. Provide Fire Alarm System components that are the products of a single manufacturer (independent dealers and/or distributors will NOT be considered). The manufacturer must have engaged in the production of this type of equipment (software driven) for at least 10 years, and have a fully equipped service organization within one hundred (100) miles of this installation. The supplier's technicians performing the panel terminations, programming, startup, checkout, and acceptance testing shall be factory trained and certified to perform such activities. This individual must possess at a minimum Level II certification from NICET in the Fire Alarm System field.
C. Provide system controls that are UL listed for Power Limited Applications per NEC 760 (latest adopted edition).
D. Provide transient protection devices on all control equipment to comply with current and adopted UL864 requirements.
E. Additional transient protection must be provided for each circuit, where fire alarm circuits leave the building. Provide devices that are UL listed under Standard 497B (Isolated Loop Circuit Protectors).
PART 2 - PRODUCTS
2.01 FACP
A. With Voice Annunciation:
1. Simplex 4100ES/4120
2. Siemens FireFinder XLSV
B. Special Hazard Suppression Systems: Wherever possible, operate through the main building FACP. Where special hazard suppression system panels are required, use one of the following:

JANUARY 8, 2016 WASHINGTON STATE UNIVERSITY

FIRE DETECTION AND ALARM 28 31 00

DIVISION 28 ­ ELECTRONIC SAFETY AND SECURITY 28 31 00 FIRE DETECTION AND ALARM
1. Simplex 4004R Suppression Release Panel 2. Siemens FireFinder XLS 3. Siemens TXR-320 2.02 REMOTE ANNUNCIATOR A. Simplex #4603-9101. Two line LCD display. B. Simplex #4100-9403, Sixteen line InfoAlarm Display C. Siemens SSD-C D. Siemens PMI-2 2.03 REMOTE MICROPHONE A. Simplex #4003-9803 B. Simplex Remote Microphone cabinet shall be Space Age YM9067 w/46039101 or Space Age YM9324 w/4100-9403 InfoAlarm annunciator. C. Siemens LVM D. Siemens Remote Microphone cabinet shall be SSD-REM2 or SSD-REM4 2.04 ADDRESSABLE DEVICES A. Sensor Bases: 1. Simplex #4098-9792 ("E" for high humidity applications) 2. Siemens DB-11 B. Smoke Detectors: 1. Simplex #4098-9714 2. Siemens FDO421 C. Heat Detectors: 1. Simplex #4098-9733 ("E" for high humidity applications) 2. Siemens FDT421 D. Pull Stations:

JANUARY 8, 2016 WASHINGTON STATE UNIVERSITY

FIRE DETECTION AND ALARM 28 31 00

DIVISION 28 ­ ELECTRONIC SAFETY AND SECURITY 28 31 00 FIRE DETECTION AND ALARM

1. Simplex #4099-9006

2. Siemens HMS-D

E. Duct Detectors:
1. Simplex #4098-9755 with TrueAlarm Smoke Sensor #4098-9714 internal to unit
2. Siemens FDBZ492-HR with FDO421 smoke detector

F. Single Input Module (IAM):

1. Simplex #4090-9001 2. Siemens HTRI-S G. Input/Output (I/O) Module: 1. Simplex Monitor IAM #4090-9101 2. Simplex Relay IAM #4090-9002

3. Simplex Relay IAM, High Current 4090-9008 4. Simplex 4-20ma AMZ #4190-9050 5. Siemens HTRI-R 6. Siemens HTRI-D H. Relay IAM with T-Sense Input:

1. Simplex #4090-9118

2. Siemens FDCIO422 2.05 FIRE SMOKE DAMPER ACTUATORS
A. See section 23 30 00 "HVAC Air Distribution." 2.06 PERIPHERAL DEVICES

A. General:

1. Install audio and visual signals on a common housing. Use 5-Square box and appropriate extension ring as manufactured by RANDL Industries, Inc. for flush mount installations and Wheelock SBB-R Backbox for surface mount installations.

JANUARY 8, 2016 WASHINGTON STATE UNIVERSITY

FIRE DETECTION AND ALARM 28 31 00

DIVISION 28 ­ ELECTRONIC SAFETY AND SECURITY 28 31 00 FIRE DETECTION AND ALARM
B. Horn/Strobes: 1. Wheelock Model #HSR 2. Simplex Model 49AV-24xxx 3. Siemens series ZH
C. Speaker/Strobes: 1. Wheelock Model ET70-24MCW-FR or 2. Wheelock ET90-24MCC-FW, multi-candela or 3. Simplex addressable speaker strobes #4906-92xx 4. Siemens Series SET
D. Visual Flashing Lamps: 1. Wheelock STR, multi-candela 2. Simplex Model 49VO-24xxx 3. Siemens Series ZR
E. Sprinkler System Water Flow Switches: 1. Equipment furnished & installed by Division 21.
F. Sprinkler System Valve Tamper and Low Air Pressure Supervisory Switches: 1. Equipment furnished & installed by Division 21.
G. Magnetic Door Holders: 1. Simplex 120VAC Model #2088-9608 Semi Flush Mounting with Long Catch Plate or approved equivalent 2. Siemens 120VAC SDH Series or approved equivalent
H. Fire Detection and Alarm Auxiliary Relay: 1. Simplex #2088-9008 and #2088-9010 2. Space Age Electronics MR 100 and 200 series relays

JANUARY 8, 2016 WASHINGTON STATE UNIVERSITY

FIRE DETECTION AND ALARM 28 31 00

DIVISION 28 ­ ELECTRONIC SAFETY AND SECURITY 28 31 00 FIRE DETECTION AND ALARM
PART 3 - EXECUTION
3.01 ACCEPTABLE FIRE ALARM VENDORS
A. Simplex Grinnell
B. Siemens Industry Inc.
3.02 INSTALLATION
A. For any circuit that extends beyond the building by any means furnish and install Isolated Loop Circuit Protectors (ICLP) including shields.
B. Surface mount all fire alarm terminal cabinets on wall with top at 60 inches above finish floor.
C. Smoke detection devices shall be installed a minimum of three (3) feet away from any HVAC diffuser or return.
D. Synchronize visual notification Horn or Speaker/Strobe installations where two (2) or more devices are in the line of sight.
E. Provide fire alarm system supervision of all 24VDC circuits.
F. Mounting:
1. Mount FDA equipment on recessed boxes in finished spaces. In back-ofhouse spaces FDA equipment may be surface mounted.
2. To avoid contamination during construction mount FDA components after all interior finishes have been completed and cleaned.
3.03 FIRE ALARM CONTROL PANEL OPERATIONS
A. Under normal operating conditions display the current date, time and a "SYSTEM NORMAL" message on the front LCD screen of both the FACP and Remote Annunciator.
B. When an abnormal condition is detected at any point pulse the appropriate LED (Alarm, Supervisory or Trouble) should display on the FACP. The local audible signal should pulse during an alarm condition and sound steadily for trouble and/or supervisory conditions.
C. Simultaneously display the following information on the FACP LCD display relative to each abnormal point in the system:
1. Custom Location Label

JANUARY 8, 2016 WASHINGTON STATE UNIVERSITY

FIRE DETECTION AND ALARM 28 31 00

DIVISION 28 ­ ELECTRONIC SAFETY AND SECURITY 28 31 00 FIRE DETECTION AND ALARM
2. Type of Device
3. Point Status
D. Upon acknowledgment of all abnormal points or tamper switches illuminate the appropriate LED(s) and silence the FACP audible signal. Display the total number of abnormal points for each condition and provide a prompt to review each list chronologically. Indicate the end of the list.
E. Upon restoration of all devices and tamper switches pulse the appropriate audible signal and extinguish the relevant LED(s) indicating restoration to normal operating conditions.
F. Upon activation of the "Alarm Silence" control by authorized personnel silence all audible signals. Continue to flash visual signals until the FDA system is reset.
G. Upon activation of the "System Reset" control by authorized personnel the FDA system shall scan all points in the system and if all clear return the system to normal operation. Should an alarm condition continue to exist maintain the system in an abnormal state and indicate failure to reset with a locally audible pulse and display the total number of abnormal points.
H. Upon System Reset permit restarting of all equipment that was shut down during the FDA operations.
I. Access Levels:
1. The FACP shall be programmed to have four (4) distinct Passcode protected access levels.
2. When a correct Passcode is entered display "ACCESS GRANTED". The access level shall be in effect until the operator leaves the keypad inactive for ten (10) minutes or manually logs out. Allow all functions of the permitted access level and all lower access levels. If a user attempts to perform an access outside of their permitted access level display an "INSUFFICIENT ACCESS" message.
3. If a Passcode is improperly entered three (3) times display an "ACCESS DENIED" message.
4. Provide access levels for the following keys/switches. User information for Passcode assignment will be provided during acceptance training.
i. Alarm Silence ­ Level 1
ii. System Reset ­ Level 1

JANUARY 8, 2016 WASHINGTON STATE UNIVERSITY

FIRE DETECTION AND ALARM 28 31 00

DIVISION 28 ­ ELECTRONIC SAFETY AND SECURITY 28 31 00 FIRE DETECTION AND ALARM
iii. Set Time/Date ­ Level 3
iv. Manual Control ­ Level 3
v. On/Off/Auto Control ­ Level 3
vi. Disable/Enable ­ Level 3
vii. Clear Historical Alarm Log ­ Level 3
viii.Clear Historical Trouble Log ­ Level 3
ix. Walk Test ­ Level 3
x. Change Alarm Verification ­ Level 3
J. Configure the FACP to monitor each smoke detector by comparing sensor values to stored values in the system.
K. Maintain a moving average of the detectors smoke chamber value to automatically compensate (move the threshold) for dust and dirty conditions that could affect detection operations of the FACP. Automatically maintain constant smoke obscuration sensitivity for each detector (via the floating threshold) by compensating in the FACP for environmental factors at the individual detector's location. The smoke obscuration sensitivity shall be adjustable to within 0.3% of either limit of the UL window (0.5% - 4.0%) to compensate for any environment.
L. Automatically indicate at the FACP when an individual detector needs cleaning. Audibly and visually indicate a "DIRTY SENSOR" trouble condition and flash the LED on the detector base for the individual sensor when a detector's average value reaches a predetermined value for the individual sensor (to be set during acceptance training). If the detector is left unattended and reaches a second predetermined value for the individual sensor (also to be set during acceptance training) automatically indicate an "EXCESSIVELY DIRTY SENSOR" trouble condition at the FACP. To prevent false alarms these "dirty" conditions shall not decrease the amount of smoke obscuration necessary for system activation.
M. Program the FACP to identify "almost dirty" detector conditions. With the entry of an appropriate Passcode the FACP shall be commanded to print and/or log a list of all detectors that are within ten (10) analog units of causing a "DIRTY DETECTOR" trouble. The "ALMOST DIRTY DETECTOR" log shall list only the devices meeting "almost dirty" criteria and not a list of the analog value of every detector in the system.

JANUARY 8, 2016 WASHINGTON STATE UNIVERSITY

FIRE DETECTION AND ALARM 28 31 00

DIVISION 28 ­ ELECTRONIC SAFETY AND SECURITY 28 31 00 FIRE DETECTION AND ALARM
N. Program the FACP to provide manual access to the following information for each detector to an operator at the FACP that has a proper Passcode:
1. Primary Status
2. Device Type
3. Present average value
4. Present sensitivity selected
5. Peak detection values
6. Detector range
O. No interpretation or calculation shall be required to review detector sensor obscuration. Display all values as percent of smoke obscuration.
P. Program the FACP to provide manual control of the following function for each detector to an operator that has a proper Passcode:
1. Clear peak detection values
2. Enable or disable the point
3. Clear verification tally
4. Control a sensor's relay driver output
Q. Auxiliary Bypass Keys:
1. Program the FACP to function as follows upon authorized activation of any auxiliary bypass key: The normal alarm sequence operations of the programmed devices/control functions will not occur. Indicate a trouble condition on the FACP for each signal circuit/type of device/control function that is affected by the bypass.
R. Furnish and install Isolated Loop Circuit Protectors (ICLP) on all communication, IDNet II SCU/RCU and signaling lines, including shields on all circuits that extend beyond the building by any means. The ICLP shall be located as close as practicable to the point at which the circuits enter or leave a building. The ICLP grounding conductor shall be #12 AWG wire having a maximum length of 28 feet in as straight a line as practicable and connected to the building unified ground per Article 800-40 of the NEC.
S. All wiring shall be installed in conduit. Wiring and conduit arrangement shall be supplied by vendor in shop drawings. All wire installed must be approved

JANUARY 8, 2016 WASHINGTON STATE UNIVERSITY

FIRE DETECTION AND ALARM 28 31 00

DIVISION 28 ­ ELECTRONIC SAFETY AND SECURITY 28 31 00 FIRE DETECTION AND ALARM

for "Power Limited" fire alarm use under Article 760 of the National Electrical Code.

T. Final connections between the equipment and the wiring system shall be made under the supervision of a representative of the equipment manufacturer.

U. Upon completion of the installation and after testing and demonstration, the Contractor shall submit to the Architect a signed statement substantially in the form as follows:
1. The undersigned having been engaged as the Electrical Contractor for the [Insert Building Name Here] confirms that the fire alarm equipment was installed in accordance with the plans and specifications and in accordance with the wiring diagrams and directions provided to us by the manufacturer and that all wire installed is approved for "Power Limited Fire Alarm" use under Article 760 of the National Electrical Code.
2. It has been completely tested and demonstrated to the Owner's representative and accepted by the Code Enforcing Authority having jurisdiction.

3.04 ALARM SEQUENCE OF OPERATIONS
A. The alarm sequence to follow indicates the system order of operations for a complete FDA system with many possible device combinations.
B. The system alarm operation subsequent to any alarm initiating device shall be as follows:
1. Sound a continuous FDA signal on all audible alarm devices until the alarm is silenced at the Fire Alarm Control Panel or the Remote Annunciator.

2. Continuously flash strobes on all visual alarm devices until the system is reset.
3. Release all door hold open devices.
4. For WSU-Pullman installations:
i. Send a supervised alarm signal via the Campus IT Fiber network to the appropriate campus fire alarm network.
5. For non-WSU Pullman Installations:
i. Send a supervised signal to notify the central monitoring station via an internal Digital Alarm Communicator (DACT).

JANUARY 8, 2016 WASHINGTON STATE UNIVERSITY

FIRE DETECTION AND ALARM 28 31 00

DIVISION 28 ­ ELECTRONIC SAFETY AND SECURITY 28 31 00 FIRE DETECTION AND ALARM
ii. To accommodate and facilitate job site changes the "city connection circuit" shall be on-site configurable to provide a "reverse polarity", "local energy", "shunt" or dry contact connection.
6. Activate/Deactivate mechanical controls on the air handling system as required by NFPA 72 and all applicable codes. Send a notification signal to the Building Automation System (BAS).
i. Operate combination Fire/Smoke Dampers.
ii. Send a signal to the BAS indicating that the facility has gone into alarm.
7. Display an alarm condition on the FACP and Remote Annunciator consistent with this specification.
i. Pulse the alarm LED in each location until the alarm has been acknowledged.
ii. Upon alarm acknowledgement re-flash the alarm LED upon receipt of any subsequent alarms for any devices/zones.
iii. Display the new alarm information on the FACP display.
8. Provide a pulsing alarm tone within the FACP and remote Annunciator until acknowledged.
C. In addition, the activation of any initiating device shall start the following elevator recall sequence:
1. Recall all elevator cabs to their primary egress floors upon the activation of an alarm on any floor other than the primary level of egress.
2. Recall the elevator cabs to the alternate egress floor upon the activation of an alarm initiating device on the primary egress level.
3. Recall the elevator cabs to the higher of the primary or alternate recall floors and flash the firefighter's helmet symbol in each cab upon the activation of an initiating device in the elevator shaft or the elevator machine room.
D. Provide a manual evacuation switch to operate the system's alarm indicating appliances and other control circuits.
E. Upon activation of auxiliary bypass keys override the automatic alarm functions as programmed.

JANUARY 8, 2016 WASHINGTON STATE UNIVERSITY

FIRE DETECTION AND ALARM 28 31 00

DIVISION 28 ­ ELECTRONIC SAFETY AND SECURITY 28 31 00 FIRE DETECTION AND ALARM
F. Display all open alarm and trouble conditions on the FACP. If multiple alarm or trouble conditions exist display each in order of occurrence. This will allow for the determination of not only the most recent alarm but also may indicate the path that the fire is traveling.
END OF SECTION

JANUARY 8, 2016 WASHINGTON STATE UNIVERSITY

FIRE DETECTION AND ALARM 28 31 00



