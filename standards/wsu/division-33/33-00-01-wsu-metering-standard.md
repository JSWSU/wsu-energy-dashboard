# CSI 33 00 01 - WSU Metering Standard

> **Division:** 33
> **CSI Code:** 33 00 01
> **Title:** WSU Metering Standard
> **Date:** 2025-06-26
> **Source:** WSU Facilities Services Design & Construction Standards (June 2025)

---

DIVISION 33 ­ UTILITIES 33 00 01 UTILITY METERING REQUIREMENTS
PART 1 ­ GENERAL
1.01 RELATED WORK
A. For BAS-integrated metering devices, please refer to Division 25 ­ Integrated Automation.
B. For BAS-integrated metering devices, please refer to WSU's BAS Meter Network Overview and Standards design criteria.
C. For utility construction specifications please refer to the attachments for Division 33 ­ Utilities.
D. For network cabling and termination specifications, reference WSU's Telecommunications Distribution Design Guide.
E. All utility metering shall comply with Washington State Energy Code Section C409 and WAC 5111C-40904.
1.02 METER IDENTIFICATION & SPECIFICATION
A. The A/E is to specify that utility meters complying with the requirements of this specification are to be procured, installed, and integrated to account for all building utility services affected by the scope of the construction project. If there are existing meters installed and reporting data to WSU's Skyspark data collection system, no additional meters are required but the A/E must specify that meters not currently reporting be connected to Skyspark and commissioned according to the requirements of this specification.
a. All buildings affected must be equipped with meters to measure, monitor, record and display energy and water consumption connected through existing campus utility distribution systems.
b. The A/E shall enumerate all meter requirements, specify which building(s) or system(s) are served for each meter, and shall ensure that total utility consumption of the associated building or complex can be monitored with the meter solution.
c. WSU Facilities Services Information Services (FSIS) will confirm the integration status or integration capability of any existing utility meters identified by the A/E or contracting team upon request.
B. Submetering is not explicitly required for any systems except where addressed in the Washington State Energy Code section C409; it is the A/E's responsibility to work with WSU's Energy Group to determine the project submetering requirements. Submetering shall comply with Washington State Energy Code section C409.3.

June 26, 2025 WASHINGTON STATE UNIVERSITY

Metering 33 00 01

DIVISION 33 ­ UTILITIES 33 00 01 UTILITY METERING REQUIREMENTS

1.03 RESPONSIBILITIES MATRIX

A. The following table shows the matrix of responsibilities required for each stakeholder throughout the design and construction phases of a project requiring utility metering. L = Lead, C = Coordination (as needed), S = Submit, R = Review, V = Verify

Phase Design Construction

Task
Incorporate all WSU Design & Construction Standards to design documents. Provide single line diagram(s) of all existing utility service connections. Coordinate approximate meter location(s) and incorporate to design drawings. Determine meter size and location. Create and fill out the Exhibit A Metering spreadsheet with available metering information. Documentation of meter utility source (facility meter, or submeter of) Provide and review all meter product submittal data. Provide single line diagram(s) of all utility meter networking connections. Provide meter MAC addresses and all required networking information. Fill out the Exhibit A spreadsheet with this and all forthcoming information.

Architect/ Engineer (A/E)
L
L
L L
C
L

Contracting Team (GC, Controls, Elec, Mech)
C C,S
L, S L, S
L, S

WSU Facilities Services
C C C, V C, V R,V C C, R
C

WSU FSIS
L,S,R,V C, R, V C, R, V

Cx Contractor

June 26, 2025 WASHINGTON STATE UNIVERSITY

Metering 33 00 01

DIVISION 33 ­ UTILITIES 33 00 01 UTILITY METERING REQUIREMENTS

Phase

Task
Provide IP address, BACnet instance number, and/or QR label. Construct and connect new utilities services to existing campus distribution systems. Install meter. Provide electrical power to meter. Provide network infrastructure. Connect meter to network. Verify meter functionality and data reporting.

Architect/ Engineer (A/E)

Contracting Team (GC, Controls, Elec, Mech)

WSU Facilities Services

WSU FSIS

C

C

L, V

L

C, R

L, C

C

L, C

C

C

C

L, C

L, C

C

C

C

Cx Contractor
V V
V L, V

