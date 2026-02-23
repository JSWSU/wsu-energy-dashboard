# 25-appendix-3-bas-point-naming

> **Title:** 25-appendix-3-bas-point-naming
> **Source:** WSU Facilities Services Design & Construction Standards (June 2025)
> **Category:** supplemental

---


DIVISION 25 ­ INTEGRATED AUTOMATION 25 50 00 INTEGRATED AUTOMATION FACTILITY CONTROLS BAS POINT NAMING SCHEME
PART 8 - POINT NAMING - CONTINUED
8.01 BAS POINT NAMING BREAKDOWN
A. ALL WSU FS BAS point names will conform to the following point naming scheme.
1. [CAMPUS][FACILITY#][NON-PRIMARY FACILITY INDICATOR][FLOOR][ZONE/SYSTEM][ORDER][DESCRIPTOR]
B. Point names will not exceed 30 characters except in special conditions.
1. WSU accepts that vendors may have an architecture that does not allow them to adhere to this rule. As such any special condition or deviation from this must be approved by WSU FS Control Shop and the project manager.
i. See point J for special conditions.
C. Example point name:
1. 0860__01N.AHU1A EM DMPR CMD Under the Siemens format or 0860__01N.AHU1AAA EM DMPR CMD Under the Alerton format.
A. 0 = [CAMPUS]
B. 860= [FACILITY#]
C. _ = [NON-PRIMARY FACILITY INDICATOR] Could be 0860A at this point in the structure.
D. _= [FLOOR] _ Indicates common mechanical equipment common to any floor. A -Would indicate the bottom floor and B- would be the next floor up. Alpha characters usually indicate zone controllers on the floors.
E. 01= [ZONE/SYSTEM] Indicates the first system on a floor or the first system of common equipment like AHU 1.
F. A= [ORDER] The Siemens version of this character is 1 digit.
G. AAA= [ORDER] The Alerton version of this character is 3 digits. This item would take the place of Item F when the Alerton system is used.
H. [DESCRIPTOR] is the name segment that users use to describe with a point or point alarm is. It is derived from Appendix 2 - BAS ACRONYM LIST and the ACRONYM LIST will be provided to users, dispatch operators and others for verification of the point meaning.

Page1

OCTOBER 23, 2019 WASHINGTON STATE UNIVERSITY

INTEGRATED AUTOMATION 25 50 00

DIVISION 25 ­ INTEGRATED AUTOMATION 25 50 00 INTEGRATED AUTOMATION FACTILITY CONTROLS BAS POINT NAMING SCHEME
I. [12 CHARACTER DESCRIPTOR] is used only on the Siemens system and is a different field. It is used as a shorter version of the descriptor and can enhance it. Because BACnet is limited in reference to the selection units, the 12 character descriptor can also be used to enhance the value of units types.
D. Point name breakdown more defined:
1. The first character is reserved for CAMPUS identifiers and will be omitted if the job is on the Pullman campus.
2. The next four characters are reserved for the FACILITY number designated by WSU FS - FIRM.
E. An alpha character will follow the facility number if the building is a NON-PRIMARY building of a complex and will be replaced with an underscore character (ASCII code 95) if the building is not a NON-PRIMARY building.
i. Example: for Desigo.systems
1) 0807A_01A SF1A FAN CMD- Facility number that is a non-primary building of a complex.
2) 0807__01A SF1 FAN CMD- Facility number that is a primary building of a complex.
ii. Example: for Alerton systems
1) 0807A_01AAA SF1A FAN CMD- Facility number that is a non-primary building of a complex.
2) 0807__01AAA SF1 FAN CMD- Facility number that is a primary building of a complex.
F. A FLOOR indicator will follow as a single alpha character and will be replaced with an underscore character (ASCII code 95) if this is not applicable.
i. Example: for Desigo.systems
1) 0025_D03A.CTL STPT
ii. Example: for Alerton systems
1) 0025_D03AAA.CTL STPT

Page2

OCTOBER 23, 2019 WASHINGTON STATE UNIVERSITY

INTEGRATED AUTOMATION 25 50 00

DIVISION 25 ­ INTEGRATED AUTOMATION 25 50 00 INTEGRATED AUTOMATION FACTILITY CONTROLS BAS POINT NAMING SCHEME
G. The ZONE/SYSTEM Group indicator follows as a two digit numeric value ranging from 01 - 99.
1. Items associated with this group or zone will all be associated by this number.
i. Example: for Desigo SSystems 1) 0095_G02A S1 RM 412 FT (004) ROOM TEMP 2) 0095_G02A S1 RM 412 FT (004) HEAT_COOL 3) 0095_G02A S1 RM 412 FT (004) DAY CLG STPT 4) 0095_G02A S1 RM 412 FT (004) DAY HTG STPT 5) 0095_G02A S1 RM 412 FT (004) NGT CLG STPT 6) 0095_G02A S1 RM 412 FT (004) NGT HTG STPT Note: These are actually subpoints.
ii. Example: for Alerton Systems 1) 0025_D03AAA.CTL STPT 2) 0025_D03AAB.DAY CLG STPT 3) 0025_D03AAC.DAY HTG STPT
H. Immediately following the Zone/System Group indicator is the Point ORDER identifier.
1. This section dictates the order the points are displayed in a Point Log Report.
2. This is to be a single, base 26 alpha character.
i. Characters "I" (ASCII code 73 or 105) and "O" (ASCII code 79 or 111) being omitted in order to eliminate confusion between similarly appearing characters.
ii. Example: for Siemens systems 1) 0860__07A.EF1A VFD OT
iii. Example:for Alerton systems 1) 0860__07AAA.EF1A VFD OT

