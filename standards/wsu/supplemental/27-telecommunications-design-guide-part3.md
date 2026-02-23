# 27-telecommunications-design-guide (Part 3 of 10)

> **Continued from:** 27-telecommunications-design-guide-part2.md

---

connect in the interposing telecommunications room. Intra-building

backbone cabling shall be continuous (non-spliced) between the main

telecommunications room and each intermediate telecommunications

room.

4.4.1.1 BACKBONE RACEWAY SIZE AND QUANTITY REQUIREMENTS

A. Future growth requirements shall be considered when sizing intra-building backbone pathways. The cost to install additional spare pathways during initial construction is significantly less than the cost of retrofitting additional pathway in the future.

B. In general, for new construction and modernization projects, WSUP requires a minimum quantity of four EzPath sleeves (4-inch size) leaving the main telecommunications room/entrance facility enroute to the intermediate telecommunications rooms on floors above. However, for buildings higher than five floors, additional EzPath sleeves shall be provided.

·

For projects in existing buildings, if existing riser pathways comprised

of conduit sleeves are intended for reuse, firestopping pillows shall be

used. Caulk and putty products are not permitted.

4.4.1.1.1 SINGLE-STORY BUILDINGS
A. For single-story buildings with multiple telecommunications rooms, 4-inch conduit pathways shall be routed through the ceiling, not in or under the floor slab. The Designer shall determine the number of 4-inch conduits required to serve initial and future backbone cabling requirements.

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

40

June 24, 2015

DESIGN CRITERIA
BACKBONE DISTRIBUTION SYSTEMS
1. In cases where it is not possible to route 4-inch conduits to each of the telecommunications rooms, three 2-inch conduits may be substituted for each required 4-inch conduit.
4.4.1.1.2 MULTI-STORY BUILDINGS A. In new construction and modernization projects, telecommunications rooms shall be vertically aligned (stacked) floor-to-floor wherever possible. Sleeved vertical pathways shall be extended to the roof (or to an attic space with access to the roof) to facilitate access for future roof or side-of-building mounted antennas or other telecommunications equipment.
B. Ladder racking shall be vertically mounted in the stacked telecommunications rooms to route and support backbone cable passing from the room below to upper rooms.
4.4.2 INTRA-BUILDING BACKBONE CABLING
The diagram below depicts intra-building and inter-building backbone cabling requirements (including strand and pair counts) for WSUP buildings:

4.4.2.1 INTRA-BUILDING BACKBONE CABLE TYPES

A. WSUP uses three types of telecommunications cabling for intra-building backbone systems:

· Multipair copper voice backbone cable. · 8/125µm OS2 Singlemode fiber optic cabling (yellow color).

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

41

June 24, 2015

DESIGN CRITERIA
BACKBONE DISTRIBUTION SYSTEMS

