#ifndef TRADEGEN_FAST_TG_FP128_HPP
#define TRADEGEN_FAST_TG_FP128_HPP

#include <cstdint>
#include "tg_abi.h"

namespace tg {

using i128 = __int128;
using u128 = unsigned __int128;

constexpr u128 SCALE_FP18 = static_cast<u128>(1000000000000000000ULL); /* 10^18 */
/* 10^20 whole units * 10^18 scale = 10^38 (< 2^127 - 1 ~= 1.7014e38) */
constexpr u128 MAX_MAG_FP18 = SCALE_FP18 * static_cast<u128>(10000000000000000000ULL) * static_cast<u128>(10ULL);

inline constexpr i128 unpack_i128(const tg_i128_t& v) noexcept {
    u128 u = (static_cast<u128>(static_cast<uint64_t>(v.hi)) << 64) | static_cast<u128>(v.lo);
    return static_cast<i128>(u);
}

inline constexpr tg_i128_t pack_i128(i128 v) noexcept {
    u128 u = static_cast<u128>(v);
    tg_i128_t out{};
    out.hi = static_cast<int64_t>(static_cast<uint64_t>(u >> 64));
    out.lo = static_cast<uint64_t>(u);
    return out;
}

inline constexpr u128 abs_i128(i128 v) noexcept {
    if (v >= 0) {
        return static_cast<u128>(v);
    }
    return static_cast<u128>(0) - static_cast<u128>(v);
}

inline constexpr bool in_fp18_range(i128 v) noexcept {
    return abs_i128(v) <= MAX_MAG_FP18;
}

inline constexpr bool add_checked_fp18(i128 a, i128 b, i128* out) noexcept {
    i128 res = 0;
    if (__builtin_add_overflow(a, b, &res)) {
        return false;
    }
    if (!in_fp18_range(res)) {
        return false;
    }
    *out = res;
    return true;
}

inline constexpr bool sub_checked_fp18(i128 a, i128 b, i128* out) noexcept {
    i128 res = 0;
    if (__builtin_sub_overflow(a, b, &res)) {
        return false;
    }
    if (!in_fp18_range(res)) {
        return false;
    }
    *out = res;
    return true;
}

struct u256 {
    u128 lo{0};
    u128 hi{0};
};

inline constexpr int cmp_u256(const u256& a, const u256& b) noexcept {
    if (a.hi != b.hi) {
        return (a.hi < b.hi) ? -1 : 1;
    }
    if (a.lo != b.lo) {
        return (a.lo < b.lo) ? -1 : 1;
    }
    return 0;
}

inline constexpr bool add_u256(const u256& a, const u256& b, u256* out) noexcept {
    u128 lo = a.lo + b.lo;
    u128 carry = (lo < a.lo) ? 1 : 0;
    u128 hi1 = a.hi + b.hi;
    bool ovf1 = (hi1 < a.hi);
    u128 hi2 = hi1 + carry;
    bool ovf2 = (hi2 < hi1);
    if (ovf1 || ovf2) {
        return false;
    }
    out->lo = lo;
    out->hi = hi2;
    return true;
}

inline constexpr u256 sub_u256(const u256& a, const u256& b) noexcept {
    u128 borrow = (a.lo < b.lo) ? 1 : 0;
    return u256{a.lo - b.lo, a.hi - b.hi - borrow};
}

/* Exact 128x128 -> 256 unsigned multiplication */
inline constexpr u256 mul128_u256(u128 a, u128 b) noexcept {
    const u128 mask64 = static_cast<u128>(0xFFFFFFFFFFFFFFFFULL);
    u128 a_lo = a & mask64;
    u128 a_hi = a >> 64;
    u128 b_lo = b & mask64;
    u128 b_hi = b >> 64;

    u128 p0 = a_lo * b_lo;
    u128 p1 = a_lo * b_hi;
    u128 p2 = a_hi * b_lo;
    u128 p3 = a_hi * b_hi;

    u128 mid1 = (p0 >> 64) + (p1 & mask64) + (p2 & mask64);
    u128 hi = p3 + (p1 >> 64) + (p2 >> 64) + (mid1 >> 64);
    u128 lo = (p0 & mask64) | (mid1 << 64);
    return u256{lo, hi};
}

/* Exact 256-bit divided by 128-bit -> 256-bit quotient + 128-bit remainder */
inline constexpr bool divrem_u256_u128(const u256& num, u128 den, u256* quot_out, u128* rem_out) noexcept {
    if (den == 0) {
        return false;
    }
    if (num.hi == 0) {
        quot_out->hi = 0;
        quot_out->lo = num.lo / den;
        *rem_out = num.lo % den;
        return true;
    }
    u128 q_hi = num.hi / den;
    u128 rem = num.hi % den;
    u128 q_lo = 0;
    /* Binary long division of (rem : num.lo) by den over 128 bits */
    for (int bit = 127; bit >= 0; --bit) {
        bool top = (rem >> 127) != 0;
        rem = (rem << 1) | ((num.lo >> bit) & 1u);
        if (top || rem >= den) {
            rem -= den;
            q_lo |= (static_cast<u128>(1) << bit);
        }
    }
    quot_out->hi = q_hi;
    quot_out->lo = q_lo;
    *rem_out = rem;
    return true;
}

/* Floor division where quotient must fit in u128 and <= MAX_MAG_FP18 */
inline constexpr bool div_floor_u256_u128(const u256& num, u128 den, u128* quot_out, u128* rem_out = nullptr) noexcept {
    u256 q{};
    u128 r = 0;
    if (!divrem_u256_u128(num, den, &q, &r)) {
        return false;
    }
    if (q.hi != 0 || q.lo > MAX_MAG_FP18) {
        return false;
    }
    *quot_out = q.lo;
    if (rem_out != nullptr) {
        *rem_out = r;
    }
    return true;
}

/* Ceiling division where quotient must fit in u128 and <= MAX_MAG_FP18 */
inline constexpr bool div_ceil_u256_u128(const u256& num, u128 den, u128* quot_out) noexcept {
    u256 q{};
    u128 r = 0;
    if (!divrem_u256_u128(num, den, &q, &r)) {
        return false;
    }
    if (r != 0) {
        u256 one{1, 0};
        if (!add_u256(q, one, &q)) {
            return false;
        }
    }
    if (q.hi != 0 || q.lo > MAX_MAG_FP18) {
        return false;
    }
    *quot_out = q.lo;
    return true;
}

/* Exact multiplication of two non-negative fp18 values requiring (a * b) % 10^18 == 0 */
inline constexpr bool mul_fp18_exact(u128 a, u128 b, u128* out) noexcept {
    u256 prod = mul128_u256(a, b);
    u128 q = 0;
    u128 rem = 0;
    if (!div_floor_u256_u128(prod, SCALE_FP18, &q, &rem)) {
        return false;
    }
    if (rem != 0) {
        return false;
    }
    *out = q;
    return true;
}

/* Partial FIFO cost share rounded DOWN at 10^-18, or full remaining basis when taken == held. */
inline constexpr bool fifo_alloc_cost_fp18(u128 basis, u128 taken, u128 held, u128* out_alloc) noexcept {
    if (held == 0 || taken > held) {
        return false;
    }
    if (taken == held) {
        *out_alloc = basis;
        return true;
    }
    u256 prod = mul128_u256(basis, taken);
    u128 alloc = 0;
    if (!div_floor_u256_u128(prod, held, &alloc, nullptr)) {
        return false;
    }
    if (alloc > basis) {
        return false;
    }
    *out_alloc = alloc;
    return true;
}

/* 384-bit unsigned integer (6 x 64-bit words, little-endian) for triple products qty * price * fx */
struct u384 {
    uint64_t w[6]{0, 0, 0, 0, 0, 0};
};

inline constexpr u384 mul_u256_u128(const u256& a, u128 b) noexcept {
    uint64_t aw[4] = {
        static_cast<uint64_t>(a.lo),
        static_cast<uint64_t>(a.lo >> 64),
        static_cast<uint64_t>(a.hi),
        static_cast<uint64_t>(a.hi >> 64)
    };
    uint64_t bw[2] = {
        static_cast<uint64_t>(b),
        static_cast<uint64_t>(b >> 64)
    };
    u384 out{};
    for (int i = 0; i < 4; ++i) {
        u128 carry = 0;
        for (int j = 0; j < 2; ++j) {
            u128 cur = static_cast<u128>(out.w[i + j]) + static_cast<u128>(aw[i]) * static_cast<u128>(bw[j]) + carry;
            out.w[i + j] = static_cast<uint64_t>(cur);
            carry = cur >> 64;
        }
        int k = i + 2;
        while (carry != 0 && k < 6) {
            u128 cur = static_cast<u128>(out.w[k]) + carry;
            out.w[k] = static_cast<uint64_t>(cur);
            carry = cur >> 64;
            ++k;
        }
    }
    return out;
}

inline constexpr int cmp_u384(const u384& a, const u384& b) noexcept {
    for (int i = 5; i >= 0; --i) {
        if (a.w[i] != b.w[i]) {
            return (a.w[i] < b.w[i]) ? -1 : 1;
        }
    }
    return 0;
}

} /* namespace tg */

#endif /* TRADEGEN_FAST_TG_FP128_HPP */
