📄 CASE NO. - 00001-A1C-SLA
Date: YYYY-MM-DD HH:MM UTC
Device(s): A1C

🔹 Reported Issue:
  - A1C lost OSPF adjacency with C1C (ABR)

🔹 All Commands Used To Isolate Issue:
  - get_interfaces(A1C)
  - get_ospf(A1C, neighbors)
  - get_ospf(A1C, interfaces)
  - traceroute(A1C, 10.0.0.26)

🔹 Commands That Actually Identified the Issue:
  - get_ospf(A1C, neighbors)
  - get_ospf(A1C, interfaces)

🔹 Proposed Fixes (Per Device):
  - Removing passive-interface on A1C's Ethernet1/3 (toward C1C)

🔹 Commands Used Upon User Approval:
  router ospf 1
   no passive-interface Ethernet1/3

🔹 Post-Fix State:
  - OSPF adjacency restored (FULL)

🔹 Verification: PASSED
🔹 Case Status: FIXED
