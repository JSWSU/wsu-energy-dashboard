# CSI 27 15 23 - Optical Fiber Horizontal Cabling

> **Division:** 27
> **CSI Code:** 27 15 23
> **Title:** Optical Fiber Horizontal Cabling
> **Source:** WSU Facilities Services Design & Construction Standards (June 2025)

---

Washington State University (Pullman) Telecommunications Construction Guide Specification

Communications Optical Fiber Horizontal Cabling Section 27 15 23

PART 1 - GENERAL This section of the Telecommunications Construction Guide Specification has references, products, procedures, processes, and work descriptions/summaries that are common to many Washington State University Pullman (WSUP) campus telecommunications projects. This information is provided in specification format to serve as a guide to the Designer in producing a CSI-compliant specification that will meet the unique requirements of WSUP Telecommunications projects. However, this document is not intended to be a Master Specification. The information included in this section is not intended to be allinclusive for any given project.
The Designer shall edit this section (adding and/or removing content where required) to meet the requirements of a given project.
Prior to publishing the specifications for bid or construction purposes, all edits shall be made using the MS Word Tracking Changes feature. When submitting the specifications for review at each progress milestone, print the specifications showing the revision markings.
Text in shaded boxes (such as this text) is included to aid the Designer in understanding areas of this section that may require modification for a particular circumstance. Although this text is generally written in declarative form, the Designer shall consider it guidance only. The Designer shall not assume that the content of this specification section is suitable or sufficient for any given project in its current form, and shall remain responsible for developing a thorough and complete specification that meets the requirements of the project being designed.

1.1

SUMMARY

Review and edit the following list of generic type products for relevance to this project. This listing should not include procedures or processes, preparatory work, or final cleaning.

A. 1.2

Provide all materials and labor for the installation of an inside plant Gigabit Passive Optical Network (GPON). This section includes Inside Plant Communications cabling, termination, and administration equipment and installation requirements for the specified Passive Optical Network as well as the required electronics.
SYSTEM DESCRIPTION Review and edit the following statement(s) for applicability to this project, restricted to describing performance, design requirements and functional tolerances of a complete system.
Typically GPON infrastructure will be used for all residential facilities. The Designer shall inquire with the WSUP ITPM to determine whether GPON will be used for a particular academic building project.

A. Furnish, install, test and place into satisfactory and successful operation all equipment, materials, devices, and necessary appurtenances to provide a complete ANSI/TIA/EIA, NECA/NEIS and lSO/IEC compliant communications Gigabit Passive Optical Network as hereinafter specified and/or shown on the Contract Documents. The system is intended to be capable of integrating voice, data, and video signals onto a common medium, and shall be tested for and be capable of 1 Gigabit Ethernet operation as specified in TIA/EIA 568-B.2-10 and ISO/IEC 11801:2002/Amd 1:2008.
B. The work shall include all materials, equipment and apparatus not specifically mentioned herein or noted on the plans but which are necessary for a complete working ANSI/TIA/EIA and ISO/IEC compliant GPON.

Project No. #

Page 1

Washington State University (Pullman) Telecommunications Construction Guide Specification

Communications Optical Fiber Horizontal Cabling Section 27 15 23

1.3

SEQUENCING

Include any requirements for coordinating work with potentially unusual or specifically required sequencing. WSUP may choose to construct a project under two bid packages one for pathways and spaces (perhaps under a General Contract), and a second bid package for the Structured Cabling System (perhaps using the WA State DIS Master Contract). The Designer must coordinate with WSUP to determine if two bid packages will be used and include verbiage in the appropriate specification sections requiring the contractors to coordinate construction phasing and schedules.

A. Provide coordination with cabling system manufacturer's representatives to ensure that the manufacturer's inspectors are available to schedule site visits, inspections, and certification of the system. Provide and coordinate any modifications required by the manufacturer and have the manufacturer re-inspect and certify the system prior to the scheduled use of the system by the Owner.

B. Contractor is solely responsible for all costs associated with scheduling the manufacturer inspection, the inspection itself and any manufacturer-required re-inspections, and for any modifications to the installation as required by the manufacturers.

