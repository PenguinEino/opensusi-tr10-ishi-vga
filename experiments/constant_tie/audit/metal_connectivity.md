# Metal connectivity audit

GDS `experiments/constant_tie/build/constant_tied.gds`; 421 actual placed instances matched, 987 signal pins labeled from v59_4 LEF and GDS transforms.

Actual short components: **14**; transitive within-component net pairs: **153**; directly overlapping routed net pairs: **24**. Source map points: {'on_same_pin_component_route_anchor': 1017}. Unlocated route-map shapes: 1.

## Shorted components

### 1. Nets _048_, _082_, h[0]
BBox [260.2, 124.5, 1484.0, 1394.7] µm; mapped crossing candidates 1; pins 13.
- M2 overlap [773.2, 287.5, 776.6, 287.5] µm; nets ['_048_', 'h[0]']; shape indices [3, 7]; candidate local M2 [772.2, 284.8, 777.6, 290.2] µm; nearby pins []
- Candidate local M2 edit window: [257.5, 121.8, 1486.7, 1397.4] µm (diagnostic bbox expansion, not a repair recommendation).

### 2. Nets _051_, _143_, v[9]
BBox [44.2, 124.5, 1754.0, 1390.2] µm; mapped crossing candidates 0; pins 14.
- No cross-net map rectangle overlap found inside this component; inspect cell/via geometry and near-pin connectivity in JSON.
- Candidate local M2 edit window: [41.5, 121.8, 1756.7, 1392.9] µm (diagnostic bbox expansion, not a repair recommendation).

### 3. Nets _068_, _179_, h[1]
BBox [44.2, 103.4, 1705.4, 1512.9] µm; mapped crossing candidates 2; pins 16.
- M2 overlap [362.8, 537.6, 366.2, 565.6] µm; nets ['h[1]', '_068_']; shape indices [3, 5]; candidate local M2 [361.8, 548.9, 367.2, 554.3] µm; nearby pins []
- M2 overlap [362.8, 565.6, 366.2, 681.0] µm; nets ['h[1]', '_068_']; shape indices [4, 5]; candidate local M2 [361.8, 620.6, 367.2, 626.0] µm; nearby pins []
- Candidate local M2 edit window: [41.5, 100.7, 1708.1, 1515.6] µm (diagnostic bbox expansion, not a repair recommendation).

### 4. Nets _244_, h[3], h[5]
BBox [37.9, 121.5, 1710.8, 1015.6] µm; mapped crossing candidates 0; pins 14.
- No cross-net map rectangle overlap found inside this component; inspect cell/via geometry and near-pin connectivity in JSON.
- Candidate local M2 edit window: [35.2, 118.8, 1713.5, 1018.3] µm (diagnostic bbox expansion, not a repair recommendation).