· 50/125µm OM3 Multimode fiber optic cabling (aqua color). o 62.5/125µm OM1 is permitted only for additions to existing infrastructure in a building. Do not mix multimode fiber optic cabling types in a building.
B. When a horizontal application requires 10GB communications, WSUP uses:
· 8/125µm OM2 Singlemode fiber optic cabling (yellow color)
C. Splices are prohibited for backbone cabling.
4.4.2.2 STRAND AND PAIR COUNTS
A. The diagram above indicates the minimum standard provisions for all strand and pair counts. Each application should be increased above these counts if additional pairs or strands are required.
B. Backbone cable sizing (# of strands, # of pairs) shall be considered with respect to possible future requirements. The cost to add additional backbone pairs and strands during the initial installation is significantly less than the cost of adding another cable in the future.
The Designer shall inquire whether 40GB or 100GB backbone bandwidths are required. These bandwidths require multiple strands for each circuit.
C. WSUP permits appropriate use of hybrid singlemode/multimode fiber optic cabling, and allows both types of fiber to be terminated on separate bulkheads in a single fiber optic patch panel.
4.4.2.3 CABLE SEGREGATION
In no case shall copper or fiber optic backbone cabling be run in the same raceways as those used by electrical power conductors. However copper, fiber optic and other low-voltage cables are permitted to run together in shared raceways.
4.4.2.4 INNERDUCT FOR RISER APPLICATIONS
The Designer shall show on the Contract Documents where innerduct is required for routing inside plant fiber optic backbone cabling, in accordance with the following conditions:
· Innerduct is required for routing inside plant fiber optic backbone cabling through all vertical riser pathways (conduits and sleeves) that exceed 4 feet in length.
· Innerduct is also required for routing inside plant fiber optic backbone cabling through cable trays where larger outside plant cable shares the cable tray. This is a relatively rare circumstance.
· Otherwise, innerduct is not required for routing inside plant fiber optic backbone cabling.
See Section 4.5.3.4.6 for innerduct requirements for horizontal and GPON applications.
See Section 4.4.3.2.9 for innerduct requirements for outside plant fiber optic backbone cabling.

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

42

June 24, 2015

DESIGN CRITERIA
BACKBONE DISTRIBUTION SYSTEMS
4.4.3 INTER-BUILDING (CAMPUS) BACKBONE PATHWAYS
The Designer shall follow the guidelines in the BICSI TDMM and the BICSI OSPDRM when designing underground outside plant pathways.
4.4.3.1 EXISTING CONDITIONS AT THE PULLMAN CAMPUS
The existing conditions of the outside plant pathway infrastructure at the WSUP campus are not ideal. There is much shared use of underground tunnels by multiple different utilities, in some cases presenting circumstances that can be hostile, such as asbestos, steam and electrical power.
· The WSUP ITPM shall designate the routing to be used for each outside plant cable that is designed for a project.
· The Designer shall receive training and certification from WSUP Facilities Services prior to entering any underground spaces at the WSUP campus. Untrained, uncertified Designers shall not enter any underground spaces at the WSUP campus.
· Proper safety procedures and hardware shall be used when accessing any underground spaces.
· The ITPM and the Designer shall physically verify all OSP routes together prior to designing an OSP cable installation.
The outside plant pathway standard requirements described below are intended for application wherever circumstances will permit, and especially for new pathway installation. However, acknowledging that best-case conditions do not always exist, the WSUP ITPM will provide direction to the Designer on a case-by-case basis regarding the extent to which the design shall comply with the standard-practice requirements below.
4.4.3.2 DUCTBANK
The diagram below depicts the features of telecommunications ductbank, which are described in detail in the paragraphs that follow.

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

43

June 24, 2015

DESIGN CRITERIA
BACKBONE DISTRIBUTION SYSTEMS

4.4.3.2.1 CONDUIT TYPES
A. WSUP requires 4-inch Schedule 40 PVC for all outside plant pathway except ducts serving Blue Light Emergency Telephones, which shall be trade-size 1½ inch conduit.
B. OSP conduit shall transition from PVC to PVC-coated rigid steel conduit when it enters within 10 feet of the building foundation, and shall route from that point to the building entrance facility. PVC-coated, rigid steel conduit is intended to defend against the shearing effects of differential ground settling around the building foundation. It also increases the protection against future landscaping activities near the building.

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

44

June 24, 2015

DESIGN CRITERIA
BACKBONE DISTRIBUTION SYSTEMS

· Transition back to PVC conduit after passing five feet inside the building foundation is acceptable as long as the conduit remains in or under the slab. Otherwise, it shall transition to rigid galvanized steel conduit.
· A maximum of fifty feet of outdoor-rated cable is permitted in a building space. Therefore, rigid galvanized steel conduit shall be used to route the cable until it is close enough to its termination point that fifty feet or less of outdoor-rated cable (including slack loops) will be exposed.
C. The use of flexible metallic conduit and flexible non-metallic conduit is prohibited.
4.4.3.2.2 GROUND CONDUCTOR
A. A continuous ground conductor (#2 AWG) shall be installed running the length of each ductbank. The ground conductor shall be placed on the top row of conduits so that it will be detectable by underground utility locating equipment.
B. The ground conductor shall be bonded to other ground conductors from other ductbanks meeting at an underground maintenance hole or handhole.
C. The ground conductor shall be bonded to the main telecommunications grounding busbar in the MDF or main entrance facility of the building.

4.4.3.2.3 BURIAL DEPTH AND SLOPE
A. The preferred ductbank depth is 36 inches to the top of the conduit. Where this is unattainable, a 30 inch depth is permitted.

· Under no circumstances will ductbanks ever be permitted shallower than the
extent of the frost zone. In Pullman, the frost zone reaches 30 inches below the surface, according to the City of Pullman3.

B. Conduit to be used for routing entrance cables from third party service providers to an entrance facility shall be installed per the service providers' requirements, generally 36 to 48 inches deep. The Designer shall consult with the service providers prior to designing conduits serving an entrance facility.

C. A continuous drain slope should exist at all points along the ductbank to allow drainage and prevent the accumulation of water.

· A drain slope of ¼ inch per foot is desirable where possible. · Where ¼ inch per foot is not possible due to inadequate natural slope or long
duct runs, a drain slope of no less than 1/8 inch per foot is acceptable. · If no other option exists, require the Contractor to provide a "center crown"
drain slope by sloping the first half of the ductbank up towards the midpoint, and then down from the midpoint to the end. Of course, the center crown technique cannot be used for conduits between a maintenance hole and a building, because water would then drain into the building.

3 http://www.pullman-wa.gov/city-of-pullman-statistics

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

45

June 24, 2015

DESIGN CRITERIA
BACKBONE DISTRIBUTION SYSTEMS
4.4.3.2.4 CONDUIT SWEEPS (BENDS)
A. WSUP has standardized on the use of factory-manufactured fiberglass sweeps with a minimum bend radius of 48 inches for all OSP ductbanks with the following exceptions and alternatives:
· Shallow curves comprised of continuous lengths of individual straight RNC conduit are permissible with a minimum sweep radius of 40 feet.
· Where cabling larger than 400-PR UTP copper is intended to be installed, conduit bends shall have a radius larger than 48 inches. The Designer shall consult with the WSUP ITPM on a case-by-case basis to select appropriatelysized conduit sweeps.
B. The Designer shall minimize, where possible, the effects of sidewall pressure between the cable and conduit at bend points, by designing bends with the tightest bend radii to be near the cable feed end of the duct section rather than the middle or end of the duct bank.
4.4.3.2.5 DUCTBANK ENCASEMENT
WSUP requires concrete encasement with full-length reinforcement and formed sides for all ductbanks except ducts serving Blue Light Emergency Telephones, which shall not be encased in concrete.
A. Prior to concrete being poured, the WSUP ITPM or a designated representative shall observe the OSP conduit installation to identify unacceptable installations that need to be corrected prior to concrete encasement.
B. In general, direct-buried conduit ductbanks are not permissible, unless extenuating circumstances warrant and this is approved by WSUP through the SVR process. Should the use of direct-buried conduit ductbank be warranted, the Designer shall ensure that all bends in the ductbanks are encased in concrete.
C. Wherever cold-joints are required in concrete encasement, the design shall require rebar spanning the joint between ductbank encasement segments.
4.4.3.2.6 NUMBER OF DUCTS
A. The OSP pathway system shall accommodate the requirements for signal and low-voltage cabling systems at WSUP facilities. The Designer shall inquire with the WSUP ITPM and FSPM about the potential for future buildings or building expansions that may adversely affect an existing or proposed distribution pathway, and accommodate those plans within the design.
B. The number of 4-inch conduits in a ductbank should be determined to meet the needs of the specific application and should offer future expansion capability. The following list is a guideline for consideration when designing a new ductbank:

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

46

June 24, 2015

DESIGN CRITERIA
BACKBONE DISTRIBUTION SYSTEMS

· Small utility buildings up to 5,000 sq. ft.: 2 ducts (approvable on a case-bycase basis)
· Buildings up to 100,000 sq. ft.: 4 ducts · Buildings 100,000 sq. ft. to 300,000 sq. ft.: 6 ducts · Buildings larger than 300,000 sq. ft.: multiple redundant entrances with 6
ducts each · Buildings serving as a data center or a Main Communication Facility (MCF):
6 ducts
4.4.3.2.7 DUCTBANK LENGTH
A. In general, ductbank systems shall be designed with section lengths averaging 400 feet and as straight as possible.
B. The maximum permissible ductbank length (between maintenance holes and/or buildings) is 600 ft. Ductbank runs that exceed this distance require intermediate maintenance holes or handholes. This requirement may be waived through the SVR process in rare cases having the following conditions:
· The ductbank run has no bends. · The Designer can demonstrate that the pulling tension of WSUP's standard
OSP telecommunications cable types will not be exceeded during installation.
4.4.3.2.8 SEPARATION FROM OTHER UTILITIES
A. In general, ductbank used as pathway for telecommunications and other lowvoltage cabling should not be routed with other utilities. Budgetary constraints, space limitations, and various obstructions can make this difficult to achieve at times. Should shared routing be a necessity (perhaps for overbuild construction projects), the Designer shall ensure that adequate separation exists between ducts used for telecommunications and ducts used for other utilities.
B. The pathway system shall be designed such that telecommunications and other low-voltage systems do not share conduits, maintenance holes, or handholes with the electrical power distribution system. The telecommunications distribution pathway shall also maintain minimum separation distances from electrical power distribution infrastructure as required by WSUP.
C. Unfortunately, circumstances require some shared use of underground tunnels.
The vertical and horizontal separation requirements for OSP telecommunications pathways from other underground utility infrastructure are as follows:

4.4.3.2.8.1 Proximity to Power or Other Foreign Conduits
NESC requirements state that outside plant telecommunications conduits shall not be installed closer to power conduits or other unidentified underground conduits than:

o 3 inches where the surrounding material is concrete o 4 inches where the surrounding material is masonry o 12 inches where the surrounding material is well-tamped earth

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

47

June 24, 2015

DESIGN CRITERIA
BACKBONE DISTRIBUTION SYSTEMS

The NESC requirements above are focused on safety issues, and the performance of telecommunications systems can be negatively affected by the presence of nearby sources of EMI, even though the NESC safety-related separation requirements are met. Where the Designer is concerned about EMI due to the proximity of power distribution infrastructure, the Designer shall discuss the issue with the WSUP ITPM.
4.4.3.2.8.2 Proximity to Water, Gas, or Oil Conduits
The proximity between outside plant telecommunications conduits and other non-power conduits shall not be closer than:
o 6 inches where the conduits cross o 12 inches where the conduits run parallel to each other
Telecommunications conduits running parallel to water, gas, or oil conduits shall not be installed vertically above the other conduits, but rather to the side of the conduits. This arrangement should contribute to decreased disruption to the telecommunications conduits in the event of excavation maintenance activities associated with the other nearby conduits.
4.4.3.2.8.3 Proximity to Steam Lines and Steam Utilidors
A. A minimum separation distance of 12 inches is required between a steam utilidor and telecommunications conduits.
B. Steam lines pose two primary risks to telecommunications cabling:
· Under steady state operating conditions, objects in the vicinity of steam lines may become warm due to heat lost through the insulation of the steam line. As the temperature of telecommunications cabling increases, its performance can degrade. In situations where there is concern about the risk of exposure to steady state heat, the separation distance between the steam line and telecommunications infrastructure shall be increased.
· In the event of a steam line failure in the proximity of telecommunications infrastructure, significant damage to the conduits and cabling can result from the high-temperature steam. In situations where there is concern about the risk of exposure to high temperatures from steam line failure events, the design shall require telecommunications conduits to be encased within an insulating sleeve in the vicinity of the risk.
C. High-temperature insulation may be necessary to protect telecommunications conduits and cabling.
D. WSUP's practice is to install steam lines in utilidors, rather than to direct-bury the steam lines. The utilidors are typically 3 to 4 feet high, and may be buried with 0 to 2 feet of surface cover. Therefore, the bottom of most utilidors on campus is typically somewhere between 3 and 6 feet deep.
E. The Designer shall field-investigate the actual utilidor routing to identify accurate field conditions. Potholing to confirm record drawing information is typically required.

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

48

June 24, 2015

DESIGN CRITERIA
BACKBONE DISTRIBUTION SYSTEMS
F. Where physical conditions appear to preclude compliance with the following requirements, an SVR shall be submitted demonstrating solutions for mitigating exposure to worst-case conditions, including steam line failure where steam vents in the direction of the telecommunications conduits.
4.4.3.2.8.3.1 Crossing Above Steam Utilidors
A. Due to the requirement to bury conduit beneath the frost line, a cover depth of 50 inches is required for a topside conduit crossing. Unless a utilidor has at least this much topside cover, it will not be possible to install a single-level conduit ductbank over the top of the utilidor while maintaining a 12 inch separation from the top of the utilidor and while keeping the conduit below the frost line.
· It is unlikely that a circumstance permitting a topside crossing will occur at WSUP.
B. Telecommunications ductbanks shall not cross over the top of a steam utilidor in a live load area where vehicle traffic passes without the review of a Civil Engineer.
4.4.3.2.8.3.2 Crossing Beneath Steam Utilidors
A. Most commonly, where telecommunications conduits must cross a steam utilidor, the conduits must cross underneath the utilidor. Care shall be taken to avoid creating a dip in the conduit at this point where water will collect ­ the conduit slope shall be designed to permit any water entering the conduits to drain out. The following diagram depicts this concept:

B. The Designer shall design a utilidor crossing similar to the pre-approved solution shown in the diagram above, or some other solution that accomplishes a utilidor crossing without trapped water and without risking cable damage due to nearby steam heat. The Designer shall include details of any steam utilidor crossings in the Construction Documents.

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

49

June 24, 2015

DESIGN CRITERIA
BACKBONE DISTRIBUTION SYSTEMS

4.4.3.2.8.3.3 Direct Buried Steam Lines
A. If it becomes necessary to install telecommunications conduits in the vicinity of direct-buried steam lines, the following requirements apply:
· Telecommunications conduits shall not be installed closer than 12 inches to steam lines, and shall cross perpendicular to the steam lines.
· Direct-buried steam lines within 12 to 24 inches of telecommunications conduits shall be encased within an insulated pipe sleeve surrounding the steam line. The sleeve shall be constructed from a material designed to withstand steam temperatures and protect against physical/mechanical damage from jets of steam. The insulated sleeve shall extend at least 5 feet on both sides of the crossing point of the telecommunications conduits.
4.4.3.2.9 INNERDUCT FOR OUTSIDE PLANT APPLICATIONS
The Designer shall show on the Contract Documents where innerduct is required for routing outside plant fiber optic backbone cabling, in accordance with the following conditions:
· Innerduct is required for routing outside plant fiber optic backbone cabling through all conduits (ductbank) and sleeves that exceed 4 feet in length.
· Innerduct is not required for routing outside plant fiber optic backbone cabling through underground tunnels.
· Innerduct is not required for routing outside plant fiber optic backbone cabling after it leaves an entrance conduit and terminates on a patch panel (within the 50-foot rule).
See Section 4.5.3.4.6 for innerduct requirements for horizontal and GPON applications.
See Section 4.4.2.4 for innerduct requirements for inside plant fiber optic backbone cabling.
4.4.3.2.10 COORDINATION WITH UTILITY SERVICE PROVIDERS
The Designer shall inquire with the WSUP ITPM to determine whether services from utility service providers will be necessary. If so, the Designer shall contact the utilities to obtain their entrance pathway, entrance facility, and demarcation point requirements.
4.4.3.3 MAINTENANCE HOLES AND HANDHOLES
A. Typically, maintenance holes are installed for main ductbanks (i.e., ductbanks used for routing large portions of the telecommunications system backbone), and handholes/pullholes are installed for subsidiary ductbanks (i.e., ductbanks serving a single small building).
B. Maintenance holes and their covers shall be appropriately sized for the application.
· Covers for maintenance holes and handholes shall be either lockable or use bolts to prevent unauthorized access.
· Diamond plate hinged covers and removable diamond plate covers are not

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

50

June 24, 2015

DESIGN CRITERIA
BACKBONE DISTRIBUTION SYSTEMS
permitted for maintenance holes at WSUP.
C. Telecommunications maintenance holes and handholes shall not be shared with electrical power distribution infrastructure. In general, powered devices should not be located in telecommunications maintenance holes and handholes.
D. The number of duct entrances in a maintenance hole or handhole should be sized for both immediate and future requirements. Also, splayed duct entrance arrangements are preferred over center entrances.
· It is desirable to have ducts enter and exit from opposite ends of a maintenance hole or handhole. Sidewall duct entrances should be avoided because such entrances may obstruct racking space, cause cable bends to exceed limits, interfere with cable maintenance activities, and increase construction costs during cable installation.
· WSUP recognizes that sidewall duct entry may be necessary or desirable in some circumstances. In these cases, sidewall ducts shall enter and exit at diagonally opposite corners ­ ducts shall not enter and exit at the midpoints of the endwalls or sidewalls. The Designer shall ensure that endwall and sidewall duct entry in a maintenance hole or handhole will not hinder access to the maintenance hole, or to the proper installation and maintenance of cabling.
E. Ducts shall be designed to enter the maintenance holes and handholes starting at the lowest conduit knockouts and moving upward, preserving remaining knockouts accessible for future conduit additions. The Designer shall design the duct entrances such that the relative position of each duct does not change as it enters and exits the maintenance hole or handhole. Also, the Designer shall endeavor to design ductbank arrangements so that the conduits enter and exit a sequence of maintenance holes or handholes in the same relative positions.
F. Splices in backbone fiber optic cable are not allowed, and while splices in backbone copper cable may be permitted in some rare cases (through an approved ADR), they are discouraged. However, when sizing OSP telecommunications maintenance holes, the design shall require the Contractor to provide space for possible future splice closures when required (for example, to repair cable breaks).
G. Some situations may require placement of maintenance holes at below-typical depths. In such cases, the top of the maintenance hole shall be placed at normal depth, and the height of maintenance hole shall be increased through the use of intermediate riser extensions between the base and the top. WSUP wishes to avoid deep-collar entrance portals wherever possible, to improve lighting and ventilation.

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

51

June 24, 2015

DESIGN CRITERIA
BACKBONE DISTRIBUTION SYSTEMS
4.4.3.4 AERIAL DISTRIBUTION
Aerial distribution of telecommunications cabling at WSUP facilities is not authorized. If an application requires aerial distribution, permission to use this method shall be requested through the SVR process.
4.4.3.5 BRIDGE AND WATERWAY CROSSINGS
A Civil Engineer shall review the construction of bridge and waterway crossing distribution systems. The design and installation shall also be reviewed by the WSUP ITPM.
4.4.3.6 WIRELESS AND RADIO SYSTEM DISTRIBUTION
A. WSUP facilities use wireless or radio systems for telecommunications with mobile units and personnel, both on and off campus. These systems typically use one or more radio antennas connected by cabling to radio transceiver equipment. In some cases, the radio equipment may be interfaced into the telephone system. The outside plant telecommunications substructure shall be designed with adequate cable routing pathways between antenna locations, radio transceiver locations, and the telephone backbone cabling system.
B. Radio antenna transmission cables that connect the antenna to the radio transceiver emit radio frequency (RF) radiation. These cables may be routed through the common telecommunications ductbank and maintenance hole system if necessary, but shall be routed in a separate conduit from non-fiber optic telecommunications cables. Cables containing RF radiation shall be shielded cables.
C. Radio interconnection cables (for analog or digital signaling to remote radio operating positions or to the telephone system) typically emit low levels of radio frequency radiation. These interconnection cables shall be routed through the common telecommunications ductbank and maintenance hole system. Individual conduits may be shared for these interconnection cables and other telecommunications services, and available cable pairs in telephone backbone cables may be used for these interconnections, provided that the signaling is analog or digital signaling, and is not direct radio frequency signal.
D. The Designer shall inquire with the WSUP FSPM whether a building will require rooftop satellite, wireless or radio systems. These systems typically use one or more radio antennas connected by cabling to radio transceiver equipment. If rooftop applications are required, pathways shall be designed from rooftop locations down to the nearest telecommunications room to serve these applications.
4.4.4 CAMPUS CABLING
When OSP cabling is required, the Designer shall follow the guidelines in the BICSI TDMM and the BICSI OSPDRM.

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

52

June 24, 2015

DESIGN CRITERIA
HORIZONTAL DISTRIBUTION SYSTEMS

A. The design shall require that a slack loop be installed inside the nearest maintenance hole or handhole (not stored in the TR). The Designer shall require that sufficient racking hardware be provided in the maintenance hole or handhole to support the slack loop.
B. The length of the loop shall be a minimum of 25 feet. The Designer shall consider the arrangement of the telecommunications room and the possibility of a rearrangement that might consume the cable slack. If necessary, additional slack shall be required in the design, up to the NEC limit of 50 feet of exposed OSP-rated cabling.
4.4.4.1 UTILITY SERVICES
At WSUP, telephone services, cable television services and Internet services are typically provided via campus infrastructure. The Designer shall request from the WSUP ITPM information about any needed telecommunications infrastructure to support the required services. The Designer shall also request similar information from the WSUP FSPM for requirements to support non-WSUP tenants of the building.
4.4.4.2 WIRELESS AND RADIO SYSTEM DISTRIBUTION
A. Outdoor-rated backbone cabling shall be designed to serve rooftop satellite, wireless, or other radio system applications. Lightning protection equipment shall also be designed as appropriate.
B. Radio antenna transmission cables that connect the antenna to the radio transceiver emit radio frequency (RF) radiation. These cables may be routed in a separate conduit from other telecommunications cables. Cables containing RF radiation shall be shielded cables.
4.5 Horizontal Distribution Systems
Please refer to Chapter 5, Horizontal Distribution Systems in the BICSI TDMM for general information regarding the design of horizontal distribution pathway and cabling. The following requirements take precedence over the BICSI TDMM guidelines for telecommunications infrastructure at WSUP facilities:
4.5.1 DEVICE BOX CONSIDERATIONS
A. Device boxes intended for use with low-voltage cabling (telecommunications, CATV, etc.) shall not host electrical power receptacles or power wiring. "Combo boxes" (divided, multi-gang device boxes for power and data behind a single faceplate) are not permitted.
B. Device boxes shall not be mounted in the floor (i.e. "floor boxes") except where no suitable alternative exists. If device boxes must be mounted in the floor, each device box shall be served with its own individual conduit ­ floor boxes shall not be "daisy-chained" together.

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

53

June 24, 2015

DESIGN CRITERIA
HORIZONTAL DISTRIBUTION SYSTEMS

·

Power outlets may be combined with CATV and telecommunications

cabling in floor boxes if the power wiring is routed to the floor boxes

separately from the other cable media, and if the floor box provides for

metallic barrier segregation of the power and telecommunications cabling

within the box.

C. Within the limitations of the project budget, the provision of spare outlets and spare jacks in a work area is encouraged, to provide flexibility for future needs.

D. Both telecommunications cabling and CATV coaxial cabling are permitted to be terminated in a shared device box.

E. Device boxes for telecommunications outlets shall be mounted at the same height as the electrical power receptacles.

4.5.1.1 FOR NEW CONSTRUCTION AND FULL REMODEL

A. A device box shall be provided for each telecommunications outlet. Device boxes shall be 4"x4"x3-½" (where 2-¼" is the depth of the box and 1-¼" is the depth of the extension ring, with an overall depth of 3-½"). Device boxes shall be recess-mounted.

·

WSUP requires double-gang faceplates for all telecommunications

outlets.

B. Surface-mounted device boxes are not acceptable. However, for concrete masonry unit (CMU) walls or other wall types that may obstruct cable or conduit installation, the Designer shall request direction from the WSUP ITPM on a caseby-case basis.

4.5.1.2 FOR OTHER PROJECTS
A. Existing device boxes and conduits shall be reused where they are standardscompliant or where it can be verified that the existing conduits and boxes will permit telecommunications cabling to be installed without negatively affecting the performance of the cabling. The bend radius of the cabling inside each box shall be considered carefully when evaluating existing boxes. For concealed conduits that cannot be verified, the Designer shall assist the WSUP ITPM to consider conduit length, number of bends and cable fill percentage, then decide on a case-by-case basis whether they are suitable for reuse.
B. A device box shall be provided for each telecommunications outlet. Device boxes shall be recess-mounted wherever possible and shall be 4"x4" and at least 2-½" deep (a 3-½" depth is preferable). Surface-mounted device boxes (if required) shall be standard double gang (4" x 4") and at least 2-½" deep.
C. Where cabling can be fished through interstitial wall spaces, it is typically permissible to use faceplate mounting brackets in lieu of device boxes.

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

