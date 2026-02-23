# 27-telecommunications-design-guide (Part 4 of 10)

> **Continued from:** 27-telecommunications-design-guide-part3.md

---


84

June 24, 2015

DESIGN CRITERIA
DATA CENTERS AND MCFS

4.18.4 ENVIRONMENTAL PROVISIONING
Environmentally friendly solutions shall be considered in the design of data center cooling systems, incorporating heat reclamation and non-mechanical cooling features where reasonable and practical.
Environmental management and monitoring systems shall be designed for data centers.
Consideration shall be given to both in-row cooling and whole-room cooled air solutions. Whole-room cooled solutions shall be designed to implement hot-aisle/cold-aisle arrangements, and captured-ducting solutions for hot air return shall be considered.
Air conditioning systems for technology/server and UPS rooms shall be supported by standby power systems.
4.18.5 FIRE DETECTION AND SUPPRESSION
All Data Centers shall be protected by a pre-action, dry-pipe, water-based suppression system. Fire suppression systems shall activate when two sensors detect an actionable condition.
4.18.6 RACKS AND CABINETS
Two-post equipment racks and four-post equipment cabinets are both required. The Designer shall discuss with the ITPM about the network electronics that will be hosted in each rack and cabinet in the Data Center, and shall show this equipment on the rack elevation details in the plan drawings. The Designer shall also discuss with the ITPM the potential for future additional racks and cabinets, and shall identify space on the plan drawings to accommodate them.
Other styles of equipment racks and cabinets might be used in the Data Center, some of which may be proprietary to a particular system or service provider. The Designer shall plan the Data Center layout to make allowances for proprietary cabinets and racks, and allow expansion room for future equipment.
A. Floor-standing cabinets shall have front- and rear-hinged doors to permit access to both the front and rear of the equipment. Cabinets shall be constructed of heavy-gauge steel. The side panels of the cabinet shall be removable for maintenance accessibility.
B. Each cabinet shall be vented, and where appropriate, equipped with cooling fans.
C. WSUP has used APC NetShelter 750mm cabinets in recent projects.
D. Each rack and cabinet shall be provided with the following telecommunications cabling:
· 1U fiber optic patch panel, with 24 strands of singlemode fiber (APC, LC) and 24 strands of 50-micron multimode fiber (UPC, SC). The Designer shall inquire whether 62.5-micron multimode fiber is required in lieu of 50-micron.
· 1U copper patch panel with 24 jacks of Category 6 cabling installed.

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

85

June 24, 2015

DESIGN CRITERIA
DATA CENTERS AND MCFS

4.18.7 POWER REQUIREMENTS

4.18.7.1 TECHNICAL POWER PANELS
A. The WSUP campus electrical power generator distributes standby power throughout campus on Feeder 13. Data Centers and MCFs require Feeder 13.

B. A separate supply circuit serving the room shall be provided and terminated in its own electrical panel located in the Data Center. This power panel shall be designated as "Data Center Technical Power." The Data Center technical power panel shall be used exclusively for supplying power to electronics equipment in the equipment room. Sizing of electrical power supply is dependent upon the equipment types and equipment load, and shall be calculated on a case-by-case basis, including sufficient spare capacity for future growth.

C. The technical power circuits in each Data Center shall originate from a technical power panel, dedicated to serving the Data Center. The technical power panel shall not be used to supply power to sources of electromagnetic interference such as large electric motors, arc welding, or industrial equipment.

D. Power for critical network components such as servers, routers, switches, and telephone systems shall always be provided through at least one uninterruptible power supply (UPS).

E. WSUP requires the use of centralized UPS equipment for Data Centers. WSUP has used APC Symmetra 40kVA equipment on recent projects, with power distribution via whips or modules to a PDU in each rack.

· The Designer shall work with the WSUP ITPM to determine an appropriate battery capacity on a case-by-case basis.

· Upon installation, a qualified electrician shall test new centralized UPS units for correct output voltage prior to connecting electronic equipment.

· Centralized UPS equipment shall be provided with a network interface card, so that the UPS can communicate via the network with servers and other equipment to orchestrate a coordinated safe-shutdown of the equipment in the event of an extended power outage.

· WSUP recognizes that flywheel-based UPS equipment is available. However, the initial cost of flywheel equipment is typically very costly, and as a result, the return on investment is low with a lengthy time to payback. For most applications, flywheel-based UPS systems are probably cost-prohibitive.

