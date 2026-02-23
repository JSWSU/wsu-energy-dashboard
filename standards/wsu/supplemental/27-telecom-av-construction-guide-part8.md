# 27-telecom-av-construction-guide (Part 8 of 18)

> **Continued from:** 27-telecom-av-construction-guide-part7.md

---

3.5 A.
B.

When building identifiers, room identifiers, and cable numbers lack a character in a given position, an asterisk shall be used as a placeholder or that position deleted, as follows:
· * This character position should be replaced by an asterisk if the number doesn't include an alpha character in that position.
·  This character position should be deleted if not necessary. c. Pull-out labeling plate: Each fiber patch panel includes a pull-out labeling plate with space
to document the purpose of each fiber optic cable. Apply self-adhesive labels to the plate to matching the cable label content described above.
TESTING
Provide test records on a form approved by the Owner and Designer. Include the test results for each cable in the system. Submit the test results for each cable tested with identification as discussed under LABELING AND ADMINISTRATION above. Include the cable identifier, outcome of test, indication of errors found, cable length, retest results, and name and signature of technician completing the tests. Provide test results to the Owner and Designer for review and acceptance within two weeks of Substantial Completion. 1. Print test records for each cable within the system directly from the tester and submit in paper
form (in a binder) and in electronic PDF format (on flash drive or CDROM) to the Owner and Designer for review. Handwritten test results will not be accepted.
Test the SCS after installation for compliance to all applicable standards as follows: 1. Intrabuilding Backbone Copper: Test all cable pairs for length, shorts, opens, grounds, continuity,
polarity reversals, termination order, transposition (wire map), attenuation, and the presence of AC voltage. All pairs shall demonstrate compliance to TIA/EIA 568-B Category 3 standards.

Project No. #

Page 8

Washington State University (Pullman) Telecommunications Construction Guide Specification

Communications Backbone Cabling Section 27 13 00

a. Test copper cable on the reel upon delivery to the job site, again prior to installation, and again after installation.
b. Test entire channel, from entrance protection to patch panel. c. Use a TIA/EIA Level III testing instrument, re-calibrated within the manufacturer's
recommended calibration period, with the most current software revision based upon the most current TIA/EIA testing guidelines, capable of storing and printing test records for each cable within the system. 1) Fluke DSP-4000, or approved equal. 2. Fiber: Test fiber optic cable on the reel upon delivery to the job site prior to installation, and again after installation. a. Prior to testing, calculate the cable loss budget for each fiber optic cable and clearly show the result on the test documentation. Calculate maximum loss using the following formula, assuming no splices: 1) Horizontal Distribution:
a) Max Loss = 2.0db (per ANSI/TIA/EIA 568-B) 2) Backbone Distribution:
a) Max Loss = [(allowable loss/km) * (km of fiber)] + [(.3db) * (# of connectors)] b) A mated connector to connector interface is defined as a single connector for
the purposes of the above formula. c) A given fiber strand shall not exceed its calculated maximum loss (per the
above formula). b. Test all strands using a bi-directional end-to-end optical transmission loss test instrument
(such as an OTDR) trace performed per ANSI/TIA/EIA 455-61 or a bi-directional end-toend power meter test performed per ANSI/TIA/EIA 455-53A, and ANSI/TIA/EIA 568-B. Test the polarity of each pair of strands. Record the following measurements: length and attenuation. 1) Calculate attenuation loss numbers by taking the sum of the two bi-directional
measurements and dividing that sum by two. 2) Provide test measurements as follows:
a) Multimode Cable: Test at both 850 and 1300nm. b) Singlemode Cable: Test at both 1310 and 1550nm. c. Test results shall conform to: 1) The criteria specified in ANSI/TIA/EIA-568B. 2) The Contractor's calculated loss budget above. 3) The criteria specified in IEEE 802.3ae-2002 (10GBase-X 10 Gigabit Ethernet). a) In addition to the above, perform tests both recommended and mandated by
Corning. Tests shall confirm/guarantee compliance to Corning's performance standards and also IEEE 802.3ae-2002 for a maximum end-to-end dB loss of 2.5 dB. 4) The criteria specified in IEEE 802.3ae-2002 (10GBase-X 10 Gigabit Ethernet).