54

June 24, 2015

DESIGN CRITERIA
HORIZONTAL DISTRIBUTION SYSTEMS

4.5.2 HORIZONTAL PATHWAY SYSTEMS
The process of selecting the type of pathway that would be appropriate for a particular project shall be a cooperative effort involving the Designer and the WSUP ITPM.

4.5.2.1 GENERAL PATHWAY DESIGN CONSIDERATIONS
A. All cables shall be fully supported and properly transitioned throughout the length of the cables, including proper bend radius fittings at pathway transitions. Where cabling is routed vertically, it shall be appropriately secured such that the weight of the cabling does not subject the cabling to stresses that could potentially reduce the performance of the cabling.
B. The Designer shall discuss pathway type and size options with the WSUP ITPM.
1. The Designer shall discuss the relative merits of the pathway options available and shall assist the WSUP ITPM and the project design team to select the most appropriate pathway solution for the project.
2. The future growth anticipated for the facilities affected by the project shall be discussed. Horizontal feeder pathways (cable trays, conduits from TRs to distribution junction boxes) shall be sized to support the initial cabling installation plus a minimum of 25% growth.
3. For new construction and full remodel projects, J-hook pathways are not permitted. For other projects, J-hook pathways shall be sized to support 100% additional cables after the original cabling installation. In other words, the pathway shall be no more than 50% full after installation is completed.
C. Spare pathway shall be designed to terminate at building perimeters where future expansion of the building is anticipated.
D. When considering the design of a ceiling-located cable tray or J-hook pathway, the Designer shall verify that the pathway locations will comply with accessibility and clearance requirements. Cable tray and J-hook pathways routed through ceiling spaces shall be designed such that all installed cable is conveniently accessible after construction, both for cable maintenance and to install subsequent cable additions. J-hooks shall be installed at approximate intervals of 4 to 5 feet. Conduit shall be used to span inaccessible areas where the pathway will cross "hard-lid" ceilings, where ceiling tiles are not readily removable, or where accessibility is impeded.
E. Pathway routing shall remain on the same floor as the telecommunications room and telecommunications outlets served by the pathways. Where project-specific conditions exist that justify other routing, the Designer shall request WSUP approval through the SVR process.
F. "Poke-thru" penetrations to the ceiling space of the floor below are normally not permitted. For minor remodel construction, poke-thru penetrations may be allowed given budgetary, project size, or other limiting factors. Permission to use poke-thru pathways in any circumstance requires an SVR on a project-by-project basis, and always requires the services of a structural engineer to avoid

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

55

June 24, 2015

DESIGN CRITERIA
HORIZONTAL DISTRIBUTION SYSTEMS

irreparable structural damage.

G. All wall and floor penetrations for cabling shall be fully sleeved with bushings, and protected in accordance with the requirements in the International Building Code.

H. For on-grade slab construction, telecommunications conduits shall not be routed in or under the slab (a designated wet environment) unless no other options exist.

·

Floor boxes under conference tables in Conference Rooms and under

instructor podiums in Classrooms are granted exception to this

requirement.

·

In any application (including Conference Rooms and Classrooms) where

telecommunications conduit passes in or under an on-grade slab,

outdoor-rated cabling shall be provided.

4.5.2.2 PATHWAYS FOR NEW CONSTRUCTION AND MODERNIZATION PROJECTS
A. Where ceiling spaces will be inaccessible after construction, the only permitted pathway option is conduit. J-hook pathway systems, cable tray, and wire basket are not permitted if ceiling spaces will be difficult to access after construction.
B. Surface raceways and surface-mounted device boxes are not permitted.

4.5.2.3 PATHWAYS FOR MINOR REMODEL AND TELECOMMUNICATIONS-ONLY PROJECTS
A. For minor remodel construction, there may not be an existing (or suitable space for a new) telecommunications room available on the same floor as an outlet. While pathways shall generally be designed from the device box serving the telecommunications outlet to the nearest telecommunications room on the same floor as the outlet, this requirement may be waived at the discretion of the WSUP ITPM.
B. Existing pathways shall be reused where existing raceway is standardscompliant, or where it can be verified that the existing pathway will permit telecommunications cabling to be installed without negatively affecting the performance of the cabling. Where a pathway is concealed or cannot otherwise be verified, the Designer shall request direction from the WSUP ITPM on a caseby-case basis.
C. Where existing pathways cannot be reused, or where additional pathways are required:
1. J-hook pathway may be used. D-ring and bridal-ring pathways are not permitted. J-hook pathways shall be established through concealed spaces. J-hook pathways shall be sized for a minimum of 100% expansion. In other words, the pathway shall be no more than 50% full after installation is completed.

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

