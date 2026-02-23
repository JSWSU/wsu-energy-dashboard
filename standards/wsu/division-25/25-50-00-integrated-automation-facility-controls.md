# CSI 25 50 00 - INTEGRATED AUTOMATION FACILITY CONTROLS

> **Division:** 25
> **CSI Code:** 25 50 00
> **Title:** INTEGRATED AUTOMATION FACILITY CONTROLS
> **Date:** 2025-06-06
> **Source:** WSU Facilities Services Design & Construction Standards (June 2025)

---

DIVISION 25 ­ INTEGRATED AUTOMATION 25 50 00 INTEGRATED AUTOMATION FACILITY CONTROLS

PART 1 - GENERAL
1.01 GENERAL
Please refer to Section 5 - Building Systems of the Washington State University Design Guidelines for a brief introduction to WSU Facility Services' Building Automation HVAC control system.
The WSU Facility Services Building Automation System (BAS) is defined by the Field Panels, control and monitoring devices that report directly to a Building Automation System software, as well as the segment of the WSU Facilities Services private network that functions as the Ethernet communications backbone. The DIVISION 25 section is devoted to only Building Automation Systems and their control and monitoring points and meters related to these points.

Note: At this time Electrical control points such as Real Time Automation Controllers (RTAC) and Automatic Transfer Systems (ATS) and Utility meters are NOT considered part of the WSU Facilities Services BAS.

1. For non-BAS metering standards please refer to Division 33 ­ Utilities.

APPENDIX LIST

1. Appendix 1A ­ SIEMENS BAS NAMING SCHEME TOOL 2. Appendix 1B ­ ALERTON BAS NAMING SCHEME TOOL 3. Appendix 2 ­ BAS ACRONYM LIST 4. Appendix 3 ­ BAS POINT NAMING SCHEME 5. Appendix 4 ­ BAS STANDARD OPERATING PROCEDURES 6. Appendix 5 ­ PROJECT SEQUENCE (Future) 7. Appendix 6 ­PRODUCT REQUIREMENTS 8. Appendix 7 ­ AIRFLOW CONTROL DEVICES 9. Appendix 8 - NETWORK DEVICE RISER DIAGRAM 10. Appendix 9 ­ TYPICAL NON- RECIRCULATING AIR HANDLING
SYSTEM. 11. Appendix 10 ­RECIRCULATING AIR HANDLING SYSTEM.

RELATED SECTIONS

1. 11 53 13 ­ Laboratory Fume Hoods 2. 13 20 81 ­ Maintenance Mechanic Rooms 3. 26 33 53 ­ Static UPS 4. 27 00 00 ­ Communications, Technology, Audio/Visual 5. 28 31 00 ­ Electronic Safety and Security

May 6, 2025 WASHINGTON STATE UNIVERSITY

INTEGRATED AUTOMATION FACILITY CONTROLS 25 50 00

Page1

DIVISION 25 ­ INTEGRATED AUTOMATION 25 50 00 INTEGRATED AUTOMATION FACILITY CONTROLS
6. 26 29 23 ­ Variable-Frequency Motor Controllers 7. 32 17 43 26 ­ Pavement Snow Melting Systems (Electric) 8. 32 17 43 60 ­ Pavement Snow Melting Systems (Hydronic) 9. 33 00 00 ­ Utilities 10. 33 82 00 ­ Communications Distribution
DEFINITIONS
1. "BACnet" is the primary communications protocol utilized by the BAS devices on the WSU Facilities Services private network.
2. "BAS" means the Building Automation System that is maintained by WSU Facilities Services. This system is defined by the Field Panels, control devices, monitoring devices and the Ethernet backbone on which they communicate.
3. "BAS Workstation" means the interface in which the WSU Facilities Services BAS is interacted with.
4. "Commissioning Agent" means the entity performing Commissioning work that is employed EXTERNALLY to WSU.
5. "Commissioning" means the process of connecting a new BAS device to any system and verifying functionality with and operating that system.
6. "Control Shop" means the entity primarily responsible for the health and management of the WSU Facilities Services BAS.
7. "Device" means any piece of hardware, mechanical or digital, that is deployed in the field and connected to the WSU Facilities Services BAS system.
8. "Ethernet" the primary communications media for the WSU Facilities Services Private Network. Ethernet is used in conjunction with Fiber Optics on the WSU Facilities Services Private Network.
9. "Fiber Optic" is the backbone for long distance communications on the WSU Facilities Services Private Network allowing for Ethernet over IP communications across the WSU Pullman campus.
10. "FS" means Facilities Services.
11. "FIRM" means Facility Information Resource Management.

