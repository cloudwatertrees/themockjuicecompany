import SwiftUI

// Animation for the rigged apple (MascotSandbox.swift). A frame is a pure function of time, a
// seed and the cued clips: an idle performance generated from the seed always runs, clips layer
// over it, and the leaf, stem and arms trail the body through a damped spring computed from the
// body's own recent motion. Nothing is carried from frame to frame, so any frame renders on its
// own; the caches only skip recomputing what the same inputs always give.
//
// Use: one MascotDirector per mascot on screen, shown with MascotAnimatedView(director:), cued
// with director.play(.hop), .play(.celebrate), .play(.happy) and .play(.idle).

// MARK: - Clips

/// What the mascot can be asked to do. Idle always runs underneath: Happy loops until Idle is
/// cued again; Hop and Celebrate are one-shots that hand back to idle on their own.
enum MascotAnimation: String, CaseIterable, Identifiable {
    case idle, happy, hop, celebrate

    var id: String { rawValue }
    var title: String {
        switch self {
        case .idle: "Idle"
        case .happy: "Happy"
        case .hop: "Correct hop"
        case .celebrate: "Milestone"
        }
    }
}

/// A clip's pose at its local time. Body values are absolute (about the rest pose); each hold is
/// how much of what lies underneath (idle and earlier clips) the clip holds back, 0...1.
struct MascotClipPose {
    var body = MascotBody()
    var hold = 0.0
    var gaze = SIMD2<Double>()
    var gazeHold = 0.0
    var brow = 0.0
    var browHold = 0.0
    var eyes = 0.0
    var face: AppleFace.Expression? = nil
    /// Sparkles and confetti, in character space.
    var props: [MascotProp] = []
}

protocol MascotClip {
    /// Loops until Idle is cued (layered under one-shots) rather than playing once.
    var loops: Bool { get }
    /// Local time by which the clip has handed back to idle. `off` is when Idle was cued
    /// (looping clips only; nil while still on).
    func end(off: Double?) -> Double
    /// Local time from which another one-shot may take over without a pop.
    var interruptible: Double { get }
    func pose(at τ: Double, off: Double?) -> MascotClipPose
    /// Blinks in local time.
    func blinks(off: Double?) -> [MascotBlink]
}

// MARK: - Channels

/// MascotRigState's body channels as a vector, so layers can be added and scaled.
struct MascotBody {
    var tilt = 0.0, lift = 0.0, squash = 0.0
    var armLeft = 0.0, armRight = 0.0, legLeft = 0.0, legRight = 0.0

    static func + (a: Self, b: Self) -> Self {
        Self(tilt: a.tilt + b.tilt, lift: a.lift + b.lift, squash: a.squash + b.squash,
             armLeft: a.armLeft + b.armLeft, armRight: a.armRight + b.armRight,
             legLeft: a.legLeft + b.legLeft, legRight: a.legRight + b.legRight)
    }

    static func * (a: Self, k: Double) -> Self {
        Self(tilt: a.tilt * k, lift: a.lift * k, squash: a.squash * k, armLeft: a.armLeft * k,
             armRight: a.armRight * k, legLeft: a.legLeft * k, legRight: a.legRight * k)
    }
}

/// One blink: the lid accelerates shut, holds, and opens more slowly than it shut. The eye
/// squashes into the shut pose and stretches a touch as it reopens; the brows dip a frame behind.
struct MascotBlink {
    var start: Double
    var close = 0.085
    var hold = 0.03
    var open = 0.15
    var depth = 1.0

    func lid(_ t: Double) -> Double {
        let τ = t - start
        if τ <= 0 { return 0 }
        if τ < close {
            let p = τ / close
            return depth * p * p * (2.2 - 1.2 * p)
        }
        if τ < close + hold { return depth }
        let p = min((τ - close - hold) / open, 1), q = 1 - p
        return depth * q * q * (1 + 0.6 * p)
    }

    /// (lid closure, eye squash, eye stretch, brow drop in sheet pixels) at time t. The lid snaps
    /// shut; the squash eases in behind it and peaks in the hold, and the brows dip a beat later.
    func sample(_ t: Double) -> (lid: Double, squash: Double, stretch: Double, brow: Double) {
        let τ = t - start, shut = close + hold
        func bump(_ a: Double, _ b: Double, _ c: Double) -> Double {
            τ < b ? MascotMotion.ease((τ - a) / (b - a)) : 1 - MascotMotion.ease((τ - b) / (c - b))
        }
        let u = (τ - shut - open * 0.3) / (open * 0.95)
        let stretch = u > 0 && u < 1 ? sin(.pi * u) * sin(.pi * u) : 0
        return (lid(t), 0.085 * depth * bump(close * 0.3, close + hold * 0.5, shut + open * 0.55),
                0.045 * depth * stretch, 1.3 * depth * bump(close * 0.4, shut + 0.03, shut + open * 0.8 + 0.04))
    }
}

enum MascotMotion {
    /// Eye dart (saccade), 0 → 1: the move lands within a few milliseconds, so at 60 fps nearly
    /// all of it shows in one frame, then a small overshoot settles over the next three.
    static func dart(_ τ: Double) -> Double {
        guard τ > 0 else { return 0 }
        return 1 - exp(-τ / 0.0035) + 9 * τ * exp(-τ / 0.012)
    }

    /// Index of the last element at or before t (elements sorted by time).
    static func last<T>(_ a: [T], _ t: Double, _ time: (T) -> Double) -> Int? {
        var lo = 0, hi = a.count
        while lo < hi {
            let mid = (lo + hi) / 2
            if time(a[mid]) <= t { lo = mid + 1 } else { hi = mid }
        }
        return lo > 0 ? lo - 1 : nil
    }

    /// Smoothstep, clamped to 0...1.
    static func ease(_ x: Double) -> Double {
        let x = min(max(x, 0), 1)
        return x * x * (3 - 2 * x)
    }

    /// One gravity for every jump, so the character weighs the same in all of them (sheet px/s²).
    static let gravity = 1400.0

    /// |x| with the corner rounded off below about `r`, so a sign change has no kink.
    static func soft(_ x: Double, _ r: Double) -> Double { (x * x + r * r).squareRoot() - r }
}

/// SplitMix64: seeded, so a seed always replays the same performance.
struct MascotRandom {
    private var state: UInt64

    init(_ seed: UInt64, _ stream: UInt64 = 0) { state = MascotRandom.hash(seed, stream) }

    static func hash(_ a: UInt64, _ b: UInt64) -> UInt64 {
        var z = a &+ b &* 0x9E37_79B9_7F4A_7C15 &+ 0x632B_E59B_D9B4_E019
        z = (z ^ (z >> 30)) &* 0xBF58_476D_1CE4_E5B9
        z = (z ^ (z >> 27)) &* 0x94D0_49BB_1331_11EB
        return z ^ (z >> 31)
    }

    /// Uniform in 0..<1.
    mutating func next() -> Double {
        state &+= 0x9E37_79B9_7F4A_7C15
        return Double(MascotRandom.hash(state, 0) >> 11) * 0x1p-53
    }

    mutating func callAsFunction(_ r: ClosedRange<Double>) -> Double { r.lowerBound + (r.upperBound - r.lowerBound) * next() }
    mutating func chance(_ p: Double) -> Bool { next() < p }
    mutating func sign() -> Double { next() < 0.5 ? -1 : 1 }

    /// Smooth value noise, about -1...1: Catmull-Rom through seeded knots one unit apart.
    static func noise(_ x: Double, _ seed: UInt64) -> Double {
        let i = x.rounded(.down), f = x - i
        func knot(_ k: Double) -> Double { Double(hash(seed, UInt64(bitPattern: Int64(k))) >> 11) * 0x1p-52 - 1 }
        let a = knot(i - 1), b = knot(i), c = knot(i + 1), d = knot(i + 2)
        return b + 0.5 * f * (c - a + f * (2 * a - 5 * b + 4 * c - d + f * (3 * (b - c) + d - a)))
    }
}

/// A keyframed channel: cubic Hermite through (time, value) keys. Slopes are flat at the ends and
/// at every turning point (slow in, slow out) and monotone between, so a curve only overshoots
/// where a key puts the overshoot; `slopes` sets a key's slope outright (by its time).
struct MascotCurve {
    private let t: [Double], v: [Double], m: [Double]

    init(_ keys: [(Double, Double)], slopes: [Double: Double] = [:]) {
        t = keys.map { $0.0 }
        v = keys.map { $0.1 }
        var m = [Double](repeating: 0, count: keys.count)
        for i in keys.indices.dropFirst().dropLast() {
            let w0 = t[i] - t[i - 1], w1 = t[i + 1] - t[i]
            let d0 = (v[i] - v[i - 1]) / w0, d1 = (v[i + 1] - v[i]) / w1
            if d0 * d1 > 0 { m[i] = 3 * (w0 + w1) / ((2 * w1 + w0) / d0 + (w1 + 2 * w0) / d1) }
        }
        for (i, k) in keys.enumerated() { if let slope = slopes[k.0] { m[i] = slope } }
        self.m = m
    }

    func callAsFunction(_ x: Double) -> Double {
        guard x > t[0] else { return v[0] }
        guard x < t[t.count - 1] else { return v[v.count - 1] }
        var i = 0
        while t[i + 1] <= x { i += 1 }
        let h = t[i + 1] - t[i], s = (x - t[i]) / h
        return v[i] + s * s * (3 - 2 * s) * (v[i + 1] - v[i]) + h * s * (1 - s) * ((1 - s) * m[i] - s * m[i + 1])
    }
}

/// A looping channel: keys for one period (times in 0..<period), wrapped so the curve runs
/// smoothly across the seam.
struct MascotLoop {
    let period: Double
    private let curve: MascotCurve