F. WSUP typically uses network electronics that provide Power-over-Ethernet (POE).

G. The Designer shall request power consumption data for the equipment that WSUP will use, and will size the power distribution infrastructure sufficient to support this equipment plus 50% growth.

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

86

June 24, 2015

DESIGN CRITERIA
DATA CENTERS AND MCFS

4.18.7.1.1 EMERGENCY POWER OFF (EPO) BUTTON
A. Where required by Code (NEC 645.A), an Emergency Power Off (EPO) pushbutton shall be provided near the exit of the Data Center room. The button shall be located per Code requirements, preferably at the same elevation as the light switch, at least a foot away from the light switch but not more than two feet from the door. The button shall be provided with a shield to prevent accidental actuation from inadvertent contact.
B. When the EPO button is pressed, all power to the room shall be shut off immediately, per Code requirements, except for power to light fixtures. Power to the UPS equipment shall be shut off, and power from the UPS to equipment shall also be shut off when the EPO button is pressed.
C. Provide a permanent, wall-mounted plaque near the EPO with instructions for restarting the power following an EPO event. It is recommended that the plaque be fabricated from engraved plastic or a similar indelible material. The text on each plaque shall be specifically written for the facility. The following is an approximate example to be modified by the Electrical Engineer to reflect actual conditions at the facility:
1. Before resetting any EPO pushbutton, verify that:
· The condition has been corrected for which EPO activation occurred. · Fire suppression systems have been reset to clear alarms.
2. Reset the activated EPO Station. 3. Verify that all loads are fully energized and reset. Shunt any tripped
breakers. If air conditioning unit is not working, consult manufacturer's startup procedures.
D. The Electrical Engineer shall prepare written guidelines describing examples of events that would warrant pressing the EPO button. The guidelines are not expected to be a comprehensive list.

4.18.7.2 TECHNICAL POWER OUTLETS
A. Generally, the power outlet requirements that are applicable to telecommunications rooms are also applicable to equipment rooms. See TDDG Section 4.3.6 Power Requirements (above).
B. The Designer shall obtain connection/load requirements from WSUP for each piece of equipment, and tabulate the information for review and confirmation by WSUP. This equipment may include network electronics, UPS equipment, computers/servers, phone system equipment, voice mail systems, video equipment and service provider equipment.
C. Some telephone PBX equipment, UPS equipment and network switch equipment requires specialized plugs or electrical service. The Designer shall specifically investigate the potential need for voltage or current requirements other than the

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

87

June 24, 2015

DESIGN CRITERIA
HEALTH CARE

typical 120VAC/20 Ampere power outlet, and shall coordinate with the design team to design the electrical power infrastructure to serve the needs of the equipment.
4.18.7.2.1 FOR REMODEL PROJECTS
If an equipment room is truly required in a remodel project, budget limitations and other constraints shall be resolved through actions that do not deviate from meeting the requirements of this document. In particular, the electrical power requirements of equipment in an equipment room shall not be discounted or taken lightly.

4.18.7.3 CONVENIENCE POWER OUTLETS
Convenience power outlets shall be provided as described (above) in TDDG Section 4.3.6 Power Requirements (above).

4.18.8 GROUNDING, BONDING, AND ELECTRICAL PROTECTION
All equipment racks, metallic conduits, and exposed non-current-carrying metal parts of telecommunications and information technology equipment in the Data Center shall be bonded to the TGB. Please refer to Chapter 9, Bonding and Grounding (Earthing) in the BICSI TDMM and TDDG Section 4.8 for more information regarding the design of grounding, bonding and electrical protection systems.
· The Data Center requires a dedicated/isolated ground wire routed inside a metallic conduit directly from the main electrical service-grounding electrode for PBX equipment. This ground wire is in addition to and separate from the telecommunications grounding system.
· Grounding and bonding conductors shall be sized according to the requirements in ANSI/TIA/EIA J-STD-607A.

4.19 Health Care
Please refer to Chapter 19, Health Care in the BICSI TDMM for general information regarding the design of telecommunications infrastructure for serving health care facilities.
The Designer shall inquire with the FSPM whether a project will include health care-related spaces. If so, the Designer shall design telecommunications infrastructure for these spaces in compliance with TIA-1179 - Healthcare Facility Telecommunications Infrastructure Standard.