### 5. Nets _027_, _033_, _038_, _079_, _162_, _194_, _211_, _213_, _227_, _246_, hsync
BBox [82.0, 70.5, 1721.6, 1749.8] µm; mapped crossing candidates 11; pins 49.
- M2 overlap [1064.8, 995.9, 1068.2, 1023.9] µm; nets ['_227_', '_213_']; shape indices [17, 26]; candidate local M2 [1063.8, 1007.2, 1069.2, 1012.6] µm; nearby pins []
- M2 overlap [1064.8, 1023.9, 1068.2, 1042.1] µm; nets ['_227_', '_213_']; shape indices [18, 26]; candidate local M2 [1063.8, 1030.3, 1069.2, 1035.7] µm; nearby pins []
- M2 overlap [1237.6, 454.9, 1241.0, 506.2] µm; nets ['_162_', '_038_']; shape indices [2, 5]; candidate local M2 [1236.6, 477.85, 1242.0, 483.25] µm; nearby pins []
- M2 overlap [1237.6, 506.2, 1241.0, 534.2] µm; nets ['_162_', '_038_']; shape indices [3, 5]; candidate local M2 [1236.6, 517.5, 1242.0, 522.9] µm; nearby pins []
- M1 overlap [1061.1, 707.1, 1071.9, 708.9] µm; nets ['_079_', '_246_']; shape indices [1, 9]; candidate local M2 [1063.8, 705.3, 1069.2, 710.7] µm; nearby pins []
- M2 overlap [1102.6, 1258.1, 1106.0, 1341.8] µm; nets ['_194_', '_038_']; shape indices [29, 10]; candidate local M2 [1101.6, 1297.25, 1107.0, 1302.65] µm; nearby pins []
- M2 overlap [1102.6, 1341.8, 1106.0, 1369.8] µm; nets ['_194_', '_038_']; shape indices [30, 10]; candidate local M2 [1101.6, 1353.1, 1107.0, 1358.5] µm; nearby pins []
- M2 overlap [1556.2, 565.6, 1559.6, 956.4] µm; nets ['_038_', '_033_']; shape indices [16, 0]; candidate local M2 [1555.2, 758.3, 1560.6, 763.7] µm; nearby pins []
- M2 overlap [1556.2, 537.6, 1559.6, 565.6] µm; nets ['_038_', '_033_']; shape indices [17, 0]; candidate local M2 [1555.2, 548.9, 1560.6, 554.3] µm; nearby pins []
- M2 overlap [1556.2, 565.6, 1559.6, 945.6] µm; nets ['_038_', '_033_']; shape indices [25, 0]; candidate local M2 [1555.2, 752.9, 1560.6, 758.3] µm; nearby pins []
- M2 overlap [1556.2, 537.6, 1559.6, 565.6] µm; nets ['_038_', '_033_']; shape indices [26, 0]; candidate local M2 [1555.2, 548.9, 1560.6, 554.3] µm; nearby pins []
- Candidate local M2 edit window: [79.3, 67.8, 1724.3, 1752.5] µm (diagnostic bbox expansion, not a repair recommendation).

### 6. Nets _059_, _083_, _103_, _209_
BBox [627.4, 48.9, 1619.0, 1378.3] µm; mapped crossing candidates 10; pins 22.
- M2 overlap [1145.8, 565.6, 1149.2, 794.4] µm; nets ['_059_', '_083_']; shape indices [12, 6]; candidate local M2 [1144.8, 677.3, 1150.2, 682.7] µm; nearby pins []
- M2 overlap [1145.8, 537.6, 1149.2, 565.6] µm; nets ['_059_', '_083_']; shape indices [13, 6]; candidate local M2 [1144.8, 548.9, 1150.2, 554.3] µm; nearby pins []
- M2 overlap [1124.2, 506.2, 1127.6, 534.2] µm; nets ['_103_', '_209_']; shape indices [4, 2]; candidate local M2 [1123.2, 517.5, 1128.6, 522.9] µm; nearby pins []
- M2 overlap [1124.2, 487.3, 1127.6, 506.2] µm; nets ['_103_', '_209_']; shape indices [5, 2]; candidate local M2 [1123.2, 494.05, 1128.6, 499.45] µm; nearby pins []
- M2 overlap [946.0, 964.5, 949.4, 992.5] µm; nets ['_209_', '_083_']; shape indices [16, 10]; candidate local M2 [945.0, 975.8, 950.4, 981.2] µm; nearby pins []
- M2 overlap [946.0, 924.0, 949.4, 964.5] µm; nets ['_209_', '_083_']; shape indices [17, 10]; candidate local M2 [945.0, 941.55, 950.4, 946.95] µm; nearby pins []
- M2 overlap [946.0, 964.5, 949.4, 992.5] µm; nets ['_209_', '_083_']; shape indices [29, 10]; candidate local M2 [945.0, 975.8, 950.4, 981.2] µm; nearby pins []
- M2 overlap [946.0, 907.8, 949.4, 964.5] µm; nets ['_209_', '_083_']; shape indices [30, 10]; candidate local M2 [945.0, 933.45, 950.4, 938.85] µm; nearby pins []
- M2 overlap [946.0, 964.5, 949.4, 992.5] µm; nets ['_209_', '_083_']; shape indices [42, 10]; candidate local M2 [945.0, 975.8, 950.4, 981.2] µm; nearby pins []
- M2 overlap [946.0, 897.0, 949.4, 964.5] µm; nets ['_209_', '_083_']; shape indices [43, 10]; candidate local M2 [945.0, 928.05, 950.4, 933.45] µm; nearby pins []
- Candidate local M2 edit window: [624.7, 46.2, 1621.7, 1381.0] µm (diagnostic bbox expansion, not a repair recommendation).