Page2

May 6, 2025 WASHINGTON STATE UNIVERSITY

INTEGRATED AUTOMATION FACILITY CONTROLS 25 50 00

DIVISION 25 ­ INTEGRATED AUTOMATION 25 50 00 INTEGRATED AUTOMATION FACILITY CONTROLS
12. "Graphic(s)" means the visual screens by which BAS control points are interacted with.
13. "Person" means a corporation, partnership, business association of any kind, trust, company, or individual.
14. "Point" means a device that interacts with, is controlled or monitored by the WSU Facilities Services BAS.
15. "Pre-Commissioning" means the process of verifying functionality of existing BAS components. This will take place PRIOR to Commissioning.
16. "Specifications" are the portion of the Contract Documents consisting of the written requirements for materials, equipment, construction systems, standards and workmanship for the work, and performance of related services.
17. "TAB" means Testing and Balancing. Specifically the stage of a BAS project in which the Commissioning Agent verifies proper functionality of newly installed BAS devices.
18. "VPN" means Virtual Private Network which refers to an isolated and secure connection to the WSU Facilities Services Private Network.
19. "WSU Facilities Services Private Network" means the logically and physically isolated network space allocated for WSU Facilities Services use.
20. "WSU" means Washington State University.
1.02 PROJECT SEQUENCE
1. This is to be determined on a per project basis by the WSU FS Capital team and is to be enforced by the PM/CM assigned to the project.
PART 2 - PRODUCTS
2.01 BACNET
All WSU Facilities Services BAS devices on the WSU Facilities Services private network shall be capable of communicating via the ANSI/ASHRAE 135-1995 BACnet over IP protocol.

Page3

May 6, 2025 WASHINGTON STATE UNIVERSITY

INTEGRATED AUTOMATION FACILITY CONTROLS 25 50 00

DIVISION 25 ­ INTEGRATED AUTOMATION 25 50 00 INTEGRATED AUTOMATION FACILITY CONTROLS
1. As of this writing (10/2019) the current BACnet protocol is Ver. 1, Rev. 21. A current version of the ASHRAE 135 standard can be found at www.bacnet.org.
2. Please refer to Appendix 6 ­PRODUCT REQUIREMENTS for a breakdown of preferred Building Automation System product requirements.
2.02 AIRFLOW CONTROL DEVICES
As outlined in Appendix 7 ­ AIRFLOW CONTROL DEVICES.
2.03 NETWORKING
BAS Switches and UPSs:
1. All switches and UPS devices used in the BAS will be specified, procured and installed by WSU Finance and Administration Information Systems (FAIS). Not all projects will require BAS infrastructure, as it may already exist.
i. Contact FAIS through the WSU Project Manager to identify the closest BAS annexation point.
1) Current standard BAS equipment: a) Switch: Cisco 2960X-24-PS-L b) UPS: APC SMC1000-2RU
Sub-network Cabling for zone controllers, expansion devices, meters and other devices.
1. MSTP Network Cable:
i. Alerton MSTP Cable standard-Cable utilized on an MS/TP Network shall be ;
Plenum rated Cable
Gauge - 24 AWG
a) Color ­ Purple b) Conductors 2 each plus a shielding conductor c) Manufacturer/Part number ­ Connect Air W241P-2010PRB d) Capacitance, Mutual ­ 12.5 pF/ft +/- 10% e) Impedance- 100 Ohms +/- 10% f) D.C. Resistance-24.5 Ohms/Mft at 20C

Page4

May 6, 2025 WASHINGTON STATE UNIVERSITY

INTEGRATED AUTOMATION FACILITY CONTROLS 25 50 00

DIVISION 25 ­ INTEGRATED AUTOMATION 25 50 00 INTEGRATED AUTOMATION FACILITY CONTROLS
g) Temperature/ Working voltage 75C/300 VRMS ii. Siemens MSTP Cable standard-Cable utilized on an MS/TP Network shall
be;
Non- Plenum rated Cable
a) Gauge - 24 AWG b) Color ­ Orange c) SBT Part number ­ H-F-1.5TSP24LC-CM d) Description ­ FLN485, 24AWG, STR,TP+1C, OAS,LOCAP,CM
Plenum rated Cable
a) Gauge - 24 AWG b) Color ­ Orange c) SBT Part number ­ H-F-1.5TSP24LC-CMP d) Description ­ FLN485, 24AWG, STR,TP+1C, OAS,LOCAP,CMP