4.20 Residential Cabling

Please refer to Chapter 20, Residential Cabling in the BICSI TDMM for information regarding the design of telecommunications infrastructure to support residential facilities within WSUP facilities.

Residential facilities at WSUP shall be designed using GPON telecommunications infrastructure. WSUP Housing & Dining directs design decisions for residential facilities. The

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

88

June 24, 2015

DESIGN CRITERIA
BUSINESS DEVELOPMENT AND PROJECT MANAGEMENT
Designer shall inquire with both the ITPM and the IT representatives of Housing & Dining for direction regarding telecommunications infrastructure for a residential facility project.
4.21 Business Development and Project Management
Please refer to Chapter 21, Business Development and Project Management in the BICSI TDMM for general information regarding design, construction and project management of telecommunications infrastructure.
Please refer to TDDG Section 3 Project Procedures for WSUP-specific telecommunications project procedure requirements.
4.21.1 CODES, STANDARDS AND REGULATIONS
Please refer to Appendix A: Codes, Standards and Regulations in the BICSI TDMM for general information regarding the codes, standards and regulations that apply to telecommunications infrastructure.

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

89

June 24, 2015

CONSTRUCTION DOCUMENT CONTENT
PLANS AND DRAWINGS

5 Construction Document Content
This section of the TDDG describes the content requirements that the Designer shall include when creating the Construction Documents5. This content is in addition to the content found in some generally accepted document sets. The documents produced by the Designer and the services provided by the Designer shall comply with the requirements in the Conditions of the Agreement and the Instructions for Architects and Engineers doing Business with Division of Engineering and Architectural Services. In addition to these requirements, the Designer shall also meet the requirements in this document, including the Construction Document content requirements in this section. Construction Documents shall communicate a fully detailed and coordinated design (rather than making adjustments in the field during construction) and are expected to result in reduced construction costs and fewer change orders. The level of detail required to meet this objective may be substantially greater than some telecommunications designers may be accustomed to providing. The Designer shall include the following content in the Construction Documents:
5.1 Plans and Drawings
5.1.1 GENERAL
The telecommunications portion of the Construction Drawing set shall include the following: · Cover Sheet · Sheet List · Site Map · Symbol Schedule · List of Abbreviations · Plan Sheets · Elevation Diagrams · Schematic Diagrams · Construction Details · Demolition
All plan sheets shall be scaled, shall indicate the scale, and shall show a north arrow. All plan sheets shall show a key plan when the building or site is too big to fit on a single sheet.

5 As of this writing, the Conditions of the Agreement and the Instructions for Architects and Engineers Doing Business with Division of Engineering and Architectural Services (both published by the Washington State Department of General Administration) make reference to the term "Construction Drawings." However, the Manual of Practice from the Construction Specifications Institute (CSI) defines "Construction Documents" as a subset of the "Contract Documents" and indicates that drawings, specifications and other written documentation are contained within the Construction Document subset. The TDDG will use the term "Construction Documents" according to CSI's definition.

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

90

June 24, 2015

CONSTRUCTION DOCUMENT CONTENT
PLANS AND DRAWINGS
Equipment and cable identifiers shall be shown on the drawings and diagrams.
5.1.2 OUTSIDE PLANT SITE PLAN DRAWINGS
A. Provide drawings showing a scaled telecommunications distribution site plan. These drawings shall show the following:
· Maintenance hole or handhole locations (labeled with their identifiers) · Complete ductbank routing, details, and elevations · Conduit sizes, quantities, and arrangements · Section cuts · Existing and new surface conditions · Outside plant copper telecommunications cabling, including pair counts · Outside plant fiber optic telecommunications cabling, including fiber types
and strand counts · Locations of buildings, roads, poles, existing underground utilities, and other
obstructions
B. These sheets should also identify coordination arrangements where conflicts with site work for other disciplines could possibly arise, in particular indicating the separation distances between telecommunications and power or steam. The sequencing of site work also should be shown, if applicable.
C. The site plan shall show the cabling from the service providers (cable television, telephone, etc.) and shall indicate the requirements for owner-provided maintenance holes or handholes and pathway to the point of demarcation.
D. These sheets should also identify coordination arrangements where conflicts with site work for other disciplines could possibly arise, in particular indicating the separation distances between low-voltage and power or steam. The sequencing of site work also should be shown, if applicable.
5.1.3 MAINTENANCE HOLE/HANDHOLE BUTTERFLY DIAGRAMS
A. Butterfly diagrams are a combination of tabular information and a schematic diagram used to organize and communicate information related to the conduits and cabling in each maintenance hole and handhole. These diagrams are CAD files to be included in the project's drawing set.
B. The Designer shall provide a set of butterfly diagrams depicting each maintenance hole or handhole affected by the project, and showing new cabling as well as existing cabling to remain in the maintenance hole or handhole.
· Ducts to be used for new cabling shall be assigned during the course of design, not during construction. Duct assignments must be approved by WSUP prior to the release of construction documents.

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