    init(_ period: Double, _ keys: [(Double, Double)]) {
        self.period = period
        curve = MascotCurve((-1...1).flatMap { k in keys.map { ($0.0 + Double(k) * period, $0.1) } })
    }

    func callAsFunction(_ t: Double) -> Double { curve(t - (t / period).rounded(.down) * period) }
}

/// A jump. In the air the body's middle flies a ballistic arc: it leaves at the speed the stretch
/// was giving it at takeoff and lands at the speed the landing squash takes over, so the middle
/// never jolts while the feet leave and meet the ground at speed. `air` is the body's squash in
/// flight; the ground squash either side meets it with `takeoffSlope` and `landingSlope`.
struct MascotJump {
    /// Height of the body's middle above the feet (sheet px).
    static let middle = 85.0
    let takeoff: Double, landing: Double
    let air: MascotCurve
    /// Speed of the middle leaving and reaching the ground (px/s, up positive).
    let rise: Double, fall: Double

    init(_ takeoff: Double, _ landing: Double, air keys: [(Double, Double)]) {
        self.takeoff = takeoff
        self.landing = landing
        air = MascotCurve(keys)
        let s0 = air(takeoff), s1 = air(landing), d = landing - takeoff
        rise = (Self.middle * (s0 - s1) + MascotMotion.gravity * d * d / 2) / d
        fall = rise - MascotMotion.gravity * d
    }

    var takeoffSlope: Double { -rise / Self.middle }
    var landingSlope: Double { -fall / Self.middle }

    func lift(_ t: Double) -> Double {
        guard t > takeoff, t < landing else { return 0 }
        let d = t - takeoff
        let middle = Self.middle * (1 - air(takeoff)) + rise * d - MascotMotion.gravity / 2 * d * d
        return max(0, middle - Self.middle * (1 - air(t)))
    }
}

// MARK: - Idle

/// One seed's idle performance: breaths, looks, blinks, weight shifts and fidgets. Generated
/// phrase by phrase, so each beat follows from the last (a big glance rides on a blink, a fidget
/// looks at what it is doing), and from separate random streams, so the result never depends on
/// how far ahead it has been generated.
final class MascotIdleScript {
    enum Fidget { case shift, tap, settle, wiggle, stretch, peek }
    struct Breath { var start, length, depth: Double }
    struct Look { var time: Double; var to: SIMD2<Double> }
    struct Move { var kind: Fidget; var start, side, size: Double }
    struct Lean { var time, to: Double }
    struct Flash { var time, size: Double }

    /// Eyes at rest, on the viewer. (At look 0 the art's own pupils sit off to the right.)
    static let home = SIMD2<Double>(-0.85, 0)

    let calm: Bool
    private(set) var breaths: [Breath] = []
    /// Every eye move, micro-saccades included; `glances` are the deliberate ones the body follows.
    private(set) var looks = [Look(time: -1, to: home)]
    private(set) var glances = [Look(time: -1, to: home)]
    private(set) var blinks: [MascotBlink] = []
    private(set) var moves: [Move] = []
    private(set) var leans = [Lean(time: -1, to: 0)]
    private(set) var flashes: [Flash] = []

    private let noiseSeeds: [UInt64]
    private var acts: MascotRandom, lungs: MascotRandom, lids: MascotRandom
    private var cued: [MascotBlink] = [], filled: [MascotBlink] = []
    private var phraseEnd = 0.0, breathEnd = 0.0, blinkCursor = 0.0
    private var pendingBlink: Double?
    private var gaze = home, lean = 0.0, nextFidget: Double, nextSigh: Double, lastStretch = -100.0

    init(seed: UInt64, calm: Bool) {
        self.calm = calm
        noiseSeeds = (0..<6).map { MascotRandom.hash(seed, 100 + $0) }
        var a = MascotRandom(seed, calm ? 11 : 1)
        nextFidget = calm ? a(10...18) : a(6...12)
        acts = a
        var l = MascotRandom(seed, calm ? 12 : 2)
        nextSigh = l(15...30)
        lungs = l
        lids = MascotRandom(seed, calm ? 13 : 3)
    }

    /// Makes sure the performance is written well past t.
    func extend(to t: Double) {
        guard phraseEnd < t + 12 else { return }
        while phraseEnd < t + 24 { phrase() }
        while breathEnd < phraseEnd { breath() }
        fillBlinks(to: phraseEnd - 4)
    }

    // MARK: Writing

    private func phrase() {
        let t = phraseEnd
        if t >= nextFidget { return fidget(at: t) }
        let home = Self.home
        let away = hypot(gaze.x - home.x, gaze.y - home.y) > 0.3
        let hold = away ? acts(0.8...2.2) : calm ? acts(2.8...6.5) : acts(2.2...5.5)
        saccades(t, t + hold)
        let s = t + hold
        phraseEnd = s
        if away {
            if acts.chance(0.75) {
                shift(at: s, to: home + jitter(0.07))
                if acts.chance(0.3) { flashes.append(Flash(time: s + acts(0.06...0.16), size: acts(0.8...1.2) * (calm ? 0.6 : 1))) }
            } else {
                shift(at: s, to: home + interest())
            }
            return
        }
        let r = acts.next()
        if r < (calm ? 0.4 : 0.55) {
            shift(at: s, to: home + interest() * (calm ? 0.55 : 1))
        } else if r < 0.88 || calm {
            shift(at: s, to: home + jitter(0.28))
        } else {
            // Looks around: to one side, then the other; the next phrase brings the eyes home.
            let side = acts.sign()
            shift(at: s, to: home + SIMD2(side * acts(0.55...0.75), acts(-0.35...0.1)))
            let s2 = s + acts(0.6...1.0)
            saccades(s, s2)
            shift(at: s2, to: home + SIMD2(-side * acts(0.55...0.75), acts(-0.35...0.1)))
            phraseEnd = s2
        }
    }

    /// Moves the eyes. A big move nearly always rides on a blink: the lid is on its way down as
    /// the eyes go, and they arrive under it.
    private func shift(at s: Double, to target: SIMD2<Double>) {
        let d = hypot(target.x - gaze.x, target.y - gaze.y)
        if acts.chance(d > 0.5 ? 0.9 : d > 0.25 ? 0.4 : 0.05) {
            var b = Self.blink(at: s, calm: calm, &acts)
            b.start = s - b.close * 0.55
            cued.append(b)
        }
        looks.append(Look(time: s, to: target))
        glances.append(Look(time: s, to: target))
        gaze = target
    }

    /// Micro-saccades while a look holds: tiny re-fixations around its target.
    private func saccades(_ from: Double, _ to: Double) {
        var t = from + acts(0.25...0.6)
        while t < to - 0.2 {
            looks.append(Look(time: t, to: gaze + SIMD2(acts(-0.15...0.15), acts(-0.1...0.1))))
            t += calm ? acts(0.7...1.6) : acts(0.35...1.1)
        }
    }

    private func jitter(_ r: Double) -> SIMD2<Double> { SIMD2(acts(-r...r), acts(-r...r) * 0.7) }

    /// Somewhere worth a glance, relative to home.
    private func interest() -> SIMD2<Double> {
        let points: [SIMD2<Double>] = [[-0.75, 0.05], [0.8, 0], [-0.55, -0.6], [0.6, -0.55], [0.05, 0.6], [-0.5, 0.45], [0.55, 0.5]]
        return points[min(Int(acts.next() * Double(points.count)), points.count - 1)] + jitter(0.1)
    }

    static let fidgetLength: [Fidget: Double] = [.shift: 1.2, .tap: 0.75, .settle: 1.05, .wiggle: 1.2, .stretch: 2.35, .peek: 1.5]

    private func fidget(at t: Double) {
        var kinds: [(Fidget, Double)] = calm ? [(.shift, 1)] :
            [(.shift, 0.28), (.tap, 0.16), (.settle, 0.18), (.wiggle, 0.14), (.peek, 0.14)]
        if !calm, t - lastStretch > 50 { kinds.append((.stretch, 0.1)) }
        var r = acts.next() * kinds.reduce(0) { $0 + $1.1 }
        let kind = kinds.first { r -= $0.1; return r < 0 }?.0 ?? .shift
        // A beat after the last look, so a fidget doesn't land on the blink that came with it.
        let side = acts.sign(), at = t + acts(0.5...1.0)
        switch kind {
        case .shift:
            lean = abs(lean) < 0.3 ? side * acts(0.6...1) : (acts.chance(0.6) ? -lean : 0) * acts(0.7...1)
            leans.append(Lean(time: at, to: lean * (calm ? 0.6 : 1)))
            if acts.chance(0.5) { cued.append(Self.blink(at: at + 0.05, calm: calm, &acts)) }
        case .tap:
            // The eyes go first; the foot follows a few frames later.
            if acts.chance(0.4) {
                shift(at: at - 0.12, to: Self.home + SIMD2(side * 0.3, 0.6))
                shift(at: at + 0.95, to: Self.home)
            }
        case .settle:
            cued.append(Self.blink(at: at + 0.3, calm: calm, slow: 1.3, &acts))
        case .wiggle:
            flashes.append(Flash(time: at + 0.05, size: acts(0.8...1.1)))
        case .stretch:
            var b = Self.blink(at: at + 0.4, calm: calm, slow: 1.5, &acts)
            b.hold = 0.75
            cued.append(b)
            lastStretch = t
        case .peek:
            shift(at: at - 0.12, to: Self.home + SIMD2(acts(-0.25...0.25), 0.65))
            let back = at + acts(0.8...1.1)
            shift(at: back, to: Self.home)
            flashes.append(Flash(time: back + 0.06, size: acts(0.9...1.2)))
        }
        moves.append(Move(kind: kind, start: at, side: side, size: acts(0.85...1.15)))
        phraseEnd = at + Self.fidgetLength[kind]! + acts(0.3...0.8)
        nextFidget = phraseEnd + (calm ? acts(14...28) : acts(11...26))
    }