### 7. Nets _119_, _185_, _247_, h[4]
BBox [167.5, 124.5, 1678.4, 1394.7] µm; mapped crossing candidates 5; pins 14.
- M2 overlap [1108.0, 697.2, 1111.4, 697.2] µm; nets ['_247_', 'h[4]']; shape indices [12, 0]; candidate local M2 [1107.0, 694.5, 1112.4, 699.9] µm; nearby pins []
- M2 overlap [989.2, 1023.9, 992.6, 1241.9] µm; nets ['_185_', 'h[4]']; shape indices [4, 5]; candidate local M2 [988.2, 1130.2, 993.6, 1135.6] µm; nearby pins []
- M2 overlap [989.2, 995.9, 992.6, 1023.9] µm; nets ['_185_', 'h[4]']; shape indices [5, 5]; candidate local M2 [988.2, 1007.2, 993.6, 1012.6] µm; nearby pins []
- M2 overlap [989.2, 1023.9, 992.6, 1241.9] µm; nets ['_185_', 'h[4]']; shape indices [8, 5]; candidate local M2 [988.2, 1130.2, 993.6, 1135.6] µm; nearby pins []
- M2 overlap [989.2, 995.9, 992.6, 1023.9] µm; nets ['_185_', 'h[4]']; shape indices [9, 5]; candidate local M2 [988.2, 1007.2, 993.6, 1012.6] µm; nearby pins []
- Candidate local M2 edit window: [164.8, 121.8, 1681.1, 1397.4] µm (diagnostic bbox expansion, not a repair recommendation).

### 8. Nets _104_, _139_
BBox [739.1, 103.0, 1386.8, 1017.4] µm; mapped crossing candidates 0; pins 5.
- No cross-net map rectangle overlap found inside this component; inspect cell/via geometry and near-pin connectivity in JSON.
- Candidate local M2 edit window: [736.4, 100.3, 1389.5, 1020.1] µm (diagnostic bbox expansion, not a repair recommendation).

### 9. Nets _040_, _058_
BBox [141.4, 124.5, 1570.7, 1394.7] µm; mapped crossing candidates 2; pins 6.
- M2 overlap [973.0, 964.5, 976.4, 992.5] µm; nets ['_058_', '_040_']; shape indices [8, 2]; candidate local M2 [972.0, 975.8, 977.4, 981.2] µm; nearby pins []
- M2 overlap [973.0, 918.6, 976.4, 964.5] µm; nets ['_058_', '_040_']; shape indices [8, 3]; candidate local M2 [972.0, 938.85, 977.4, 944.25] µm; nearby pins []
- Candidate local M2 edit window: [138.7, 121.8, 1573.4, 1397.4] µm (diagnostic bbox expansion, not a repair recommendation).