PART 2 - PRODUCTS Ensure that products listed under the PART 2 ­ Products paragraphs have corresponding installation instructions in PART 3 ­ Execution, or in another specification section if furnished but not installed under this section.
WSUP has standardized on certain manufacturers and certain products for all new Structured Cabling Systems in WSUP facilities. Products shall be specified accordingly. The Designer shall ensure that the latest part numbers are used for specified products. Any substitutions require WSUP pre-approval before specification.
If the Designer wishes to use products that deviate from WSUP standards, a Standards Variance Request shall be made, as described in the Technology Infrastructure Design Guide (TIDG). If the alternative product is approved, the Designer shall adapt this to reflect the approved changes.
The products listed throughout Part 2 - Products below are not all-inclusive for any given project. The Designer shall ensure that all required products are specified. The Designer shall also verify that the most current part number of each specified product is listed in this section.

2.1 A.
B.

GENERAL
GPON components shall be manufactured by the manufacturers listed below. Components shall not be intermixed between different manufacturers unless the manufacturer of the GPON has listed (in writing) another manufacturer's component as an "Approved Alternative Product" and will warrant the "Approved Alternative Product" as part of the GPON Manufacturer Warranty (see Section 27 05 00 -- "Common Works Results for Communications" PART 1 ­ WARRANTY). 1. Bid only the following GPON Manufacturers and only bid manufacturers for which the Contractor
is certified. Substitution is not acceptable. The GPON Manufacturers shall be the following: a. Fiber optic-related products: TE Connectivity
1) Corning fiber optic cabling products are not acceptable for GPON applications.
All fiber optic-related components shall be part of the fiber optic GPON product line ­ components shall not be intermixed between manufacturers' GPON product lines. The GPON product lines shall be

Project No. #

Page 2

Washington State University (Pullman) Telecommunications Construction Guide Specification

Communications Optical Fiber Horizontal Cabling Section 27 15 23

engineered "end-to-end" ­ the system and all of its components shall be engineered to function together as a single, continuous transmission path.

2.2 A.
2.3 A.

PATCH PANELS
Fiber Patch Panels: Shall be rack mountable and equipped with vertical cable guides and angleleft/angle-right adapters. Patch panels shall support both plug-and-play angled cassettes with bend radius protection and adapter plates. 1. Panels shall be TE TrueNet Fiber Panels (TFP) or TE RMG Series:
a. 1RU (Accommodate 2 plug-and-play cassettes): TE TFP-1TT00-000B b. 2RU (Accommodate 4 plug-and-play cassettes): TE TFP-2TT00-000B c. 4RU (Accommodate 8 plug-and-play cassettes): TE TFP-4TT00-000B d. 5RU (Accommodate 12 plug-and-play cassettes): TE TFP-5TT00-000B e. 1RU (Accommodate 3 adapter packs): TE RMG-1000-000B f. 2RU (Accommodate 6 adapter packs): TE RMG-2000-000B g. 4RU (Accommodate 12 adapter packs): TE RMG-4000-000B 2. Cassettes shall be equipped with 12 SC/APC singlemode adapters on the front with MPO feeder adapters on the rear, and shall be: a. Angle Left: TE TFP-12MPLSA1 b. Angle Right: TE TFP-12MPRSA1 3. Adapter Plates shall be equipped with 12 SC/APC singlemode adapters, and shall be: a. Left: TE TFP-12APLA1 b. Right: TE TFP-12APRA1 c. RMG SC/APC MPO Cassette: TE 1918447-1 4. Horizontal Cable Manager shall be: a. TE/ADC ADCCMHIB-2U
VIDEO WAVE DIVISION MULTIPLEXER MODULE
MicroVAM Chassis, 12-Position for up to 24 MicroVam modules: 1. TE FMT-GVM000000-A72P

B. Video-WDM Module, Dual MicroVAM 1x2, with 1310/1490 voice/data with 1550 video. 1. TE OPM-HVJNJ02-VZB

2.4

FIBER DISTRIBUTION HUBS

A. Fiber Indoor Distribution Hubs (iFDH) shall host optical fiber cable terminations and passive optical splitters in a wall-mounted or rack-mounted, UL 1863 Listed, NEMA-12 rated enclosure with rear access. Fiber Distribution Hubs shall include an integrated feeder cable.

