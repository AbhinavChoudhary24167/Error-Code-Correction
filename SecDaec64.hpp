#ifndef SECDAEC64_HPP
#define SECDAEC64_HPP

#include <array>
#include <cstdint>
#include <cstdlib>
#include "BitVector.hpp"
#include "ParityCheckMatrix.hpp"

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
    };
    DecodingResult decode(CodeWord) const;

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

    uint64_t extractDataBits(const BitVector &word) const {
        uint64_t data=0;
        int dataBit=0;
        for(int i=0;i<TOTAL_BITS-1;++i){
            bool isParity=false;
            for(int p=0;p<PARITY_BITS;++p) if(i==parityPos[p]) { isParity=true; break; }
            if(i==(TOTAL_BITS-1)) isParity=true;
            if(!isParity){
                if(word.get(i))
                    data |= (1ULL<<dataBit);
                ++dataBit;
            }
        }
        return data;
    }

    int bitFromSyndrome(int s) const { return s-1; }
    std::pair<int,int> bitsFromDoubleAdj(int s) const {
        for(int i=0;i<TOTAL_BITS-2;++i){
            BitVector temp;
            if(i<64) temp.words[0]|=1ULL<<i; else temp.words[1]|=1ULL<<(i-64);
            if(i+1<64) temp.words[0]|=1ULL<<(i+1); else temp.words[1]|=1ULL<<((i+1)-64);
            BitVector syn = H.syndrome(temp);
            int synVal=0;
            for(int b=0;b<PARITY_BITS;++b) if(syn.get(b)) synVal|=1<<b;
            if(synVal==s) return {i,i+1};
        }
        return {-1,-1};
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
        unsigned parity = __builtin_popcountll(cw.bits.words[0] & H.rows[p][0]) +
                          __builtin_popcountll(cw.bits.words[1] & H.rows[p][1]);
        cw.bits.set(parityPos[p], parity & 1);
    }
    bool daec = 0;
    for(int i=0;i<DATA_BITS-1;++i)
        daec ^= ((data>>i) ^ (data>>(i+1))) & 1ULL;
    cw.bits.set(parityPos[7], daec);
    bool ovp = (__builtin_popcountll(cw.bits.words[0]) +
                __builtin_popcountll(cw.bits.words[1])) & 1ULL;
    cw.bits.set(TOTAL_BITS-1, ovp);
    return cw;
}

inline SecDaec64::DecodingResult SecDaec64::decode(CodeWord recv) const {
    BitVector synVec = H.syndrome(recv.bits);
    uint8_t s = 0;
    for(int i=0;i<PARITY_BITS;++i)
        if(synVec.get(i)) s |= (1<<i);
    bool ovp = (__builtin_popcountll(recv.bits.words[0]) +
                __builtin_popcountll(recv.bits.words[1])) & 1ULL;

    DecodingResult res{};
    res.data = extractDataBits(recv.bits);
    res.corrected = false;
    res.detected = (s!=0) || ovp;

    if(s==0 && !ovp) {
        return res; // clean
    }

    auto flip = [&](int b){
        if(b < 64) recv.bits.words[0] ^= (1ULL<<b);
        else recv.bits.words[1] ^= (1ULL<<(b-64));
    };
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
    res.data = extractDataBits(recv.bits);
    return res;
}

#endif // SECDAEC64_HPP