C. Identify cables and equipment that do not pass to the Owner and Designer. Determine the source of the non-compliance and replace or correct the cable or the connection materials. Retest the cable or connection materials at no additional expense to the Owner. Provide a complete revised set of all test results to the Owner and Designer, in the same manner as above. Remove original individual cable test reports that are unacceptable and insert the new corrected cable test reports. Do not simply resubmit the test reports for the corrected cabling only. 1. In addition to the above, if it is determined that the cable is faulty, remove the damaged cable and replace it with a new cable. Cable repairs are not acceptable. The procedure for removing the cable shall be as follows: a. Prior to removal of damaged cable and installation of new cable: 1) Inform the Owner and Designer of the schedule for the removal and installation. 2) Test the new cable on the reel per paragraph B, above.

Project No. #

Page 9

Washington State University (Pullman) Telecommunications Construction Guide Specification

Communications Backbone Cabling Section 27 13 00

3) Test cables that occupy the same innerduct or conduit (if not in innerduct) as the damaged cable per paragraph B, above, regardless of whether or not they are new cables installed as part of this project or existing cables installed prior to this project.
b. Remove the damaged cable and provide new cable. c. After the removal of the damaged cable and installation of the new cable:
1) Test the new cable per the paragraph titled TESTING. 2) Test cables that occupy the same innerduct or conduit (if not in innerduct) as the
damaged cable per paragraph B, above, regardless of whether they are new cables installed as part of this project or existing cables installed prior to this project. a) If any of the cables requiring testing are in use, coordinate with the Owner to
schedule an outage opportunity during which the testing can be performed. d. If a cable which occupies the same innerduct or conduit (if not in innerduct) as a damaged
cable is damaged by the extraction and installation process, replace the cable at no additional expense to the Owner. 1) Damaged cables which are replaced shall be subject to the testing procedures of the
paragraph titled TESTING.

3.6

CLOSE-OUT

A. Furnish uninstalled fiber optic cable reel remnants to the Owner.

END OF SECTION

Project No. #

Page 10

Washington State University (Pullman) Telecommunications Construction Guide Specification

Communications Horizontal Cabling Section 27 15 00

PART 1 - GENERAL This section of the Telecommunications Construction Guide Specification has references, products, procedures, processes, and work descriptions/summaries that are common to many Washington State University Pullman (WSUP) campus telecommunications projects. This information is provided in specification format to serve as a guide to the Designer in producing a CSI-compliant specification that will meet the unique requirements of WSUP Telecommunications projects. However, this document is not intended to be a Master Specification. The information included in this section is not intended to be allinclusive for any given project.
The Designer shall edit this section (adding and/or removing content where required) to meet the requirements of a given project.
Prior to publishing the specifications for bid or construction purposes, all edits shall be made using the MS Word Tracking Changes feature. When submitting the specifications for review at each progress milestone, print the specifications showing the revision markings.
Text in shaded boxes (such as this text) is included to aid the Designer in understanding areas of this section that may require modification for a particular circumstance. Although this text is generally written in declarative form, the Designer shall consider it guidance only. The Designer shall not assume that the content of this specification section is suitable or sufficient for any given project in its current form, and shall remain responsible for developing a thorough and complete specification that meets the requirements of the project being designed.

1.1

SUMMARY

Review and edit the following list of generic type products for relevance to this project. This listing should not include procedures or processes, preparatory work, or final cleaning.

A. 1.2

Provide all materials and labor for the installation of an inside plant telecommunication system. This section includes Inside Plant Communications cabling, termination, and administration equipment and installation requirements for the specified Structured Cabling System (SCS - See Definition Below).
SYSTEM DESCRIPTION Review and edit the following statement(s) for applicability to this project, restricted to describing performance, design requirements and functional tolerances of a complete system.

