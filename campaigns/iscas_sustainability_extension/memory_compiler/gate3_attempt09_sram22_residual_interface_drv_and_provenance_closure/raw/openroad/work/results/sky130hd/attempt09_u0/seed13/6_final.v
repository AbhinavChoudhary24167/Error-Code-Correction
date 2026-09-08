module u0_sram22_top (ce,
    clk,
    rstb,
    we,
    addr,
    data_in,
    data_out,
    wmask);
 input ce;
 input clk;
 input rstb;
 input we;
 input [7:0] addr;
 input [63:0] data_in;
 output [63:0] data_out;
 input [7:0] wmask;

 wire net1;
 wire net2;
 wire net3;
 wire net4;
 wire net5;
 wire net6;
 wire net7;
 wire net8;
 wire net9;
 wire net10;
 wire net11;
 wire net12;
 wire net13;
 wire net14;
 wire net15;
 wire net16;
 wire net17;
 wire net18;
 wire net19;
 wire net20;
 wire net21;
 wire net22;
 wire net23;
 wire net24;
 wire net25;
 wire net26;
 wire net27;
 wire net28;
 wire net29;
 wire net30;
 wire net31;
 wire net32;
 wire net33;
 wire net34;
 wire net35;
 wire net36;
 wire net37;
 wire net38;
 wire net39;
 wire net40;
 wire net41;
 wire net42;
 wire net43;
 wire net44;
 wire net45;
 wire net46;
 wire net47;
 wire net48;
 wire net49;
 wire net50;
 wire net51;
 wire net52;
 wire net53;
 wire net54;
 wire net55;
 wire net56;
 wire net57;
 wire net58;
 wire net59;
 wire net60;
 wire net61;
 wire net62;
 wire net63;
 wire net64;
 wire net65;
 wire net66;
 wire net67;
 wire net68;
 wire net69;
 wire net70;
 wire net71;
 wire net72;
 wire net73;
 wire net84;
 wire net85;
 wire net86;
 wire net87;
 wire net88;
 wire net89;
 wire net90;
 wire net91;
 wire net92;
 wire net93;
 wire net94;
 wire net95;
 wire net96;
 wire net97;
 wire net98;
 wire net99;
 wire net100;
 wire net101;
 wire net102;
 wire net103;
 wire net104;
 wire net105;
 wire net106;
 wire net107;
 wire net108;
 wire net109;
 wire net110;
 wire net111;
 wire net112;
 wire net113;
 wire net114;
 wire net115;
 wire net116;
 wire net117;
 wire net118;
 wire net119;
 wire net120;
 wire net121;
 wire net122;
 wire net123;
 wire net124;
 wire net125;
 wire net126;
 wire net127;
 wire net128;
 wire net129;
 wire net130;
 wire net131;
 wire net132;
 wire net133;
 wire net134;
 wire net135;
 wire net136;
 wire net137;
 wire net138;
 wire net139;
 wire net140;
 wire net141;
 wire net142;
 wire net143;
 wire net144;
 wire net145;
 wire net146;
 wire net147;
 wire net74;
 wire net75;
 wire net76;
 wire net77;
 wire net78;
 wire net79;
 wire net80;
 wire net81;
 wire net82;
 wire net83;
 wire net148;
 wire net149;
 wire net150;
 wire net151;
 wire net152;
 wire net153;
 wire net154;
 wire net155;
 wire net156;

 sky130_fd_sc_hd__dlygate4sd3_1 hold149 (.A(net152),
    .X(net149));
 sky130_fd_sc_hd__dlygate4sd3_1 hold150 (.A(net154),
    .X(net150));
 sky130_fd_sc_hd__buf_16 hold151 (.A(net156),
    .X(net151));
 sky130_fd_sc_hd__dlygate4sd3_1 hold152 (.A(rstb),
    .X(net152));
 sky130_fd_sc_hd__dlygate4sd3_1 hold153 (.A(net149),
    .X(net153));
 sky130_fd_sc_hd__dlygate4sd3_1 hold154 (.A(net74),
    .X(net154));
 sky130_fd_sc_hd__dlygate4sd3_1 hold155 (.A(net150),
    .X(net155));
 sky130_fd_sc_hd__dlygate4sd3_1 hold156 (.A(net148),
    .X(net156));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input1 (.A(addr[0]),
    .X(net1));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input10 (.A(data_in[0]),
    .X(net10));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input11 (.A(data_in[10]),
    .X(net11));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input12 (.A(data_in[11]),
    .X(net12));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input13 (.A(data_in[12]),
    .X(net13));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input14 (.A(data_in[13]),
    .X(net14));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input15 (.A(data_in[14]),
    .X(net15));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input16 (.A(data_in[15]),
    .X(net16));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input17 (.A(data_in[16]),
    .X(net17));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input18 (.A(data_in[17]),
    .X(net18));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input19 (.A(data_in[18]),
    .X(net19));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input2 (.A(addr[1]),
    .X(net2));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input20 (.A(data_in[19]),
    .X(net20));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input21 (.A(data_in[1]),
    .X(net21));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input22 (.A(data_in[20]),
    .X(net22));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input23 (.A(data_in[21]),
    .X(net23));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input24 (.A(data_in[22]),
    .X(net24));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input25 (.A(data_in[23]),
    .X(net25));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input26 (.A(data_in[24]),
    .X(net26));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input27 (.A(data_in[25]),
    .X(net27));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input28 (.A(data_in[26]),
    .X(net28));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input29 (.A(data_in[27]),
    .X(net29));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input3 (.A(addr[2]),
    .X(net3));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input30 (.A(data_in[28]),
    .X(net30));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input31 (.A(data_in[29]),
    .X(net31));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input32 (.A(data_in[2]),
    .X(net32));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input33 (.A(data_in[30]),
    .X(net33));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input34 (.A(data_in[31]),
    .X(net34));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input35 (.A(data_in[32]),
    .X(net35));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input36 (.A(data_in[33]),
    .X(net36));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input37 (.A(data_in[34]),
    .X(net37));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input38 (.A(data_in[35]),
    .X(net38));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input39 (.A(data_in[36]),
    .X(net39));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input4 (.A(addr[3]),
    .X(net4));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input40 (.A(data_in[37]),
    .X(net40));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input41 (.A(data_in[38]),
    .X(net41));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input42 (.A(data_in[39]),
    .X(net42));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input43 (.A(data_in[3]),
    .X(net43));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input44 (.A(data_in[40]),
    .X(net44));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input45 (.A(data_in[41]),
    .X(net45));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input46 (.A(data_in[42]),
    .X(net46));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input47 (.A(data_in[43]),
    .X(net47));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input48 (.A(data_in[44]),
    .X(net48));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input49 (.A(data_in[45]),
    .X(net49));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input5 (.A(addr[4]),
    .X(net5));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input50 (.A(data_in[46]),
    .X(net50));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input51 (.A(data_in[47]),
    .X(net51));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input52 (.A(data_in[48]),
    .X(net52));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input53 (.A(data_in[49]),
    .X(net53));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input54 (.A(data_in[4]),
    .X(net54));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input55 (.A(data_in[50]),
    .X(net55));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input56 (.A(data_in[51]),
    .X(net56));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input57 (.A(data_in[52]),
    .X(net57));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input58 (.A(data_in[53]),
    .X(net58));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input59 (.A(data_in[54]),
    .X(net59));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input6 (.A(addr[5]),
    .X(net6));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input60 (.A(data_in[55]),
    .X(net60));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input61 (.A(data_in[56]),
    .X(net61));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input62 (.A(data_in[57]),
    .X(net62));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input63 (.A(data_in[58]),
    .X(net63));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input64 (.A(data_in[59]),
    .X(net64));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input65 (.A(data_in[5]),
    .X(net65));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input66 (.A(data_in[60]),
    .X(net66));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input67 (.A(data_in[61]),
    .X(net67));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input68 (.A(data_in[62]),
    .X(net68));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input69 (.A(data_in[63]),
    .X(net69));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input7 (.A(addr[6]),
    .X(net7));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input70 (.A(data_in[6]),
    .X(net70));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input71 (.A(data_in[7]),
    .X(net71));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input72 (.A(data_in[8]),
    .X(net72));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input73 (.A(data_in[9]),
    .X(net73));
 sky130_fd_sc_hd__buf_12 input74 (.A(net153),
    .X(net74));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input75 (.A(we),
    .X(net75));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input76 (.A(wmask[0]),
    .X(net76));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input77 (.A(wmask[1]),
    .X(net77));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input78 (.A(wmask[2]),
    .X(net78));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input79 (.A(wmask[3]),
    .X(net79));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input8 (.A(addr[7]),
    .X(net8));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input80 (.A(wmask[4]),
    .X(net80));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input81 (.A(wmask[5]),
    .X(net81));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input82 (.A(wmask[6]),
    .X(net82));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input83 (.A(wmask[7]),
    .X(net83));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input9 (.A(ce),
    .X(net9));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output100 (.A(net100),
    .X(data_out[24]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output101 (.A(net101),
    .X(data_out[25]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output102 (.A(net102),
    .X(data_out[26]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output103 (.A(net103),
    .X(data_out[27]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output104 (.A(net104),
    .X(data_out[28]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output105 (.A(net105),
    .X(data_out[29]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output106 (.A(net106),
    .X(data_out[2]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output107 (.A(net107),
    .X(data_out[30]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output108 (.A(net108),
    .X(data_out[31]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output109 (.A(net109),
    .X(data_out[32]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output110 (.A(net110),
    .X(data_out[33]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output111 (.A(net111),
    .X(data_out[34]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output112 (.A(net112),
    .X(data_out[35]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output113 (.A(net113),
    .X(data_out[36]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output114 (.A(net114),
    .X(data_out[37]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output115 (.A(net115),
    .X(data_out[38]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output116 (.A(net116),
    .X(data_out[39]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output117 (.A(net117),
    .X(data_out[3]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output118 (.A(net118),
    .X(data_out[40]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output119 (.A(net119),
    .X(data_out[41]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output120 (.A(net120),
    .X(data_out[42]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output121 (.A(net121),
    .X(data_out[43]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output122 (.A(net122),
    .X(data_out[44]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output123 (.A(net123),
    .X(data_out[45]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output124 (.A(net124),
    .X(data_out[46]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output125 (.A(net125),
    .X(data_out[47]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output126 (.A(net126),
    .X(data_out[48]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output127 (.A(net127),
    .X(data_out[49]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output128 (.A(net128),
    .X(data_out[4]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output129 (.A(net129),
    .X(data_out[50]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output130 (.A(net130),
    .X(data_out[51]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output131 (.A(net131),
    .X(data_out[52]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output132 (.A(net132),
    .X(data_out[53]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output133 (.A(net133),
    .X(data_out[54]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output134 (.A(net134),
    .X(data_out[55]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output135 (.A(net135),
    .X(data_out[56]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output136 (.A(net136),
    .X(data_out[57]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output137 (.A(net137),
    .X(data_out[58]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output138 (.A(net138),
    .X(data_out[59]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output139 (.A(net139),
    .X(data_out[5]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output140 (.A(net140),
    .X(data_out[60]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output141 (.A(net141),
    .X(data_out[61]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output142 (.A(net142),
    .X(data_out[62]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output143 (.A(net143),
    .X(data_out[63]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output144 (.A(net144),
    .X(data_out[6]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output145 (.A(net145),
    .X(data_out[7]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output146 (.A(net146),
    .X(data_out[8]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output147 (.A(net147),
    .X(data_out[9]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output84 (.A(net84),
    .X(data_out[0]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output85 (.A(net85),
    .X(data_out[10]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output86 (.A(net86),
    .X(data_out[11]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output87 (.A(net87),
    .X(data_out[12]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output88 (.A(net88),
    .X(data_out[13]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output89 (.A(net89),
    .X(data_out[14]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output90 (.A(net90),
    .X(data_out[15]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output91 (.A(net91),
    .X(data_out[16]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output92 (.A(net92),
    .X(data_out[17]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output93 (.A(net93),
    .X(data_out[18]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output94 (.A(net94),
    .X(data_out[19]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output95 (.A(net95),
    .X(data_out[1]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output96 (.A(net96),
    .X(data_out[20]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output97 (.A(net97),
    .X(data_out[21]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output98 (.A(net98),
    .X(data_out[22]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output99 (.A(net99),
    .X(data_out[23]));
 sram22_256x64m4w8 u_data (.we(net75),
    .ce(net9),
    .clk(clk),
    .rstb(net151),
    .addr({net8,
    net7,
    net6,
    net5,
    net4,
    net3,
    net2,
    net1}),
    .din({net69,
    net68,
    net67,
    net66,
    net64,
    net63,
    net62,
    net61,
    net60,
    net59,
    net58,
    net57,
    net56,
    net55,
    net53,
    net52,
    net51,
    net50,
    net49,
    net48,
    net47,
    net46,
    net45,
    net44,
    net42,
    net41,
    net40,
    net39,
    net38,
    net37,
    net36,
    net35,
    net34,
    net33,
    net31,
    net30,
    net29,
    net28,
    net27,
    net26,
    net25,
    net24,
    net23,
    net22,
    net20,
    net19,
    net18,
    net17,
    net16,
    net15,
    net14,
    net13,
    net12,
    net11,
    net73,
    net72,
    net71,
    net70,
    net65,
    net54,
    net43,
    net32,
    net21,
    net10}),
    .dout({net143,
    net142,
    net141,
    net140,
    net138,
    net137,
    net136,
    net135,
    net134,
    net133,
    net132,
    net131,
    net130,
    net129,
    net127,
    net126,
    net125,
    net124,
    net123,
    net122,
    net121,
    net120,
    net119,
    net118,
    net116,
    net115,
    net114,
    net113,
    net112,
    net111,
    net110,
    net109,
    net108,
    net107,
    net105,
    net104,
    net103,
    net102,
    net101,
    net100,
    net99,
    net98,
    net97,
    net96,
    net94,
    net93,
    net92,
    net91,
    net90,
    net89,
    net88,
    net87,
    net86,
    net85,
    net147,
    net146,
    net145,
    net144,
    net139,
    net128,
    net117,
    net106,
    net95,
    net84}),
    .wmask({net83,
    net82,
    net81,
    net80,
    net79,
    net78,
    net77,
    net76}));
 sky130_fd_sc_hd__buf_16 wire148 (.A(net155),
    .X(net148));
endmodule
