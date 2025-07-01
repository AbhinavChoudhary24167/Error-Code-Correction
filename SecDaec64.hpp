#ifndef SECDAEC64_HPP
#define SECDAEC64_HPP

#include <array>
#include <cstdint>
#include <vector>
#include <cmath>
#include "BitVector.hpp"
#include "ParityCheckMatrix.hpp"
#include "telemetry.hpp"
#include <fstream>

class SecDaec64 {
public:
    static constexpr int DATA_BITS = 64;
    static constexpr int PARITY_BITS = 8;   // 7 Hamming + 1 DAEC
    static constexpr int TOTAL_BITS = DATA_BITS + PARITY_BITS + 1; // + overall

    struct CodeWord { uint64_t bits; };

    SecDaec64();

    CodeWord encode(uint64_t data) const;
    struct DecodingResult {
        uint64_t data;
        bool corrected;
        bool detected;
        Telemetry t;
    };
    DecodingResult decode(CodeWord) const;

    std::vector<int> getDataPositions() const;
    bool isParityPosition(int pos) const;

private:
    ParityCheckMatrix H;
    int parityPos[PARITY_BITS];

    void placeDataBits(uint64_t &word, uint64_t data) const {
        int dataBit=0;
        for(int i=0;i<TOTAL_BITS-1;++i){
            bool isParity=false;
            for(int p=0;p<PARITY_BITS;++p) if(i==parityPos[p]) { isParity=true; break; }
            if(i==(TOTAL_BITS-1)) isParity=true; // overall
            if(!isParity){
                if(data & (1ULL<<dataBit))
                    word |= (1ULL<<i);
                ++dataBit;
            }
        }
    }

    int bitFromSyndrome(int s) const { return s-1; }
    std::pair<int,int> bitsFromDoubleAdj(int s) const {
        static std::pair<int,int> table[1<<PARITY_BITS];
        static bool init = false;
        if(!init) {
            for(int idx=0; idx<(1<<PARITY_BITS); ++idx)
                table[idx] = {0,0};
            for(int i=0;i<TOTAL_BITS-1;++i) {
                int j=i+1;
                if(j>=TOTAL_BITS) break;
                uint64_t low=0, high=0;
                if(i<64) low |= 1ULL<<i; else high |= 1ULL<<(i-64);
                if(j<64) low |= 1ULL<<j; else high |= 1ULL<<(j-64);
                BitVector cw(low,high);
                BitVector syn = H.syndrome(cw);
                int synInt=0;
                for(int p=0;p<PARITY_BITS;++p)
                    if(syn.get(p)) synInt |= (1<<p);
                table[synInt] = {i,j};
            }
            init = true;
        }
        return table[s];
    }
};

inline SecDaec64::SecDaec64() {
    int base[7] = {1,2,4,8,16,32,64};
    for(int i=0;i<7;++i) {
        parityPos[i] = base[i]-1; // store as 0-index
        std::array<uint64_t,2> row{0,0};
        for(int pos=1; pos<=TOTAL_BITS-1; ++pos) {
            if(pos & base[i]) {
                int idx = pos-1;
                if(idx < 64) row[0] |= (1ULL<<idx);
                else row[1] |= (1ULL<<(idx-64));
            }
        }
        H.rows.push_back(row);
    }

    parityPos[7] = 69; // example position for DAEC parity
    uint64_t daecRow = 0;
    for(int i=0;i<DATA_BITS-1;++i)
        daecRow ^= (1ULL<<i) | (1ULL<<(i+1));
    H.rows.push_back({daecRow,0});
}

inline SecDaec64::CodeWord SecDaec64::encode(uint64_t data) const {
    CodeWord cw{};
    placeDataBits(cw.bits, data);
    for(int p=0;p<7;++p) {
        bool parity = __builtin_parityll(cw.bits & H.rows[p][0]);
        cw.bits |= (uint64_t)parity << parityPos[p];
    }
    bool daec = 0;
    for(int i=0;i<DATA_BITS-1;++i)
        daec ^= ((data>>i) ^ (data>>(i+1))) & 1ULL;
    cw.bits |= (uint64_t)daec << parityPos[7];
    bool ovp = __builtin_parityll(cw.bits);
    cw.bits |= (uint64_t)ovp << (TOTAL_BITS-1);
    return cw;
}

inline SecDaec64::DecodingResult SecDaec64::decode(CodeWord recv) const {
    DecodingResult res{};
    res.data = recv.bits;
    res.corrected = false;
    res.detected = false;

    Telemetry &t = res.t;

    BitVector vec(recv.bits);
    BitVector synVec = H.syndrome(vec);
    uint8_t s = 0;
    for(int i=0;i<PARITY_BITS;++i)
        if(synVec.get(i)) s |= (1<<i);
    t.xor_ops += PARITY_BITS; // parity checks

    bool ovp = __builtin_parityll(recv.bits);
    t.xor_ops += 1; // overall parity

    res.detected = (s!=0) || ovp;

    if(s==0 && !ovp) {
        std::ofstream ofs("secdaec_energy.csv", std::ios::app);
        ofs << t.xor_ops << ',' << t.and_ops << ',' << estimate_energy(t) << '\n';
        return res; // clean
    }

    auto flip = [&](int b){ recv.bits ^= (1ULL<<b); };
    int wt = __builtin_popcount((unsigned)s);
    if(wt==1) {
        flip(bitFromSyndrome(s));
        res.corrected = true;
    } else if(wt==2) {
        auto bits = bitsFromDoubleAdj(s);
        if(std::abs(bits.first - bits.second)==1) {
            flip(bits.first);
            flip(bits.second);
            res.corrected = true;
        }
    }
    res.data = recv.bits;
    {
        std::ofstream ofs("secdaec_energy.csv", std::ios::app);
        ofs << t.xor_ops << ',' << t.and_ops << ',' << estimate_energy(t) << '\n';
    }
    return res;
}

inline std::vector<int> SecDaec64::getDataPositions() const {
    std::vector<int> pos;
    for(int i=0;i<TOTAL_BITS-1;++i)
        if(!isParityPosition(i))
            pos.push_back(i);
    return pos;
}

inline bool SecDaec64::isParityPosition(int pos) const {
    for(int p=0;p<PARITY_BITS;++p)
        if(pos==parityPos[p]) return true;
    return pos==TOTAL_BITS-1;
}

#endif // SECDAEC64_HPP
