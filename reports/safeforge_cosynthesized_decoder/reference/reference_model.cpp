// Generated bit-exact reference for safeforge-robust-8-4-v1-safe.
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <string>

static constexpr unsigned K = 4;
static constexpr unsigned R = 4;
static constexpr unsigned N = 8;
static constexpr std::uint64_t H_COLUMNS[N] = {10ULL, 5ULL, 12ULL, 7ULL, 1ULL, 2ULL, 4ULL, 8ULL};
static constexpr std::uint64_t G_ROWS[K] = {161ULL, 82ULL, 196ULL, 120ULL};

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
        case 1ULL: mask = 16ULL; known = true; break;
        case 2ULL: mask = 32ULL; known = true; break;
        case 5ULL: mask = 2ULL; known = true; break;
        case 8ULL: mask = 128ULL; known = true; break;
        case 9ULL: mask = 6ULL; known = true; break;
        case 11ULL: mask = 12ULL; known = true; break;
        case 13ULL: mask = 9ULL; known = true; break;
        case 15ULL: mask = 3ULL; known = true; break;
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