### 10. Nets _031_, _065_, _069_, _073_, _148_, _161_, _214_, _222_, _223_, _233_, _240_, v[7]
BBox [17.2, 377.6, 1759.4, 1728.2] µm; mapped crossing candidates 27; pins 64.
- M2 overlap [76.6, 891.6, 80.0, 964.5] µm; nets ['_233_', '_222_']; shape indices [2, 8]; candidate local M2 [75.6, 925.35, 81.0, 930.75] µm; nearby pins []
- M2 overlap [76.6, 964.5, 80.0, 992.5] µm; nets ['_233_', '_222_']; shape indices [3, 8]; candidate local M2 [75.6, 975.8, 81.0, 981.2] µm; nearby pins []
- M2 overlap [119.8, 995.9, 123.2, 1023.9] µm; nets ['_148_', '_031_']; shape indices [2, 0]; candidate local M2 [118.8, 1007.2, 124.2, 1012.6] µm; nearby pins []
- M2 overlap [119.8, 1023.9, 123.2, 1025.9] µm; nets ['_148_', '_031_']; shape indices [3, 0]; candidate local M2 [118.8, 1022.2, 124.2, 1027.6] µm; nearby pins []
- M2 overlap [157.6, 1312.1, 161.0, 1341.8] µm; nets ['_148_', '_069_']; shape indices [5, 15]; candidate local M2 [156.6, 1324.25, 162.0, 1329.65] µm; nearby pins []
- M2 overlap [157.6, 1341.8, 161.0, 1369.8] µm; nets ['_148_', '_069_']; shape indices [6, 15]; candidate local M2 [156.6, 1353.1, 162.0, 1358.5] µm; nearby pins []
- M2 overlap [238.6, 670.2, 242.0, 670.2] µm; nets ['_222_', '_223_']; shape indices [6, 0]; candidate local M2 [237.6, 667.5, 243.0, 672.9] µm; nearby pins []
- M2 overlap [179.2, 995.9, 182.6, 1023.9] µm; nets ['_073_', '_240_']; shape indices [3, 24]; candidate local M2 [178.2, 1007.2, 183.6, 1012.6] µm; nearby pins []
- M2 overlap [179.2, 1023.9, 182.6, 1025.9] µm; nets ['_073_', '_240_']; shape indices [4, 24]; candidate local M2 [178.2, 1022.2, 183.6, 1027.6] µm; nearby pins []
- M2 overlap [265.6, 565.6, 269.0, 826.8] µm; nets ['_069_', '_240_']; shape indices [3, 0]; candidate local M2 [264.6, 693.5, 270.0, 698.9] µm; nearby pins []
- M2 overlap [265.6, 537.6, 269.0, 565.6] µm; nets ['_069_', '_240_']; shape indices [4, 0]; candidate local M2 [264.6, 548.9, 270.0, 554.3] µm; nearby pins []
- M2 overlap [265.6, 1023.9, 269.0, 1252.7] µm; nets ['_069_', '_161_']; shape indices [8, 0]; candidate local M2 [264.6, 1135.6, 270.0, 1141.0] µm; nearby pins []
- Candidate local M2 edit window: [14.5, 374.9, 1762.1, 1730.9] µm (diagnostic bbox expansion, not a repair recommendation).

### 11. Nets _108_, _173_
BBox [55.0, 264.2, 873.8, 1394.7] µm; mapped crossing candidates 4; pins 5.
- M2 overlap [238.6, 964.5, 242.0, 992.5] µm; nets ['_173_', '_108_']; shape indices [5, 2]; candidate local M2 [237.6, 975.8, 243.0, 981.2] µm; nearby pins []
- M2 overlap [238.6, 961.8, 242.0, 964.5] µm; nets ['_173_', '_108_']; shape indices [6, 2]; candidate local M2 [237.6, 960.45, 243.0, 965.85] µm; nearby pins []
- M2 overlap [206.2, 565.6, 209.6, 816.0] µm; nets ['_173_', '_108_']; shape indices [8, 0]; candidate local M2 [205.2, 688.1, 210.6, 693.5] µm; nearby pins []
- M2 overlap [206.2, 537.6, 209.6, 565.6] µm; nets ['_173_', '_108_']; shape indices [9, 0]; candidate local M2 [205.2, 548.9, 210.6, 554.3] µm; nearby pins []
- Candidate local M2 edit window: [52.3, 261.5, 876.5, 1397.4] µm (diagnostic bbox expansion, not a repair recommendation).

### 12. Nets _034_, _052_
BBox [334.1, 534.2, 1430.0, 1394.7] µm; mapped crossing candidates 0; pins 4.
- No cross-net map rectangle overlap found inside this component; inspect cell/via geometry and near-pin connectivity in JSON.
- Candidate local M2 edit window: [331.4, 531.5, 1432.7, 1397.4] µm (diagnostic bbox expansion, not a repair recommendation).

### 13. Nets _000_[1], _193_
BBox [983.8, 512.7, 1754.0, 1755.2] µm; mapped crossing candidates 2; pins 8.
- M2 overlap [1723.6, 864.6, 1727.0, 964.5] µm; nets ['_193_', '_000_[1]']; shape indices [2, 4]; candidate local M2 [1722.6, 911.85, 1728.0, 917.25] µm; nearby pins []
- M2 overlap [1723.6, 964.5, 1727.0, 992.5] µm; nets ['_193_', '_000_[1]']; shape indices [3, 4]; candidate local M2 [1722.6, 975.8, 1728.0, 981.2] µm; nearby pins []
- Candidate local M2 edit window: [981.1, 510.0, 1756.7, 1757.9] µm (diagnostic bbox expansion, not a repair recommendation).