B. Fiber Enclosures with plenum-rated, bend-optimized, MPO-terminated, feeder cable stubs shall be: 1. 72-Port with 9 splitter ports, 12-strand feeder cable stub and 6 MPO adapters for distribution: a. Empty (no feeder cable) TE OLH-MK072J00M0M000 b. 100 foot stub length, TE OLH-MK072J00M0MKCA c. 250 foot stub length, TE OLH-MK072J00M0MKEA d. 500 foot stub length, TE OLH-MK072J00M0MKBA 2. 288-Port with 18 splitter ports, 24-strand feeder cable stub and 24 MPO adapters for distribution: a. Empty (no feeder cable) TE OLH-MK288J00M0M000 b. 100 foot stub length, TE OLH-MK288J00M0MKCB c. 250 foot stub length, TE OLH-MK288J00M0MKEB d. 500 foot stub length, TE OLH-MK288J00M0MKBB 3. 432-Port with 22 splitter ports, 24-strand feeder cable stub and 36 MPO adapters for distribution: a. Empty (no feeder cable) TE OLH-MK432J00M0M000

Project No. #

Page 3

Washington State University (Pullman) Telecommunications Construction Guide Specification

Communications Optical Fiber Horizontal Cabling Section 27 15 23

b. 100 foot stub length, TE OLH-MK432J00M0MKCB c. 250 foot stub length, TE OLH-MK432J00M0MKEB d. 500 foot stub length, TE OLH-MK432J00M0MKBB
C. Splitters shall be equipped with bend-optimized fiber, with a wavelength range of 1260 to 1635 nm, with APC/SC pigtails, and shall be: 1. 2 x 16 splitter, TE OLS-MPP1P66 2. 2 x 32 WDM splitter, TE OLS-MPP1E66 3. 2 x 32 splitter, TE OLS-MPP12A66

2.5

FIBER DISTRIBUTION TERMINALS

A. Fiber Distribution Terminals (FDT) shall serve as a lockable distribution/consolidation point with an integrated patch field and slack-storage reel. Fiber Distribution Terminals shall be UL 1863 Listed, NEMA-12 rated and be suitable for wall-mounting above ceilings or under accessible floors. Fiber Distribution Terminals shall include an integrated, bend-optimized, fiber feeder cable.

B. Rapid Fiber Distribution Terminals (Rapid FDT) (with integrated cable reel) shall be: 1. 12-strand, loose tube, plenum-rated feeder cable, with MPO termination: a. 100 foot stub length, TE OLR-SJ12J00D1002A b. 200 foot stub length, TE OLR-SJ12J00D2002A c. 300 foot stub length, TE OLR-SJ12J00D3002A 2. 24-strand, loose tube, plenum-rated feeder cable, with MPO termination: a. 100 foot stub length, TE OLR-SJ24J00D1002A b. 200 foot stub length, TE OLR-SJ24J00D2002A c. 300 foot stub length, TE OLR-SJ24J00D3002A
C. Mini Rapid Distribution Terminals (Mini RDT) (requires separate cable spool) shall be: 1. 12-strand, loose tube, plenum-rated feeder cable, with MPO termination: a. 200 foot stub length, TE ODT-SM12J00D0619A b. 300 foot stub length, TE ODT-SM12J00D0929A c. 400 foot stub length, TE ODT-SM12J00D1229A d. 500 foot stub length, TE ODT-SM12J00D1529A

2.6

FIBER SPLITTERS

A. Wall-mounted Fiber Splitter Boxes, for up to 32 fibers: 1. Double Sided, Single Door Wall Mount Box, supporting 1 splitter adapter plate and up to 3 SC/APC adapter plates: TE 1435128-1 2. FSB-32 Indoor Enclosure, with SC/APC adapters: a. No splitters, no splice trays: TE OSB-SBJ032000000 b. No splitters, with heat shrink splice trays: TE OSB-SBJ232000000 c. 2 x 32 splitter installed, no splice trays: TE OSB-SBJ032G10000 d. 2 x 32 splitter installed, with heat shrink splice trays: TE OSB-SBJ232G10000

B. Rack-mounted Splitter Enclosure, 4RU, supporting up to 3 splitter adapter plates (3 fiber inputs) and up to 9 SC/APC adapter plates (96 fiber outputs): 1. Rack Mount Enclosure: TE 559552-2
C. Rack-mounted Splitter Panel: 1. Rack Mount Panel, supporting up to 3 splitter adapter plates (3 fiber inputs) and up to 9 SC/APC adapter plates (96 fiber outputs) (1U each, quantity 4 required): TE 1777125-1 2. FMT Rack Mount Splitter Panel, 1U a. 2 x 32 Splitter: TE OPS-FMTSP-GJJ01

