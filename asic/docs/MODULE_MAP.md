# ECC Entry -> RTL Mapping

| code_db_entry | rtl_family | encoder_module | decoder_module | wrapper_module | tb_module |
|---|---|---|---|---|---|
| sec-ded-64 | SEC-DED | secded_encoder(DATA_W=64) | secded_decoder(DATA_W=64) | sec_ded_64 | tb_secded |
| sec-daec-64 | SEC-DAEC | secdaec_encoder(DATA_W=64) | secdaec_decoder(DATA_W=64) | sec_daec_64 | tb_secdaec |
| taec-64 | TAEC | taec_encoder(DATA_W=64) | taec_decoder(DATA_W=64) | taec_64 | tb_taec |
| bch-63 | BCH | bch_encoder(N=63,K=51) | bch_decoder(N=63,K=51) | bch_63 | tb_bch |
| polar-64-32 | Polar | polar_encoder(N=64,K=32) | polar_decoder(N=64,K=32) | polar_64_32 | tb_polar |
| polar-64-48 | Polar | polar_encoder(N=64,K=48) | polar_decoder(N=64,K=48) | polar_64_48 | tb_polar |
| polar-128-96 | Polar | polar_encoder(N=128,K=96) | polar_decoder(N=128,K=96) | polar_128_96 | tb_polar |
| sram-secded-8 | SEC-DED | secded_encoder(DATA_W=8) | secded_decoder(DATA_W=8) | sram_secded_8 | tb_sram_wrappers |
| sram-secded-16 | SEC-DED | secded_encoder(DATA_W=16) | secded_decoder(DATA_W=16) | sram_secded_16 | tb_sram_wrappers |
| sram-secded-32 | SEC-DED | secded_encoder(DATA_W=32) | secded_decoder(DATA_W=32) | sram_secded_32 | tb_sram_wrappers |
| sram-taec-8 | TAEC | taec_encoder(DATA_W=8) | taec_decoder(DATA_W=8) | sram_taec_8 | tb_sram_wrappers |
| sram-taec-16 | TAEC | taec_encoder(DATA_W=16) | taec_decoder(DATA_W=16) | sram_taec_16 | tb_sram_wrappers |
| sram-taec-32 | TAEC | taec_encoder(DATA_W=32) | taec_decoder(DATA_W=32) | sram_taec_32 | tb_sram_wrappers |
| sram-bch-8 | BCH | bch_encoder(N=14,K=8) | bch_decoder(N=14,K=8) | sram_bch_8 | tb_sram_wrappers |
| sram-bch-16 | BCH | bch_encoder(N=24,K=16) | bch_decoder(N=24,K=16) | sram_bch_16 | tb_sram_wrappers |
| sram-bch-32 | BCH | bch_encoder(N=45,K=32) | bch_decoder(N=45,K=32) | sram_bch_32 | tb_sram_wrappers |
| sram-polar-8 | Polar | polar_encoder(N=16,K=8) | polar_decoder(N=16,K=8) | sram_polar_8 | tb_sram_wrappers |
| sram-polar-16 | Polar | polar_encoder(N=32,K=16) | polar_decoder(N=32,K=16) | sram_polar_16 | tb_sram_wrappers |
| sram-polar-32 | Polar | polar_encoder(N=64,K=32) | polar_decoder(N=64,K=32) | sram_polar_32 | tb_sram_wrappers |

## RTL file locations
- `asic/include/ecc_pkg.sv`
- `asic/rtl/common/ecc_entries.sv`
- `asic/rtl/secded/secded_codec.sv`
- `asic/rtl/secdaec/secdaec_codec.sv`
- `asic/rtl/taec/taec_codec.sv`
- `asic/rtl/bch/bch_codec.sv`
- `asic/rtl/polar/polar_pkg.sv`
- `asic/rtl/polar/polar_codec.sv`
- `asic/rtl/sram/sram_wrappers.sv`