91

June 24, 2015

CONSTRUCTION DOCUMENT CONTENT
PLANS AND DRAWINGS

C. A second set of butterfly diagrams shall be provided for each maintenance hole or handhole that contains existing cabling intended to be demolished under the project.
D. The diagrams shall be formatted as shown in the sample butterfly diagram in Appendix 6.5. Upon request, WSUP will provide an electronic AutoCAD file of this diagram to be used as a template as well as electronic CAD files for each butterfly diagram affected by a project.

5.1.4 INSIDE PLANT PLAN DRAWINGS
A. Scaled plan drawings shall be provided for each building showing the telecommunications applications and cabling inside the building. These drawings shall show the following:
· Routing of new pathway to be constructed during the project. o The content of the drawings shall be coordinated with other disciplines and shall be representative of the complete pathway route that the Contractor shall use, rather than a schematic depiction. o It is expected that the Designer will expend considerable coordination effort during the design process. Non-coordinated pathway/raceway is not acceptable to WSUP.
· Approximate locations of junction boxes and conduit bends. · The cable quantities and the raceway at any given point in the system. · Backbone distribution cabling.
B. Where new cabling will be pulled into existing conduits, the Construction Documents shall show the routes of each existing conduit. Where it is not possible to determine the routing of existing conduits, the Designer shall inform the WSUP ITPM and seek direction on whether to use the existing conduits or design new conduits for use on the project. Typically, the Designer is required to identify such conditions during field investigation activities.

5.1.5 DEMOLITION
A. Any existing equipment and cabling intended to be no longer in use following the new installation shall be removed (salvaged and returned to the Owner undamaged and in working condition) as a part of the project. WSUP uses salvaged equipment as spare parts to support the existing equipment in other buildings.
B. Existing cabling to be demolished shall be shown on the plans and schematic diagrams. Separate demolition plan sheets and schematic diagrams shall be provided for projects with extensive cable demolition.

5.1.6 TELECOMMUNICATIONS ROOM PLAN DETAILS
A. Construction documents for WSUP projects shall show scaled plan drawing details for the telecommunications spaces. The details shall show the footprint

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

92

June 24, 2015

CONSTRUCTION DOCUMENT CONTENT
PLANS AND DRAWINGS

and location of each of the major components in the room, including at least the following:

· Backboards · Ladder Racking · Work Area · UPS Equipment

· Backbone Cable Routing · Entrance Conduits · Space for Future Racks · Termination Blocks · Grounding Busbar

· Space Reserved for Utility Demarc · Racks and Vertical Cable Mgmt · Space for other low-voltage systems · Entrance Protection Equipment · PBX and Voice Mail Equipment

B. For modifications to existing telecommunications rooms, it may be necessary to provide a demolition plan.

C. Sample telecommunications room plan diagrams are included in Appendix 6.1.

5.1.7 ELEVATION DIAGRAMS

A. The Designer shall provide scaled wall elevation details for each telecommunications room and equipment room affected by the project.

B. For remodel projects, the Designer shall produce digital photographs of each wall depicting the existing conditions where future telecommunications rooms and equipment rooms will be located. These photos shall be provided with the wall elevation details in the Construction Documents.

C. The wall elevation details shall show the components that are mounted on the walls in the room, including at least the following:

· Backboards · Ladder Racking · Cable Slack Loops · Grounding Busbar · Existing Devices · Work Area · UPS Equipment · Entrance Pit

· Backbone Cable Routing · Cable Management · Termination Blocks · Power Receptacles · Entrance Conduits · Space for Future Racks · PBX and Voice Mail