56

June 24, 2015

DESIGN CRITERIA
HORIZONTAL DISTRIBUTION SYSTEMS

2. When 40 or more cables are designed to be routed through an area, the use of cable tray or conduit shall be considered in lieu of J-hooks.
D. It may be permissible to use faceplate mounting brackets in lieu of device boxes. In these cases, cabling is routed to the outlet location through interstitial wall spaces. WSUP permission for this method is required on a project-by-project basis.

4.5.2.4 CABLE TRAY PATHWAY SYSTEMS
A. In general, cable tray systems shall be located in corridor or office throughway spaces, and shall not be installed above office or classroom space. Distances from EMI/RFI sources shall be maintained according to Section 4.2, Electromagnetic Compatibility (above), regardless of whether the raceway is routing copper- or fiber optic based media.
B. From a technology perspective, WSUP ITS does not have a preference for any particular style of cable tray (solid bottom, open rungs, welded wire, etc.) so long as the cable tray performs reliably. Cable tray style shall be determined by the Designer in coordination with the Architect to ensure that the selected tray contributes to the aesthetic appearance of the building while meeting the budgetary parameters of the project.
· Steel cable tray is preferred over aluminum because aluminum is much easier to dent and deform, either inadvertently or through careless handling during construction.
· Where the Architect wishes to have the cable tray painted to blend in with its surroundings, the Designer shall add cautionary notes to the Contract Documents prohibiting the painting of telecommunications cabling which could void the manufacturer's warranty.
· Where solid-bottom tray is specified, the bottom shall have openings at strategic locations (not inside telecommunications rooms) to allow water to drain out. Otherwise, solid-bottom tray may channel water from leaks, condensation, or fire suppression into telecommunications rooms.
C. Wall mounting is preferred for cable tray because it provides unrestricted access to the side of the cable tray.
· Where wall mounting is not practical, use trapeze-style hangers.
D. The Designer shall coordinate the selection of the cable tray materials with the design intent of the Architect or interior designer and the ITPM.
E. Telecommunications cable trays shall not be shared with power cables.
F. Conduit used to route cabling from the cable tray to the work area outlet shall be sized a minimum of 1 inch.
G. Ladder racking shall be used only in telecommunications rooms. It shall not be used anywhere else.

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

57

June 24, 2015

DESIGN CRITERIA
HORIZONTAL DISTRIBUTION SYSTEMS

H. Spine-style tray is not acceptable.

I.

Wherever possible, WSUP prefers that cable trays be routed through non-

plenum spaces, even through plenum-rated cable is always required.

4.5.2.5 CONDUIT AND JUNCTION BOX PATHWAY SYSTEMS

A. Conduits both in and under the ground floor slab are considered "wet locations" where indoor-rated cabling is not permitted. Therefore, conduit serving the main floors of such buildings shall be routed in walls and ceilings ­ not in or under the slab. Intra-building and horizontal pathways shall only be installed in "dry" locations where indoor cabling can be protected from humidity levels and condensation that are beyond the intended range of indoor-only rated cable.

·

Floor boxes in an on-grade slab are the only permissible exception. This

application also requires outdoor-rated Category 6 cabling.

B. Where conduit runs terminate at cable trays, the conduits shall be arranged in an organized, uniform manner to facilitate an orderly cable transition from conduit to cable tray. Conduits shall terminate within a range of 3 inches to 18 inches of the cable tray.

C. Where conduit runs terminate in telecommunications rooms, the conduits shall be arranged in an organized, uniform manner to facilitate an orderly cable transition from conduit to ladder rack.

D. Non-metallic conduit and metallic flex conduit shall not be used for horizontal pathways, unless the WSUP ITPM has granted advance approval for its use.

E. Conduits shall not be filled beyond 40%. The Designer shall verify the outer diameter of the cabling for a project at the time of the design, to determine the maximum number of cables that can be placed inside a conduit without exceeding the 40% fill limitation.

F. In new construction, all work area outlets shall have a minimum 1-inch conduit routing from the device box to an accessible cable pulling location. The conduit size shall be increased as necessary for the quantity of cables to be installed. Where new conduit is installed in existing buildings, the Designer shall notify WSUP when existing conditions prevent the use of 1 inch trade size conduit as a minimum conduit size.

G. Device boxes shall not be "daisy-chained." Each device box shall be complete with its own dedicated conduit to the nearest distribution point/pathway.

H. Junction boxes and pull boxes shall be oriented for access doors to open from the area where the cable installer will normally work. For ceiling-mounted boxes, this is typically from the bottom (floor) side of the box.

I.

Ceiling access to junction boxes and pull boxes shall be designed to allow full

access to the door, adequate working room for installation personnel, and proper

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

58

June 24, 2015

DESIGN CRITERIA
HORIZONTAL DISTRIBUTION SYSTEMS

looping of the cable during installation.
J. Junction boxes and pull boxes shall be located in spaces that are easily accessible during normal working hours, such as hallways and common areas. Junction boxes and pull boxes shall not be located in conference rooms or offices unless there is an overriding design reason for doing so, dependent upon approval from WSUP.

4.5.2.6 SURFACE RACEWAY
A. Surface raceway may be permissible in areas where no suitable alternatives exist. Surface raceway shall conform to bend radius requirements for the cable type being installed.
B. Surface raceway may be either plastic or metal.

4.5.2.7 UNDERFLOOR DUCT SYSTEMS
A. The design of new underfloor duct systems is discouraged. Some existing buildings have existing underfloor duct systems, and as long as the existing ducts are suitable for use with new cabling, it is permitted.

4.5.2.8 ACCESS FLOORS
A. Data Centers typically require access flooring.
B. While some open office circumstances may require access flooring, it may be more expensive than other pathway options. When considering solutions to provide cabling in open office situations, the Designer shall consider other solutions (such as floor boxes) ahead of an access flooring solution.

4.5.3 HORIZONTAL CABLING SYSTEMS

4.5.3.1 GENERAL
A. The Designer shall work with the WSUP FSPM and the WSUP ITPM to identify and understand the needs and requirements for the facility on a project-byproject basis. This includes understanding the expected future uses of the facility. The Designer shall design the horizontal cabling accordingly.

B. The Designer shall inquire with the WSUP ITPM at the start of each project to determine whether a traditional (Category 6) telecommunications infrastructure shall be designed or whether a GPON solution shall be designed.

C. Telecommunications infrastructure designs and specifications shall be based upon products from the required manufacturers, as defined in TDDG Section 1.5 Required Manufacturers (above).

D. Regardless of the plenum rating of the space through which horizontal cable

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

59

June 24, 2015

DESIGN CRITERIA
HORIZONTAL DISTRIBUTION SYSTEMS

passes, WSUP requires plenum-rated cabling everywhere on campus.
E. In addition to the manufacturers listed above, WSUP has selected several manufacturers of products for telecommunications cabling systems (cable, connectors, termination blocks, patch panels, etc.) and telecommunications distribution hardware (racks, cable tray, enclosures, etc.). The Designer shall incorporate only these manufacturers into the design, and shall design a telecommunications distribution system that will be suitable for the use of products from these manufacturers.
F. Splitting of wire pairs degrades the performance of the cable pairs and voids the manufacturer's warranty.
1. Under no circumstances shall cable pairs be split or removed from the back of a modular jack or patch panel. All four pairs of each horizontal distribution cable must be terminated to a single 8-position, 8-conductor jack.
G. Whenever moves, adds, and changes (MAC) are made to existing systems, the new cabling shall follow the routes of existing established telecommunications cabling pathways.

4.5.3.2 TOPOLOGY
WSUP has standardized on the star topology for all horizontal cabling, with some exceptions for certain building automation systems that require or benefit greatly from ring or other topologies.

4.5.3.3 TRADITIONAL HORIZONTAL CABLING SOLUTION

4.5.3.3.1 HORIZONTAL CABLE TO SUPPORT DATA APPLICATIONS
A. At WSUP facilities, horizontal distribution copper cable and components for data applications shall be rated for and installed in compliance with the IEEE 802.3ab 1000Base-T Gigabit Ethernet standard. WSUP requires 4-pair, 100-ohm, 24 AWG, unshielded twisted-pair (UTP) copper Category 6-rated cabling for all horizontal cabling applications. There are only two exceptions to this is as follows:

·

Some audio/visual applications require Category 6A cabling for HDMI

extension and HDBaseT.

·

Where isolated applications require 10GB network bandwidth, use

singlemode fiber optic cabling to a 10GB network switch and Category 6A

patch cords from the switch to each device in the 10GB network, as

depicted in the diagram below:

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

60

June 24, 2015

DESIGN CRITERIA
HORIZONTAL DISTRIBUTION SYSTEMS

10GB APPLICATION
BUILDING

SINGLEMODE FIBER OPTIC HORIZONTAL CABLE (YELLOW)
SINGLEMODE FIBER OPTIC BACKBONE CABLE (YELLOW)
MAIN COMMUNICATION FACILTY (MCF)

IDF
PATCH PANEL

WORKSTATION
10G SWITCH
FIBER OUTLET
10 10 10 10 GB GB GB GB
NETWORKED DEVICES

10G SWITCH

PATCH PANEL

PATCH PANEL

MDF

MDF

CAT6A PATCH CORD
SINGLEMODE FIBER OPTIC PATCH CORD

SINGLEMODE FIBER OPTIC INTER-BUILDING CABLE

B. Horizontal cables shall be terminated at the work area end and patch panel end with modular jacks.

1. WSUP has no color preference for horizontal cabling. 2. Regardless of the faceplate color selected by the Architect or interior
designer, Category 6 cables shall always be terminated with an Almondcolored jack. This is intended to differentiate the cable type from Category 5 cables (Gray) and Category 3 cables (Black).

C. In existing buildings, where additions are made to an existing Category 5 or 5e installation, only Category 6 cabling shall be added. Under no circumstances shall any new cabling and termination hardware be installed that is rated less than Category 6.
4.5.3.3.1.1 Innerduct for Horizontal Fiber Optic Applications
A. The Designer shall show on the Contract Documents where innerduct is required for routing horizontal fiber optic cabling (typically a 10GB application), in accordance with the following conditions:

· Innerduct is required for routing horizontal fiber optic cabling through nonhorizontal pathways (such as riser conduits and sleeves) that exceed 4 feet in length, and which will be shared with non-horizontal cabling.
· Otherwise, innerduct is not required for routing horizontal fiber optic cabling.

B. See Section 4.4.2.4 for innerduct requirements for inside plant fiber optic backbone cabling.

C. See Section 4.4.3.2.9 for innerduct requirements for outside plant fiber optic backbone cabling.

D. See Section 4.5.3.4.6 for innerduct requirements for GPON fiber optic cabling.

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

61

June 24, 2015