2) 24 AWG STR TSP LOCAP CM ORANGE JACKET
2. Siemens -FLN Network Cable:
i. Siemens - Cable utilized on an MS/TP BLN shall be a 24 gauge stranded, twisted pair low capacity [CM] cable in an orange and blue jacket. 1) 24 AWG STR TSP LOCAP CM ORANGE JACKET W/ BLUE STRIP
PART 3 - EXECUTION AND DEVELOPMENT?
3.01 SINGLE POINT GLOBAL CAMPUS CONTROL
Network wide control strategies shall not be restricted to a single DDC Controller or HVAC Mechanical Equipment controller, but shall be able to include data from any and all other network panels to allow the development of Global control strategies.

The following procedures shall be maintained:
1. Staggered electrical power load recovery. The engineering design shall include development of this scheme with Facilities Services.
2. Heating and cooling demand management or load shedding. 3. Campus wide snow and ice melt. 4. Domestic water wells and reservoirs.

May 6, 2025 WASHINGTON STATE UNIVERSITY

INTEGRATED AUTOMATION FACILITY CONTROLS 25 50 00

Page5

DIVISION 25 ­ INTEGRATED AUTOMATION 25 50 00 INTEGRATED AUTOMATION FACILITY CONTROLS
Reference Appendix 3 ­ STANDARD OPERATING PROCEDURES for additional information.
3.02 BAS CONTROL SOFTWARE
The primary control and monitoring software for all WSU Facilities Services Building Automation System operations is the Siemens Desigo CC platform.
1. All proposed control solutions must be compatible with Desigo CC. 2. Any concerns about this must be raised to the WSU Control Shop, other
shops and Facilities Services Engineering via the project manager as soon as possible. 3. Template points that are not used to display values, for alarms, in programs or schedules will be either excluded from loading on the Desigo platform or will be removed from it after the system is loaded. 4. Any point that is added to the Desigo System will be made legible and understandable through the Point Naming Standards. If nothing in the standard applies, the standard can be appended upon approval by the Control Shop, other shops and engineering via the project manager.
Each control solution may have their own proprietary commissioning system that allows for configuration, database management and control logic implementation.
1. Any concerns about this must be raised to the WSU Control Shop other shops and Facilities Services Engineering via the project manager as soon as possible.
3.03 CONTROL SYSTEM VENDOR INSTALLATION REQUIREMENTS
THE CONTROL SYSTEMS CONTRACTOR SHALL:
1. The Control systems contractor will submit control system schematics, sequence of operations, network diagrams for network layers 1, 2 and 3, point listings, graphics and programs to WSU prior to construction for approval.
A. Network Layer 1 - Graphically illustrate on building plans the cabling path between the devices and the T-Closet. Specify type of cabling and connectors being used. Indicate the speed and duplex of network interfaces.
B. Network Layer 2 - Graphically illustrate and explain the use of any Open System Interconnection (OSI) Layer 2 protocols being used in network design.
C. Network Layer 3 - Graphically illustrate and explain the use of any

Page6

May 6, 2025 WASHINGTON STATE UNIVERSITY

INTEGRATED AUTOMATION FACILITY CONTROLS 25 50 00

DIVISION 25 ­ INTEGRATED AUTOMATION 25 50 00 INTEGRATED AUTOMATION FACILITY CONTROLS
gateways or firewalls being proposed to translate protocols or segment networks.
2. Restore or install existing global commands and procedures back to and from the procedure controller(s). These commands include;
A. Chilled Water Load Shed procedures · Load shed level 1 sets AHU cooling set points up in select areas. · Load shed level 2 sets AHU cooling set points up in addition to Load shed level 1 in select areas. · Load shed level 3 shuts down chilled water pumps in select areas.
B. Steam Load Shed procedures · Load shed level 1 Sets mixed air dampers to recirculation in select areas. · Load shed level 1A Shuts down low priority exhaust like toilet exhaust fans in select locations. · Load shed level 2 Reduces or shuts down humidity in select locations. · Load shed level 2A Reduces or shuts down domestic Hot water in select locations. · Load shed level 3 Sets zone controls to night set points in select areas.
C. Snowmelt Global procedures. · This procedure operates Snowmelt systems globally during the winter months based on an operator command.
D. Heat Tape Global procedures · This procedure operates heat tapes globally during the winter months based on temperature.
E. Chilled Water Pump Loop procedures · This procedure can shut of a large number of chilled water pumps in facilities. The goal has been if there is a major distribution leak, pumps would not run without water and destroy seals and bearings.