    private func breath() {
        let t = breathEnd
        let sigh = t >= nextSigh
        let length = sigh ? lungs(4.8...5.8) : lungs(2.9...4.3)
        breaths.append(Breath(start: t, length: length, depth: sigh ? lungs(1.6...1.9) : lungs(0.8...1.15)))
        if sigh {
            // The eyes close slowly at the top of a sigh.
            var b = Self.blink(at: t + length * 0.4 - 0.12, calm: calm, slow: 1.6, &lungs)
            b.hold = lungs(0.2...0.35)
            cued.append(b)
            nextSigh = t + lungs(22...45)
        }
        breathEnd = t + length
    }

    /// Unprompted blinks between the ones the performance asked for, 2.4-6 s apart, some doubled.
    private func fillBlinks(to end: Double) {
        cued.sort { $0.start < $1.start }
        while true {
            let t = pendingBlink ?? blinkCursor + (calm ? lids(2.8...6.6) : lids(2.4...6.0))
            guard t < end else { pendingBlink = t; break }
            pendingBlink = nil
            // A blink the performance asked for covers this stretch: count on from it.
            if let i = MascotMotion.last(cued, t + 1.2, { $0.start }), cued[i].start > blinkCursor {
                blinkCursor = cued[i].start
                continue
            }
            let b = Self.blink(at: t, calm: calm, &lids)
            filled.append(b)
            blinkCursor = t
            if lids.chance(0.2) {
                var second = Self.blink(at: t + b.close + b.hold + b.open * 0.8 + lids(0.03...0.07), calm: calm, slow: 0.85, &lids)
                second.depth = 0.92
                filled.append(second)
                blinkCursor = second.start
            }
        }
        blinks = (cued + filled).sorted { $0.start < $1.start }
    }

    static func blink(at t: Double, calm: Bool, slow: Double = 1, _ r: inout MascotRandom) -> MascotBlink {
        let close = r(0.07...0.1) * (calm ? 1.15 : 1) * slow
        return MascotBlink(start: t, close: close, hold: r(0.015...0.045) * slow, open: close * r(1.6...2.1))
    }

    // MARK: Reading (pure in t)

    static let breathCurve = MascotCurve([(0, 0), (0.42, 1), (0.86, 0), (0.93, -0.05), (1, 0)])
    static let followCurve = MascotCurve([(0, 0), (0.62, 1.06), (1, 1)])
    static let browCurve = MascotCurve([(0, 0), (1, 1)])
    static let leanCurve = MascotCurve([(0, 0), (0.6, 1.08), (0.85, 0.98), (1, 1)])
    static let flashCurve = MascotCurve([(0, 0), (0.1, -1.8), (0.34, -1.5), (0.66, 0)])

    func breath(at t: Double) -> Double {
        guard let i = MascotMotion.last(breaths, t, { $0.start }) else { return 0 }
        let b = breaths[i]
        return b.depth * Self.breathCurve((t - b.start) / b.length)
    }

    func gaze(at t: Double) -> SIMD2<Double> {
        guard let k = MascotMotion.last(looks, t, { $0.time }), k > 0 else { return Self.home }
        let from = looks[k - 1].to, to = looks[k].to
        return from + (to - from) * MascotMotion.dart(t - looks[k].time)
    }

    /// Where the body has turned to follow the eyes: it sets off a few frames after a glance and
    /// eases over 0.6 s, overshooting a little.
    func follow(at t: Double) -> SIMD2<Double> { eased(t - 0.09, length: 0.62, Self.followCurve) }

    /// The glances eased over `length` each, overlapping when they come close together.
    private func eased(_ t: Double, length: Double, _ curve: MascotCurve) -> SIMD2<Double> {
        guard var j = MascotMotion.last(glances, t, { $0.time }) else { return Self.home }
        let k = j
        while j > 0, t - glances[j].time < length { j -= 1 }
        var v = glances[j].to
        if j < k { for i in (j + 1)...k { v += (glances[i].to - glances[i - 1].to) * curve((t - glances[i].time) / length) } }
        return v
    }

    /// Brows ride the eyes up and down, a beat behind them.
    func browLook(at t: Double) -> Double { 1.1 * (eased(t - 0.03, length: 0.2, Self.browCurve).y - Self.home.y) }

    /// Weight on one foot (-1 left ... 1 right), eased between shifts.
    func lean(at t: Double) -> Double {
        let length = 1.1
        guard var j = MascotMotion.last(leans, t, { $0.time }) else { return 0 }
        let k = j
        while j > 0, t - leans[j].time < length { j -= 1 }
        var v = leans[j].to
        if j < k { for i in (j + 1)...k { v += (leans[i].to - leans[i - 1].to) * Self.leanCurve((t - leans[i].time) / length) } }
        return v
    }

    /// Brow raise from flashes (negative is up).
    func flash(at t: Double) -> Double {
        guard var i = MascotMotion.last(flashes, t, { $0.time }) else { return 0 }
        var v = 0.0
        while i >= 0, t - flashes[i].time < 0.7 {
            v += flashes[i].size * Self.flashCurve(t - flashes[i].time)
            i -= 1
        }
        return v
    }

    /// Blinks around t, leaving out those `skip` drops.
    func blinks(near t: Double, skip: (Double) -> Bool) -> [MascotBlink] {
        guard var i = MascotMotion.last(blinks, t, { $0.start }) else { return [] }
        var out: [MascotBlink] = []
        while i >= 0, blinks[i].start > t - 2.5 {
            if !skip(blinks[i].start) { out.append(blinks[i]) }
            i -= 1
        }
        return out
    }

    /// The idle body: breathing, drift, weight on one foot, turning after the eyes, fidgets.
    func body(at t: Double, skip: (Double) -> Bool) -> MascotBody {
        let k = calm ? 0.65 : 1.0, n = noiseSeeds
        let breath = self.breath(at: t), late = self.breath(at: t - 0.2)
        let look = follow(at: t) - Self.home, lean = self.lean(at: t)
        var b = fidgets(at: t, skip: skip)
        b.squash += k * (-0.024 * breath + 0.004 * MascotRandom.noise(t / 5.3, n[0])) + 0.008 * look.y
        b.tilt += (calm ? 0.35 : 1) * (0.45 * MascotRandom.noise(t / 6.3, n[1]) + 0.2 * MascotRandom.noise(t / 2.9, n[2]))
            + 1.2 * lean + (calm ? 0.7 : 1.4) * look.x
        b.armLeft += k * (1.6 * late + 1.4 * MascotRandom.noise(t / 4.1, n[3]))
        b.armRight += k * (1.6 * late + 1.4 * MascotRandom.noise(t / 4.7, n[4]))
        // The leg off the weight relaxes outward; the one under it straightens.
        b.legLeft += 2.1 * lean + 0.9 * MascotMotion.soft(lean, 0.1)
        b.legRight += -2.1 * lean + 0.9 * MascotMotion.soft(lean, 0.1)
        return b
    }

    /// The leaf and stem trail the body as each breath lifts and lowers it (the leaf, pointing left,
    /// drags anticlockwise; the stem, leaning right, clockwise), and the leaf lifts a beat after.
    func echo(at t: Double) -> (leaf: Double, stem: Double) {
        let k = calm ? 0.5 : 1.0, now = breath(at: t)
        return (k * (7 * (breath(at: t - 0.35) - now) + 1.2 * breath(at: t - 0.4)),
                k * 2.5 * (now - breath(at: t - 0.15)))
    }

    private func fidgets(at t: Double, skip: (Double) -> Bool) -> MascotBody {
        var b = MascotBody()
        guard let k = MascotMotion.last(moves, t, { $0.start }) else { return b }
        for m in moves[max(0, k - 1)...k] where t - m.start < Self.fidgetLength[m.kind]! && !skip(m.start) {
            b = b + Self.fidget(m.kind, t - m.start, side: m.side) * m.size
        }
        return b
    }

    private static let tapLeg = MascotCurve([(0, 0), (0.12, 13), (0.26, 0), (0.44, 11), (0.58, 0)])
    private static let tapBob = MascotCurve([(0, 0), (0.17, 0), (0.27, 0.012), (0.38, 0), (0.49, 0), (0.59, 0.011), (0.72, 0)])
    private static let tapLean = MascotCurve([(0, 0), (0.18, 0.9), (0.58, 0.9), (0.75, 0)])
    private static let settleArms = MascotCurve([(0, 0), (0.22, 9), (0.5, -2.5), (0.75, 0.8), (1.05, 0)])
    private static let settleSquash = MascotCurve([(0, 0), (0.22, -0.018), (0.48, 0.028), (0.7, -0.006), (1.0, 0)])
    private static let wiggleTilt = MascotCurve([(0, 0), (0.2, 2.2), (0.45, -2.0), (0.7, 1.0), (0.95, -0.3), (1.2, 0)])
    private static let wiggleArms = MascotCurve([(0, 0), (0.22, 6), (0.47, -6), (0.72, 3), (1.2, 0)])
    private static let wiggleBob = MascotCurve([(0, 0), (0.2, 0.012), (0.32, 0), (0.45, 0.012), (0.58, 0), (0.7, 0.008), (0.85, 0)])
    private static let stretchArms = MascotCurve([(0, 0), (0.65, 80), (1.3, 85), (1.85, -4), (2.35, 0)])
    private static let stretchSquash = MascotCurve([(0, 0), (0.65, -0.07), (1.3, -0.075), (1.68, 0.032), (1.98, -0.007), (2.35, 0)])
    private static let stretchTilt = MascotCurve([(0, 0), (0.7, 2.5), (1.3, 3.0), (1.9, 0)])
    private static let peekSquash = MascotCurve([(0, 0), (0.25, 0.014), (0.9, 0.012), (1.2, -0.01), (1.5, 0)])