DESIGN CRITERIA
HORIZONTAL DISTRIBUTION SYSTEMS

4.5.3.3.2 HORIZONTAL CABLE TO SUPPORT VOICE APPLICATIONS
A. WSUP uses VOIP for all new voice applications. Therefore, horizontal distribution cable intended to support voice services shall be the same Category 6 cable that is used for data applications. This cabling shall meet the same performance and test requirements as cabling intended for data applications.
B. In existing buildings where Category 3 cabling currently serves voice applications for non-VOIP telephone systems, Category 6 cable shall be used when new voice cabling is installed. WSUP is in the process of converting all of its telephone systems to VOIP. Therefore, it is prudent to install Category 6 cabling even if analog telephones are being used.
4.5.3.3.3 LOW-VOLTAGE AND BUILDING AUTOMATION SYSTEMS
A. During planning for intra-building telecommunications cabling installations, the Designer shall identify options for supporting power-limited (low-voltage) and building automation systems with the common structured cabling system, and present the options to WSUP for consideration. These options shall comply with ANSI/TIA/EIA 862 ­ Building Automation Systems Cabling Standard for Commercial Buildings.
B. By providing a common cabling distribution system for the various building automation systems, it may be possible to reduce construction costs and operational costs while creating an intelligent building that can contribute many other benefits (see TDMM Chapter 16 Building Automation Systems for further information). Low-voltage systems that are capable of using a common structured cabling system (either backbone or horizontal cabling) shall be designed to use telecommunications cable and termination hardware wherever possible.
C. The Designer shall request from WSUP a list of systems that will require telecommunications outlets for operations. The Designer shall then include horizontal cabling in the design as necessary to meet the listed requirements.
D. Some low-voltage and building automation equipment benefits from installing a connector directly onto the horizontal cable without first terminating it in a jack.
· One significant uniqueness for Category 6 telecommunications cabling intended for use with permanently mounted equipment is detailed in the new standard ANSI/BICSI D005 - Electronic Safety and Security (ESS) Information Technology System (ITS) Design and Implementation Best Practices.
o This standard permits Category 6 cabling to be terminated on the device end of the cable using a connector (as opposed to a jack), allowing the horizontal cable to plug straight into the device.
o The Category 6 horizontal cable does not need to terminate in a faceplate-mounted jack.
o The Designer shall inquire with the WSUP ITPM before applying this solution.

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

62

June 24, 2015

DESIGN CRITERIA
HORIZONTAL DISTRIBUTION SYSTEMS

E. Other low voltage and building automation equipment uses terminals that require the cable to be terminated directly onto the equipment without using a modular jack. There is no method of testing a cable in this configuration.
· This application is not standards-compliant, and is unlikely to be approved by the ITPM.
· In most cases, it is possible to terminate the horizontal cable in a standard outlet inside a panel, field-manufacture a half-patch cord to plug into the outlet, and then terminate the raw end of the half-patch cord directly onto the terminals of the equipment.
4.5.3.3.4 HORIZONTAL CROSS-CONNECT (HC)
WSUP has standardized on patch panels for terminating all copper horizontal telecommunications media, regardless of the intended use of the horizontal cabling, including cabling that will be used for voice, data, video, or building automation systems.
There is no preference for angled or flat patch panels, other than a compelling requirement to support increased cable density through the use of angled patch panels.
For existing applications, the Designer shall match existing patch panels.

4.5.3.4 GPON HORIZONTAL CABLING SOLUTION

WSUP is currently pilot-testing several GPON architectures in different building types on campus. It is anticipated that upon completion of the pilot testing, WSUP will have operational experience with these architecture options to determine which styles perform best for each building type.

4.5.3.4.1 GPON ARCHITECTURE
A. WSUP has not yet determined guidelines for selecting the GPON architecture for a given building type or application.

· Generally speaking, it is desirable to locate the splitters close to the workstation to increase the flexibility and scalability of the system over time.

4.5.3.4.2 ACADEMIC AND ADMINISTRATIVE BUILDINGS
A. The Designer shall inquire with the WSUP ITPM to get instructions regarding the number of ONT ports to allocate to each office, workstation, and other applications.
B. See the AVDG for instructions regarding the number of ONT ports to allocate to audio/visual applications, such as the instructor podiums in classrooms and the audio/visual equipment racks in conference rooms.

4.5.3.4.3 RESIDENCE HALLS
A. The telecommunications infrastructure for all residence halls shall be designed as GPON systems, and shall include television distribution via GPON.
B. The Designer shall inquire with the Director of WSUP Housing and Dining to get instructions regarding the number of ONT ports to allocate to each person, room, or apartment space in each residence hall.

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

63

June 24, 2015

DESIGN CRITERIA
HORIZONTAL DISTRIBUTION SYSTEMS

4.5.3.4.4 OUTLETS A. All GPON outlets, regardless of application, shall be designed with a single strand of singlemode fiber optic cabling, and shall use factory-terminated cables.
4.5.3.4.5 CABLE TRAYS A. GPON solutions typically require less cable tray capacity than traditional systems. When GPON is being designed for a new facility, the Designer shall design cable trays that are appropriately sized for GPON (smaller than traditional).
4.5.3.4.6 INNERDUCT FOR GPON APPLICATIONS A. The Designer shall show on the Contract Documents where innerduct is required for routing GPON fiber optic cabling, in accordance with the following conditions:
· Innerduct is required for routing GPON fiber optic cabling through nonhorizontal pathways (such as riser conduits and sleeves) that exceed 4 feet in length, and which will be shared with non-GPON cabling.
· Otherwise, innerduct is not required for routing GPON fiber optic cabling.
B. See Section 4.4.2.4 for innerduct requirements for inside plant fiber optic backbone cabling.
C. See Section 4.4.3.2.9 for innerduct requirements for outside plant fiber optic backbone cabling.
4.5.3.4.7 ONT INSTALLATION A. WSUP requires that the Contractor furnish, install, and power-up the ONT devices at each workstation, and also verify that the data link light is active. The Contractor shall also be required to provide a spreadsheet report that correlates the ONT's FSAN identifier with the outlet number, room name, and room number.
· The Designer shall include this requirement in the Contract Documents.
B. WSUP will configure the ONT devices after the Contractor has established successful operation of each ONT.
4.5.3.4.8 SPECIAL APPLICATIONS A. Where multiple devices share an ONT, an outlet shall be provided in the ceiling near the zone where the devices are located. Some of the devices sharing the ONT may require a conduit in the wall and a box at standard mounting height for copper patch cords to route down from the ONT in the ceiling.
B. For WAP applications, the Designer shall inquire with the ITPM which of the following two permissible solutions to design:
· One outlet and one ONT per WAP, mounted in a ceiling location near the WAP.
· One outlet and one ONT serving multiple WAPs in a zone.

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

64

June 24, 2015

DESIGN CRITERIA
HORIZONTAL DISTRIBUTION SYSTEMS
C. For the analog telephone applications supporting life-safety systems, provide a Category 6 cable from the nearest telecommunications room. Do not use GPON for the following:
· Courtesy phone · Elevator phone
D. For all other analog telephone applications, including fax machines, use a nearby GPON ONT to obtain a POTS connection.
4.5.3.4.9 TELECOMMUNICATIONS ROOM SIZING FOR GPON APPLICATIONS
A. For buildings being designed with GPON solutions, the main telecommunications room (MDF) shall be sized the same as buildings with traditional telecommunications infrastructure.
B. WSUP has not yet determined guidelines for sizing secondary telecommunications rooms (IDFs) in buildings being designed with GPON solutions. The Designer shall inquire with the WSUP ITPM to determine the IDF sizing strategy for a given project.
4.5.3.5 PATCH CORDS
A. Do not specify patch cords of any type. WSUP will procure both copper and fiber optic patch cords to match the quantities and lengths required for the Ownerprovided equipment.
B. WSUP ITS will install all patch cords. This includes routing patch cords through modular furniture, connecting to telephones, and also the patch panel-to-switch connections in the telecommunications rooms.
4.5.3.6 PHYSICAL SEPARATION REQUIREMENTS
There are currently no WSUP-driven applications or policies that require certain cables to be physically segregated from other cables. The only expected source of such a requirement would come from a regulatory authority. The Designer shall consider whether any such regulations exist when designing cabling applications for WSUP.
4.5.4 WORK AREAS
4.5.4.1 PERMANENT OFFICE SPACES
A. The standard treatment for each permanent office space (walls, door, etc.) is two outlets on opposite sides of the room with two jacks (two copper cables) per outlet. The outlets shall be arranged as shown in the floor plan at right, intended to complement the possible furniture orientations.

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

65

June 24, 2015

DESIGN CRITERIA
HORIZONTAL DISTRIBUTION SYSTEMS
· See GPON application guidelines in Section 4.5.3.4 of this document.
B. For larger offices, a third outlet (two jacks) shall be provided. A general guideline is to provide at least one telecommunications outlet per two power receptacles.
C. Telecommunications outlets (and companion power receptacles) shall be mounted above desktop height.
D. If a window prevents outlets on opposite sides, two outlets may be positioned on the same wall if spaced widely apart.
E. Outlets shall not be placed on the wall with the door or on an exterior wall.
F. The Designer shall coordinate with the furniture designers/specifiers to make sure that access to power and data outlets is not obstructed by the furniture. The Designer shall involve the ITPM in this effort.
4.5.4.2 OPEN OFFICE/MODULAR FURNITURE
A. WSUP prefers to serve open office areas using permanently mounted outlets in the wall nearest the modular furniture. Where modular furniture is not located adjacent to a wall, floor boxes are required.
· It is usually preferable to route cabling inside concealed conduits or through interstitial wall spaces. Therefore, columns that are wrapped or furred are preferable because conduits and device boxes can be concealed inside.
· The ITPM may authorize the use of surface-mounted raceway in certain projects for columns that are not able to conceal raceway.
· Where columns and floor boxes do not exist and cannot be added, utility poles shall be designed as a last resort.
· Where columns are available, raceways shall route cabling down from the ceiling space to two outlets on opposite sides of each column, allowing furniture to sit against the columns on the sides without outlets.
· Outlets on columns shall have up to 6 jacks per outlet.
B. Raceways integrated into modular furniture shall have separate channels for power and data. The channels shall be designed with abrasion protection features.
C. The standard treatment for each modular furniture office space (cubicle) is two jacks (two copper cables). The following diagram depicts WSUP's preferred method of routing cabling to modular furniture:

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

66

June 24, 2015

DESIGN CRITERIA
HORIZONTAL DISTRIBUTION SYSTEMS

D. Furniture shall not obstruct access to power or telecommunications outlets. Where necessary, access panels shall be provided and/or holes shall be cut through obstructions to allow access to the outlets.

4.5.4.3 BREAKOUT ROOMS
A. Small groups meet in "Breakout Rooms." The rooms are typically sized for 4 occupants (6 maximum) and usually do not have a conference-style table. A video panel with integrated speakers is the only audio/visual feature in Breakout Rooms.
B. One outlet shall be provided in Breakout Rooms. The outlet shall be located on a wall opposite the door and shall be provided with two jacks.

