// Generated bit-exact reference for forge-spatial-hotspot-72-64-v1.
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <string>

static constexpr unsigned K = 64;
static constexpr unsigned R = 8;
static constexpr unsigned N = 72;
static constexpr std::uint64_t H_COLUMNS[N] = {7ULL, 11ULL, 13ULL, 14ULL, 47ULL, 21ULL, 162ULL, 25ULL, 26ULL, 28ULL, 35ULL, 37ULL, 100ULL, 41ULL, 168ULL, 44ULL, 49ULL, 72ULL, 52ULL, 140ULL, 67ULL, 193ULL, 70ULL, 81ULL, 74ULL, 76ULL, 196ULL, 82ULL, 170ULL, 108ULL, 131ULL, 98ULL, 38ULL, 104ULL, 138ULL, 97ULL, 133ULL, 230ULL, 137ULL, 157ULL, 56ULL, 145ULL, 200ULL, 102ULL, 152ULL, 161ULL, 164ULL, 22ULL, 42ULL, 176ULL, 69ULL, 194ULL, 73ULL, 146ULL, 208ULL, 224ULL, 31ULL, 19ULL, 55ULL, 59ULL, 61ULL, 62ULL, 79ULL, 87ULL, 1ULL, 2ULL, 4ULL, 8ULL, 16ULL, 32ULL, 64ULL, 128ULL};
static constexpr std::uint64_t G_ROWS[K] = {129127208515966861313ULL, 202914184810805067778ULL, 239807672958224171012ULL, 258254417031933722632ULL, 866996971464348925968ULL, 387381625547900583968ULL, 2988372539940947361856ULL, 461168601842738790528ULL, 479615345916448342272ULL, 516508834063867445760ULL, 645636042579834307584ULL, 682529530727253411840ULL, 1844674407370955165696ULL, 756316507022091624448ULL, 3099053004383204687872ULL, 811656739243220303872ULL, 903890459611768094720ULL, 1328165573307087847424ULL, 959230691832896946176ULL, 2582544170319337750528ULL, 1235931852938541006848ULL, 3560221606225945559040ULL, 1291272085159672807424ULL, 1494186269970482069504ULL, 1365059061454523596800ULL, 1401952549601959477248ULL, 3615561838447139225600ULL, 1512633014044317450240ULL, 3135946492530892210176ULL, 1992248359961168445440ULL, 2416523473657025003520ULL, 1807780919225683542016ULL, 700976274805257928704ULL, 1918461383674383302656ULL, 2545650682189097992192ULL, 1789334175184186245120ULL, 2453416961872089841664ULL, 4242751137090635825152ULL, 2527203938373086478336ULL, 2896138820122155417600ULL, 1033017669227246518272ULL, 2674777892886908239872ULL, 3689348819139956834304ULL, 1881567904314467287040ULL, 2803905116796037890048ULL, 2969925831051609899008ULL, 3025266098457110642688ULL, 405828510359098490880ULL, 774763532570777878528ULL, 3246627519922834505728ULL, 1272826466985865904128ULL, 3578670602099466698752ULL, 1346616820980424638464ULL, 2693233641960849276928ULL, 3836940781730096218112ULL, 4132106701307958525952ULL, 571921123879034028032ULL, 350632252588557336576ULL, 1014859154430177050624ULL, 1088934361101166968832ULL, 1126404310000889495552ULL, 1146003975579205894144ULL, 1461904467841481965568ULL, 1614090106449585766400ULL};

std::uint64_t syndrome(std::uint64_t word) {
    std::uint64_t value = 0;
    for (unsigned position = 0; position < N; ++position) if ((word >> position) & 1ULL) value ^= H_COLUMNS[position];
    return value;
}

std::uint64_t encode(std::uint64_t data) {
    std::uint64_t out = 0;
    for (unsigned source = 0; source < K; ++source) if ((data >> source) & 1ULL) out ^= G_ROWS[source];
    return out;
}