· Wall-mounted Electronic Equipment · Wall-mounted Swing Racks & Contents · Racks and Vertical Cable Mgmt · Entrance Protection Equipment · Other low-voltage systems · Space for Future Equipment · Space Reserved for Utility Demarc

D. Elevation details for each of the telecommunications racks in each telecommunications room and equipment room shall also be provided. Rack elevation details shall show the racks and any components that are mounted on or near the racks, including at least the following:

· Patch Panels · UPS Equipment · Existing Devices

· Shelves/Drawers · Termination Blocks · Power Receptacles

· Space for Future Equipment · Electronic Equipment · Cable Management

E. The details shall depict the telecommunications materials that are listed in the specification.

F. Where a project involves additions to existing racks, the elevation details shall show the existing equipment in the racks and indicate which items are existing, in addition to indicating which items are "new, to be provided under the Contract."

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

93

June 24, 2015

CONSTRUCTION DOCUMENT CONTENT
PROJECT MANUAL
G. Examples of rack and wall elevation details are included in Appendix 6.2 and Appendix 6.3.
5.1.8 INTRA-BUILDING BACKBONE SCHEMATIC DIAGRAMS
A. A schematic diagram of the intra-building telecommunications backbone cabling is required, and shall show all termination points.
B. On projects where existing intra-building distribution cabling is to be removed, it may be useful to provide a separate schematic diagram depicting cabling to be demolished.
5.2 Project Manual
A. The Instructions for Architects and Engineers Doing Business with Division of Engineering and Architectural Services (published by the Washington State Department of General Administration) lists requirements for the Project Manual. The State of Washington Conditions of the Agreement (also published by the Washington State Department of General Administration) lists additional requirements for the Designer.
B. The Project Manual shall contain a summary of the telecommunications work on the project, a description of the demolition requirements (if applicable), and a discussion of the utility coordination requirements.
C. In addition to these requirements, the Project Manual shall contain the following items as listed below:
· Horizontal Cabling Labeling Spreadsheet · Fiber Link-Loss Budget Analyses · Cutover Plans
5.2.1 SPECIFICATIONS
5.2.1.1 WSUP TELECOMMUNICATIONS CONSTRUCTION GUIDE SPECIFICATION
A. The WSUP Telecommunications Construction Guide Specification (TCGS) is a guide specification as opposed to a master specification. It does not include an exhaustive listing of all possible products or installation methods that could be employed in a telecommunications infrastructure project.
B. The TCGS is an example of a specification that shall be used for an infrastructure replacement project or for a new facility project. It has verbiage that identifies issues that the Designer shall consider throughout the adaptation process. The Designer shall adapt the sections in the TCGS to the particular requirements of the given project.

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

94

June 24, 2015

CONSTRUCTION DOCUMENT CONTENT
RECORD DRAWINGS AND DOCUMENTATION
C. The Designer shall directly edit the TCGS for use on each project. The Designer shall notify the WSUP ITPM where changes or additions to the specifications are desired. Edits to the documents shall be performed with the "Revision Tracking" features activated. At the various project milestones when the documents are submitted to WSUP for review, the specifications shall be printed showing the revision markings.
D. The Designer shall be responsible for adding any necessary content to the specification that is applicable to the project and not already contained in the TCGS.
E. Please refer to the more detailed instructions contained in the TCGS, both in the Preface of that document as well as in the "hidden text" comments contained in the electronic files.
5.2.1.2 COMMON SPECIFICATION SECTIONS
There are several specification sections that are commonly used for telecommunications systems, or which contain content that supports telecommunications functionality.
Sections typically provided by the architect, but requiring Designer input:
· 099100 ­ Painting · 078413 ­ Penetration Firestopping
Sections typically provided by the Telecommunications Engineer:
· 270500 ­ Common Work Results for Communications · 270526 ­ Grounding and Bonding for Communications Systems · 270528.29 ­ Hangers and Supports for Communications Systems · 270528.33 ­ Conduits and Backboxes for Communications Systems · 270528.36 ­ Cable Trays for Communications Systems · 271100 ­ Communications Equipment Room Fittings · 271300 ­ Communications Backbone Cabling · 271500 ­ Communications Horizontal Cabling · 271523 ­ Communications Optical Fiber Horizontal Cabling · 273200 ­ Voice Communication Telephone Sets · 338126 ­ Communications Underground Ducts, Manholes, and Handholes · 338200 ­ Communications Distribution · 338243 ­ Grounding and Bonding for Communications Distribution