4.5.4.4 CONFERENCE ROOMS

A. All Conference Rooms shall have conduits and boxes required to support video conferencing, even if the initial design and construction will be limited to presentation audio/visual features.

B. Typically, it is desirable to locate a wireless access point in or near each Conference Room.

C. On the end wall of each Conference Room, provide a quad power outlet and two telecom outlets. These outlets shall be accessible inside casework as shown in the wall elevation below. The Designer shall work with the A/V designer and refer to the AVDG to provide the correct quantities, types and colors of cables for each application.

D. Behind each TV panel, provide a duplex power outlet and a telecom outlet with two jacks. (See wall elevation at right). The Designer shall work with the A/V

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

67

June 24, 2015

DESIGN CRITERIA
HORIZONTAL DISTRIBUTION SYSTEMS
designer and refer to the AVDG to provide the correct quantities, types and colors of cables for each application.

E. Conference tables shall have floor boxes installed beneath them, with patch cords routed up from the floor box to a table-top connection point providing access to power outlets, data outlets and audio/visual inputs.
· The Designer shall work with the A/V designer and refer to the AVDG to provide the correct quantities and types of cables for each application.
· See the AVDG for guidelines about the sizing and quantity of floor boxes and cable cubbies required for each conference table application.
· The two diagrams below depict the required methods of terminating horizontal cabling in floor boxes and cable cubbies serving conference table applications. The main determining factor is whether the table is large and stationary ("unmovable") or whether it is intended to be flexible for rearrangement ("movable") to serve the purposes of a specific event.

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

68

June 24, 2015

DESIGN CRITERIA
HORIZONTAL DISTRIBUTION SYSTEMS

4.5.4.5 TELECOMMUNICATIONS OUTLETS FOR SPECIAL INDOOR APPLICATIONS
A. As of this writing, the telecommunications industry is on the verge of establishing a standards-supported4 application where the field end of a cable is terminated with an RJ45 connector (as opposed to a jack) to support fixed-mounted, technician-installed equipment (such as video surveillance cameras). WSUP approves this solution for some applications.

4 ANSI/BICSI D005 - "Electronic Safety and Security (ESS) Information Technology System (ITS) Design and Implementation Best Practices". Currently under industry review.

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

69

June 24, 2015

DESIGN CRITERIA
HORIZONTAL DISTRIBUTION SYSTEMS

·

The Designer shall inquire with the ITPM which devices should be

terminated with a connector instead of a jack.

·

The Telecommunications Room end of the cable shall terminate in a

patch panel, just like any other horizontal cable application.

B. All WSUP facilities shall provide ubiquitous wireless network coverage. Outlets serving wireless access points (WAP) shall be designed by WSUP ITS with the use of a third-party site survey contractor. This is a two-pass process where the initial design is based on the analysis of building modeling, followed by an on-site survey during construction to identify any areas in the building where WiFi signal is weak. Additional conduits, boxes and cabling will then be added as a construction change order to augment the WiFi signal and address any weak zones.

Outlets shall have two cables to each WAP, and shall be mounted at the desired WAP location. Cables for WAP outlets shall be terminated with an RJ45 connector. If the outlet is intended for future WAP use, a blank faceplate will be required and the terminated cables coiled inside. Otherwise, the Contract Documents shall be prepared to require the Contractor to install the Ownerfurnished WAP device.

·

See GPON application guidelines in Section 4.5.3.4 of this document.

·

See additional Wireless application guidelines in Section 4.16 of this

document.

C. IP video surveillance cameras shall be provided an outlet with one jack for each camera, located at the desired camera location. Cables for cameras shall be terminated with an RJ45 connector. If the outlet is intended for future camera use, a blank faceplate will be required and the terminated and labeled cable coiled inside. Otherwise, the Contract Documents shall be prepared to require the Contractor to install the Owner-furnished camera device.

D. At the discretion of the FSPM, a courtesy telephone with TDD features may be provided in a main floor gathering space.

·

See GPON application guidelines in Section 4.5.3.4 of this document.

E. Outlets will be required in mechanical and electrical spaces to provide network services to mechanical control equipment, electrical power monitoring equipment, and lighting control panels. The Designer shall address these needs on a project-by-project basis.

F. Analog telephone circuits shall be provided for elevators.

·

See GPON application guidelines in Section 4.5.3.4 of this document.

G. Outlets serving digital signage shall be provided with two data jacks. WSUP currently uses a Cisco digital media player device mounted in the nearest telecommunications room. A powered adapter is used in the telecommunications

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

70

June 24, 2015

DESIGN CRITERIA
HORIZONTAL DISTRIBUTION SYSTEMS

room and behind the flat panel television to carry HDMI signals via telecommunications cabling.

H. Outlets serving televisions shall be provided with two data jacks.

I.

Outlets serving copy machines shall have two jacks. A power outlet with a

dedicated circuit shall be provided adjacent to the telecommunications outlet.

J. Vending machines are Ethernet-connected and require one cable per machine.

K. Access Control Systems are Ethernet-connected, and require one cable at each panel location.

L. WSUP uses SmartGrid power monitoring devices that are network-connected. Outlets shall be provided to support this equipment. The Designer shall coordinate with the Electrical Engineer and the FSPM to determine where to place outlets to support the SmartGrid devices.

M. Area of Refuge communication devices shall be provided as governed by Code. Each device requires a communication cable terminated with a jack inside the rough-in box.

N. Outlets serving fire alarm panels, elevators, security systems, access control systems, security systems, security scanning stations, point-of-sale equipment, etc. shall be provided under the direction of the WSUP FSPM, SSPM, LSPM, BASPM, ITPM, and non-WSUP tenants.

O. The Designer shall inquire about the requirements for any special design considerations, including:

·

Public-use telephones within WSUP facilities

·

Spaces within WSUP facilities which must address Architectural Barriers

Act Accessibility Standard (ABAAS) requirements

·

Point-of-Sale applications

·

ATM Machines

·

Reception Areas

4.5.4.6 SPECIAL OUTDOOR APPLICATIONS
A. Outdoor-rated outlets may be required to serve outdoor applications such as wireless access points, hardened convenience telephones, and emergency telephones.
B. The Designer shall inquire with the FSPM whether network-connected irrigation controllers will require an outlet and cabling.
C. Outlets serving security cameras, public access telephone systems (PATS), power monitoring equipment, security systems, irrigation controllers, etc. shall be provided under the direction of the WSUP FSPM, SSPM, LSPM, BASPM, and ITPM.

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

71

June 24, 2015

DESIGN CRITERIA
ITS CABLES AND CONNECTING HARDWARE

4.5.4.7 OTHER CONSIDERATIONS
A. WSUP rarely accepts consolidation point solutions.
B. WSUP considers undercarpet telecommunications cabling (UTC) solutions to be undesirable in most cases. The Designer shall discuss any apparent justifications for undercarpet cabling with the WSUP ITPM prior to its inclusion in a design, and shall also discuss the next best alternative to using undercarpet cabling.

4.5.4.8 WORKSTATION POWER OUTLETS

A. There shall be at least one general-purpose convenience power outlet (120VAC, 15 Ampere minimum) located within three feet of every telecommunications outlet. The Designer shall discuss any application-specific needs with WSUP IT staff and adjust the power outlet locations and amperage accordingly.

·

In the case of new construction and modernization projects, the power

outlet associated with each telecommunications outlet shall be a 4"x4"

device box (dual gang) with four power receptacles. Power outlets shall

be mounted above desktop height, such that a user can plug in power

cords without crawling under the desk. It is the Designer's responsibility

to coordinate with the electrical engineer to ensure that power outlets are

located near telecommunications device boxes.

·

In the case of minor remodel, historical building remodel, and

telecommunications-only projects, it may be difficult to meet this

requirement. Therefore, where existing power outlets are not located

within six feet of each telecommunications outlet, the Designer shall alert

the WSUP ITPM and request consideration of the situation on a case-by-

case basis.

4.6 ITS Cables and Connecting Hardware
Please refer to Chapter 6, ITS Cables and Connecting Hardware in the BICSI TDMM for information regarding the design of telecommunications cables and connecting hardware. The following requirements take precedence over the BICSI TDMM guidelines for telecommunications infrastructure at WSUP facilities:

4.6.1 COPPER CABLING
A. Copper backbone cabling shall terminate on building entrance protection equipment and patch panels. Termination of copper backbone cables on 110blocks is no longer permitted at WSUP facilities. However, patch panels with 110-style connections (individual jack-style) and building entrance protection equipment shall be used.
· 2-pair per jack on patch panels

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

72

June 24, 2015

DESIGN CRITERIA
FIRESTOP SYSTEMS
B. The design of new telecommunications infrastructure at WSUP facilities shall not include the use of the following termination blocks or connectors. This prohibition applies to both voice and data circuits.
· 110-style blocks · 66-style blocks or connectors · BIX-style blocks or connectors · LSA-style blocks or connectors · 50-position miniature ribbon connectors
C. Category 6 horizontal cables shall terminate on patch panels. See Section 4.5.3.3 in this document for further information.
4.6.2 FIBER OPTIC CABLING
A. Singlemode fiber optic cabling shall be terminated at patch panels (both riser and outside plant) and outlets using Angle-Polish, SC-style connectors (APC), with ceramic ferrules.
B. 50-micron multimode fiber optic cabling shall be terminated at patch panels (both riser and outside plant) and outlets using Ultra-Polish, SC-style connectors (UPC), with ceramic ferrules.
C. Where an application requires connectors with more than two strands of fiber (high bandwidth applications, pre-terminated cables, etc.) MPO connectors shall be used in accordance with manufacturer recommendations. Other connector types may be approved by the WSUP ITPM on a case-by-case basis.
D. For fiber optic cabling with 24 or fewer strands, terminate all strands in the fiber ­ do not leave unterminated "dark" strands. For fiber optic cabling with more than 24 strands, the Designer shall inquire with the ITPM for direction on the number of strands to terminate. Specify a patch panel with sufficient size to terminate all strands in a cable, regardless of whether all strands will be terminated at the time the cable is installed.
E. See Section 4.4.2.2 in this document for further information.
4.6.3 SPLICING
Splicing or coupling copper or fiber optic cable is prohibited for inside plant infrastructure.
4.7 Firestop Systems
Please refer to Chapter 7, Firestop Systems in the BICSI TDMM for general information regarding the design of firestopping for telecommunications infrastructure. The following requirements take precedence over the BICSI TDMM guidelines for telecommunications infrastructure at WSUP facilities:

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

73

June 24, 2015

DESIGN CRITERIA
BONDING AND GROUNDING (EARTHING)