3. The Control systems contractor will be responsible for creating a plan for this retrofit period to recover as quickly as needed to service and to protect the facility against failure during cold or hot weather or to protect process cooling and other systems as required during the retrofit process by establishing priorities to bringing required systems online first and to operate required systems while the control system is not functioning. The plan will be submitted to Facilities Services Maintenance.
4. Pneumatic output modules will not be located on controller enclosure

May 6, 2025 WASHINGTON STATE UNIVERSITY

INTEGRATED AUTOMATION FACILITY CONTROLS 25 50 00

Page7

DIVISION 25 ­ INTEGRATED AUTOMATION 25 50 00 INTEGRATED AUTOMATION FACILITY CONTROLS
doors. They will be located in a separate enclosure as needed.
5. Outputs to final control elements will be scaled to the signal medium that to actuator or other device receives. Examples are 4-20Ma, 0-10vdc or through 0-10vdc or 4-20 to 3-15 or 0-20 psig if the actuator is pneumatic and using a transducer.
6. Provide wiring and control schematics, sequence of operations and controller installation manuals.
7. Provide a written sequence of operation.
8. Power recovery will be installed in the programs so that electrical loads do not come online simultaneously. The timed startups will be provided by the Electrical and Control Shops via the Project manager.
9. Provide a floor layout that marks the locations of added sensors, enclosures and physical locations required to perform work and complete the project.
10. Install graphics on the Desigo and Compass servers as the systems involved dictate.
11. The Compass or Datamate and Desigo Server will be uploaded from the control system and the databases, programs and scheduler and will be synchronized.
12. An alarmable point listing will be provided for all projects.
13. Provide device failure notification of controllers and components to the control systems Desigo System and Compass system. The WSU Facilities Work Management Center Dispatch system shall receive those notifications.
14. Provide the point data bases, programming and scheduling for all HVAC systems within the project scope.
15. The project scope will include controls, power supplies and everything required to control all equipment currently operated by the existing DDC controls. The Control System Contractor will install this equipment.
16. All BAS network devices and I/O shall be labeled in a manner that is easily descriptive for users and system operators in regard to both hardware and software. For damper and valve actuators, the label must include warranty length and start date. The control systems contractor will provide and install the labels.
17. Sensors and other devices that are located in obscure locations shall be recorded on plans regarding their locations.
18. The Desigo Guiding Principles document will the standard for Desigo installations.
19. The control systems contractor is responsible for all physical installation, including wiring and installation of the controllers. The systems are to be

Page8

May 6, 2025 WASHINGTON STATE UNIVERSITY

INTEGRATED AUTOMATION FACILITY CONTROLS 25 50 00

DIVISION 25 ­ INTEGRATED AUTOMATION 25 50 00 INTEGRATED AUTOMATION FACILITY CONTROLS
made operable by the control systems contractor in regard to automation and to the user interface.
20. The control system contractor will complete all physical installation of hardware components, wiring and network cable, and other required components.
21. The control systems will be backed up by ups systems for a minimum of 5 hours.
22. Provide a commissioning plan to test the systems against the sequence of operations for both pre-commissioning and post commissioning procedures.
23. Accommodate the cross network communications that will be required to maintain these systems operations during renovations including creating temporary stub points for use in the older controllers across the networks.
24. The control system contractor will provide commissioning forms designed to test all components and programming associated with the facility based upon the sequence of operations and will include alarms. The commissioning forms will be submitted to Washington State University, Facilities Services as part of the submittal packages. Training will be included in the post commissioning phase this project.
25. Network impact associated with each control system project will be monitored before and after implementation. Remediation by the control system contractor may required if work results in unacceptable network impact.
REQUIREMENTS RELATED TO FACILITIES RETROFIT AND UPGRADE PROJECTS.
THE CONTROL SYSTEMS CONTRACTOR SHALL:
1. All equipment scheduling will be relocated to the BACnet schedule. The schedules will be submitted to WSU prior to project completion and will be included in the final O&M package as a record.
2. Participate in a preconstruction maintenance commissioning review of the systems and hardware with the WSU maintenance department prior to the construction schedule. All existing switches, sensors, dampers and valves will be deemed operational prior to replacement of the BAS