A. Furnish, install, test and place into satisfactory and successful operation all equipment, materials, devices, and necessary appurtenances to provide a complete ANSI/TIA/EIA, NECA/NEIS and lSO/IEC compliant communications Structured Cabling System (SCS) as hereinafter specified and/or shown on the Contract Documents. The system is intended to be capable of integrating voice, data, and video signals onto a common media, and shall be tested for and be capable of 10 Gigabit Ethernet operation as specified in TIA/EIA 568-B.2-10 and ISO/IEC 11801:2002/Amd 1:2008.
B. The work shall include all materials, equipment and apparatus not specifically mentioned herein or noted on the plans but which are necessary to make a complete working ANSI/TIA/EIA and ISO/IEC compliant SCS.

Project No. #

Page 1

Washington State University (Pullman) Telecommunications Construction Guide Specification

Communications Horizontal Cabling Section 27 15 00

1.3

SEQUENCING

Include any requirements for coordinating work with potentially unusual or specifically required sequencing. WSUP may choose to construct a project under two bid packages one for pathways and spaces (perhaps under a General Contract), and a second bid package for the Structured Cabling System (perhaps using the WA State DIS Master Contract). The Designer must coordinate with WSUP to determine if two bid packages will be used and include verbiage in the appropriate specification sections requiring the contractors to coordinate construction phasing and schedules.

A. Provide coordination with the cabling manufacturers to ensure that manufacturers' inspectors are available to schedule site visits, inspections, and certification of the system. Provide and coordinate any manufacturer-required modifications and have manufacturer re-inspect and certify the system prior to the scheduled use of the system by the Owner.

B. The Contractor is solely responsible for all costs associated with scheduling the manufacturer inspection, the inspection itself and any manufacturer-required re-inspections, and for any modifications to the installation as required by the manufacturers.

PART 2 - PRODUCTS Ensure that products listed under the PART 2 ­ Products paragraphs have corresponding installation instructions in PART 3 ­ Execution, or in another specification section if furnished but not installed under this section.
WSUP has standardized on certain manufacturers and certain products for all new Structured Cabling Systems in WSUP facilities. Products shall be specified accordingly. The Designer shall ensure that the latest part numbers are used for specified products. Any substitutions require WSUP pre-approval before specification.
If the Designer wishes to use products that deviate from WSUP standards, a Standards Variance Request shall be made, as described in the Technology Infrastructure Design Guide (TIDG). If the alternative product is approved, the Designer shall adapt this to reflect the approved changes.
The products listed throughout Part 2 - Products below are not all-inclusive for any given project. The Designer shall ensure that all required products are specified. The Designer shall also verify that the most current part number of each specified product is listed in this section.

2.1 A.

GENERAL
SCS components shall be manufactured by the manufacturers listed below. Components shall not be intermixed between different manufacturers unless the manufacturer of the SCS has listed (in writing) another manufacturer's component as an "Approved Alternative Product" and will warrant the "Approved Alternative Product" as part of the SCS Manufacturer Warranty (see Section 27 05 00 -- "Common Works Results for Communications" PART 1 ­ WARRANTY). 1. Bid only the following SCS Manufacturers and only bid manufacturers for which the Contractor is
certified. The SCS Manufacturers shall be the following. Substitution is not acceptable: a. TE, for copper-related products b. Fiber optic-related products: Corning
1) TE Connectivity fiber optic cabling products are not acceptable for non-GPON horizontal fiber optic applications. For GPON applications, see Section 27 15 23 ­ Communications Optical Fiber Horizontal Cabling.

Project No. #

Page 2

Washington State University (Pullman) Telecommunications Construction Guide Specification

Communications Horizontal Cabling Section 27 15 00

B.
2.2 A.