Project No. #

Page 4

Washington State University (Pullman) Telecommunications Construction Guide Specification

Communications Optical Fiber Horizontal Cabling Section 27 15 23

D. E. F. G. H. I.
J.
2.7 A.
2.8 A.

Rack-mounted Splitter Drawer, 1U, supporting up to 4 splitter adapter plates: 1. Rack Mount Panel (1U): TE OPS-MPPACCRMPNL
Access Floor-mounted Enclosure, supporting 1 splitter adapter plate (1 fiber input): 1. 32-Fiber EAZ Floor Mount Enclosure: TE 1777215-1
Bracket for Wall-mounting or Furniture-mounting: 1. Bracket: TE 1777126-1, with optional cable ring
SC/APC MPO Cassette: 1. 12-Fiber: TE 1918447-1
SC/APC Adapter Plate: 1. 12-Fiber: TE 559596-3
Splitter with Adapter Plate: Bend-optimized and rugged fiber (54 inch cable length), terminated with SC/APC connectors, shall be: 1. Front input kit (cable assembly and adapter): TE 2111699-1
Optical Splitter Modules, with APC/SC pigtails, for use with TE iFDH, FSB, Splitter Drawers and Splitter Panels: 1. 2 x 16 splitter: TE OLS-MPP1P66 2. 2 x 32 WDM Splitter: TE OLS-MPP1E66 3. 2 x 32 splitter: TE OLS-MPP12A66
CONNECTORS
Fiber Optic Couplers (modular jacks): Shall be TE SL form factor, such that the jacks will snap into the faceplates specified in Section 27 15 00. 1. SC Simplex Coupler, APC, Green: TE 2-1375055-1
STATIONS
Faceplates: See Section 27 15 00. Reuse existing doublegang faceplates when upgrading existing applications (that already have doublegang faceplates). TE does not manufacture doublegang faceplates with 2 or 4 port angled port inserts. Currently, the best that can be done is to reused the existing faceplates with their straight port inserts.

B. 2.9
A.
B.

Faceplates: Single gang, angled faceplate 1. 2-ports: TE 1375155-X 2. 4-ports: TE 406185-X.
ELECTRONICS
Optical Network Terminals (ONT) shall be: 1. Zhone zNID GPON Indoor ONT
a. Model with Power-over-Ethernet (POE) b. Model that is non-POE c. Model that is non-POE with RF Video
Optical Line Terminals (OLT) shall be: 1. Zhone MXK OLT Chassis

Project No. #

Page 5

Washington State University (Pullman) Telecommunications Construction Guide Specification

Communications Optical Fiber Horizontal Cabling Section 27 15 23

2. Zhone MXK Line Cards

2.10 CABLE

A. General: Cables shall be manufactured by the selected SCS Manufacturer. All cables shall be plenumrated.
B. Fiber Cable: 1. Fiber cables shall be Singlemode 8.3/125 µm OS2, factory-terminated, 3mm yellow jacket, and shall permit a bend radius of 7.5mm without changing cable characteristics. Cable shall be manufactured by the selected SCS Manufacturer and shall be: a. SC APC to SC APC, plenum-rated, Ivory drop cable: TE PAT-6C6C-PS0GxxxM b. TE Single Strand SM 3MM Jacket 7-1553409-3 Commscope manufactures a multimode zipcord product that is indoor/outdoor rated, and plenum rated. However, they don't currently manufacture this cable in singlemode. With the pending merger between Commscope and TE expected to culminate in 2015, it is anticipated that a singlemode product can be procured within TE's warranty coverage at some point in the near future.
Delete the following paragraph if there are no wet area applications in the project. 2. For wet environments, fiber cables shall meet the performance and behavioral characteristics
described above, be rated for indoor/outdoor use, and be plenum-rated where required. a. Commscope, zipcord

C. Hook and Loop Cable Managers: Reusable hook and loop straps (similar to Velcro), adjustable tension, roll or spool dispensed: 1. Panduit HLS-15R0 2. SIEMON VCM-xxxx-xxx 3. TE 5/8 inch wide: 1375255-X 4. Or approved equal

2.11 INNERDUCT

A. Intra-building innerduct shall be 1 inch size, orange, unsplit, corrugated, with pull tape: 1. Plenum-rated: Carlon Plenum-Gard CF4x1C-nnnn 2. Riser-rated: Carlon Riser-Gard DF4x1C-nnnn