Page9

May 6, 2025 WASHINGTON STATE UNIVERSITY

INTEGRATED AUTOMATION FACILITY CONTROLS 25 50 00

DIVISION 25 ­ INTEGRATED AUTOMATION 25 50 00 INTEGRATED AUTOMATION FACILITY CONTROLS
controller or replaced prior to construction by the WSU maintenance division.
3. Participate in a preconstruction maintenance commissioning review of the systems and hardware with the WSU maintenance department prior to the construction schedule. All existing switches, sensors, dampers and valves will be deemed operational prior to replacement of the BAS controller or replaced prior to construction by the WSU maintenance division. Notify Facilities Services of the appropriate time, prior to installation or upgrades of equipment, to run a BACnet analysis of the impacted network to be used as a baseline for analysis post-installation (reference section 4.01.C).
4. Work with WSU Facilities Services to start up and commission the new control systems.
5. The databases and programming for updated facilities shall be cleaned up during this effort. The databases shall be set up in an orderly fashion to accommodate report functions, not limited to trending. Programming needs to be made efficient for operation and logic flow.
6. Duplicate the alarms that are currently in place. The alarms shall be tested, and shall be received at the WSU Facilities Services Work Management Center Dispatch system initially to the Desigo Systems.
7. This system will be functional for any procedures such as snow melt and steam shed procedures that currently exist when these projects are completed.
PART 4 - QUALITY
4.01 COMMISSIONING (PRE/POST)
At the end of pre-commissioning the commissioning authority shall provide a list of pre-existing issues and deficiencies to both the WSU Facilities Services BAS Admins and PM/CM. Following post-commissioning the commissioning authority shall provide a list of remaining issues and deficiencies to both the WSU Facilities Services BAS Admins and WSU Facilities Services Capital Project/Construction Manager. Following post-commissioning, notify Facilities Services to perform a second BACnet analysis to compare to the baseline analysis performed prior to the installation and or upgrades. Deficiencies of medium impact and higher will be added to the issues list for resolution. When deficiencies are believed to be resolved, an analysis will be run again to confirm.

Page1 0

May 6, 2025 WASHINGTON STATE UNIVERSITY

INTEGRATED AUTOMATION FACILITY CONTROLS 25 50 00

DIVISION 25 ­ INTEGRATED AUTOMATION 25 50 00 INTEGRATED AUTOMATION FACILITY CONTROLS

4.02 BAS WORKSTATION GRAPHICS
All graphic screens shall include links to the main building graphic as well as the campus graphic for easy navigation. At WSU Facilities Services' discretion a point list graphic will be required if the point list tool is not functional or too cumbersome to use. This listing will be provided in the Desigo or Compass systems as a default unless the control system provider can provide a simple, convenient, method of providing a listing of points and active values to be used to troubleshoot systems and the Washington State University Desigo or Compass representative allows them not to be. These graphics will include every point required to operate a system, including those that are used to hold values in control programs. Graphical screens shall link directly to the device properties screens. Where deemed necessary, Graphics systems will be linked to navigate together related systems. Graphics will be required to be linked together to navigate HVAC systems unless the Washington State University Desigo or Compass representative allows them not to be. Any information added to the graphics for commissioning use shall be removed prior to WSU Facilities Services hand over. Instructions for adding graphics to the system will be provided at the time of hand over to WSU Facilities Services. Graphics will be reviewed by WSU Control Shop prior to the hand off to WSU Facilities Services. Graphics will maintain a cohesive feel across the environment.
POINT LABELING
1. All points included on a graphic and used on the system will be sufficiently labeled to allow for easy, logical, human understandable identification. This will enable quick reference by Work Management and Dispatch personnel. The acronym list that is developed under the point naming standards will be provided to groups like Dispatchers to reference. If new requirements are necessary they will be submitted to Control Shop, other shops and engineering via the project manager to be appended to the acronym listing.
GRAPHIC FUNCTIONALITY
1. All command-able points associated with a graphic shall be commandable from that graphic.
2. All graphic animations shall reflect the current state of the device.

May 6, 2025 WASHINGTON STATE UNIVERSITY

INTEGRATED AUTOMATION FACILITY CONTROLS 25 50 00

Page11