A. The Designer shall pay careful attention to the fire ratings of existing and new walls. Wherever penetrations are made through fire-rated walls, the Drawings shall identify the firestopping requirements.
B. Penetrations through fire-rated walls and floors shall be firestopped in accordance with the requirements of the manufacturer of the firestopping materials, and to satisfy local code officials.
C. The Designer shall avoid design solutions calling for penetration of fire walls, fire barriers, fire partitions, smoke barriers, and smoke partitions when other reasonable cable routing options exist.
D. The predominant color of fire-rated pathway devices shall be red.
E. For new construction, WSUP requires re-enterable firestopping devices like the STI EzPath for penetrations through fire-rated walls and floors.
F. Firestopping pillows are acceptable for existing buildings where conduit sleeve pathways already exist.
G. The use of firestopping putty materials is prohibited.
H. WSUP Facilities Services maintains specification section 07 27 00 ­ "Firestopping" which should contain telecommunications-specific firestopping requirements. The Designer shall work with the FSPM to review this specification section and verify that it is appropriately written for a given project.

4.8 Bonding and Grounding (Earthing)
Please refer to Chapter 8, Bonding and Grounding (Earthing) in the BICSI TDMM for general information regarding the design of grounding, bonding and electrical protection systems. The following requirements take precedence over the BICSI TDMM guidelines for telecommunications infrastructure at WSUP facilities:
· Grounding and bonding conductors shall be sized according to the requirements in ANSI/TIA/EIA J-STD-607A and per the NEC.

4.9 Power Distribution

Please refer to Chapter 9, Power Distribution in the BICSI TDMM for general information regarding the design of power distribution for telecommunications infrastructure. The following requirements take precedence over the BICSI TDMM guidelines for telecommunications infrastructure at WSUP facilities:

A. The Designer shall be responsible to determine that the electrical power distribution requirements supporting the telecommunications infrastructure are met as described in this document.

B. For projects where an electrical engineer is involved, the Designer shall

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

74

June 24, 2015

DESIGN CRITERIA
TELECOMMUNICATIONS ADMINISTRATION

coordinate directly with the engineer, and verify that the engineer's design documentation meets these requirements. For projects without the involvement of an electrical engineer, the Designer shall alert WSUP where additional power infrastructure is needed to meet the requirements.
1. Please refer to Chapter 4, Work Areas in the BICSI TDMM and also in TDDG Section 4.3 Work Areas for information on the power outlet requirements for work areas.
2. Please refer to Chapter 7, Telecommunications Spaces in the BICSI TDMM and also in TDDG Section 4.3 Telecommunications Spaces for information on the power outlet requirements for TRs.
o WSUP typically provides network electronics that provide Power-overEthernet.
o The Designer shall request power consumption data for the equipment that WSUP will use, and will size the power distribution infrastructure sufficient to support this equipment.
3. Please refer to Chapter 21, Data Centers in the BICSI TDMM and also in TDDG Section 4.18 Data Centers for information on the power outlet requirements for data centers.
o WSUP data centers will typically be either Tier II or Tier III systems. o The Designer shall inquire which tier is to be designed for each
project, and design appropriate power distribution systems to support the Tier designation.
C. The Designer shall inquire which type of power conditioning/power protection equipment should be designed for each project.
o WSUP recognizes that flywheel-based UPS equipment is available. However, the initial cost of flywheel equipment is typically very high. As a result, the return on investment is low with a lengthy time to payback. For most applications, flywheel-based UPS systems are probably cost-prohibitive.

4.10 Telecommunications Administration
Please refer to Chapter 10, Telecommunications Administration in the BICSI TDMM for general information regarding the documentation and labeling of telecommunications infrastructure. The following requirements take precedence over the BICSI TDMM guidelines for telecommunications infrastructure at WSUP facilities:

4.10.1 IDENTIFICATION STRATEGY
A. The "identifier" is the unique name or description assigned to a given telecommunications infrastructure component. The Designer shall assign identifiers to the telecommunications infrastructure components listed below and

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

75

June 24, 2015

DESIGN CRITERIA
TELECOMMUNICATIONS ADMINISTRATION
clearly show the identifier assignments on the Construction Documents.
B. While it is the Contractor's responsibility to provide marked-up drawings to the Designer indicating any construction-related changes to the identifiers, the Designer shall verify that the identifiers are clearly and accurately shown on the record drawings.
C. Telecommunications components shall not be labeled with an applicationspecific identifier. Jacks shall not be labeled with the name or function of the device that is served by the jack (server name, computer type). Also, the use of "V-#" and "D-#" are inconsistent with the industry standard-based philosophy of designing cabling systems that are independent of the application, and are therefore not permitted.
D. The Designer shall prepare construction specifications that shall contain a comprehensive listing of the identification strategy requirements.
4.10.1.1 NEW TELECOMMUNICATIONS DISTRIBUTION SYSTEMS
The items listed below shall be shown on the Construction Documents. The Designer shall assign the identifiers to the telecommunications components based on the following suggested identification strategy. The circumstances of each project may require adjustments. The Designer shall discuss with WSUP any recommendations for customization and cooperatively develop an identification strategy, prior to adopting any customizations.
A. WSUP has a campus building numbering scheme that shall be incorporated into all applicable labeling. Each building on campus has been assigned a 4- or 5digit numeric code. The Designer shall obtain the official numbering scheme from the following website. The FSPM and ITPM can assist to provide new numbering for a new building (if needed).
http://facilitiesservices.wsu.edu/facility_roster.aspx
At a minimum, buildings and rooms always have a 4-digit numeric identifier. Some buildings and rooms may also have an alpha character prefix, in addition to the 4-digit number. Some buildings and rooms may also have up to two alpha characters as a suffix. Telecommunications rooms, for example, end with the letter "T". Up to 5 spaces are reserved for building numbering and up to 7 spaces are reserved for room numbering. Therefore, if a room or building identifier lacks an alpha character prefix, use an asterisk as a placeholder. If a room or building lacks one or both alpha characters in the suffix, just delete those character positions (no asterisk for either of those positions).
B. Telecommunications Rooms, Equipment Rooms and Data Centers shall be identified by room number, followed by the letter "T". o For example: a telecommunications room located in Room #1242T in a building would be identified as "1242T".

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

76

June 24, 2015

DESIGN CRITERIA
TELECOMMUNICATIONS ADMINISTRATION

C. Racks in telecommunications rooms shall have identifiers of the form "Rack #" where "#" is the sequential rack number within a given TR, numbered from the wall out, with the rack located closest to the wall being "Rack 1". o For example: the first rack in a given telecommunications room would have the label "Rack 1", the second "Rack 2", and so on.

D. Backbone Cables shall have identifiers of the form of:

Source Telecom Room Destination Telecom Room Cable

Building

at Source

Building

at Destination Number

a a a a a - b* b b b b b b c c c c c* - d* d d d d d d e e e e e

When building identifiers, room identifiers, and cable numbers lack a character in a given position, an asterisk shall be used as a placeholder or that position deleted, as follows:

· * This character position should be replaced by an asterisk if the number
doesn't include an alpha character in that position. ·  This character position should be deleted if not necessary.

The Source Building is typically the MCF. The Destination Building is the customer/outlet-end of the cable.

Three or four-position sequentially numbered Cable Numbers are structured as follows:

o 001-999 o FM01-FM99 o FS01-FS99 o X01-X99 o Z01-Z99

for UTP cables for Multimode Fiber cables for Singlemode Fiber cables for Coax cables for Composite cables

There is one special case for a prefix character on a cable number: cables that are owned by a third party (not WSU). For example, cables owned by Housing and Dining are labeled with a prefix of "H". The Designer shall inquire about other prefixes that might be required for a given project.

Cables shall be labeled within 6 feet of entrance into a telecom room and within 12 inches of the fiber optic patch panel or copper termination. Cables shall also be labeled twice in maintenance holes, within 3 feet of the entrance and exit conduits. The labels shall designate the origin, destination, and owner of the cable. o For example: A 24-strand singlemode fiber optic cable (the second fiber
cable) running between Telecommunications Room 2047T in the Information Technology Building (0812) and Telecommunications Room 23T in Bohler Gymnasium (0011) shall be numbered:

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

77

June 24, 2015

DESIGN CRITERIA
TELECOMMUNICATIONS ADMINISTRATION

Source Telecom Rm Destination Telecom Rm Cable

Building

at Source Building at Destination Number

0812*-*2047T0011 * - * 0023TFS02

E. Fiber Optic Patch Panels shall have identifiers sequentially numbered in the form

of "F#" where "F" stands for "Fiber" and "#" is the sequential fiber optic patch panel number terminated within a given telecommunications room. The numbering sequence does not restart for each rack.

Fiber Patch Panel

1st Fiber Patch Panel in the Rack

o For example: the first fiber optic patch panel would be

labeled "F1". The second fiber optic patch panel would be

labeled "F2".

F. Ports on Patch Panels for Fiber Optic Cabling are typically pre-labeled by the manufacturer with sequential numbers (i.e. 1 to 12). o In addition to the pre-labeling, each bulkhead/connector panel shall also be labeled with the opposite end termination point and type of the cable terminated at that location, in the form of "aaaaa-bbbbbbb-cccc" (referencing the cable numbering discussed above).

o For example: the bulkhead/connector panel in a patch panel terminating singlemode fiber optic cable #2 (strand count is irrelevant to the labeling) whose far end terminates in Telecommunications Room 2047T in the Information Technology Building (0812) shall be numbered:

Far End Building

Telecom Rm Cable at Far End Number

0 8 1 2 * - * 2 0 4 7 T- FS0 2

G. Building Entrance Protectors (BEP) and Copper Backbone Patch Panels shall be labeled with the far end termination point and cable of the cable terminated at that jack, in the form of "aaaaa-bbbbbbb-cccc" (referencing the cable numbering discussed above). o For example: the BEPs and Copper Backbone Patch Panels for copper cable #121 whose far end terminates in Telecommunications Room 2047T in the Information Technology Building (0812) shall be numbered:

H. Patch Panel Jacks for Horizontal Cables shall have identifiers in the form of "aaaaa", where:

 aaaaa

Room Number where outlet is located

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

78

June 24, 2015

DESIGN CRITERIA
FIELD TESTING

Labels shall be applied to the front of the patch panel adjacent to each jack, without obscuring the jack number printed on the patch panel, and also on the cable behind the jack within 4 inches of the termination.

I.

Outlet Jacks for Horizontal Cables shall have identifiers in the form of

"aaaaa:bcdd", where:

 aaaaa b c  dd

Telecommunications Room Number serving outlet Equipment Rack Number Patch Panel Number Patch Panel Jack Number (two digits, with leading zero)

Labels shall be applied to the front of the faceplate adjacent to each jack, and also on the cable behind the jack within 4 inches of the termination.

o For example: a horizontal UTP cable terminated in patch panel jack 22 of workstation patch panel A in rack 2 in telecommunications room 020T, serving an outlet in office 050, would be labeled at the outlet as follows:
o The jack numbering on the faceplate may also be printed in two rows, one above the other, with a colon, as follows:
0020T:
2A22