### 14. Nets _270_, v[0], v[2]
BBox [654.4, 522.8, 1656.8, 1733.6] µm; mapped crossing candidates 4; pins 13.
- M2 overlap [1642.6, 600.0, 1646.0, 964.5] µm; nets ['_270_', 'v[2]']; shape indices [0, 0]; candidate local M2 [1641.6, 779.55, 1647.0, 784.95] µm; nearby pins []
- M2 overlap [1642.6, 964.5, 1646.0, 992.4] µm; nets ['_270_', 'v[2]']; shape indices [0, 1]; candidate local M2 [1641.6, 975.75, 1647.0, 981.15] µm; nearby pins []
- M2 overlap [1642.6, 600.0, 1646.0, 964.5] µm; nets ['_270_', 'v[2]']; shape indices [1, 0]; candidate local M2 [1641.6, 779.55, 1647.0, 784.95] µm; nearby pins []
- M2 overlap [1642.6, 964.5, 1646.0, 992.4] µm; nets ['_270_', 'v[2]']; shape indices [1, 1]; candidate local M2 [1641.6, 975.75, 1647.0, 981.15] µm; nearby pins []
- Candidate local M2 edit window: [651.7, 520.1, 1659.5, 1736.3] µm (diagnostic bbox expansion, not a repair recommendation).

## Pin-map coordinate audit