    private static func fidget(_ kind: Fidget, _ τ: Double, side: Double) -> MascotBody {
        var b = MascotBody()
        switch kind {
        case .shift:
            break
        case .tap:
            if side > 0 { b.legRight = tapLeg(τ) } else { b.legLeft = tapLeg(τ) }
            b.squash = tapBob(τ)
            b.tilt = -side * tapLean(τ)
        case .settle:
            b.armLeft = settleArms(τ)
            b.armRight = settleArms(τ)
            b.squash = settleSquash(τ)
        case .wiggle:
            b.tilt = side * wiggleTilt(τ)
            b.armLeft = side * wiggleArms(τ)
            b.armRight = -side * wiggleArms(τ)
            b.squash = wiggleBob(τ)
        case .stretch:
            b.armLeft = stretchArms(τ)
            b.armRight = stretchArms(τ) * 0.92
            b.squash = stretchSquash(τ)
            b.tilt = side * stretchTilt(τ)
        case .peek:
            b.squash = peekSquash(τ)
        }
        return b
    }
}

// MARK: - Happy

/// Happy: the Happy face over a bouncing two-beat loop (about 111 bpm). Each beat lands in a
/// squash, pushes off through a stretch into a small hop and leans to alternate sides; the arms
/// cheer, the high arm swapping sides each beat, and the leg under it kicks out at the top. The
/// bounce builds in over its first beats and winds down over one more when Idle is cued, starting
/// on a landing; the face swaps under a blink at both ends. Reduce Motion keeps both feet down:
/// the same face and arms on a slow sway with a gentle breathing bob.
struct MascotHappyClip: MascotClip {
    let calm: Bool
    let seed: UInt64

    static let beat = 0.54
    /// Local time of the first landing (the loop's phase 0).
    static let first = 0.2
    static let windDown = beat * 1.25

    var loops: Bool { true }
    var interruptible: Double { 0 }

    /// The landing the wind-down starts from: the first one after Idle is cued.
    func exit(_ off: Double) -> Double {
        let b = Self.beat, k = ((off + 0.05 - Self.first) / b).rounded(.up)
        return Self.first + max(k, 1) * b
    }

    /// Where the face goes back to neutral, under the exit blink.
    func swapBack(_ off: Double) -> Double { exit(off) + Self.windDown - 0.06 }

    func end(off: Double?) -> Double { off.map { swapBack($0) + 0.3 } ?? .infinity }

    func blinks(off: Double?) -> [MascotBlink] {
        // Shut by 0.09, swapped to the Happy face at 0.11; at the end shut across the swap back.
        var b = [MascotBlink(start: 0.02, close: 0.07, hold: 0.05, open: 0.13)]
        if let off { b.append(MascotBlink(start: swapBack(off) - 0.09, close: 0.07, hold: 0.06, open: 0.16)) }
        return b
    }

    // One beat lands at 0, squashes, pushes off through a stretch at 0.32 and lands again at the
    // next beat. Over the two-beat cycle beat 1 leans left with the right arm high and beat 2
    // mirrors it, so the left side reuses the right side's curves a beat later.
    static let cycle = beat * 2
    static let jump = MascotJump(0.32, beat, air: [(0.32, -0.065), (0.43, -0.01), (beat, -0.035)])
    static let ground = MascotCurve([(0, -0.035), (0.07, 0.095), (0.2, 0.02), (0.32, -0.065)],
                                    slopes: [0: jump.landingSlope, 0.32: jump.takeoffSlope])
    static let tilt = MascotLoop(cycle, [(0.13, 0), (0.43, -4), (0.67, 0), (0.97, 4)])
    static let arm = MascotLoop(cycle, [(0.14, 2), (0.43, 88), (0.54, 34), (0.64, 4), (0.97, 36)])
    static let kick = MascotLoop(cycle, [(0.22, 0), (0.43, 12), (0.6, 0), (0.97, -2)])
    static let brow = MascotLoop(beat, [(0.02, 0.5), (0.12, 1.1), (0.34, -0.9), (0.47, -0.6)])
    // Reduce Motion: a slow sway with both feet down.
    static let calmTilt = MascotLoop(2.4, [(0, 0), (0.6, -1.6), (1.2, 0), (1.8, 1.6)])
    static let calmBob = MascotLoop(1.2, [(0, 0.012), (0.6, -0.006)])
    static let calmArm = MascotLoop(2.4, [(0, 14), (0.6, 18), (1.2, 14), (1.8, 10)])

    func pose(at τ: Double, off: Double?) -> MascotClipPose {
        let b = Self.beat, u = τ - Self.first
        var env = MascotMotion.ease(τ / 0.75)
        if let off { env *= 1 - MascotMotion.ease((τ - exit(off)) / Self.windDown) }
        var p = MascotClipPose()
        if calm {
            p.body.tilt = Self.calmTilt(u)
            p.body.squash = Self.calmBob(u)
            p.body.armRight = Self.calmArm(u)
            p.body.armLeft = Self.calmArm(u + 1.2)
            p.brow = -0.4 * Self.calmBob(u) / 0.012 * env
        } else {
            let beatTime = u - (u / b).rounded(.down) * b
            p.body.squash = beatTime < Self.jump.takeoff ? Self.ground(beatTime) : Self.jump.air(beatTime)
            p.body.lift = Self.jump.lift(beatTime)
            p.body.tilt = Self.tilt(u)
            p.body.armRight = Self.arm(u)
            p.body.armLeft = Self.arm(u + b)
            p.body.legRight = Self.kick(u)
            p.body.legLeft = Self.kick(u + b)
            p.brow = Self.brow(u) * env
            // A slow seeded swell in the bounce, so no two cycles are quite alike.
            p.body = p.body * (1 + 0.12 * MascotRandom.noise(τ / 2.3, MascotRandom.hash(seed, 7)))
        }
        p.body = p.body * env
        p.hold = env
        p.browHold = env
        if τ >= 0.11, off.map({ τ < swapBack($0) }) ?? true { p.face = .happy }
        return p
    }
}

// MARK: - Hop

/// Correct-answer hop: 0.85 s of action, back in idle by 1 s. The eyes go first: a blink carries
/// them up to where the hop is headed and opens on the Excited face, wide. The body crouches under
/// them with the arms swung back, springs up through a stretch with the arms flung up, hangs round
/// at the top with the legs kicked out, lands in a squash with the arms flopping, rebounds through a
/// small stretch and settles; a second blink brings the eyes back to the viewer and the face back to
/// neutral as it hands back to idle. Reduce Motion keeps the feet down: the same eyes and face over
/// a soft nod with the arms lifting.
struct MascotHopClip: MascotClip {
    let calm: Bool

    var loops: Bool { false }
    var interruptible: Double { calm ? 0.5 : 0.55 }
    func end(off: Double?) -> Double { calm ? 0.95 : 1.0 }

    static let jump = MascotJump(0.25, 0.55, air: [(0.25, -0.12), (0.4, 0.02), (0.55, -0.06)])
    static let crouch = MascotCurve([(0, 0), (0.16, 0.15), (0.19, 0.155), (0.25, -0.12)], slopes: [0.25: jump.takeoffSlope])
    static let landing = MascotCurve([(0.55, -0.06), (0.605, 0.16), (0.68, -0.06), (0.77, 0.018), (0.87, 0)],
                                     slopes: [0.55: jump.landingSlope])
    static let arm = MascotCurve([(0, 0), (0.15, -22), (0.27, 60), (0.38, 90), (0.52, 50), (0.6, 6), (0.71, 12), (0.86, 0)])
    static let leg = MascotCurve([(0, 0), (0.25, -2), (0.38, 11), (0.53, 2), (0.6, 0)])
    static let tilt = MascotCurve([(0, 0), (0.16, -1.5), (0.4, 2.2), (0.59, -0.8), (0.72, 0.3), (0.88, 0)])
    static let brow = MascotCurve([(0, 0), (0.09, -2.2), (0.45, -1.9), (0.62, -0.6), (0.82, 0)])
    static let wide = MascotCurve([(0.07, 0), (0.14, -0.05), (0.5, -0.04), (0.64, 0)])
    // Reduce Motion: a nod and a lift of the arms, feet down.
    static let calmSquash = MascotCurve([(0, 0), (0.15, 0.05), (0.35, -0.03), (0.5, 0.01), (0.66, 0)])
    static let calmArm = MascotCurve([(0, 0), (0.35, 30), (0.5, 26), (0.78, 0)])
    static let calmTilt = MascotCurve([(0, 0), (0.35, 1.2), (0.7, 0)])

    /// Second blink: shut across the swap back to neutral, with the eyes coming home under it.
    var back: Double { calm ? 0.62 : 0.68 }

    func blinks(off: Double?) -> [MascotBlink] {
        [MascotBlink(start: 0, close: 0.06, hold: 0.03, open: 0.1), MascotBlink(start: back, close: 0.07, hold: 0.04, open: 0.14)]
    }