DIVISION 25 ­ INTEGRATED AUTOMATION 25 50 00 INTEGRATED AUTOMATION FACILITY CONTROLS
3. Graphics files shall be provided to WSU Facilities Services in .DWG auto-cad format for easy cross platform usage.
4. Graphic screens shall allow for resizing without issue. 5. Imported graphics will be of a high enough resolution such that resizing
the images does not cause pixilation. 6. Graphics file sizes will not exceed 400 mb.
4.03 NEW PANEL INSTALLATION
Existing Infrastructure 1. Installation of new panels must be coordinated with Facilities Services prior to installation i. New panels must include at a minimum, a 4" gutter above, below or beside the new panel for extra wires or splices
1) Extra wires shall be labeled "extra" or "Not in use" 2) Splices shall have wire nuts or crimp on splicing to ensure proper
connection at all times.
PART 5 - WARRANTY
Provide all services, materials and equipment necessary for the successful operation of a BAS system for a period of 12 months after acceptance by WSU. In addition, all materials and equipment shall be warranted for an additional 12 months for a total warranty period of 24 months. Warranty services for the first 12 months shall include replacement automation components, equipment or materials, and the associated labor for installation, termination, database management and related programming in the event a device or procedure has failed, broken or become unusable. Warranty services for the second 12 months shall include replacement automation components, equipment or materials at no cost to WSU. The associated labor in the second year of warranty will be charged on an hourly basis if requested by WSU. Provide an extended warranty on all damper and valve actuators for a total of 5 years. All BAS devices shall be locally identified with the warranty termination date allowing for easy warranty period identification by the owner.
PART 6 - TRAINING REQUIREMENTS (NOT APPLICABLE)
PART 7 - STOCK AND SPARE PARTS
7.01 TIME AND MATERIALS

Page1 2

May 6, 2025 WASHINGTON STATE UNIVERSITY

INTEGRATED AUTOMATION FACILITY CONTROLS 25 50 00

DIVISION 25 ­ INTEGRATED AUTOMATION 25 50 00 INTEGRATED AUTOMATION FACILITY CONTROLS
Each WSU Facilities Services Capital building project shall provide two additional VAV controllers and two additional room sensors.

Each project involving a laboratory shall include two additional spare components per control element to allow for quick replacement.

WSU Facilities Services shall reserve the right to convert any service agreement items deemed unnecessary into materials and equipment costs.

PART 8 - PREINSTALL REQUIREMENTS

8.01 POINT NAMING

All WSU Facilities Services BAS point names shall conform to the WSU Facilities Services point naming scheme as more fully set forth in the WSU Facilities Services BAS Acronym list.

1. Please reference the following appendixes for full requirements:

i. Appendix 1A ­ BAS NAMING SCHEME TOOL ii. Appendix 1B ­ BAS NAMING SCHEME TOOL iii. Appendix 2 ­ BAS ACRONYM LIST iv. Appendix 3 ­ BAS POINT NAMING SCHEME

Vendors will contact the WSU Facilities Services BAS Group via the Contract chain regarding list additions and removals on a case by case basis.

PART 9 - SPECIAL INSPECTIONS (NOT APPLICABLE)

PART 10 - SHOP DRAWINGS (NOT APPLICABLE)

PART 11 - SPECIAL INSTRUCTIONS OR PROVISIONS

11.01 TELECOMMUNICATIONS INFRASTRUCTURE

Because the WSU BAS is a closed system, several design standards are critical to maintain its overall health and security:

Rack Space: In order to accommodate building automation networks and associated equipment, the BAS will need at least 8 rack units of space per Telecomm Closet and 10 rack units per MCF. This specification will accommodate all BAS switches, UPS, and surveillance servers.

Page1 3

Power: WSU BAS will require at least four (4) 120v power outlets in each Telecomm Closet and in each MCF to accommodate power for BAS network components.

May 6, 2025 WASHINGTON STATE UNIVERSITY

INTEGRATED AUTOMATION FACILITY CONTROLS 25 50 00