All copper-related components shall be part of the copper SCS product line ­ components shall not be intermixed between manufacturers' SCS product lines. The SCS product lines shall be engineered "end-to-end" ­ the system and all of its components shall be engineered to function together as a single, continuous transmission path. 1. The SCS Product Line shall be the following:
a. Category 6 U/UTP Copper Distribution: TE 620 Series solution. Substitution is not acceptable. WSUP has standardized on using Category 6 cabling for all projects ­ no exceptions.
However, some audio visual applications require Category 6A cabling. The Telecommunications Designer shall work with the Audio Visual Designer to determine whether/where Category 6A cabling is required. The Telecommunications Designer shall specify all telecommunications cabling, including that required to serve audio visual system requirements. b. Category 6A F/UTP Copper Distribution: TE XG Series solution. Substitution is not acceptable.
PATCH PANELS
Copper Patch Panels: Shall be complete with pre-manufactured cable management for supporting station cable behind the patch panel, with incidental materials necessary for mounting and wired for T568A. 1. Category 6 Horizontal Distribution Patch Panels (Workstation Patch Panels):
a. 24 Port, SL, Straight, Multimedia: TE 1375291-1 with Category 6 connectors TE 1375055-2 (Black) as required Category 6A is only required for certain Audio/Visual applications. Verify requirements with AVPM and Audio Visual Designer. Delete the following paragraph if it is not required.
2. Category 6A Horizontal Distribution Patch Panels (Workstation Patch Panels): a. Category 6A, 24 Port, SL, Shielded, Straight: TE 1933319-2 b. Cable Management Bar: TE 557548-1
3. Horizontal Cable Management Panels a. 2U: Panduit WMPH2E Review and edit the following fiber optic products/part numbers as applicable to this project.

B.
2.3 A.

Fiber Optic Patch Panels: See Section 27 13 00 ­ Communications Backbone Cabling. 1. Connector Panels:
a. Multimode: Corning (12-strand/6-connector) duplex SC, CCH-CP12-91
CONNECTORS
Copper Connectors (modular jacks): 8-position/8-conductor, insulation displacement connection (IDC), non-keyed, and shall accept modular 8-position/8-conductor plugs, complete with multicolored identification labels/icons for identification, and with a universally color-coded wiring pattern for both T568A and T568B. Copper connectors shall be manufactured by the selected SCS Manufacturer. 1. Category 6 Horizontal Distribution: Shall meet or exceed Category 6 transmission requirements
for connecting hardware, as specified in ANSI/TIA/EIA 568-B.2-10 and ISO/IEC 11801:2002/Amd 1:2008, and shall be part of the UL LAN Certification and Follow-up Program: a. Category 6:
1) TE 1375055-1 (both rear and side cable entry), (Almond) 2. Category 6A Horizontal Distribution: Shall meet or exceed Category 6A transmission
requirements for connecting hardware, as specified in ANSI/TIA/EIA 568-B.2-10 and ISO/IEC 11801:2002/Amd 1:2008, and shall be part of the UL LAN Certification and Follow-up Program: a. Category 6A:

Project No. #

Page 3

Washington State University (Pullman) Telecommunications Construction Guide Specification

Communications Horizontal Cabling Section 27 15 00

2.4 A.
B. C. 2.5 A. B.
C.