2.12 LABELING AND ADMINISTRATION

A. Labels: 1. As recommended in ANSI/TIA/EIA 606. Labels shall be permanently inscribed (i.e. not subject to fading or erasure), permanently affixed, and created by a hand-carried label maker or a computer/software-based label making system. Handwritten labels are not acceptable. a. For Station Cable: 1) Brady: Bradymaker Wire Marking Labels WML-511-292 (or approved equal)

B. Hand-carried label maker: 1. Brady: ID Pro Plus (or approved equal).

Project No. #

Page 6

Washington State University (Pullman) Telecommunications Construction Guide Specification

Communications Optical Fiber Horizontal Cabling Section 27 15 23

PART 3 - EXECUTION

3.1

GENERAL

Review and edit the following installation requirements based on the products specified in PART 2 ­ Products above or on the products specified in another section if installed but not supplied under this section, and as applicable to this project.

A. Provide a complete functioning GPON infrastructure, including all required components. Ensure that products incorporated into the project under PART 3 paragraphs have corresponding Product information in PART 2 ­ Products, or in another specification Section if installed but not supplied under this Section.
The following paragraphs include installation requirements written specifically for the Products listed in Part 2 above. If other products are approved, the Designer shall ensure that appropriate Part 3 installation requirements are added/removed or modified as applicable and described in equal or greater detail to the following paragraphs.
All installation requirements shall be consistent with the manufacturer's requirements.

3.2

PATCH PANELS

Review and edit the following installation requirements based on the products specified in PART 2 ­ Products above or on the products specified in another section if installed but not supplied under this section, and as applicable to this project.

A.
3.3 A.
3.4 A.
3.5 A.
3.6 A.
3.7 A.

Provide patch panels and horizontal wire management according to locations, elevations, and plan views as shown on the Contract Documents. 1. Fiber Optic: Terminate horizontal fiber optic cabling from all floors on horizontal fiber optic patch
panels in the main telecommunications room (MDF). 2. Horizontal Wire Management: Provide horizontal wire management as shown on the Contract
Documents.
FIBER DISTRIBUTION HUBS
Provide fiber distribution hubs according to locations, elevations, and plan views as shown on the Contract Documents.
FIBER DISTRIBUTION TERMINALS
Provide fiber distribution terminals according to locations, elevations, and plan views as shown on the Contract Documents.
FIBER SPLITTERS
Provide fiber splitters as shown on the Contract Documents.
CONNECTORS
Provide fiber optic couplers for each outlet as shown on the Contract Documents.
STATIONS
Provide outlets, faceplates, fiber terminations, and ONT devices for each endpoint application as shown on the Contract Documents.

Project No. #

Page 7

Washington State University (Pullman) Telecommunications Construction Guide Specification

Communications Optical Fiber Horizontal Cabling Section 27 15 23

3.8

CABLE

A. General (applicable to all cable types): Provide non-plenum (CM/CMR, OFNR) rated cable for locations where cable is to be installed in conduit. For cable not installed in conduit, provide plenum (CMP, OFNP) rated cable if cable is installed in a plenum air space environment. Otherwise, provide nonplenum-rated (CMR) cabling. Cabling shall bear plenum or non-plenum markings for the environment in which it is installed. 1. Horizontal Distribution: Provide station cable in types, sizes, and quantities as defined by the Symbol Schedule and as shown on the Contract Documents. Install cable between the station and its associated telecommunications room. Provide one cable per each connector at each station. Provide cables of the same type in the same color ­ multiple colors of the same cable type are not acceptable. 2. Install cable in compliance with ANSI/TIA/EIA and ISO/IEC 11801 requirements and BICSI TCIM practices. 3. Adhere to the bending radius and pull strength requirements as detailed in the ANSI/TIA/EIA standards and the manufacturer's installation recommendations during cable handling and installation. a. Pull all cables simultaneously where more than one cable is being installed in the same raceway. b. Use pulling compound or lubricant where necessary. Use compounds that will not damage conductor or insulation (Polywater, or approved equal). c. Use pulling means, including fish tape, cable, rope, and basket-weave wire/cable grips that will not damage media or raceway. Repair or replace conduit bushings that become damaged during cabling installation. 4. Install cable in a continuous (non-spliced) manner unless otherwise indicated. 5. Install exposed cable parallel to and perpendicular to surfaces on exposed structural members and follow surface contours where possible. 6. Tie or clamp cabling. Attaching cables to pipes, electrical conduit, mechanical items, existing cables, or the ceiling support system (grids, hanger wires, etc. ­ with the exception of ceiling support anchors) is not acceptable. Install tie-wraps in conformance with the GPON manufacturer's installation recommendations. Do not over-tighten tie wraps or cause crosssectional deformation of cabling. 7. Cable at the backboards: a. Lay and dress cables to allow other cables to enter raceway (conduit or otherwise) without difficulty at a later time by maintaining a working distance from these openings. b. Route cable as close as possible to the ceiling, floor, sides, or corners to insure that adequate wall or backboard space is available for current and future equipment and for cable terminations. c. Do not use D-rings to route horizontal GPON cabling. Instead, use vertical ladder racking (securing cabling with hook-and-loop straps) and horizontal ladder racking, using the most direct route to the termination point. Route via a path that will minimize obstruction to future installation of equipment, backboards or other cables. 8. Cable in the telecommunications rooms: a. For telecommunications rooms with ladder racking, lay cable neatly in ladder rack in even bundles and loosely secure cabling to the ladder rack at regular intervals with hook-andloop straps. 9. Cable terminating on patch panels located on racks: a. Route cables in telecommunications rooms to patch panels on racks by routing across ladder rack across top of rack and then down vertical ladder rack to patch panel.