DIVISION 25 ­ INTEGRATED AUTOMATION 25 50 00 INTEGRATED AUTOMATION FACILITY CONTROLS
Gigabit Passive Optical Network (GPON): No GPON equipment shall be used as part of the BAS infrastructure, and BAS devices shall not be connected to Optical Line Terminal (OLT) devices. Since GPON buildings contain significant fiber cable plans, allocating fiber per the BAS standard will allow for proper configuration and deployment.
Fiber Optic: WSU BAS networks require 4 strands of single mode fiber feeding each new building or remodeled building and 4 strands of single mode fiber between each MCF and Telecomm Closet. This will accommodate a redundant pair of network uplinks for critical network components. All fiber media shall be 62.5 microns.
1. If single mode fiber is not available in the building's distribution media, then this standard can be applied to multi-mode media instead.
11.01 NETWORKING COMMUNICATIONS
The WSU Facilities Services Private Network on which the WSU Facilities Services BAS resides is and shall remain a physically and logically isolated network accessible only via a strictly monitored VPN connection.
The network architecture shall consist of three levels, a campus-wide (Management Level Network) Ethernet network based on TCP/IP protocol, high performance peer-to-peer building level network(s) and DDC Controller floor level local area networks with access being totally transparent to the common user when accessing data or developing control programs.
BAS Switches and UPSs: All switches and UPS devices used in the BAS will be specified, procured and installed by WSU Finance and Administration Information Systems (FAIS). Not all projects will require BAS infrastructure, as it may already exist. Contact FAIS through the WSU FS Project Manager to identify the closest BAS annexation point.
Rack Space: In order to accommodate building automation networks and associated equipment, the BAS will need at least 8 rack units of space per Telecomm Closet and 10 rack units per MCF. This specification will accommodate all BAS switches, UPS, and surveillance servers.
Power: WSU BAS will require at least four (4) 120v power outlets in each Telecomm Closet and in each MCF to accommodate power for BAS network components.
The mechanical and electrical project designers will include a facility or project network system design and will work with control vendors and WSU FAIS to create plans suitable for any control system vendor that may be used on their project. The plan will include a design for the network entering the facility from a wsu Major Communications Facility. The project manager will be the point of contact.

Page1 4

May 6, 2025 WASHINGTON STATE UNIVERSITY

INTEGRATED AUTOMATION FACILITY CONTROLS 25 50 00

DIVISION 25 ­ INTEGRATED AUTOMATION 25 50 00 INTEGRATED AUTOMATION FACILITY CONTROLS
11.02
The Design of the WSU Facilities Services BAS shall allow the co-existence of new DDC Controllers with existing DDC Controllers in the same network without the use of third-party gateways or protocol converters.
The BAS infrastructure and/or software shall not impose a maximum constraint on the number of operator workstations without limiting performance.
Peer-to-Peer Building Level Network:
1. All operator devices shall have the ability to access all point status and application report data or execute control functions via the peer-to-peer network.
2. The peer-to-peer network shall allow for expansion and capacity changes as required.
3. The system shall support integration of third party systems (PLC, chiller, boiler, etc.) via panel-mounted open protocol processor. This processor shall exchange data between the two systems for process control. All exchange points shall have full system functionality as specified herein for hardwired points. If BACnet IP or MSTP will not be employed as the protocols during this type of integration, both the WSU Control Shop or other shops and Facilities Services Engineering will approve the integration solution. The purpose of the solution will be provided along with a description of the implementation requirements. Via the PM.
Management Level Network:
1. All PCs shall simultaneously direct connect to the Ethernet and Building Level Network without the use of an interposing device.
2. Operator Workstation shall be capable of simultaneous direct connection and communication with all WSU FS BAS devices without the use of interposing devices.
If a device will utilize any Ethernet connectivity, it shall leverage the IP stack and be able to communicate with other devices in the same subnet and therefore have the capability to be layer 2 adjacent.
1. IP-based Protocols currently supported are limited to the following: Approval for below via PM.
i. TCP/IP ( Upon approval by both the WSU Control Shop, or other shops and Facilities Services Engineering.)

Page1 5

May 6, 2025 WASHINGTON STATE UNIVERSITY

INTEGRATED AUTOMATION FACILITY CONTROLS 25 50 00

DIVISION 25 ­ INTEGRATED AUTOMATION 25 50 00 INTEGRATED AUTOMATION FACILITY CONTROLS
ii. BACnet-IP (BACnet Ethernet is prohibited)
iii. Modbus IP IP ( Upon approval by both the WSU Control Shop or other shops and Facilities Services Engineering.)
2. All other IP protocols in use must be pre-approved by WSU Facilities Services Control Shop AND WSU Finance and Administration Information Systems (FAIS).
END OF SECTION

Page1 6

May 6, 2025 WASHINGTON STATE UNIVERSITY

INTEGRATED AUTOMATION FACILITY CONTROLS 25 50 00



