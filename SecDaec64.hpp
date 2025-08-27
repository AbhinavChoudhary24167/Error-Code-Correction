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

    struct CodeWord { BitVector bits; };

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

    void placeDataBits(BitVector &word, uint64_t data) const {
        int dataBit=0;
        for(int i=0;i<TOTAL_BITS-1;++i){
            bool isParity=false;
            for(int p=0;p<PARITY_BITS;++p) if(i==parityPos[p]) { isParity=true; break; }
            if(i==(TOTAL_BITS-1)) isParity=true; // overall
            if(!isParity){
                if(data & (1ULL<<dataBit))
                    word.set(i, true);
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
        uint64_t a = H.rows[p][0] & cw.bits.words[0];
        uint64_t b = H.rows[p][1] & cw.bits.words[1];
        bool parity = (__builtin_popcountll(a) + __builtin_popcountll(b)) & 1;
        cw.bits.set(parityPos[p], parity);
    }

    bool daec = 0;
    for(int i=0;i<DATA_BITS-1;++i)
        daec ^= ((data>>i) ^ (data>>(i+1))) & 1ULL;
    cw.bits.set(parityPos[7], daec);

    int pop = __builtin_popcountll(cw.bits.words[0]) + __builtin_popcountll(cw.bits.words[1]);
    bool ovp = pop & 1;
    cw.bits.set(TOTAL_BITS-1, ovp);
    return cw;
}

inline SecDaec64::DecodingResult SecDaec64::decode(CodeWord recv) const {
    DecodingResult res{};
    res.corrected = false;
    res.detected = false;

    Telemetry &t = res.t;

    uint8_t s = 0;
    for(int p=0; p<PARITY_BITS; ++p) {
        bool parity = false;
        for(int w=0; w<2; ++w) {
            for(int bit=0; bit<64; ++bit) {
                if((H.rows[p][w] >> bit) & 1ULL) {
                    bool v = (recv.bits.words[w] >> bit) & 1ULL;
                    parity = XOR(parity, v, t);
                }
            }
        }
        if(parity) s |= (1<<p);
    }

    bool ovp = false;
    for(int pos=0; pos<TOTAL_BITS-1; ++pos) {
        bool v = recv.bits.get(pos);
        ovp = XOR(ovp, v, t);
    }

    res.detected = (s!=0) || ovp;

    if(AND(s==0, !ovp, t)) {
        uint64_t data=0;
        auto dataPos = getDataPositions();
        for(int i=0;i<DATA_BITS;++i)
            if(recv.bits.get(dataPos[i]))
                data |= (1ULL<<i);
        res.data = data;
        std::ofstream ofs("secdaec_energy.csv", std::ios::app);
        ofs << t.xor_ops << ',' << t.and_ops << '\n';
        return res; // clean
    }

    auto flip = [&](int b){ recv.bits.set(b, !recv.bits.get(b)); };
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
    uint64_t data=0;
    auto dataPos = getDataPositions();
    for(int i=0;i<DATA_BITS;++i)
        if(recv.bits.get(dataPos[i]))
            data |= (1ULL<<i);
    res.data = data;
    {
        std::ofstream ofs("secdaec_energy.csv", std::ios::app);
        ofs << t.xor_ops << ',' << t.and_ops << '\n';
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
