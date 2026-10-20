// Original DragShift presets for FFglitch 0.10.2's motion-vector API.
// Only the bridge is modified. The recovery I-frame is left untouched.
let index = 0;
let options;
let held;
export function setup(args) {
    args.features = ["mv"];
    options = args.params;
}
export function glitch_frame(frame) {
    const n = index++;
    const vectors = frame.mv?.forward;
    if (!vectors || n < options.start || n >= options.end) return;
    frame.mv.overflow = "truncate";
    const amount = options.strength / 100;
    const phase = (n - options.start) / Math.max(1, options.end - options.start);
    const envelope = Math.sin(Math.PI * Math.min(.98, phase + .1));
    if (options.preset === "Bloom" && (!held || (n - options.start) % 8 === 0))
        held = vectors.dup();
    for (let y = 0; y < vectors.length; y++) {
        const row = vectors[y];
        for (let x = 0; x < row.length; x++) {
            const mv = row[x];
            let dx = mv[0], dy = mv[1];
            if (options.preset === "Bloom") {
                dx = held[y][x][0] * (1 + amount * 3) + (x - row.length / 2) * amount * .4;
                dy = held[y][x][1] * (1 + amount * 3) + (y - vectors.length / 2) * amount * .4;
            } else if (options.preset === "Fluid") {
                dx = dx * (1 + amount) + Math.sin(y * .3 + phase * 10) * amount * 20 * envelope;
                dy = dy * (1 + amount) + Math.cos(x * .3 + phase * 8) * amount * 16 * envelope;
            } else if (options.preset === "Psychedelic") {
                dx = dx * (1 + amount * 3) + Math.sin(y * .45 + phase * 18) * amount * 42 * envelope;
                dy = dy * (1 + amount * 3) + Math.cos(x * .45 - phase * 15) * amount * 42 * envelope;
            } else {
                dx = dx * (1 + amount * 2) + amount * 5 * envelope;
                dy = dy * (1 + amount * 2) - amount * 3 * envelope;
            }
            mv[0] = Math.round(dx);
            mv[1] = Math.round(dy);
        }
    }
}