    func pose(at τ: Double, off: Double?) -> MascotClipPose {
        var p = MascotClipPose()
        if calm {
            p.body.squash = Self.calmSquash(τ)
            p.body.armRight = Self.calmArm(τ)
            p.body.armLeft = Self.calmArm(τ - 0.03) * 0.9
            p.body.tilt = Self.calmTilt(τ)
        } else {
            p.body.squash = τ < Self.jump.takeoff ? Self.crouch(τ) : τ < Self.jump.landing ? Self.jump.air(τ) : Self.landing(τ)
            p.body.lift = Self.jump.lift(τ)
            p.body.armRight = Self.arm(τ)
            p.body.armLeft = Self.arm(τ - 0.025) * 0.92
            p.body.legRight = Self.leg(τ) * 1.2
            p.body.legLeft = Self.leg(τ - 0.02) * 0.8
            p.body.tilt = Self.tilt(τ)
        }
        let release = 1 - MascotMotion.ease((τ - back - 0.05) / 0.25)
        // Takes over across 0.15 s: quick enough to hush idle before the crouch, slow enough to
        // carry on from a hop that is still landing.
        p.hold = MascotMotion.ease(τ / 0.15) * release
        // The eyes dart up under the first blink and home under the second.
        p.gaze = MascotIdleScript.home + SIMD2(0.12, calm ? -0.55 : -1.05)
        p.gazeHold = MascotMotion.dart(τ - 0.035) * (1 - MascotMotion.dart(τ - back - 0.03))
        p.brow = Self.brow(τ) * (calm ? 0.7 : 1)
        p.browHold = MascotMotion.ease(τ / 0.1) * release
        p.eyes = Self.wide(τ) * (calm ? 0.6 : 1)
        if τ >= 0.075, τ < back + 0.085 { p.face = .excited }
        return p
    }
}

// MARK: - Celebrate

/// Milestone celebration: back in idle 3.8 s after its cue (3.4 s calm). A blink carries the eyes up
/// and opens on the Excited face, wide; a deep crouch with the arms swung right back launches a big
/// star jump, arms flung up and legs out. At the top, sparkle bursts pop either side of the head and confetti bursts from behind it.
/// The landing squashes hard, with impact lines at the feet and a squint that swaps to the Happy
/// face; it rebounds into a victory pose that bops three times while the confetti falls, cheering
/// with one arm then the other and both on the last bop (small bursts at the hands), then lowers
/// its arms and blinks back to neutral as it hands back to idle. Reduce Motion keeps the feet down:
/// the arms rise slowly into the same victory pose, the sparkles fade in place rather than pop,
/// and a still sprinkle of confetti fades in and out around the character.
struct MascotCelebrateClip: MascotClip {
    let calm: Bool
    private let confetti: [MascotConfetti.Piece]
    private let sparkles: [(part: MascotPart, at: CGAffineTransform, time: Double)]

    static let jump = MascotJump(0.48, 1.0, air: [(0.48, -0.2), (0.62, -0.05), (0.74, 0.02), (0.88, -0.03), (1.0, -0.08)])
    static let crouch = MascotCurve([(0, 0), (0.36, 0.22), (0.41, 0.225), (0.48, -0.2)], slopes: [0.48: jump.takeoffSlope])
    // The landing, its rebound, three bops in the victory pose, then settling.
    static let ground = MascotCurve([(1.0, -0.08), (1.055, 0.22), (1.16, -0.07), (1.26, 0.03), (1.36, 0), (1.52, 0.05),
                                     (1.64, -0.025), (1.76, 0), (1.97, 0.05), (2.09, -0.025), (2.21, 0), (2.42, 0.05),
                                     (2.54, -0.025), (2.66, 0), (2.95, 0.02), (3.3, 0)], slopes: [1.0: jump.landingSlope])
    // The right arm; the left cheers a bop later, so the high arm alternates and both go up on the last.
    static let arm = MascotCurve([(0, 0), (0.36, -28), (0.5, 62), (0.62, 86), (0.75, 82), (0.9, 86), (1.06, 58), (1.26, 82),
                                  (1.52, 70), (1.64, 85), (1.97, 64), (2.09, 70), (2.42, 72), (2.54, 85), (2.9, 82), (3.35, 0)])
    static let otherArm = MascotCurve([(0, 0), (0.36, -26), (0.52, 60), (0.64, 84), (0.77, 80), (0.92, 85), (1.08, 56), (1.28, 80),
                                       (1.52, 64), (1.64, 70), (1.97, 72), (2.09, 85), (2.42, 72), (2.54, 84), (2.92, 80), (3.38, 0)])
    static let leg = MascotCurve([(0, 0), (0.48, -3), (0.62, 16), (0.86, 16), (0.99, 0)])
    static let tilt = MascotCurve([(0, 0), (0.36, -2.5), (0.7, 5), (0.95, -2.5), (1.16, 1), (1.36, 0), (1.52, -2.5),
                                   (1.97, 2.5), (2.42, -2.5), (2.85, 0)])
    static let brow = MascotCurve([(0, 0), (0.12, -2.6), (0.95, -2.2), (1.15, 0), (1.52, 0.5), (1.64, -0.5), (1.76, 0),
                                   (1.97, 0.5), (2.09, -0.5), (2.21, 0), (2.42, 0.5), (2.54, -0.5), (2.66, 0)])
    static let wide = MascotCurve([(0.08, 0), (0.18, -0.06), (0.95, -0.05), (1.04, 0)])
    // Reduce Motion: arms up slowly into the victory pose, a gentle sway, feet down.
    static let calmArm = MascotCurve([(0, 0), (0.8, 74), (1.2, 78), (2.3, 78), (2.9, 0)])
    static let calmSquash = MascotCurve([(0, 0), (0.6, -0.03), (1.0, 0.01), (1.4, 0), (1.8, 0.012), (2.2, 0)])
    static let calmTilt = MascotCurve([(0, 0), (1.0, 1.2), (1.8, -1.2), (2.6, 0)])
    // A sparkle pops out past its size and settles, then swells away as it fades.
    static let pop = MascotCurve([(0, 0.35), (0.09, 1.12), (0.2, 0.97), (0.3, 1), (0.45, 1.1)])
    static let shine = MascotCurve([(0, 0), (0.04, 1), (0.25, 1), (0.45, 0)])
    static let calmShine = MascotCurve([(0, 0), (0.3, 1), (0.8, 1), (1.3, 0)])

    /// Blinks: the eyes go up under the first, the Happy face comes in under the landing squint,
    /// neutral and the eyes' way home under the last.
    var faces: (excited: Double, happy: Double, neutral: Double) { calm ? (0.075, 0.98, 2.75) : (0.075, 1.08, 3.22) }

    init(calm: Bool, seed: UInt64) {
        self.calm = calm
        // Props are placed where the body is when they appear.
        func at(_ p: SIMD2<Double>, _ τ: Double) -> SIMD2<Double> { MascotPerformance.world(p, Self.body(τ, calm: calm)) }
        func place(_ part: MascotPart, _ p: SIMD2<Double>, _ τ: Double, focus: CGPoint, scale: Double, mirror: Bool) -> (MascotPart, CGAffineTransform, Double) {
            let w = at(p, τ)
            return (part, CGAffineTransform(translationX: w.x, y: w.y).scaledBy(x: mirror ? -scale : scale, y: scale)
                .translatedBy(x: -focus.x, y: -focus.y), τ)
        }
        let three = CGPoint(x: 44, y: 49), two = CGPoint(x: 30, y: 33)
        if calm {
            sparkles = [place(MascotAccessories.sparkleBurstThree, SIMD2(30, 58), 0.5, focus: three, scale: 0.85, mirror: false),
                        place(MascotAccessories.sparkleBurstThree, SIMD2(166, 54), 0.55, focus: three, scale: 0.85, mirror: true)]
            confetti = MascotConfetti.sprinkle(seed: seed)
        } else {
            // Where each hand is on the last bop, for the bursts there.
            let bop = 2.5, b = Self.body(bop, calm: false)
            let handL = MascotPerformance.shoulderLeft + MascotPerformance.rotate(MascotPerformance.handLeft * 1.5, b.armLeft)
            let handR = MascotPerformance.shoulderRight + MascotPerformance.rotate(MascotPerformance.handRight * 1.5, -b.armRight)
            sparkles = [place(MascotAccessories.sparkleBurstThree, SIMD2(30, 58), 0.72, focus: three, scale: 0.9, mirror: false),
                        place(MascotAccessories.sparkleBurstThree, SIMD2(166, 54), 0.76, focus: three, scale: 0.9, mirror: true),
                        place(MascotAccessories.sparkleBurstTwo, SIMD2(54, 196), 1.0, focus: two, scale: 0.7, mirror: false),
                        place(MascotAccessories.sparkleBurstTwo, SIMD2(140, 196), 1.0, focus: two, scale: 0.7, mirror: true),
                        place(MascotAccessories.sparkleBurstTwo, handL + SIMD2(-4, -4), bop, focus: two, scale: 0.7, mirror: false),
                        place(MascotAccessories.sparkleBurstTwo, handR + SIMD2(4, -4), bop, focus: two, scale: 0.7, mirror: true)]
            // From behind the body, and from just above the stem (those in front).
            confetti = MascotConfetti.burst(seed: seed, center: at(SIMD2(97, 110), 0.74), head: at(SIMD2(100, 4), 0.74))
        }
    }

    var loops: Bool { false }
    var interruptible: Double { calm ? 2.7 : 3.0 }
    func end(off: Double?) -> Double { calm ? 3.4 : 3.8 }

    func blinks(off: Double?) -> [MascotBlink] {
        let f = faces
        return [MascotBlink(start: 0, close: 0.06, hold: 0.03, open: 0.12),
                MascotBlink(start: f.happy - 0.08, close: 0.05, hold: 0.07, open: 0.1),
                MascotBlink(start: f.neutral - 0.1, close: 0.07, hold: 0.05, open: 0.14)]
    }

    static func body(_ τ: Double, calm: Bool) -> MascotBody {
        var b = MascotBody()
        if calm {
            b.squash = calmSquash(τ)
            b.armRight = calmArm(τ)
            b.armLeft = calmArm(τ - 0.05) * 0.96
            b.tilt = calmTilt(τ)
        } else {
            b.squash = τ < jump.takeoff ? crouch(τ) : τ < jump.landing ? jump.air(τ) : ground(τ)
            b.lift = jump.lift(τ)
            b.armRight = arm(τ)
            b.armLeft = otherArm(τ)
            b.legRight = leg(τ) * 1.1
            b.legLeft = leg(τ - 0.02) * 0.9
            b.tilt = tilt(τ)
        }
        return b
    }