int main(int argc, char** argv) {
    if (argc != 3) return 2;
    const std::uint64_t data = std::stoull(argv[1], nullptr, 0);
    const std::uint64_t error = std::stoull(argv[2], nullptr, 0);
    const std::uint64_t codeword = encode(data);
    const std::uint64_t received = codeword ^ error;
    const std::uint64_t syn = syndrome(received);
    std::uint64_t mask = 0;
    bool known = false;
    switch (syn) {
        case 1ULL: mask = 18446744073709551616ULL; known = true; break;
        case 2ULL: mask = 36893488147419103232ULL; known = true; break;
        case 4ULL: mask = 73786976294838206464ULL; known = true; break;
        case 5ULL: mask = 105553116266496ULL; known = true; break;
        case 7ULL: mask = 1ULL; known = true; break;
        case 8ULL: mask = 147573952589676412928ULL; known = true; break;
        case 11ULL: mask = 2ULL; known = true; break;
        case 13ULL: mask = 4ULL; known = true; break;
        case 14ULL: mask = 8ULL; known = true; break;
        case 16ULL: mask = 295147905179352825856ULL; known = true; break;
        case 19ULL: mask = 144115188075855872ULL; known = true; break;
        case 20ULL: mask = 824633720832ULL; known = true; break;
        case 21ULL: mask = 32ULL; known = true; break;
        case 22ULL: mask = 140737488355328ULL; known = true; break;
        case 23ULL: mask = 12582912ULL; known = true; break;
        case 25ULL: mask = 128ULL; known = true; break;
        case 26ULL: mask = 256ULL; known = true; break;
        case 27ULL: mask = 25165824ULL; known = true; break;
        case 28ULL: mask = 512ULL; known = true; break;
        case 29ULL: mask = 98304ULL; known = true; break;
        case 31ULL: mask = 72057594037927936ULL; known = true; break;
        case 32ULL: mask = 590295810358705651712ULL; known = true; break;
        case 33ULL: mask = 24ULL; known = true; break;
        case 35ULL: mask = 1024ULL; known = true; break;
        case 36ULL: mask = 432345564227567616ULL; known = true; break;
        case 37ULL: mask = 2048ULL; known = true; break;
        case 38ULL: mask = 4294967296ULL; known = true; break;
        case 41ULL: mask = 8192ULL; known = true; break;
        case 42ULL: mask = 281474976710656ULL; known = true; break;
        case 44ULL: mask = 32768ULL; known = true; break;
        case 47ULL: mask = 16ULL; known = true; break;
        case 49ULL: mask = 65536ULL; known = true; break;
        case 52ULL: mask = 262144ULL; known = true; break;
        case 55ULL: mask = 288230376151711744ULL; known = true; break;
        case 56ULL: mask = 1099511627776ULL; known = true; break;
        case 57ULL: mask = 52776558133248ULL; known = true; break;
        case 58ULL: mask = 48ULL; known = true; break;
        case 59ULL: mask = 576460752303423488ULL; known = true; break;
        case 60ULL: mask = 422212465065984ULL; known = true; break;
        case 61ULL: mask = 1152921504606846976ULL; known = true; break;
        case 62ULL: mask = 2305843009213693952ULL; known = true; break;
        case 63ULL: mask = 1536ULL; known = true; break;
        case 64ULL: mask = 1180591620717411303424ULL; known = true; break;
        case 65ULL: mask = 6144ULL; known = true; break;
        case 66ULL: mask = 27021597764222976ULL; known = true; break;
        case 67ULL: mask = 1048576ULL; known = true; break;
        case 68ULL: mask = 6442450944ULL; known = true; break;
        case 69ULL: mask = 1125899906842624ULL; known = true; break;
        case 70ULL: mask = 4194304ULL; known = true; break;
        case 72ULL: mask = 131072ULL; known = true; break;
        case 73ULL: mask = 4503599627370496ULL; known = true; break;
        case 74ULL: mask = 16777216ULL; known = true; break;
        case 76ULL: mask = 33554432ULL; known = true; break;
        case 77ULL: mask = 12288ULL; known = true; break;
        case 78ULL: mask = 12884901888ULL; known = true; break;
        case 79ULL: mask = 4611686018427387904ULL; known = true; break;
        case 81ULL: mask = 8388608ULL; known = true; break;
        case 82ULL: mask = 134217728ULL; known = true; break;
        case 86ULL: mask = 27670116110564327424ULL; known = true; break;
        case 87ULL: mask = 9223372036854775808ULL; known = true; break;
        case 89ULL: mask = 6597069766656ULL; known = true; break;
        case 96ULL: mask = 1770887431076116955136ULL; known = true; break;
        case 97ULL: mask = 34359738368ULL; known = true; break;
        case 98ULL: mask = 2147483648ULL; known = true; break;
        case 99ULL: mask = 206158430208ULL; known = true; break;
        case 100ULL: mask = 4096ULL; known = true; break;
        case 102ULL: mask = 8796093022208ULL; known = true; break;
        case 104ULL: mask = 8589934592ULL; known = true; break;
        case 108ULL: mask = 536870912ULL; known = true; break;
        case 111ULL: mask = 412316860416ULL; known = true; break;
        case 113ULL: mask = 6917529027641081856ULL; known = true; break;
        case 121ULL: mask = 196608ULL; known = true; break;
        case 124ULL: mask = 393216ULL; known = true; break;
        case 128ULL: mask = 2361183241434822606848ULL; known = true; break;
        case 129ULL: mask = 24576ULL; known = true; break;
        case 130ULL: mask = 3145728ULL; known = true; break;
        case 131ULL: mask = 1073741824ULL; known = true; break;
        case 132ULL: mask = 49152ULL; known = true; break;
        case 133ULL: mask = 68719476736ULL; known = true; break;
        case 136ULL: mask = 100663296ULL; known = true; break;
        case 137ULL: mask = 274877906944ULL; known = true; break;
        case 138ULL: mask = 17179869184ULL; known = true; break;
        case 139ULL: mask = 6755399441055744ULL; known = true; break;
        case 140ULL: mask = 524288ULL; known = true; break;
        case 145ULL: mask = 2199023255552ULL; known = true; break;
        case 146ULL: mask = 9007199254740992ULL; known = true; break;
        case 150ULL: mask = 201326592ULL; known = true; break;
        case 152ULL: mask = 17592186044416ULL; known = true; break;
        case 154ULL: mask = 844424930131968ULL; known = true; break;
        case 157ULL: mask = 549755813888ULL; known = true; break;
        case 161ULL: mask = 35184372088832ULL; known = true; break;
        case 162ULL: mask = 64ULL; known = true; break;
        case 164ULL: mask = 70368744177664ULL; known = true; break;
        case 165ULL: mask = 1649267441664ULL; known = true; break;
        case 168ULL: mask = 16384ULL; known = true; break;
        case 169ULL: mask = 3298534883328ULL; known = true; break;
        case 170ULL: mask = 268435456ULL; known = true; break;
        case 174ULL: mask = 13194139533312ULL; known = true; break;
        case 176ULL: mask = 562949953421312ULL; known = true; break;
        case 178ULL: mask = 211106232532992ULL; known = true; break;
        case 183ULL: mask = 96ULL; known = true; break;
        case 184ULL: mask = 786432ULL; known = true; break;
        case 187ULL: mask = 192ULL; known = true; break;
        case 192ULL: mask = 3541774862152233910272ULL; known = true; break;
        case 193ULL: mask = 2097152ULL; known = true; break;
        case 194ULL: mask = 2251799813685248ULL; known = true; break;
        case 196ULL: mask = 67108864ULL; known = true; break;
        case 198ULL: mask = 805306368ULL; known = true; break;
        case 200ULL: mask = 4398046511104ULL; known = true; break;
        case 207ULL: mask = 1572864ULL; known = true; break;
        case 208ULL: mask = 18014398509481984ULL; known = true; break;
        case 219ULL: mask = 13510798882111488ULL; known = true; break;
        case 224ULL: mask = 36028797018963968ULL; known = true; break;
        case 225ULL: mask = 3221225472ULL; known = true; break;
        case 226ULL: mask = 25769803776ULL; known = true; break;
        case 228ULL: mask = 103079215104ULL; known = true; break;
        case 230ULL: mask = 137438953472ULL; known = true; break;
        case 235ULL: mask = 51539607552ULL; known = true; break;
        case 239ULL: mask = 1610612736ULL; known = true; break;
        case 245ULL: mask = 1688849860263936ULL; known = true; break;
        case 248ULL: mask = 402653184ULL; known = true; break;
        case 254ULL: mask = 26388279066624ULL; known = true; break;
        case 255ULL: mask = 108086391056891904ULL; known = true; break;
        default: break;
    }
    std::string outcome;
    long long decoded = -1;
    if (syn == 0) {
        decoded = static_cast<long long>(received & ((1ULL << K) - 1ULL));
        outcome = decoded == static_cast<long long>(data) ? "correct" : "silent_corruption";
    } else if (!known) {
        outcome = "detected_uncorrectable";
    } else {
        const std::uint64_t corrected = received ^ mask;
        if (syndrome(corrected) != 0) outcome = "decoder_failure";
        else {
            decoded = static_cast<long long>(corrected & ((1ULL << K) - 1ULL));
            outcome = decoded == static_cast<long long>(data) ? "corrected" : "silent_corruption";
        }
    }
    std::cout << codeword << ' ' << received << ' ' << syn << ' ' << outcome << ' ' << decoded << '\n';
    return 0;
}