PART 2 - MATERIALS
2.01 SUBMITTALS
A. Stipulate and define shop drawings to be submitted by the Contractor for verifying products furnished are in compliance with the specifications. Provide enough copies for A/E's use plus one approved set to the Owner.
B. Require that single line diagrams showing all associated utility meters and network device connections be submitted by the contractor for verifying that network design is in compliance with WSU requirements.
2.02 NETWORKING
A. Contact FAIS through the WSU Project Manager to identify the appropriate meter network annexation point.
B. The meter designer or installer shall provide all of the following networking-related information for each meter prior to meter installation. WSU FSIS will provide an Exhibit A Meter Integration Spreadsheet, included as an appendix to this specification, for information to be provided by the Contractor, and will review the proper completion of the spreadsheet by the Contractor before providing the IP Address, QR label, and other required information to configure the meter. This Exhibit A will be a living document shared back and forth amongst the project team and is an

June 26, 2025 WASHINGTON STATE UNIVERSITY

Metering 33 00 01

DIVISION 33 ­ UTILITIES 33 00 01 UTILITY METERING REQUIREMENTS

integral part of the metering process. It will be first provided by and approved in its final format by the WSU FSIS team.
a. Meter designer responsibilities (A/E ­ design phase)
i. System Served ­ include designation as main meter or submeter service
ii. Meter Location (Room #)
iii. Data Communications room designated for the IT switch.
b. Meter installer responsibities (contracting team - submittal phase)
i. Type of Meter Controller ­ full product model name and serial number (see sections below for allowable models)
ii. Communication Protocol (BACnet/IP)
iii. Meter Manufacturer (see sections below for allowable manufacturers)
iv. Meter Register Totalizer ­ totalizer configuration for volume or energy
v. Units Delivered (e.g. Amps/Voltage by Phase, kW, kVA, PF, kWh, F, RP)
c. Meter installer responsibilities (contracting team ­ construction phase)
i. Meter ID Nameplate ­ meter names must be confirmed with WSU FSISMetering.
ii. Meter MAC Address ­ required to assign IP address/subnet mask/default gateway/proposed BACnet instance number
1. For meters with multiple IP ports, provide both MAC addresses, designating which port is to be used (Port #1) and which MAC is assigned to this port.
iii. CT (current transformer) Ratio or CT model number must be documented in addition to correctly configured within electrical meter software.
iv. Numbered and identify the cable drops with network switch location and port number on the device location end and the device location room number and official WSU meter designation on the network switch location end.
1. Note that WSU is responsible for the jumper from the network switch to the patch panel.

June 26, 2025 WASHINGTON STATE UNIVERSITY

Metering 33 00 01

DIVISION 33 ­ UTILITIES 33 00 01 UTILITY METERING REQUIREMENTS

2.03 METER DATA COLLECTION SOFTWARE

A. The meter data collection software for WSU is the Skyspark analytics platform. WSU operates a virtual machine operating the licensed Skyspark software, and requires that all integrated meters comply with project haystack and WSU Skyspark tagging standards.

a. All proposed meter solutions must be compatible with an automatic network data connection between the meter and Skyspark, unless noted otherwise in section 2.04 below.

b. Sensus or Calsense wireless or network/cloud meters may be used for data collection with the express approval of WSU Facilities Services.

c. Skyspark tagging standards are included as an appendix to this specification.

2.04 METER REQUIREMENTS

A. All meters shall be integrated with data collection software noted in section 2.03.A. Exceptions may be allowed with written approval from WSU Facilities Services for instances like:

a. Make-up water on closed loop systems

B. All meters shall be capable of communicating via Class A BACnet over IP protocol per current ANSI/ASHRAE standards. Exceptions may be made for Modbus TCP meters with the express approval of WSU Facilities Services.

C. All meters must be installed in a space no smaller than 2ft x 2ft x 2ft, less than 6ft above the floor/ground. Meters shall be installed such that all access ports and corresponding latches are easily accessible. Exceptions may only be explicitly approved on a case-by-case basis by written communication of WSU Facilities Services.

D. The Contractor is required to confirm meter size and type with the WSU Facilities Services, unless provided directly by the A/E according to new equipment design.

E. Calibration label on instrument shall indicate last factory calibration date. Calibration datestamped certificate must be left with the meter at the device's location.

F. All instrumentation shall be rated to operate in an ambient temperature of 32-185F.

G. All transmitter enclosures shall be rated at a minimum of NEMA 4 with a minimum of two ¾" electrical plugs.

H. All wiring must be in conduit.

I. Meters must be properly labeled with a label maker and configured with a bacnetDeviceName that matches WSU meter naming conventions. See below:

June 26, 2025 WASHINGTON STATE UNIVERSITY

Metering 33 00 01

DIVISION 33 ­ UTILITIES 33 00 01 UTILITY METERING REQUIREMENTS

a. First 5 digits: 4-digit numeric building number + building letter OR underscore (_).

b. Next 3 digits: 2-digit meter type identifier + underscore or 3-digit identifier.

i. CD: Steam Condensate

ii. CE: Chilled Water Energy

iii. DI: DI (De-ionized) Water

iv. DS: Distance Meter

v. DW: Domestic Water

vi. EL: Electricity

vii. HE: Hot Water Energy

viii. HR: Hours (Runtime)

ix. IR: Irrigation Water

x. NG: Natural Gas

xi. RO: RO (Reverse Osmosis) Water

xii. RW: Rain Water

xiii. ST: Steam Energy

xiv. SW: Sanitary Sewage Water

xv. UDW: Utility Water

xvi. UEL: Utility Electricity

xvii. UNG: Utility Natural Gas

xviii. WW: Waste Water

c. Last 3 digits: 3-digit meter number (001, 002, 003, etc.).

d. Examples: 0001ADW_001, 0001_EL_013, 0123_UNG001

i. Building numbers: 0001A, 0001, 0123

ii. Meter types: DW ­ Domestic Water, EL ­ Electric, UNG ­ Utility Natural Gas

June 26, 2025 WASHINGTON STATE UNIVERSITY

Metering 33 00 01

DIVISION 33 ­ UTILITIES 33 00 01 UTILITY METERING REQUIREMENTS
iii. Meter number: 001, 013, 001
J. All meters must also be labelled as a Main Service or Sub-Meter (, and voltage as appropriate. Sub meters should also identify upstream meter by name.
2.05 WATER METERS
A. Each water service connection (including domestic and irrigation) shall include an insertion or inline, full flow meter for measuring water consumption installed in a location physically accessible by WSU Facilities Services. Domestic water meters must be approved for potable water.
B. The meter is to be ahead of and coupled with the backflow prevention assembly, if applicable. The design of the full assembly is to give due regard to subsequent maintenance procedures, including ease of disassembly via use of unions, couplings, valves, bypass lines or other appropriate fittings.
C. Meters must be selected to report water flow (gal/min) and totalized volume (gal) accurately and comprehensively via BACnet/IP based on the system design.
D. A NIST certificate of calibration must be provided from the manufacturer for the installed flow meter
E. Accuracy of the flow meter must be within 1.5% of flow across full range for given pipe size.
F. Minimum turn-down of the flow meter shall be a ratio of 100:1.
G. The flow meter shall be specified to be installed according to the manufacturer's requirements, including ensuring that the chosen location is in a straight pipe of equal or greater length than recommended by the manufacturer.
H. All in-line electromagnetic meters shall be grounded as per the manufactur's instructions for that meter.
I. Allowable products shall be:
a. Flow meter shall be an Onicon F-3100 Series Inline Electromagnetic meter, and
b. Onicon FT-3400 Insertion Electromagnetic meter with the stainless steel shaft
c. BACnet networking device shall be an Onicon D-100 Network Display
i. An Onicon System 1000 Display shall be considered with WSU approval where applicable.

June 26, 2025 WASHINGTON STATE UNIVERSITY

Metering 33 00 01

DIVISION 33 ­ UTILITIES 33 00 01 UTILITY METERING REQUIREMENTS
2.06 HYDRONIC ENERGY METERS
A. Each chilled water and (direct) hot water service connection shall include an approved integral, system-type BTU meter using an inline, full flow meter for measuring the water flow and water supply and return temperature sensors capturing the entire load of the full flow system. All components shall be installed in a location physically accessible by WSU Facilities Services. Hot water systems heated by steam heat exchangers may use steam condensate utility metering unless specifically called out by the A/E as needed as additional data.
B. The design of the full assembly is to give due regard to subsequent maintenance procedures, including ease of disassembly via use of unions, couplings, isolation valves, bypass lines or other appropriate fittings.
C. Meters must be selected to report system flow (gal/min), totalized volume (gal), return temperature, supply temperature, and totalized cooling energy (ton-hr) or heating energy (BTU) accurately and comprehensively via BACnet/IP based on the system design.
D. Temperature sensors shall be current (mA) based or RTD-type matched temperature sensor pairs with a thermal well designed for use in hydronic systems calibrated within 0.25F.
E. A NIST certificate of calibration must be provided from the manufacturer for the installed flow meter, and a formal testing certificate, or documented commissioning tests demonstrating measured and verified meter accuracy meeting or exceeding WAC 51-11C-40904.
F. Accuracy of the flow meter must be within 1% of flow across full range for given pipe size.
G. Minimum turn-down of the flow meter shall be a ratio of 100:1.
H. The flow meter shall be specified to be installed according to the manufacturer's requirements, including ensuring that the chosen location is in a straight pipe of equal or greater length than recommended by the manufacturer.
I. Allowable products shall be:
a. Flow meter shall be an Onicon F-3100 Series Inline Electromagnetic meter, and/or an Onicon F-3400 Series Insertion Electromagnetic Meter, and
b. BACnet networking device shall be an Onicon System 10 BTU Meter
i. An Onicon System 1000 Display shall be considered with WSU approval where applicable.

June 26, 2025 WASHINGTON STATE UNIVERSITY

Metering 33 00 01

DIVISION 33 ­ UTILITIES 33 00 01 UTILITY METERING REQUIREMENTS
2.07 STEAM CONDENSATE METERS
A. Each steam connection with a condensate receiver shall include an inline, full flow meter for measuring steam condensate water consumption installed in a location physically accessible by WSU Facilities Services. Condensate water meters must be rated for potable water.
B. The design of the full assembly is to give due regard to subsequent maintenance procedures, including isolation valves, ease of disassembly via use of unions, couplings or other appropriate fittings.
C. Meters must be selected to report water flow (gal/min) and totalized volume (gal) accurately and comprehensively via BACnet/IP based on the system design.
D. A NIST certificate of calibration must be provided from the manufacturer for the installed flow meter.
E. Accuracy of the flow meter must be within 1% of flow across full range for given pipe size.
F. Minimum turn-down of the flow meter shall be a ratio of 100:1.
G. Condensate water meter shall be capable of operation with internal fluids up to at least 212F.
H. The flow meter shall be specified to be installed according to the manufacturer's requirements, including ensuring that the chosen location is in a straight pipe of equal or greater length than recommended by the manufacturer.
I. Allowable products shall be:
a. Flow meter shall be an Onicon F-3100 Series Inline Electromagnetic meter with the PTFE liner (rated for 250 degrees Fahrenheit), and
b. BACnet networking device shall be an Onicon D-100 Network Display
i. An Onicon System 1000 Display shall be considered with WSU approval where applicable.
2.08 NATURAL GAS METERS
A. Each natural gas service connection shall include an inline, full flow meter for measuring natural gas consumption installed in a location physically accessible by WSU Facilities Services.
B. The design of the full assembly is to give due regard to subsequent maintenance procedures, including isolation valves, ease of disassembly via use of unions, couplings or other appropriate fittings.

June 26, 2025 WASHINGTON STATE UNIVERSITY

Metering 33 00 01

DIVISION 33 ­ UTILITIES 33 00 01 UTILITY METERING REQUIREMENTS

C. Meters must be selected to report natural gas flow (CFM) and totalized volume (CCF) accurately and comprehensively via BACnet/IP based on the system design.

D. Accuracy of the flow meter must be within 1% of flow across full range for given pipe size.

E. The thermal mass flow meter shall be specified to be installed according to the manufacturer's requirements, including ensuring that the chosen location is in a straight pipe of equal or greater length than recommended by the manufacturer.

F. Allowable products shall be:

a. Flow meter shall be an Onicon F-5500 Series Inline Thermal Mass Flow meter, and

b. BACnet networking device shall be an Onicon D-100 Network Display

i. An Onicon System 1000 Display shall be considered with WSU approval where applicable.

2.09 ELECTRIC METERS

A. Each electric service connection shall include an electric meter assembly measuring total electrical consumption installed in a location approved by WSU Facilities Services.

B. Meters must be selected to report electrical active power (kW), apparent power (kVA), totalized energy (kWh), power factor, and current (A) and voltage (V) readings across each of its electrical phases, including neutral, accurately and comprehensively via BACnet/IP.

C. The electric meter product shall be an Accuenergy Acuvim II Series Advanced Power & Energy meter for single circuit measurements, or an Accuenergy AcuRev Series Multi-Circuit Submeter for submetering multiple circuits with the same voltage source.

D. Meter shall be rated for 60Hz power and comply with UL 508.

E. Meter will be provided with matching Rogowski style CTs (current transformers) for a complete installation. All CTs shall be removable for ease of maintenance. WSU does not typically require a separate CT for the Neutral load.

F. Accuracy of the electric meter must be within 0.1% of full-scale reading.

G. All renewable energy electricity generation systems shall have submeters matching the electric meter specifications above.

H. Install electric meters per all manufacturer recommendations, including all safety and access considerations.

I. Electric Meter Acceptable Products:
June 26, 2025 WASHINGTON STATE UNIVERSITY

Metering 33 00 01

DIVISION 33 ­ UTILITIES 33 00 01 UTILITY METERING REQUIREMENTS
a. Accuenergy AcuRev 2100 Series Multi-Circuit Multimeter
b. Accuenergy Acuvim II Series Advanced Power & Energy Meter
2.10 STEAM ENERGY METERS
A. Steam energy loads are typically addressed with a condensate meter for full building load. Exceptions are when steam is consumed in a way that will not be measured by the building condensate meter, such as HVAC humidifiers.
B. Each process steam service connection, excluding those with condensate metered per this specification, shall include a compound steam meter system measuring total steam consumption installed in a location physically accessible by WSU Facilities Services.
C. The design of the meter assembly is to give due regard to subsequent maintenance procedures, including ease of disassembly via use of unions, couplings or other appropriate fittings.
D. Meters must be selected to report steam flow (lb/h) and totalized steam consumption (lb) accurately and comprehensively via BACnet/IP or Modbus/TCP based on the system design.
E. The steam meter product must be a compound steam meter allowing for accuracy of 2.5% of full-scale reading.
F. With express permission of WSU Facilities Services, humidification-process consumption of steam energy may be calculated in Building Automation System (BAS) systems in compliance with WSU's Division 25 standards. If BAS sensors are used for calculation, the contractor must submit the sensor products and an explicit BAS sequence for calculating totalized steam humidification consumption to WSU Facilities Services, which must reset to zero upon reinitialization of the BAS controller.
G. Steam energy meters may be used in combination with building steam condensate return systems in order to account for metering of total building steam consumption.
H. Install electric meters per all manufacturer recommendations, including all safety and access considerations.
I. Steam BTU Mass Flow Meter Acceptable Products:
a. Sierra InnovaMass 240S/241S
b. Onicon F-2600 Series Inline Vortex Flow Meter.

June 26, 2025 WASHINGTON STATE UNIVERSITY

Metering 33 00 01

DIVISION 33 ­ UTILITIES 33 00 01 UTILITY METERING REQUIREMENTS
PART 3 - EXECUTION
3.01 INSTALLATION
A. All meters must be installed in compliance with Division 33 standards.
B. Installer must test the functionality of all wiring, CTs, and meters prior to meter commissioning and notify WSU FS and the commissioning agent when all components have been tested to operate properly. WSU FS and the commissioning agent will subsequently verify the meter's functionality, and identify any deficiencies to be addressed by the installing contractor.
3.02 LABELING
A. Each network cable shall be labelled on both ends. The device end shall be labelled with the network room number and switch port number. The network switch end shall be labelled with the device room number and meter type.
B. Each meter device shall be labeled with a tag secured to the instrument indicating calibration range, meter number (according to the specifications above), and system served. The tag shall be made with a label maker and affixed permanently onto the cable or device.
C. All meters shall be labeled with the QR code provided by WSU Facilities Services.
3.03 SKYSPARK INTEGRATION
A. The contracting team must work with a Skyspark-capable integration service provider to integrate all relevant meter data to the Skyspark analytics platform installed and licensed for WSU.
B. All totalized data points (volume, energy, etc.) shall be collected at hourly intervals, while flow, temperature, and current/voltage/power-factor data are collected at 15min intervals and electrical power (kW) and apparent power (kVA) are collected at 1min intervals.
C. Meter equips and their associated points must be tagged according to Project Haystack and WSU metadata tagging standards.
D. Calculated values for steam heating energy and hydronic heating/cooling power shall be created as needed to comprehensively report upon total building source energy and power consumption.
3.04 METER COMMISSIONING
A. The A/E shall specify that all meters in the project scope shall be verified to function properly by the commissioning agent, including that meter data properly reports over a BACnet connection to Skyspark. The commissioning agent may work with the WSU metering group or directly with the contractor to ensure data validity.

June 26, 2025 WASHINGTON STATE UNIVERSITY

Metering 33 00 01

DIVISION 33 ­ UTILITIES 33 00 01 UTILITY METERING REQUIREMENTS
B. The contractor shall be responsible for coordinating meter installation, networking and testing with WSU and the commissioning agent, and is required to resolve all issues identified through the commissioning process.
PART 4 - APPENDICES
4.01 EXHIBIT A METER INTEGRATION SPREADSHEET
4.02 TELECOMMUNICATIONS DISTRIBUTION DESIGN GUIDE
4.03 SKYSPARK METER TAGGING STANDARDS

June 26, 2025 WASHINGTON STATE UNIVERSITY

Metering 33 00 01