    func pose(at τ: Double, off: Double?) -> MascotClipPose {
        var p = MascotClipPose()
        let f = faces
        p.body = Self.body(τ, calm: calm)
        let release = 1 - MascotMotion.ease((τ - (calm ? 2.9 : 3.3)) / 0.35)
        p.hold = MascotMotion.ease(τ / 0.15) * release
        p.gaze = MascotIdleScript.home + SIMD2(0.1, calm ? -0.6 : -1.15)
        p.gazeHold = MascotMotion.dart(τ - 0.035) * (1 - MascotMotion.dart(τ - f.neutral + 0.06))
        p.brow = Self.brow(τ) * (calm ? 0.7 : 1)
        p.browHold = MascotMotion.ease(τ / 0.1) * release
        p.eyes = Self.wide(τ) * (calm ? 0.6 : 1)
        p.face = τ < f.excited ? nil : τ < f.happy ? .excited : τ < f.neutral ? .happy : nil
        for s in sparkles where τ >= s.time && τ < s.time + (calm ? 1.3 : 0.45) {
            let age = τ - s.time, scale = calm ? 1 : Self.pop(age)
            let opacity = calm ? Self.calmShine(age) : Self.shine(age)
            guard opacity > 0 else { continue }
            // Scaled about the burst's focus, the point it radiates from.
            let t = CGAffineTransform(scaleX: scale, y: scale).concatenating(s.at)
            p.props.append(MascotProp(kind: .part(s.part), transform: t, opacity: opacity, front: true))
        }
        let age = τ - (calm ? 0.5 : 0.74)
        if age > 0 {
            p.props.append(MascotProp(kind: .confetti(confetti, age: age)))
            p.props.append(MascotProp(kind: .confetti(confetti, age: age), front: true))
        }
        return p
    }
}

// MARK: - Props

/// Something drawn around the character: a sparkle burst (a MascotAccessories part) or confetti.
struct MascotProp {
    enum Kind {
        case part(MascotPart)
        case confetti([MascotConfetti.Piece], age: Double)
    }

    var kind: Kind
    var transform = CGAffineTransform.identity
    var opacity = 1.0
    var front = false

    func draw(in ctx: inout GraphicsContext) {
        switch kind {
        case .part(let part):
            var c = ctx
            c.opacity = opacity
            c.concatenate(transform)
            part.draw(in: &c)
        case .confetti(let pieces, let age):
            MascotConfetti.draw(pieces, age: age, front: front, in: &ctx)
        }
    }
}

/// Confetti: paper bits popped up from behind the character, stopped short by the air within a
/// fifth of a second, then fluttering down slowly while they spin and flip. Each piece is a pure
/// function of its age (linear drag has a closed form), and a frame draws one path per colour.
enum MascotConfetti {
    struct Piece {
        var origin: SIMD2<Double>, velocity: SIMD2<Double>
        var drag: Double, delay: Double, life: Double
        var spin: Double, turn: Double, flip: Double, flipPhase: Double
        var sway: Double, swayRate: Double, swayPhase: Double
        var size: CGSize, round: Bool, ink: Int, front: Bool
        /// Reduce Motion: hangs where it is, drifting down a few points.
        var still = false
    }

    static let inks: [MascotInk] = [.yellow, .blue, .leaf, .pink]
    /// With the drag below, pieces settle to a 50-70 px/s flutter.
    static let gravity = 380.0

    /// Where a piece is (character space), its turn, its flip (-1...1) and its opacity at `age`.
    static func state(_ p: Piece, _ age: Double) -> (point: SIMD2<Double>, turn: Double, flip: Double, opacity: Double) {
        let t = age - p.delay
        guard t > 0, t < p.life else { return (p.origin, 0, 1, 0) }
        var fade = MascotMotion.ease(t / 0.12) * (1 - MascotMotion.ease((t - p.life + 0.45) / 0.45))
        if p.still {
            return (p.origin + SIMD2(0, 7 * t / p.life), p.turn + p.spin * t, 1, fade)
        }
        let k = p.drag, terminal = SIMD2(0, gravity / k)
        var point = p.origin + terminal * t + (p.velocity - terminal) * ((1 - exp(-k * t)) / k)
        point.x += p.sway * (1 - exp(-2 * t)) * sin(p.swayRate * t + p.swayPhase)
        // Nearing the ground, they fade rather than land.
        fade *= 1 - MascotMotion.ease((point.y - 168) / 22)
        return (point, p.turn + p.spin * t, cos(p.flip * t + p.flipPhase), fade)
    }

    /// Opacity steps per colour: fine enough that a fade never shows a step, few enough that a
    /// frame stays a handful of fills.
    static let levels = 16

    static func draw(_ pieces: [Piece], age: Double, front: Bool, in ctx: inout GraphicsContext) {
        var paths = [Path](repeating: Path(), count: inks.count * levels)
        for p in pieces where p.front == front {
            let s = state(p, age)
            let level = Int((s.opacity * Double(levels)).rounded())
            guard level > 0 else { continue }
            let rect = CGRect(x: -p.size.width / 2, y: -p.size.height / 2, width: p.size.width, height: p.size.height)
            let shape = p.round ? Path(ellipseIn: rect) : Path(roundedRect: rect, cornerRadius: p.size.height * 0.3)
            let t = CGAffineTransform(translationX: s.point.x, y: s.point.y).rotated(by: s.turn)
                .scaledBy(x: 1, y: max(abs(s.flip), 0.12) * (s.flip < 0 ? -1 : 1))
            paths[p.ink * levels + level - 1].addPath(shape, transform: t)
        }
        for (i, path) in paths.enumerated() where !path.isEmpty {
            var c = ctx
            c.opacity = Double(i % levels + 1) / Double(levels)
            c.fill(path, with: .color(inks[i / levels].color))
        }
    }

    /// A burst from around `center`: some pieces from behind the body, some from above the head
    /// (those are drawn in front, and go up and out so they never start across the face).
    static func burst(seed: UInt64, center: SIMD2<Double>, head: SIMD2<Double>, count: Int = 58) -> [Piece] {
        var r = MascotRandom(seed, 21)
        let box = MascotRigView.box.insetBy(dx: 9, dy: 9)
        return (0..<count).map { i in
            let front = i % 5 < 2
            let angle = front ? r(-2.7 ... -0.45) : r(-3.0 ... -0.15)
            let speed = front ? r(300...460) : r(340...560)
            var p = Piece(origin: (front ? head : center) + SIMD2(r(-14...14), r(-8...8)),
                          velocity: SIMD2(cos(angle), sin(angle)) * speed,
                          drag: r(5.5...7.5), delay: r(0...0.06), life: r(2.3...2.9),
                          spin: r(3...9) * r.sign(), turn: r(0...6.3), flip: r(6...14), flipPhase: r(0...6.3),
                          sway: r(3...8), swayRate: r(5...8), swayPhase: r(0...6.3),
                          size: r.chance(0.3) ? CGSize(width: 5, height: 5) : CGSize(width: r(6.5...9), height: r(3.2...4.2)),
                          round: r.chance(0.3), ink: Int(r.next() * Double(inks.count)) % inks.count, front: front)
            // Drag caps how far a piece can carry: |v| / drag sideways (plus its flutter) and v / drag
            // upward. Throws that would leave the Canvas box are shortened to stay in it, each to its
            // own height so the spray keeps a ragged top.
            let room = p.velocity.x < 0 ? p.origin.x - box.minX : box.maxX - p.origin.x
            p.velocity.x = max(-1, min(1, p.velocity.x)) * min(abs(p.velocity.x), max(room - p.sway, 0) * p.drag)
            p.velocity.y = max(p.velocity.y, (box.minY + r(0...45) - p.origin.y) * p.drag)
            return p
        }
    }

    /// Reduce Motion: a still sprinkle on an arc over the character (clear of its face and the
    /// ground) that fades in and out.
    static func sprinkle(seed: UInt64, count: Int = 26) -> [Piece] {
        var r = MascotRandom(seed, 22)
        return (0..<count).map { i in
            let a = -3.5 + Double(i) / Double(count - 1) * 3.85 + r(-0.06...0.06), radius = r(94...106)
            let origin = SIMD2(97 + cos(a) * radius, 92 + sin(a) * radius * 0.92)
            return Piece(origin: origin, velocity: .zero, drag: 1, delay: r(0...0.3), life: r(2.0...2.4),
                         spin: r(0.2...0.5) * r.sign(), turn: r(0...6.3), flip: 0, flipPhase: 0,
                         sway: 0, swayRate: 0, swayPhase: 0,
                         size: r.chance(0.3) ? CGSize(width: 5, height: 5) : CGSize(width: r(6.5...9), height: r(3.2...4.2)),
                         round: r.chance(0.3), ink: Int(r.next() * Double(inks.count)) % inks.count, front: false, still: true)
        }
    }
}

// MARK: - Follow-through

/// A point on the leaf, stem or an arm trails where the moving body puts it, like a damped spring
/// with unit gain (so it always settles back). Computed as a tapered FIR over the body's past
/// motion on a fixed 120 Hz grid, so it needs no state carried between frames.
struct MascotSpring {
    static let step = 1.0 / 120
    let kernel: [Double]
    let gain: Double, limit: Double