4.11 Field Testing
Please refer to Chapter 11, Field Testing in the BICSI TDMM for general information regarding the field-testing of telecommunications cabling. The following requirements take precedence over the BICSI TDMM guidelines for field-testing at WSUP facilities:
A. The Designer shall require the Contractor to test 100% of cabling, both fieldterminated and pre-terminated cables.
· Copper cables shall be Link tested (not Channel tested).
B. Cable tester equipment shall be manufactured by Fluke.
C. The Designer shall review the cable test results submitted by the Contractor. The test results shall be the actual native machine test results downloaded from the test equipment. In particular, the Designer shall check for the following items on the cable test reports:
· The cable test report shall be automatically produced by the test equipment. · The report shall indicate that the cable passed the test. It shall also indicate
the date of calibration, the software version, and the name of the technician

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

79

June 24, 2015

DESIGN CRITERIA
OUTSIDE PLANT
who conducted the test. The reports shall also include graphical results of the performance curves obtained during the testing. · Indications that the cabling meets distance limitation requirements. · Indications that the wire-map of the cable is correct. · Indications that the cable test equipment was properly configured. For copper cabling, the test equipment's configuration parameter for Nominal Velocity of Propagation (NVP) shall match the value stated by the cabling manufacturer for the type of cable installed. · Marginal test results (typically indicated with an asterisk "*") are only acceptable when the condition is "over length" and when the over-length situation was intentional during design. For example, a low bandwidth device might be served by a cable that would otherwise be too long to support a high bandwidth device. Over-length issues due to choice of routing or extra service loops are not acceptable. · For fiber optic cabling: the cable test report shall indicate a headroom dB value that is equal to or better than the value calculated in the link-loss budget.
D. The cabling performance characteristics shall meet or exceed the performance guaranteed by the manufacturer, which may exceed standard industry requirements. In other words, even though a particular cable might pass its tests, the cable might still be rejected (requiring re-termination or replacement) if it does not meet the higher standard of performance that the manufacturer may list for its products.
E. WSUP may choose to spot-test cabling to back-check the Contractor's test results.
F. WSUP may choose to hire a third-party cable test company to conduct an independent cabling test.
G. The final test results shall have been verified by the Designer to be acceptable before submission to WSUP. Test results shall be submitted to WSUP in electronic form, both in PDF form and also the original test result data files.
H. Contractors shall be required to retain a copy of the test reports for a period of at least 5 years after installation.
4.12 Outside Plant
Please refer to Chapter 12, Outside Plant in the BICSI TDMM and the BICSI OSPDRM for information regarding the design of outside plant telecommunications infrastructure.
See Section 4.4.3 above.

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

80

June 24, 2015

DESIGN CRITERIA
AUDIO/VISUAL SYSTEMS

4.13 Audio/Visual Systems
Please refer to Chapter 13, Audiovisual Systems in the BICSI TDMM for information regarding the design of telecommunications infrastructure to support audio/visual systems, private CATV distribution systems, and distributed paging systems at WSUP facilities.

4.13.1 AUDIO/VISUAL SYSTEMS
The Designer shall coordinate with the AVPM and reference the Audio/Visual Design Guide (AVDG) for information about the telecommunications infrastructure required to support audio/visual applications at WSUP.

4.13.2 DISTRIBUTED PAGING SYSTEMS
Please refer to Chapter 15, Overhead Paging Systems in the BICSI TDMM for information regarding the design of telecommunications infrastructure to support overhead paging systems at WSUP facilities.
These systems are typically not used at WSUP. However, the Designer shall inquire with WSUP to determine whether emergency response paging systems are required for a given project.

4.14 Building Automation Systems
Please refer to Chapter 14, Building Automation Systems in the BICSI TDMM for information regarding the design of telecommunications infrastructure to support building automation systems at WSUP facilities.
A. ANSI/TIA/EIA-862 applies to telecommunications infrastructure serving building automation systems (BAS). The Designer shall pay particular attention to the following BAS issues:
· Verify that the voltage and current requirements of each BAS application are satisfied by the cabling materials to be installed.
· Verify that a suitable horizontal connection point (HCP) is installed for each BAS application.
B. BAS devices are increasingly converging onto structured cabling systems. While the design of these systems is typically outside the scope of work of the telecommunications infrastructure designer, the Designer shall design the telecommunications cabling required to support these systems.
C. Typically, BAS systems require telecommunications cabling routed from the devices to a patch panel termination point in a designated mechanical room or other location managed by building maintenance personnel. In addition to the device-specific cables, other cables shall be designed from the telecommunications rooms to the BAS patch panels, to permit these systems to gain access to the data networks.

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

81

June 24, 2015

DESIGN CRITERIA
DATA NETWORKS

D. Horizontal connection points are only required for BAS applications. Do not use an HCP for typical voice/data/video applications.
E. The Designer shall inquire with the ITPM and the HVACPM whether a project requires telecommunications cabling to support building automation systems.

4.15 Data Networks
Please refer to Chapter 15, Data Networks in the BICSI TDMM for general information regarding the design of telecommunications infrastructure for serving local area networks. The following requirements take precedence over the BICSI TDMM guidelines for telecommunications infrastructure at WSUP facilities:
A. All WSUP facilities use the Ethernet LAN protocol. Telecommunications infrastructure for all WSUP facilities shall be designed, installed, and tested to support the Institute of Electrical and Electronic Engineers (IEEE) Ethernet 802.3 standards. WSUP networks use the 1000Base-X Gigabit Ethernet protocol based on the IEEE 802.3z standard. All newly installed cabling shall support this protocol. WSUP networks are typically based on Cisco switches (power-over Ethernet), with 10GB backbones and 1GB service to the work area.
B. The design of the network electronics is done by WSUP and is outside the scope of work of the telecommunications Designer.
C. The Designer shall coordinate with the WSUP ITPM and HVACPM to determine the requirements for supporting the network electronics in each space. The design shall provide rack space to host WSUP's network equipment.

4.16 Wireless Networks

Please refer to Chapter 16, Wireless Networks in the BICSI TDMM and the BICSI Wireless Design Reference Manual (WDRM) for information regarding the design of telecommunications infrastructure to support wireless and microwave telecommunications systems at WSUP facilities.

A. WSUP currently uses Cisco wireless access point equipment in its buildings. This equipment operates with Power-over-Ethernet and requires one cable per device. The Designer shall accommodate POE equipment in the design, including the power and cooling requirements.

B. The Designer shall work cooperatively with the WSUP ITPM to design telecommunications infrastructure to appropriately support wireless technologies. WSUP typically uses a third party site-survey consultant to identify appropriate WAP locations and prepare associated coverage and signal strength maps. The Designer shall show the locations where wireless access points (WAP) are desired on the drawings. During the later part of the construction process, WSUP ITS may bring the site-survey consultant to the project site to analyze the actual facility and make adjustments to the design to add or move outlets serving WAPs to improve coverage in the building.

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

82

June 24, 2015

DESIGN CRITERIA
ELECTRONIC SAFETY AND SECURITY

C. WSUP prefers that the WAP devices be Owner-furnished and Contractorinstalled. The Designer shall include this requirement in the Contract Documents.

4.17 Electronic Safety and Security

Please refer to Chapter 17, Electronic Safety and Security in the BICSI TDMM for general information regarding the design of telecommunications infrastructure for serving electronic safety and security systems.

Electronic safety and security (ESS) devices are increasingly converging onto structured cabling systems. While the design of these systems is typically outside the scope of work of the telecommunications infrastructure designer, the Designer shall design the telecommunications cabling required to support these systems.

Sometimes ESS systems require telecommunications cabling routed from the devices to a patch panel termination point in a designated low-voltage electronics room or other location managed by building security personnel. In addition to the device-specific cables, additional cables shall be designed from the telecommunications rooms to the ESS patch panels, to permit these systems to gain access to the data networks.
Other times, ESS systems can be cabled directly to patch panels in the telecommunications rooms just like any other computer or telephone device.

Electronic Safety and Security Devices, located throughout the building, and connected to Patch Panel via Horizontal Cabling

Rack in Telecom Room with
Patch Panels and Network Electronics

Cabinet or Panel in Low Voltage Electronics Room
with Patch Panels and Network Electronics specific
to Electronic Safety and Security Devices

One Horizontal Cable, connecting the
remotely located Panel Serving the Electronic
Safety and Security Devices with the main network, located in a

Telecom Room.

The diagrams above depict the differences between these two solutions. The Designer shall inquire on a project-by-project basis which solution to apply to a given project. Nontechnical issues will frequently affect which solution is used.

Electronic Safety and Security Devices, located throughout the building, and connected to Patch Panels in Telecom Room via Horizontal Cabling

Head-end panels serving access control systems, HVAC control and monitoring systems, and vending machine systems shall be colocated in telecommunications rooms. The Designer shall allocate rack space and wall space to support these systems.

Rack in Telecom Room with Patch Panels and
Network Electronics

4.18 Data Centers and MCFs
Please refer to Chapter 18, Data Centers in the BICSI TDMM for general information regarding the design of telecommunications infrastructure for serving data centers. Generally speaking,

WSU Pullman Campus ­ Telecommunications Distribution Design Guide

83

June 24, 2015

DESIGN CRITERIA
DATA CENTERS AND MCFS
WSUP follows the TIA-942 Data Center Standard in the design of data centers and larger equipment rooms. The requirements below take precedence over the BICSI TDMM guidelines.
The requirements for small-scale equipment rooms are the same as for telecommunications rooms. The Designer shall inquire with WSUP whether an equipment room in a given project is intended to be designed with telecommunications room features or data center features.
WSUP does not anticipate the need to construct any new Data Centers in the foreseeable future.
The telecommunications infrastructure topology at WSUP is a two-level hierarchical star with several "main communication facilities" (MCF) at key locations throughout campus. It is unlikely but conceivable that a new MCF might be required at WSUP. The "Data Centers" section of this document shall apply to MCFs. All requirements for MDFs and IDFs apply to MCFs.
4.18.1 SIZING CONSIDERATIONS
A. The Designer shall consult with the WSUP ITPM to determine any sizing requirements for the Data Center on a project-by-project basis. The design shall include a minimum of 25% vacant space for future growth.
B. The power consumption profile of equipment to be hosted in the data center and its associated heat-load profile are the two key parameters for sizing a data center. The Designer shall work with WSUP ITPM to identify the power consumption per cabinet footprint, which will have a direct correlation to the cooling requirements of the space. The quantity of equipment cabinets that can be powered and cooled in the space drives the sizing plan.
· During the life of the data center, advances in technology may shrink the space requirements for each server, making more physical space available for additional servers. However, if there is not sufficient power to support another server, or sufficient cooling capacity to remove the heat produced by another server, then the additional space is unusable.
C. The WSUP ITPM shall approve the final space requirements and design layout for the equipment and racks.
4.18.2 TIER CLASSIFICATION
WSUP data centers are typically designed for Tier II+ classification (redundant components, single distribution path, and N+1 redundancy). However, the Designer shall inquire with the ITPM on a project-by-project basis for the desired Tier classification of each data center or equipment room.
4.18.3 ARCHITECTURAL CONSIDERATIONS
The Data Center shall be separated from other occupancies within the building by fire-resistantrated construction of not less than 1 hour.

WSU Pullman Campus ­ Telecommunications Distribution Design Guide