Category 6A is only required for some Audio Visual applications. 1) TE 1711160-2 (rear cable entry) (Orange) 2) TE 1711295-2 (side cable entry)
STATIONS
Faceplates: Complete with port identification labels and blank inserts/fillers for covering unused connector openings: 1. Stations to be used for VOIP wall-mount telephones: Brushed stainless steel with stainless steel
mounting lugs suitable for supporting wall-mount telephones: a. SEMTRON 1FM-0E-TE-Phone-DP (with CAT6 jack) b. or approved equal.
Review faceplate material/color and mounting strap color with Architect/Interior Designer for coordination with design. 2. All other stations shall be double-gang standard 4-port faceplates (Almond): a. TE 83935-1 with blank inserts as required 406339-1 3. All stations without cabling shall be double-gang standard blank faceplates (Almond).
Fiber Optic Outlets: 1. Corning: Single-Panel Housing with SC-Duplex Connector Panel:
a. Corning SPH-01P with CCH-CP06-91.
Surface Device Boxes: Surface mount device boxes shall be: 1. Wiremold
CABLE
General: Cables shall be manufactured by the selected SCS Manufacturer. All cables shall be plenumrated.
Copper Cables: Shall be 4-pair, 23 AWG, with solid copper conductors: 1. Category 6 U/UTP:
a. Plenum (CMP): TE TE620P-WTxx (white), plenum-rated. Delete the following paragraph if there is no requirement for cabling in slab-on-grade conduit/floor box applications or outdoor conduit applications.
NOTE: The Mohawk cable is not suitable for direct bury applications.
NOTE: In order for the Mohawk cabling to be included in under the TE warranty, the Cabling Contractor must submit a form to TE titled "TE Connectivity Product Warranty Deviation" prior to installing the cabling. The ND&I Cabling Contractor can request this form from TE's representatives. See paragraph 3.5.x below for more information. 2. Category 6 U/UTP Indoor/Outdoor Wet Environment Rated: a. Mohawk VersaLAN M59092 (White) (not plenum-rated) Delete the following paragraph if Category 6A cabling is not part of this project. 3. Category 6A F/UTP: a. Plenum: TE TE640PF-WTxx (white)
Fiber Cable: 1. Multimode 50/125 µm OM3: Shall be graded index, tight-buffered, extended/high grade with a
maximum attenuation of 2.8 dB/km @ 850 nm and 1.0 dB/km @ 1300 nm and a minimum effective modal bandwidth of 4700 MHz/km @ 850 nm. Cable shall support 1GB Ethernet for

Project No. #

Page 4

Washington State University (Pullman) Telecommunications Construction Guide Specification

Communications Horizontal Cabling Section 27 15 00

lengths of up to 1000 meters, 10GB Ethernet for lengths up to 550 meters and 100GB for lengths up to 150 meters. Cable shall be manufactured by the selected SCS Manufacturer: a. Corning Pretium 300, MIC and Unitized MIC
TE and Commscope will merge in late 2015, after which warranty coverage should be simpler for wet environment cable. Delete the following paragraph if there are no wet environment indoor fiber applications, otherwise additional part number information should be added.
b. Indoor/Outdoor Wet Environment Rated: 1) Commscope OM3 zipcord

D. Hook and Loop Cable Managers: Reusable hook and loop straps (similar to Velcro), adjustable tension, roll or spool dispensed: 1. Panduit HLS-15R0 2. SIEMON VCM-xxxx-xxx 3. TE 5/8 inch wide: 1375255-X 4. Or approved equal

2.6

LABELING AND ADMINISTRATION

A. Labels: 1. As recommended in ANSI/TIA/EIA 606. Permanent (i.e. not subject to fading or erasure), permanently affixed, self-laminating vinyl, and created by a hand-carried label maker or a computer/software-based label making system. Handwritten labels are not acceptable. a. Copper and Fiber Optic Cables: 1) Brady: Bradymaker Wire Marking Labels WML-511-292 (or approved equal)
B. Hand-carried label maker: 1. Brady: ID Pro Plus (or approved equal).

PART 3 - EXECUTION Ensure that products incorporated into the project under PART 3 paragraphs have corresponding Product information in PART 2 ­ Products, or in another specification Section if installed but not supplied under this Section.
The following paragraphs include installation requirements written specifically for the Products listed in Part 2 above. If other products are approved, the Designer shall ensure that appropriate Part 3 installation requirements are added/removed or modified as applicable and described in equal or greater detail to the following paragraphs.
All installation requirements shall be consistent with the manufacturer's requirements.

3.1

PATCH PANELS

Review and edit the following installation requirements based on the products specified in PART 2 ­ Products above or on the products specified in another section if installed but not supplied under this section, and as applicable to this project.

A. Provide patch panels and horizontal wire management according to locations, elevations, and plan views as shown on the Contract Documents. 1. Copper: Size and install rack-mountable patch panels as shown on the Contract Documents. Use patch panels to terminate copper horizontal cables. Do not exceed ten 2U-sized patch panels per rack.

Project No. #

Page 5

Washington State University (Pullman) Telecommunications Construction Guide Specification

Communications Horizontal Cabling Section 27 15 00