    init(hz: Double, damping ζ: Double, gain: Double, limit: Double) {
        let ω = 2 * Double.pi * hz, ωd = ω * (1 - ζ * ζ).squareRoot()
        let n = Int(7 / (ζ * ω) / Self.step), taper = n * 3 / 4
        var k = (0..<n).map { exp(-ζ * ω * Double($0) * Self.step) * sin(ωd * Double($0) * Self.step) }
        // Fade the tail, so nothing drops out of the window with a jump.
        for j in taper..<n { k[j] *= 0.5 + 0.5 * cos(Double.pi * Double(j - taper) / Double(n - taper)) }
        let sum = k.reduce(0, +)
        kernel = k.map { $0 / sum }
        self.gain = gain
        self.limit = limit
    }
}

// MARK: - Director

/// A finished frame: the rig pose plus anything drawn around the character.
struct MascotFrame {
    var rig = MascotRigState()
    var props: [MascotProp] = []

    /// Props behind the character, the character, then props in front.
    func draw(in ctx: inout GraphicsContext) {
        for p in props where !p.front { p.draw(in: &ctx) }
        MascotRigRenderer.draw(rig, in: &ctx)
        for p in props where p.front { p.draw(in: &ctx) }
    }
}

/// One performance: a seed and the cued animations. `frame(at:)` is a pure function of those and
/// the time; Reduce Motion plays designed calm versions of everything.
final class MascotDirector {
    let seed: UInt64
    /// Wall-clock time 0, for live use.
    let origin = Date()
    private(set) var cues: [(animation: MascotAnimation, time: Double)] = []
    private var performances: [Bool: MascotPerformance] = [:]

    init(seed: UInt64 = .random(in: 0 ... .max)) { self.seed = seed }

    func time(at date: Date) -> Double { date.timeIntervalSince(origin) }

    /// Cues an animation (default: now). Idle turns Happy off; a one-shot waits until the one
    /// before it reaches a point it can take over from.
    func play(_ animation: MascotAnimation, at time: Double? = nil) {
        let t = time ?? self.time(at: Date())
        cues.insert((animation, t), at: cues.firstIndex { $0.time > t } ?? cues.count)
        for p in performances.values { p.cues = cues }
    }

    func frame(at t: Double, calm: Bool = false) -> MascotFrame { performance(calm).frame(at: t) }

    func performance(_ calm: Bool) -> MascotPerformance {
        if let p = performances[calm] { return p }
        let p = MascotPerformance(seed: seed, calm: calm)
        p.cues = cues
        performances[calm] = p
        return p
    }
}

/// The engine behind MascotDirector for one motion style: the idle script, cues placed as clips,
/// and the follow-through springs.
final class MascotPerformance {
    struct Placed {
        let clip: any MascotClip
        let start: Double, end: Double
        let off: Double?
        let blinks: [MascotBlink]
    }

    let calm: Bool
    let seed: UInt64
    let script: MascotIdleScript
    private(set) var clips: [Placed] = []
    var cues: [(animation: MascotAnimation, time: Double)] = [] {
        didSet { place() }
    }

    init(seed: UInt64, calm: Bool) {
        self.calm = calm
        self.seed = seed
        script = MascotIdleScript(seed: seed, calm: calm)
    }

    /// Turns the cues into placed clips: Happy runs from its cue until Idle is cued; a one-shot
    /// starts when cued, or once the one before it is far enough along to take over from.
    private func place() {
        var placed: [Placed] = [], happyOn: Double?, last: Placed?
        func add(_ clip: any MascotClip, at start: Double, off: Double?) -> Placed {
            let p = Placed(clip: clip, start: start, end: start + clip.end(off: off), off: off, blinks: clip.blinks(off: off))
            placed.append(p)
            return p
        }
        for cue in cues {
            switch cue.animation {
            case .idle:
                if let on = happyOn { _ = add(MascotHappyClip(calm: calm, seed: seed), at: on, off: cue.time - on) }
                happyOn = nil
            case .happy:
                happyOn = happyOn ?? cue.time
            case .hop, .celebrate:
                guard let clip = Self.oneShot(cue.animation, calm: calm, seed: seed) else { continue }
                let start = max(cue.time, last.map { $0.start + $0.clip.interruptible } ?? cue.time)
                last = add(clip, at: start, off: nil)
            }
        }
        if let on = happyOn { _ = add(MascotHappyClip(calm: calm, seed: seed), at: on, off: nil) }
        // Loops lie under one-shots; within each, a later clip lies over an earlier one. Once a clip
        // above has taken over it brings its own blinks, so one underneath starting then is dropped.
        let layered = placed.sorted { ($0.clip.loops ? 0 : 1, $0.start) < ($1.clip.loops ? 0 : 1, $1.start) }
        clips = layered.enumerated().map { i, c in
            let above = layered[(i + 1)...]
            let blinks = c.blinks.filter { b in !above.contains { c.start + b.start >= $0.start && c.start + b.start < $0.end } }
            return Placed(clip: c.clip, start: c.start, end: c.end, off: c.off, blinks: blinks)
        }
        samples = samples.map { var s = $0; s.n = .min; return s }
        outputs = outputs.map { var o = $0; o.n = .min; return o }
    }

    static func oneShot(_ a: MascotAnimation, calm: Bool, seed: UInt64) -> (any MascotClip)? {
        switch a {
        case .hop: MascotHopClip(calm: calm)
        case .celebrate: MascotCelebrateClip(calm: calm, seed: seed)
        default: nil
        }
    }

    /// Idle events (blinks, fidgets) starting around a clip are dropped: the clip brings its own.
    func busy(_ t: Double) -> Bool { clips.contains { t > $0.start - 0.35 && t < $0.end + 0.25 } }

    func frame(at time: Double) -> MascotFrame {
        let t = max(time, 0)
        script.extend(to: t)
        let poses = clips.filter { t >= $0.start && t < $0.end }.map { $0.clip.pose(at: t - $0.start, off: $0.off) }
        let (body, under) = self.body(at: t)
        let follow = followThrough(at: t)

        var look = script.gaze(at: t)
        var brow = script.flash(at: t) + script.browLook(at: t)
        // Overlapping blinks merge smoothly (1 - Π(1 - x) per channel), so nothing stacks or kinks.
        var near = script.blinks(near: t, skip: busy)
        for c in clips {
            for b in c.blinks where b.start + c.start <= t && t - b.start - c.start < 2.5 {
                var b = b
                b.start += c.start
                near.append(b)
            }
        }
        var open = (lid: 1.0, squash: 1.0, stretch: 1.0, brow: 1.0)
        for b in near {
            let s = b.sample(t)
            open = (open.lid * (1 - s.lid), open.squash * (1 - s.squash / 0.085),
                    open.stretch * (1 - s.stretch / 0.045), open.brow * (1 - s.brow / 1.3))
        }
        let lid = 1 - open.lid
        brow += 1.3 * (1 - open.brow)
        var eyes = 0.085 * (1 - open.squash) - 0.045 * (1 - open.stretch)
        var face = AppleFace.Expression.neutral
        for p in poses {
            look += (p.gaze - look) * p.gazeHold
            brow = brow * (1 - p.browHold) + p.brow
            eyes += p.eyes
            if let f = p.face { face = f }
        }
        let echo = script.echo(at: t)

        var r = MascotRigState(expression: face, lookX: look.x, lookY: look.y, blink: lid)
        r.armLeft = body.armLeft + follow.armLeft
        r.armRight = body.armRight + follow.armRight
        r.legLeft = body.legLeft
        r.legRight = body.legRight
        r.tilt = body.tilt
        r.lift = body.lift
        r.squash = body.squash
        r.leafSway = follow.leaf + echo.leaf * under
        r.stemSway = follow.stem + echo.stem * under
        r.browY = brow
        r.eyeSquash = eyes
        return MascotFrame(rig: r, props: poses.flatMap(\.props))
    }

    /// The body before follow-through: idle, then each clip over what lies beneath it; `under` is
    /// how much of idle still shows. A clip's body is filtered over ±12 ms (binomial), so a key
    /// transition sharper than a frame rounds off; lift and squash are filtered alike, so the body's
    /// middle stays as smooth through takeoff and landing as the jump made it.
    func body(at time: Double) -> (body: MascotBody, under: Double) {
        let t = max(time, 0)
        script.extend(to: t)
        var b = script.body(at: t, skip: busy), under = 1.0
        for c in clips where t > c.start - 0.012 && t < c.end + 0.012 {
            var clip = MascotBody(), hold = 0.0
            for (dt, w) in Self.taps {
                let p = c.clip.pose(at: t - c.start + dt, off: c.off)
                clip = clip + p.body * w
                hold += p.hold * w
            }
            b = b * (1 - hold) + clip
            under *= 1 - hold
        }
        b.lift += Self.footLift(b.tilt)
        return (b, under)
    }

    static let taps = [(-0.012, 1.0 / 16), (-0.006, 4.0 / 16), (0, 6.0 / 16), (0.006, 4.0 / 16), (0.012, 1.0 / 16)]

    /// Tilting about the point between the feet would sink one foot; lift the body onto it instead.
    static func footLift(_ tilt: Double) -> Double { 28 * MascotMotion.soft(sin(tilt * .pi / 180), 0.026) }

    // MARK: Follow-through

    static let leafSpring = MascotSpring(hz: 1.5, damping: 0.38, gain: 0.42, limit: 20)
    static let stemSpring = MascotSpring(hz: 3.6, damping: 0.42, gain: 0.5, limit: 10)
    static let armSpring = MascotSpring(hz: 4.5, damping: 0.45, gain: 0.7, limit: 18)