B. Fiber Optic Cable: 1. Provide station cable in the locations shown on the Contract Documents. Provide service loops with a minimum length of 12 inches in outlet boxes and no less than 10 feet in the ER/TR's.

Project No. #

Page 8

Washington State University (Pullman) Telecommunications Construction Guide Specification

Communications Optical Fiber Horizontal Cabling Section 27 15 23

Store the remainder of the slack using manufacturer-recommended solutions (reels, cartridges, etc.). a. For workstation outlets with both fiber and copper cabling, terminate fiber optic cabling
after copper cabling has been installed and terminated.
Commscope manufactures a multimode zipcord product that is indoor/outdoor rated, and plenum rated. However, they don't currently manufacture this cable in singlemode. With the pending merger between Commscope and TE expected to culminate in 2015, it is anticipated that a singlemode product can be procured within TE's warranty coverage at some point in the near future.

Delete the following paragraph if there are no wet area applications in the project.
b. For fiber optic station cabling installed in wet areas, including floor boxes in slab-on-grade applications, use Indoor/Outdoor Wet Environment-rated cabling.
2. Innerduct
The Designer shall indicate in the Contract Documents where innerduct is required, consistent with the requirements described below.
a. Innerduct is required for routing horizontal GPON fiber optic cabling through all vertical riser pathways (conduits and sleeves) that exceed 4 feet in length.
b. Innerduct is also required for routing horizontal GPON fiber optic cabling through cable trays where larger outside plant cable shares the cable tray.
c. Otherwise, innerduct is not required for routing horizontal GPON fiber optic cabling. d. Where innerduct is required, install fiber optic cable in innerduct per manufacturer's
instructions. Innerduct shall terminate within 6 inches of top of each patch panel where fiber optic cable terminates. Secure innerduct with zip-ties at intervals not exceeding 24 inches. Do not use wire or tape. e. See Sections 27 13 00 and 33 82 00 for innerduct requirements related to fiber optic backbone cabling in inside plant and outside plant backbone applications, respectively.
The Designer shall verify during construction that this form has been submitted by the Contractor.

3.9

LABELING AND ADMINISTRATION

A. Horizontal Cable Labeling: 1. Provide white-colored labels. 2. Cables at Patch Panel end: a. Affix label at end of the cable within 4 inches of the cable end near the patch panel termination point (on the rear of the patch panel). Include a clear vinyl adhesive wrapping applied over the label in order to permanently affix the label to the cable. Using transparent tape to affix labels to cables is not acceptable. b. Affix a second label on the front side of the patch panel adjacent to the screen-printed jack number where the cable terminates. c. Cables shall be labeled according to the following scheme:
aaaaa
aaaaa = Room Number where outlet is located
3. Cables at Outlet end: a. Affix label at end of the cable within 4 inches of the cable end near the jack. Include a clear vinyl adhesive wrapping applied over the label in order to permanently affix the label to the cable. Using transparent tape to affix labels to cables is not acceptable. b. Affix a second label on the exterior of the faceplate, adjacent to the jack corresponding to the cable.