5.2.2 FIBER LINK-LOSS BUDGET ANALYSIS
A. In the Construction Documents, the Designer shall provide a link-loss budget analysis for each fiber optic cable.
B. The link-loss budget analysis shall be formatted as shown in Appendix 6.4. Upon request, WSUP will provide an electronic spreadsheet file to be used as a template.

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

95

June 24, 2015

CONSTRUCTION DOCUMENT CONTENT
RECORD DRAWINGS AND DOCUMENTATION
5.3 Record Drawings and Documentation
The Instructions for Architects and Engineers Doing Business with Division of Engineering and Architectural Services (published by the Washington State Department of General Administration) lists requirements for Record Drawings and submittals. The following requirements related to Record Drawings and submittals are in addition to the requirements listed in Instructions for Architects and Engineers Doing Business with Division of Engineering and Architectural Services:
5.3.1 RECORD DRAWING CONTENT
· The Record Drawings shall show the identifiers for the telecommunications equipment and cabling as constructed.
· The Record Drawings shall show actual measured signal levels and lengths of television distribution cabling as constructed.
5.3.2 RECORD DRAWING DELIVERABLES
The following shall be delivered to the WSUP FSPM, the second copy of which shall be given to the ITPM:
· Two copies of a CDROM containing editable 2D AutoCAD drawings (with all xrefs bound to the drawing) of the telecommunications plans, elevations, and details, in addition to the Revit or BIM model files.
· Two copies of a CDROM containing the digital photographs taken by the Designer during the project.

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

96

June 24, 2015

APPENDICES
SAMPLE TELECOMMUNICATIONS ROOM PLAN DETAILS
6 Appendices
6.1 Sample Telecommunications Room Plan Details
Below are sample plan details for several sizes of telecommunications rooms. The Designer shall provide similar details and information for each telecommunications room and equipment room affected by the project. This information shall be provided in the Construction Documents.
These sample plan details have been pre-approved for use at WSUP. The Designer shall use this layout wherever appropriate and shall discuss project-specific alternatives with the ITPM.
The room dimensions shown are considered to be acceptable minimums.
6.1.1 IDF: 1 RACK REACH IN ­ 10' X 4'
This example is suitable for a Day-1 design with a maximum of 96 horizontal cables (leaving room for future growth).
A one-rack room is rarely adequate, because it has very limited space for future equipment or cabling to be added. Therefore, it shall only be used as a last resort, and then only with the approval of the ITPM.

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

97

June 24, 2015

APPENDICES
SAMPLE TELECOMMUNICATIONS ROOM PLAN DETAILS
6.1.2 IDF: 1 RACK ­ 10' X 6'
This example is suitable for a Day-1 design with a maximum of 96 horizontal cables (leaving room for future growth). This solution is preferable over the reach-in design depicted above in section 6.1.1.
A one-rack room is rarely adequate, because it has very limited space for future equipment or cabling to be added. Therefore, it shall only be used as a last resort, and then only with the approval of the ITPM.

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

98

June 24, 2015

APPENDICES
SAMPLE TELECOMMUNICATIONS ROOM PLAN DETAILS
6.1.3 IDF: 2 RACKS ­ 10' X 9'
This example is suitable for a Day-1 design with a maximum of 192 horizontal cables (leaving room for future growth).
A two-rack room is rarely adequate, because it has very limited space for future equipment or cabling to be added. Therefore, it shall only be used as a last resort, and then only with the approval of the ITPM.

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

99

June 24, 2015

APPENDICES
SAMPLE TELECOMMUNICATIONS ROOM PLAN DETAILS
6.1.4 IDF: 3 RACKS ­ 10' X 12'
This example is suitable for a Day-1 design with a maximum of 288 horizontal cables (leaving room for future growth). This is the standard IDF configuration.

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

100

June 24, 2015

APPENDICES
SAMPLE TELECOMMUNICATIONS ROOM PLAN DETAILS
6.1.5 IDF AND MDF: 4 RACKS ­ 10' X 15'
This example is suitable for a Day-1 design with a maximum of 336 horizontal cables (leaving room for future growth). This solution is preferable over the face-to-face design depicted below in section 6.1.6.

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

101

June 24, 2015