- _026_ _395_.A: [580.5, 77.60000000000004] µm, nearest actual pin rect gap 46.9 µm, on_same_pin_component_route_anchor
- _026_ _328_.Y: [688.5, 77.60000000000004] µm, nearest actual pin rect gap 46.9 µm, on_same_pin_component_route_anchor
- _026_ _391_.A: [796.5, 77.60000000000004] µm, nearest actual pin rect gap 46.9 µm, on_same_pin_component_route_anchor
- _026_ _443_.A: [720.9000000000001, 341.49999999999926] µm, nearest actual pin rect gap 192.7 µm, on_same_pin_component_route_anchor
- _026_ _356_.A: [629.0999999999999, 740.4000000000038] µm, nearest actual pin rect gap 252.1 µm, on_same_pin_component_route_anchor
- _026_ _364_.A: [650.7, 740.4000000000038] µm, nearest actual pin rect gap 252.1 µm, on_same_pin_component_route_anchor
- _026_ _407_.A: [715.5, 740.4000000000038] µm, nearest actual pin rect gap 252.1 µm, on_same_pin_component_route_anchor
- _026_ _357_.A: [737.0999999999999, 740.4000000000038] µm, nearest actual pin rect gap 252.1 µm, on_same_pin_component_route_anchor
- _026_ _329_.A: [796.5, 740.4000000000038] µm, nearest actual pin rect gap 252.1 µm, on_same_pin_component_route_anchor
- _026_ _414_.A: [656.0999999999999, 1171.699999999991] µm, nearest actual pin rect gap 198.1 µm, on_same_pin_component_route_anchor
- _026_ _477_.A: [758.7, 1543.5999999999701] µm, nearest actual pin rect gap 95.5 µm, on_same_pin_component_route_anchor
- _032_ _381_.A: [180.89999999999998, 363.09999999999917] µm, nearest actual pin rect gap 171.1 µm, on_same_pin_component_route_anchor
- _032_ _449_.C: [272.7, 363.09999999999917] µm, nearest actual pin rect gap 171.1 µm, on_same_pin_component_route_anchor
- _032_ _373_.A: [542.7, 363.09999999999917] µm, nearest actual pin rect gap 171.1 µm, on_same_pin_component_route_anchor
- _032_ _387_.C: [612.9000000000001, 363.09999999999917] µm, nearest actual pin rect gap 171.1 µm, on_same_pin_component_route_anchor
- _032_ _463_.C: [186.3, 762.0000000000043] µm, nearest actual pin rect gap 230.5 µm, on_same_pin_component_route_anchor
- _032_ _440_.A: [202.5, 762.0000000000043] µm, nearest actual pin rect gap 230.5 µm, on_same_pin_component_route_anchor
- _032_ _385_.A: [256.5, 1193.2999999999895] µm, nearest actual pin rect gap 176.5 µm, on_same_pin_component_route_anchor
- _032_ _413_.B: [299.7, 1193.2999999999895] µm, nearest actual pin rect gap 176.5 µm, on_same_pin_component_route_anchor
- _032_ _336_.Y: [326.7, 1193.2999999999895] µm, nearest actual pin rect gap 176.5 µm, on_same_pin_component_route_anchor
- _032_ _337_.C: [537.3, 1193.2999999999895] µm, nearest actual pin rect gap 176.5 µm, on_same_pin_component_route_anchor
- _205_ _323_.A: [218.7, 66.80000000000003] µm, nearest actual pin rect gap 57.7 µm, on_same_pin_component_route_anchor
- _205_ _401_.B: [256.5, 66.80000000000003] µm, nearest actual pin rect gap 57.7 µm, on_same_pin_component_route_anchor
- _205_ _420_.A: [310.5, 66.80000000000003] µm, nearest actual pin rect gap 57.7 µm, on_same_pin_component_route_anchor
- _205_ _273_.Y: [337.5, 66.80000000000003] µm, nearest actual pin rect gap 57.7 µm, on_same_pin_component_route_anchor
- _205_ _443_.B: [726.3, 330.6999999999993] µm, nearest actual pin rect gap 203.5 µm, on_same_pin_component_route_anchor
- _205_ _426_.B: [845.0999999999999, 330.6999999999993] µm, nearest actual pin rect gap 203.5 µm, on_same_pin_component_route_anchor
- _205_ _355_.B: [305.1, 729.6000000000038] µm, nearest actual pin rect gap 262.9 µm, on_same_pin_component_route_anchor
- _205_ _274_.B: [353.7, 729.6000000000038] µm, nearest actual pin rect gap 262.9 µm, on_same_pin_component_route_anchor
- _205_ _356_.B: [634.5, 729.6000000000038] µm, nearest actual pin rect gap 262.9 µm, on_same_pin_component_route_anchor
- _205_ _364_.B: [656.0999999999999, 729.6000000000038] µm, nearest actual pin rect gap 262.9 µm, on_same_pin_component_route_anchor
- _205_ _329_.B: [801.9000000000001, 729.6000000000038] µm, nearest actual pin rect gap 262.9 µm, on_same_pin_component_route_anchor
- _211_ _476_.A: [548.0999999999999, 72.20000000000002] µm, nearest actual pin rect gap 52.3 µm, on_same_pin_component_route_anchor
- _211_ _395_.B: [585.9000000000001, 72.20000000000002] µm, nearest actual pin rect gap 52.3 µm, on_same_pin_component_route_anchor
- _211_ _426_.C: [850.5, 336.0999999999993] µm, nearest actual pin rect gap 198.1 µm, on_same_pin_component_route_anchor
- _211_ _389_.A: [936.9000000000001, 735.0000000000039] µm, nearest actual pin rect gap 257.5 µm, on_same_pin_component_route_anchor
- _211_ _279_.Y: [1001.7, 735.0000000000039] µm, nearest actual pin rect gap 257.5 µm, on_same_pin_component_route_anchor
- _211_ _327_.B: [1012.5, 735.0000000000039] µm, nearest actual pin rect gap 257.5 µm, on_same_pin_component_route_anchor
- _211_ _280_.B: [1028.7, 735.0000000000039] µm, nearest actual pin rect gap 257.5 µm, on_same_pin_component_route_anchor
- _211_ _510_.A: [1071.9, 735.0000000000039] µm, nearest actual pin rect gap 257.5 µm, on_same_pin_component_route_anchor
- _211_ _353_.B: [758.7, 1166.2999999999913] µm, nearest actual pin rect gap 203.5 µm, on_same_pin_component_route_anchor
- _211_ _509_.A: [1034.1, 1166.2999999999913] µm, nearest actual pin rect gap 203.4 µm, on_same_pin_component_route_anchor
- _214_ _438_.A: [29.7, 1214.899999999988] µm, nearest actual pin rect gap 154.9 µm, on_same_pin_component_route_anchor
- _214_ _297_.A: [45.900000000000006, 1214.899999999988] µm, nearest actual pin rect gap 154.9 µm, on_same_pin_component_route_anchor
- _214_ _450_.A: [62.099999999999994, 1214.899999999988] µm, nearest actual pin rect gap 154.9 µm, on_same_pin_component_route_anchor
- _214_ _282_.Y: [116.1, 1214.899999999988] µm, nearest actual pin rect gap 154.9 µm, on_same_pin_component_route_anchor
- _214_ _335_.A: [29.7, 1581.3999999999673] µm, nearest actual pin rect gap 57.7 µm, on_same_pin_component_route_anchor
- _214_ _466_.A: [45.900000000000006, 1581.3999999999673] µm, nearest actual pin rect gap 57.7 µm, on_same_pin_component_route_anchor
- _214_ _305_.A: [62.099999999999994, 1581.3999999999673] µm, nearest actual pin rect gap 57.7 µm, on_same_pin_component_route_anchor
- _214_ _283_.A: [99.9, 1581.3999999999673] µm, nearest actual pin rect gap 57.7 µm, on_same_pin_component_route_anchor
- _214_ _334_.A: [110.7, 1581.3999999999673] µm, nearest actual pin rect gap 57.7 µm, on_same_pin_component_route_anchor
- _214_ _370_.B: [148.5, 1581.3999999999673] µm, nearest actual pin rect gap 57.7 µm, on_same_pin_component_route_anchor
- _214_ _333_.A: [164.7, 1581.3999999999673] µm, nearest actual pin rect gap 57.7 µm, on_same_pin_component_route_anchor
- _216_ _316_.A: [35.099999999999994, 778.2000000000045] µm, nearest actual pin rect gap 214.2 µm, on_same_pin_component_route_anchor
- _216_ _297_.B: [51.3, 1209.4999999999884] µm, nearest actual pin rect gap 160.3 µm, on_same_pin_component_route_anchor
- _216_ _450_.B: [67.5, 1209.4999999999884] µm, nearest actual pin rect gap 160.3 µm, on_same_pin_component_route_anchor
- _216_ _437_.A: [83.7, 1209.4999999999884] µm, nearest actual pin rect gap 160.3 µm, on_same_pin_component_route_anchor
- _216_ _284_.Y: [234.89999999999998, 1209.4999999999884] µm, nearest actual pin rect gap 160.3 µm, on_same_pin_component_route_anchor
- _216_ _305_.B: [67.5, 1575.999999999968] µm, nearest actual pin rect gap 63.1 µm, on_same_pin_component_route_anchor
- _216_ _313_.A: [83.7, 1575.999999999968] µm, nearest actual pin rect gap 63.1 µm, on_same_pin_component_route_anchor
- _216_ _285_.A: [132.3, 1575.999999999968] µm, nearest actual pin rect gap 63.1 µm, on_same_pin_component_route_anchor
- _216_ _454_.A: [272.7, 1575.999999999968] µm, nearest actual pin rect gap 63.1 µm, on_same_pin_component_route_anchor
- _216_ _331_.B: [575.0999999999999, 1575.999999999968] µm, nearest actual pin rect gap 63.1 µm, on_same_pin_component_route_anchor
- _220_ _288_.Y: [116.1, 61.40000000000002] µm, nearest actual pin rect gap 63.1 µm, on_same_pin_component_route_anchor
- _220_ _481_.A: [67.5, 325.29999999999933] µm, nearest actual pin rect gap 208.9 µm, on_same_pin_component_route_anchor
- _220_ _289_.A: [83.7, 325.29999999999933] µm, nearest actual pin rect gap 208.9 µm, on_same_pin_component_route_anchor
- _220_ _484_.A: [94.5, 325.29999999999933] µm, nearest actual pin rect gap 208.9 µm, on_same_pin_component_route_anchor
- _220_ _374_.A: [116.1, 325.29999999999933] µm, nearest actual pin rect gap 208.9 µm, on_same_pin_component_route_anchor
- _220_ _464_.A: [283.5, 325.29999999999933] µm, nearest actual pin rect gap 208.9 µm, on_same_pin_component_route_anchor
- _220_ _495_.A: [305.1, 325.29999999999933] µm, nearest actual pin rect gap 208.9 µm, on_same_pin_component_route_anchor
- _220_ _524_.A: [56.7, 724.2000000000036] µm, nearest actual pin rect gap 268.3 µm, on_same_pin_component_route_anchor
- _220_ _452_.A: [278.1, 1160.8999999999917] µm, nearest actual pin rect gap 208.9 µm, on_same_pin_component_route_anchor
- _220_ _336_.A: [315.9, 1160.8999999999917] µm, nearest actual pin rect gap 208.9 µm, on_same_pin_component_route_anchor
- _220_ _332_.A: [645.3, 1538.1999999999705] µm, nearest actual pin rect gap 100.9 µm, on_same_pin_component_route_anchor
- _224_ _449_.A: [261.9, 368.49999999999915] µm, nearest actual pin rect gap 165.7 µm, on_same_pin_component_route_anchor
- _224_ _464_.B: [288.9, 368.49999999999915] µm, nearest actual pin rect gap 165.7 µm, on_same_pin_component_route_anchor
- _224_ _491_.B: [337.5, 368.49999999999915] µm, nearest actual pin rect gap 165.7 µm, on_same_pin_component_route_anchor
- _224_ _463_.A: [175.5, 767.4000000000043] µm, nearest actual pin rect gap 225.1 µm, on_same_pin_component_route_anchor
- _224_ _452_.B: [283.5, 1198.6999999999891] µm, nearest actual pin rect gap 171.1 µm, on_same_pin_component_route_anchor
- _224_ _292_.Y: [618.3, 1198.6999999999891] µm, nearest actual pin rect gap 171.1 µm, on_same_pin_component_route_anchor
- _224_ _293_.A: [683.0999999999999, 1198.6999999999891] µm, nearest actual pin rect gap 171.1 µm, on_same_pin_component_route_anchor
- _224_ _296_.A: [342.9, 1565.1999999999687] µm, nearest actual pin rect gap 73.9 µm, on_same_pin_component_route_anchor
- _224_ _307_.A: [591.3, 1565.1999999999687] µm, nearest actual pin rect gap 73.9 µm, on_same_pin_component_route_anchor
- _224_ _308_.A: [612.9000000000001, 1565.1999999999687] µm, nearest actual pin rect gap 73.9 µm, on_same_pin_component_route_anchor
- _224_ _332_.B: [650.7, 1565.1999999999687] µm, nearest actual pin rect gap 73.9 µm, on_same_pin_component_route_anchor
- _256_ _552_.SET: [1136.7, 88.40000000000005] µm, nearest actual pin rect gap 36.0 µm, on_same_pin_component_route_anchor
- _256_ _536_.SET: [1449.9, 88.40000000000005] µm, nearest actual pin rect gap 36.0 µm, on_same_pin_component_route_anchor
- _256_ _546_.SET: [1638.9, 352.2999999999992] µm, nearest actual pin rect gap 181.8 µm, on_same_pin_component_route_anchor
- _256_ _537_.SET: [1703.7, 352.2999999999992] µm, nearest actual pin rect gap 181.8 µm, on_same_pin_component_route_anchor
- _256_ _533_.SET: [1520.1, 751.200000000004] µm, nearest actual pin rect gap 241.2 µm, on_same_pin_component_route_anchor
- _256_ _540_.SET: [1649.7, 751.200000000004] µm, nearest actual pin rect gap 241.2 µm, on_same_pin_component_route_anchor
- _256_ _532_.SET: [1714.5, 751.200000000004] µm, nearest actual pin rect gap 241.2 µm, on_same_pin_component_route_anchor
- _256_ _535_.SET: [1412.1, 1182.4999999999902] µm, nearest actual pin rect gap 187.2 µm, on_same_pin_component_route_anchor
- _256_ _534_.SET: [1476.9, 1182.4999999999902] µm, nearest actual pin rect gap 187.2 µm, on_same_pin_component_route_anchor
- _256_ _548_.SET: [1541.7, 1182.4999999999902] µm, nearest actual pin rect gap 187.2 µm, on_same_pin_component_route_anchor
- _256_ _549_.SET: [1606.5, 1182.4999999999902] µm, nearest actual pin rect gap 187.2 µm, on_same_pin_component_route_anchor
- _256_ _550_.SET: [1088.1, 1554.3999999999692] µm, nearest actual pin rect gap 84.6 µm, on_same_pin_component_route_anchor
- _256_ _551_.SET: [1152.9, 1554.3999999999692] µm, nearest actual pin rect gap 84.6 µm, on_same_pin_component_route_anchor
- _256_ _543_.QB: [1730.7, 1554.3999999999692] µm, nearest actual pin rect gap 84.6 µm, on_same_pin_component_route_anchor
- _256_ _543_.QB: [1730.7, 1554.3999999999692] µm, nearest actual pin rect gap 84.6 µm, on_same_pin_component_route_anchor
