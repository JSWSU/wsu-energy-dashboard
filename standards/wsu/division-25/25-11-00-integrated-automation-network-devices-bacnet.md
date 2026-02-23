# CSI 25 11 00 - Integrated Automation Network Devices (BACnet)

> **Division:** 25
> **CSI Code:** 25 11 00
> **Title:** Integrated Automation Network Devices (BACnet)
> **Date:** 2-13-18
> **Source:** WSU Facilities Services Design & Construction Standards (June 2025)

---

DIVISION 25 ­ INTEGRATED AUTOMATION 25 11 00 INTEGRATED AUTOMATION NETWORK DEVICES (BACnet)

PART 1 - GENERAL
1.01 SCOPE
A. This section applies to all devices operating on the WSU Private Network that utilize the Building Automation and Controls network (BACnet) communications protocol. Related sections include Integrated Automation Facility Controls (25 50 00) and Instrumentation and Control for Utilities (33 09 00).
1.02 BACnet INSTANCE NUMBER EXAMPLES AND HIERARCHY
A. Siemens Devices
1. The instance prefix numbering systems and network numbers will be assigned by FAIS and Facilities Services Energy Group.
i. Siemens Controllers route only one MS/TP network per controller. ii. The assignable MAC Addresses range 1-99. Use MAC address assignments
for Device Instance Number suffixes.
2. Examples:
i. BACnet IP: 1) Network Number = 7 2) Device Instance Number = 0700100 (07001 is unique for this object numbering system system) 3) Device Instance Number = 206001 4) Device Instance Number = 423001
ii. BACnet MS/TP: 1) Network Number = 07001 2) Device Instance Number = 0700101 (1st device) 3) Device Instance Number = 0700102 (2nd device) 4) Device Instance Number = 0700199 (99th device)
B. Alerton (ATS) Devices
1. The assignable MAC Addresses range 1-99. Use MAC address assignments for Device Instance Number suffixes.
2. Examples:
i. BACnet IP: 1) Network Number 3 (1088)

FEBRUARY 13, 2018 WASHINGTON STATE UNIVERSITY

INTEGRATED AUTOMATION NETWORK DEVICES 25 11 00

DIVISION 25 ­ INTEGRATED AUTOMATION 25 11 00 INTEGRATED AUTOMATION NETWORK DEVICES (BACnet)

2) Device Instance Number 3013000 (3013 is unique for this object numbering system system)

ii. BACnet MS/TP:

1) Network Number 30131 (30131 is unique for this system)

a) ATS Controllers can route four MS/TP Networks. For example, 30132 would be a second MS/TP Network Number.

2) BACnet MS/TP Device Instance Number examples:

a) 3013101 b) 3013102 c) 3013199 d) 3013201 e) 3013202 f) 3013299 g) 3013301 h) 3013302 i) 3013399 j) 3013401 k) 3013402 l) 3013499

1st device on network 1 2nd device on network 1 99th device on network 1 1st device on network 2. 2nd device on network 2 99th device on network 2 1st device on network 3 2nd device on network 3 99th device on network 3 1st device on network 4 2nd device on network 4 99th device on network 4

C. BACnet IP Meters (Water, Chilled Water Energy, Hot Water Energy and Steam Energy)

1. Examples:

i. BACnet IP Network Number 65000
ii. Onicon Meters: BACnet IP Device Instance Number 206001 (206 is unique for this object numbering system system)
iii. Siemens Meters: BACnet IP Device Instance Number 313001 (313 is unique for this object numbering system system)
iv. Belimo Meters: BACnet IP Device Instance Number 423001 (423 is unique for this object numbering system)

PART 2 - PRODUCTS

PART 3 - EXECUTION

3.01 INSTALLATION, SETUP, AND STARTUP

A. The WSU Construction Manager (Public Works projects) or WSU Shop Supervisor (Shops projects) shall determine a list of meters or controllers to be installed. The list shall include:

FEBRUARY 13, 2018 WASHINGTON STATE UNIVERSITY

INTEGRATED AUTOMATION NETWORK DEVICES 25 11 00

DIVISION 25 ­ INTEGRATED AUTOMATION 25 11 00 INTEGRATED AUTOMATION NETWORK DEVICES (BACnet)
1. Building name and number 2. Meter, device, or controller use/function
i. Meters: Include points that will be measured and recorded (see WSU Standard 33 01 33)
ii. Controllers: Include Digital Inputs and Outputs (see WSU Standard 25 50 00) 3. Device room location 4. Meter totalization units 5. Meter totalization multiplier 6. If demand were used the demand units would be required. 7. Meter Label Name (from Facilities Services Energy Group) B. The Contractor or WSU Shop Supervisor shall provide MAC (Media Access Code) addresses to WSU Finance and Administration Information Services (FAIS) for every Ethernet device to be connected to the WSU Private Network.
C. For BACnet IP: WSU FAIS shall provide the Contractor or WSU Shop Supervisor the following for each device:
1. Network Number 2. IP Address 3. Subnet Mask 4. Default Gateway 5. BACnet Instance Number D. For BACnet MS/TP: WSU FAIS shall provide the Contractor or WSU Shop Supervisor the following for each device:
1. Network Number (Explained below.) 2. Assignable MAC Address Range 1-99 3. BACnet Instance Number Range. 4. PIC Statement (Protocol Implementation Conformance Statement)
END OF SECTION

FEBRUARY 13, 2018 WASHINGTON STATE UNIVERSITY

INTEGRATED AUTOMATION NETWORK DEVICES 25 11 00