Project No. #

Page 9

Washington State University (Pullman) Telecommunications Construction Guide Specification

Communications Optical Fiber Horizontal Cabling Section 27 15 23

c. Labeling shall be according to the following scheme:

aaaaa:bcdd

or

aaaaa:

bcdd

aaaaa = Telecom Room Number where patch panel is located b = Equipment Rack Number c = Patch Panel Number dd = Patch Panel Port Number

4. Apply the cable numbering shown in the horizontal cable labeling scheme found in the Appendix at the end of this specification section. For cable numbering that is not shown on the drawings, request numbering assignments from the Owner.
5. For outlets that are mounted above an accessible ceiling (such as for wireless access points), affix white adhesive label to the underside of the ceiling grid beneath the outlet such that the label is visible to a person walking through the room. The label's location shall allow a person to know which ceiling tile to remove to access the outlet.

B.
3.10 A.

Labeling on Patch Panels: 1. General: Label patch panels as shown on the Contract Documents. 2. Provide white-colored labels. 3. Ports: Ports are typically pre-labeled by the manufacturer with adapter pack numbering and
sequential jack numbers (i.e. 1 to 12). Provide a label for each port that matches the label of the cable terminated on that port. Do not cover the manufacturer's port numbering with the labels.
TESTING
Provide test records on a form approved by the Owner and Designer. Include the test results for each cable in the system. Submit the test results for each cable tested with identification as discussed under LABELING AND ADMINISTRATION above. Include the cable identifier, outcome of test, indication of errors found, cable length, retest results, and name and signature of technician completing the tests. Provide test results to the Owner and Designer for review and acceptance within two weeks of Substantial Completion. 1. Print test records for each cable within the system directly from the tester to an Adobe Acrobat
PDF file, and submit only in electronic form (on CDROM or DVDROM) to the Owner and Designer for review. Handwritten test results will not be accepted.

B. Test the GPON after installation for compliance to all applicable standards as follows: 1. Fiber Optic: a. Horizontal Distribution: Test all strands following the procedure in Section 27 13 00 ­ "Communications Backbone Cabling".

C. Identify cables and equipment that do not pass to the Owner and Designer. Determine the source of the non-compliance and replace or correct the cable or the connection materials. Retest the cable or connection materials at no additional expense to the Owner. Provide a complete revised set of all test results to the Owner and Designer, in the same manner as above. Remove original individual cable test reports that are unacceptable and insert the new corrected cable test reports. Do not simply resubmit the test reports for the corrected cabling only. 1. In addition to the above, if it is determined that the cable is faulty, remove the damaged cable and replace it with a new cable. Cable repairs are not acceptable. The procedure for removing the cable shall be as follows: a. Prior to removal of damaged cable and installation of new cable: 1) Inform the Owner and Designer of the schedule for the removal and installation. 2) Test the new cable on the reel per paragraph B, above.

Project No. #

Page 10

Washington State University (Pullman) Telecommunications Construction Guide Specification

Communications Optical Fiber Horizontal Cabling Section 27 15 23

3) Test cables that occupy the same innerduct or conduit (if not in innerduct) as the damaged cable per paragraph B, above, regardless of whether or not they are new cables installed as part of this project or existing cables installed prior to this project.
b. Remove the damaged cable and provide new cable. c. After the removal of the damaged cable and installation of the new cable:
1) Test the new cable per the paragraph titled TESTING. 2) Test cables that occupy the same innerduct or conduit (if not in innerduct) as the
damaged cable per paragraph B, above, regardless of whether they are new cables installed as part of this project or existing cables installed prior to this project. a) If any of the cables requiring testing are in use, coordinate with the Owner to
schedule an outage opportunity during which the testing can be performed. d. If a cable which occupies the same innerduct or conduit (if not in innerduct) as a damaged
cable is damaged by the extraction and installation process, replace the cable at no additional expense to the Owner. 1) Damaged cables which are replaced shall be subject to the testing procedures of the
paragraph titled TESTING.

Designer ­ add a cable labeling schedule to this section for horizontal copper and horizontal fiber, similar to the example provided.
Change the red-colored "X" to indicate the number of pages.

APPENDIX The following X pages contain the horizontal cable labeling content for each cable.

END OF SECTION

Project No. #

Page 11