Page3

OCTOBER 23, 2019 WASHINGTON STATE UNIVERSITY

INTEGRATED AUTOMATION 25 50 00

DIVISION 25 ­ INTEGRATED AUTOMATION 25 50 00 INTEGRATED AUTOMATION FACTILITY CONTROLS BAS POINT NAMING SCHEME
3. Example of fan controls and alarms in order as groups as an example using a Siemens system.
1) 0860__01A.AHU1A SF1 CMD (The command, proof and alarm are bundled under 1 point in this system.
2) 0860__01B.AHU1A SF1 MAT 3) 0860__01C.AHU1A SF1 MXAIR SPT 4) 0860__01D.AHU1A SF1 MXAIR OUT 5) 0860__01E.AHU1A SF1 PHT TP 6) 0860__01F.AHU1A SF1 PHT SPT 7) 0860__01G.AHU1A SF1 PHT OUT 8) (And on for this HVAC system.)
9) 0860__02A.AHU1A SF2 CMD (The command, proof and alarm are bundled under 1 point in this system.
10)0860__02B.AHU1A SF2 MAT 11)0860__02C.AHU1A SF2 MXAIR SPT 12)0860__02D.AHU1A SF2 MXAIR OUT 13)0860__02E.AHU1A SF2 PHT TP 14)0860__02F.AHU1A SF2 PHT SPT 15)0860__02G.AHU1A SF2 PHT OUT 16) (And on for this HVAC system.)

Page4

OCTOBER 23, 2019 WASHINGTON STATE UNIVERSITY

INTEGRATED AUTOMATION 25 50 00

DIVISION 25 ­ INTEGRATED AUTOMATION 25 50 00 INTEGRATED AUTOMATION FACTILITY CONTROLS BAS POINT NAMING SCHEME
4. Example of fan controls and alarms in order as groups as an example using an Alerton System.
1) 0860__01AAA.AHU1A SF1 CMD 2) 0860__01AAB.AHU1A SF1 PRF 3) 0860__01AAC.AHU1A SF1 ALM 4) 0860__01AAD.AHU1A SF1 MAT 5) 0860__01AAE.AHU1A SF1 MXAIR SPT 6) 0860__01AAF.AHU1A SF1 MXAIR OUT 7) 0860__01AAG.AHU1A SF1 PHT TP 8) 0860__01AAH.AHU1A SF1 PHT SPT 9) 0860__01AAJ.AHU1A SF1 PHT OUT 10) (And on for this HVAC system.)
11)0860__02AAA.AHU1A SF2 CMD 12)0860__02AAB.AHU1A SF2 PRF 13)0860__02AAC.AHU1A SF2 ALM 14)0860__02AAD.AHU1A SF2 MAT 15)0860__02AAE.AHU1A SF2 MXAIR SPT 16)0860__02AAF.AHU1A SF2 MXAIR OUT 17)0860__02AAG.AHU1A SF2 PHT TP 18)0860__02AAH.AHU1A SF2 PHT SPT 19)0860__02AAJ.AHU1A SF2 PHT OUT 20) (And on for this HVAC system.)
I. For systems requiring variation, such as those with Analog and Binary Values, additional base 26 alpha character designators can be added.
J. WSU FS Control Shop will enforce the 30 character limit. Variations must be approved by WSU FS Control Shop before they will be accepted by WSU FS.
K. The final section of the point name is the 12 CHARACTER POINT DESCRIPTOR. This is a combination of descriptive acronyms from the WSU FS BAS Acronym Legend and Vendor provided information.
1. Example: i. AHU1A SF1CMD

Page5

OCTOBER 23, 2019 WASHINGTON STATE UNIVERSITY

INTEGRATED AUTOMATION 25 50 00

DIVISION 25 ­ INTEGRATED AUTOMATION 25 50 00 INTEGRATED AUTOMATION FACTILITY CONTROLS BAS POINT NAMING SCHEME
L. Vendors may work with WSU FS on legend names on the following conditions:
1. ALL changes to the legend must be approved by WSU Control Shop personnel prior to use.
2. No duplicate entries are added
3. Added acronyms are clearly and distinctly marked on the legend
4. New legend entries will be added individually instead of being combined into one.
i. Example: 1) New entry 1: DMPR 2) New entry 2: STAT
END OF SECTION

Page6

OCTOBER 23, 2019 WASHINGTON STATE UNIVERSITY

INTEGRATED AUTOMATION 25 50 00