    static func point(_ p: CGPoint) -> SIMD2<Double> { SIMD2(Double(p.x), Double(p.y)) }
    static let ground = point(MascotParts.groundShadow.anchor)
    static let leafPivot = point(MascotParts.leaf.anchor), leafPoint = leafPivot + SIMD2(-25.3, -12.7)
    static let stemPivot = point(MascotParts.stem.anchor), stemPoint = stemPivot + SIMD2(9.7, -23.5)
    static let shoulderLeft = point(MascotParts.armLeft.anchor), shoulderRight = point(MascotParts.armRight.anchor)
    static let handLeft = point(CGPoint(x: MascotParts.armLeft.bounds.midX, y: MascotParts.armLeft.bounds.midY))
    static let handRight = point(CGPoint(x: MascotParts.armRight.bounds.midX, y: MascotParts.armRight.bounds.midY))

    /// A character-space point as the body pose places it (MascotRigRenderer's body transform).
    static func world(_ p: SIMD2<Double>, _ b: MascotBody) -> SIMD2<Double> {
        let a = b.tilt * .pi / 180, c = cos(a), s = sin(a)
        let q = (p - ground) * SIMD2(1 + b.squash * 0.5, 1 - b.squash)
        return ground + SIMD2(q.x * c - q.y * s, q.x * s + q.y * c - b.lift)
    }

    static func rotate(_ v: SIMD2<Double>, _ degrees: Double) -> SIMD2<Double> {
        let a = degrees * .pi / 180
        return SIMD2(v.x * cos(a) - v.y * sin(a), v.x * sin(a) + v.y * cos(a))
    }

    private struct Sample {
        var n = Int.min
        var leaf = SIMD2<Double>(), stem = SIMD2<Double>(), armLeft = SIMD2<Double>(), armRight = SIMD2<Double>()
        var pivots = (leaf: SIMD2<Double>(), stem: SIMD2<Double>(), armLeft: SIMD2<Double>(), armRight: SIMD2<Double>())
    }

    struct Deflection { var n = Int.min; var leaf = 0.0, stem = 0.0, armLeft = 0.0, armRight = 0.0 }

    private var samples = [Sample](repeating: Sample(), count: 1024)
    private var outputs = [Deflection](repeating: Deflection(), count: 1024)

    private func sample(_ n: Int) -> Sample {
        let i = n & 1023
        if samples[i].n == n { return samples[i] }
        let b = body(at: Double(n) * MascotSpring.step).body
        var s = Sample(n: n)
        s.leaf = Self.world(Self.leafPoint, b)
        s.stem = Self.world(Self.stemPoint, b)
        s.armLeft = Self.world(Self.shoulderLeft + Self.rotate(Self.handLeft, b.armLeft), b)
        s.armRight = Self.world(Self.shoulderRight + Self.rotate(Self.handRight, -b.armRight), b)
        s.pivots = (Self.world(Self.leafPivot, b), Self.world(Self.stemPivot, b),
                    Self.world(Self.shoulderLeft, b), Self.world(Self.shoulderRight, b))
        samples[i] = s
        return s
    }

    /// Spring deflections (degrees) at grid step n.
    private func deflection(_ n: Int) -> Deflection {
        let i = n & 1023
        if outputs[i].n == n { return outputs[i] }
        func angle(_ spring: MascotSpring, _ target: (Sample) -> SIMD2<Double>, _ pivot: SIMD2<Double>) -> Double {
            var tip = SIMD2<Double>()
            for (j, k) in spring.kernel.enumerated() { tip += k * target(sample(n - j)) }
            let now = target(sample(n)), r = now - pivot, d = tip - now
            let θ = (r.x * d.y - r.y * d.x) / (r.x * r.x + r.y * r.y) * 180 / .pi * spring.gain
            return spring.limit * tanh(θ / spring.limit)
        }
        let p = sample(n).pivots
        let o = Deflection(n: n,
                           leaf: angle(Self.leafSpring, { $0.leaf }, p.leaf),
                           stem: angle(Self.stemSpring, { $0.stem }, p.stem),
                           armLeft: angle(Self.armSpring, { $0.armLeft }, p.armLeft),
                           armRight: -angle(Self.armSpring, { $0.armRight }, p.armRight))
        outputs[i] = o
        return o
    }

    /// Spring deflections at any time: Catmull-Rom through the grid steps around it.
    func followThrough(at t: Double) -> Deflection {
        let x = t / MascotSpring.step, n = Int(x.rounded(.down)), f = x - Double(n)
        let a = deflection(n - 1), b = deflection(n), c = deflection(n + 1), d = deflection(n + 2)
        func cr(_ p0: Double, _ p1: Double, _ p2: Double, _ p3: Double) -> Double {
            p1 + 0.5 * f * (p2 - p0 + f * (2 * p0 - 5 * p1 + 4 * p2 - p3 + f * (3 * (p1 - p2) + p3 - p0)))
        }
        return Deflection(n: n, leaf: cr(a.leaf, b.leaf, c.leaf, d.leaf), stem: cr(a.stem, b.stem, c.stem, d.stem),
                          armLeft: cr(a.armLeft, b.armLeft, c.armLeft, d.armLeft),
                          armRight: cr(a.armRight, b.armRight, c.armRight, d.armRight))
    }
}

// MARK: - View

/// The animated mascot: one TimelineView driving one Canvas, in MascotRigView's box.
struct MascotAnimatedView: View {
    let director: MascotDirector
    /// Performance time for a frame's date (the playground's playhead); nil runs live.
    var clock: ((Date) -> Double)? = nil
    var paused = false
    /// Overrides the system Reduce Motion setting (playground); nil follows it.
    var calm: Bool? = nil

    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    var body: some View {
        let box = MascotRigView.box
        TimelineView(.animation(paused: paused)) { context in
            Canvas { ctx, canvas in
                let t = clock?(context.date) ?? director.time(at: context.date)
                let frame = director.frame(at: t, calm: calm ?? reduceMotion)
                let s = min(canvas.width / box.width, canvas.height / box.height)
                ctx.translateBy(x: (canvas.width - box.width * s) / 2, y: (canvas.height - box.height * s) / 2)
                ctx.scaleBy(x: s, y: s)
                ctx.translateBy(x: -box.minX, y: -box.minY)
                frame.draw(in: &ctx)
            }
        }
        .aspectRatio(box.size, contentMode: .fit)
    }
}

/// Animation review: pick an animation, play / pause, scrub. Each animation is cued 0.5 s into
/// every cycle of one continuous timeline over live idle, so looping playback never jumps; the
/// scrubber moves within the current cycle.
struct MascotAnimationPlayground: View {
    @State private var animation = MascotAnimation.idle
    @State private var director = MascotAnimationPlayground.director(for: .idle)
    @State private var playing = true
    /// Performance time at `anchor`; while playing it runs on from there.
    @State private var playhead = 0.0
    @State private var anchor = Date()
    @State private var calm = false
    @State private var slow = false

    private static func length(of animation: MascotAnimation) -> Double {
        switch animation {
        case .idle: 60
        case .happy: 8.5
        case .hop: 2.5
        case .celebrate: 5.5
        }
    }

    private var length: Double { Self.length(of: animation) }

    /// Half an hour of cycles.
    private static func director(for animation: MascotAnimation) -> MascotDirector {
        let d = MascotDirector(seed: 7), length = length(of: animation)
        guard animation != .idle else { return d }
        for k in 0..<Int(1800 / length) {
            let t = Double(k) * length
            if animation == .happy {
                d.play(.happy, at: t + 0.5)
                d.play(.idle, at: t + 6.3)
            } else {
                d.play(animation, at: t + 0.5)
            }
        }
        return d
    }

    private func time(at date: Date) -> Double {
        guard playing else { return playhead }
        return playhead + date.timeIntervalSince(anchor) * (slow ? 0.25 : 1)
    }

    private func cycleStart(_ t: Double) -> Double { (t / length).rounded(.down) * length }

    var body: some View {
        VStack(spacing: 0) {
            MascotAnimatedView(director: director, clock: { time(at: $0) }, paused: !playing, calm: calm)
                .frame(maxWidth: .infinity)
                .frame(height: 320)
                .padding(.vertical, 8)
            Divider()
            controls.padding(16)
            Spacer(minLength: 0)
        }
        .background(MascotPalette.background.ignoresSafeArea())
    }

    private var controls: some View {
        VStack(alignment: .leading, spacing: 12) {
            Picker("Animation", selection: Binding(get: { animation }, set: { select($0) })) {
                ForEach(MascotAnimation.allCases) { Text($0.title).tag($0) }
            }
            .pickerStyle(.segmented)
            HStack(spacing: 10) {
                Button { toggle() } label: { Image(systemName: playing ? "pause.fill" : "play.fill").frame(width: 24) }
                    .buttonStyle(.bordered)
                // Only the scrubber follows the playhead every frame.
                TimelineView(.animation(paused: !playing)) { context in
                    let t = time(at: context.date), local = t - cycleStart(t)
                    HStack(spacing: 10) {
                        Slider(value: Binding(get: { local }, set: { scrub(to: $0) }), in: 0...length)
                        Text(String(format: "%5.2f s", local))
                            .font(.system(size: 13, weight: .medium, design: .monospaced))
                            .foregroundStyle(MascotPalette.details)
                    }
                }
            }
            Toggle("Reduce Motion version", isOn: $calm)
            Toggle("Quarter speed", isOn: Binding(get: { slow }, set: { s in rebase(); slow = s }))
        }
        .font(.system(size: 13, weight: .medium, design: .rounded))
        .foregroundStyle(MascotPalette.details)
        .tint(MascotPalette.appleRed)
    }

    private func select(_ a: MascotAnimation) {
        animation = a
        director = Self.director(for: a)
        playhead = 0
        anchor = Date()
    }

    private func toggle() {
        rebase()
        playing.toggle()
    }

    private func scrub(to t: Double) {
        let now = time(at: Date())
        playing = false
        playhead = cycleStart(now) + min(t, length - 0.001)
    }

    private func rebase() {
        playhead = time(at: Date())
        anchor = Date()
    }
}

#Preview("Animation") {
    MascotAnimationPlayground()
}