APPENDICES
SAMPLE TELECOMMUNICATIONS ROOM PLAN DETAILS
6.1.6 IDF AND MDF: 4 RACKS (2 ROWS) ­ 9' X 16'
This example is suitable for a Day-1 design with a maximum of 336 horizontal cables (leaving room for future growth). This solution shall only be used if the example in 6.1.5 (above) is not feasible.

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

102

June 24, 2015

APPENDICES
SAMPLE TELECOMMUNICATIONS ROOM PLAN DETAILS
6.1.7 MCF: 6 RACKS (2 ROWS) ­ 12' X 16'
This example is a starting point for designing a main communication facility (MCF). If circumstances require, this example could also be used for a telecommunications room, for a Day-1 design with a maximum of 504 horizontal cables (leaving room for future growth).
This is the standard configuration for main communication facilities at WSUP.

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

103

June 24, 2015

Appendices
SAMPLE RACK ELEVATION DETAIL
6.2 Sample Rack Elevation Detail
The following pages show sample scaled rack elevation details. The Designer shall provide similar information for each new or existing telecommunications room affected by the project.
This information shall be provided either as a portion of the Project Manual or on the drawings, and shall be considered part of the Construction Documents.
The leftmost rack shown in each elevation detail below shall be adjacent to the wall. It may be necessary in some projects to invert the left-to-right arrangement such that the fiber optic patch panel and copper backbone cabling always terminate in the rack adjacent to the wall, and so that the horizontal cabling always terminates in the rack away from the wall.

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

104

June 24, 2015

6.2.1 IDF: 1 RACK

Appendices
SAMPLE RACK ELEVATION DETAIL

A

B

C

D

E

F

G

H

J

K

L

M

1

1

1

1

1

1

1

1

1

1

1

1

2

2

2

2

2

2

2

2

2

2

2

2

3

3

3

3

3

3

3

3

3

3

3

3

4

4

4

4

4

4

4

4

4

4

4

4

5

5

5

5

5

5

5

5

5

5

5

5

6

6

6

6

6

6

6

6

6

6

6

6

1

2

3

4

5

6

1

2

3

4

5

6

7

8

9

10

11

12

7

8

9

10

11

12

13

14

15

16

17

18

13

14

15

16

17

18

19

20

21

22

23

24

AM PT RAC

19

20

21

22

23

24

AM PT RAC

1

2

3

4

5

6

7

8

9

10

11

12

13

14

15

16

17

18

19

20

21

22

23

24

AM PT RAC

1

2

3

4

5

6

1

2

3

4

5

6

7

8

9

10

11

12

7

8

9

10

11

12

13

14

15

16

17

18

13

14

15

16

17

18

19

20

21

22

23

24

AM PT RAC

19

20

21

22

23

24

AM PT RAC

1

2

3

4

5

6

1

2

3

4

5

6

7

8

9

10

11

12

7

8

9

10

11

12

13

14

15

16

17

18

13

14

15

16

17

18

19

20

21

22

23

24

AM PT RAC

19

20

21

22

23

24

AM PT RAC

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

105

June 24, 2015

6.2.2 IDF: 2 RACKS

Fiber Optic Cabling

A

B

C

D

E

F

G

H

J

K

L

M

1

1

1

1

1

1

1

1

1

1

1

1

2

2

2

2

2

2

2

2

2

2

2

2

3

3

3

3

3

3

3

3

3

3

3

3

4

4

4

4

4

4

4

4

4

4

4

4

5

5

5

5

5

5

5

5

5

5

5

5

6

6

6

6

6

6

6

6

6

6

6

6

HP 2524 for HVAC
Panduit WMPH2E
50 pr copper from the MDF 2pr punched to ea. jack

1

2

3

4

5

6

7

8

9

10

11

12

13

14

15

16

17

18

19

20

21

22

23

24

AM PT RAC

Appendices
SAMPLE RACK ELEVATION DETAIL

1

2

3

4

5

6

1

2

3

4

5

6

7

8

9

10

11

12

7

8

9

10

11

12

13

14

15

16

17

18

13

14

15

16

17

18

19

20

21

22

23

24

AM PT RAC

19

20

21

22

23

24

AM PT RAC

1

2

3

4

5

6

1

2

3

4

5

6

7

8

9

10

11

12

7

8

9

10

11

12

13

14

15

16

17

18

13

14

15

16

17

18

19

20

