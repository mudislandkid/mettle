fn main() {
    // The updater PAT is read via option_env! in lib.rs at compile time;
    // tell cargo to rebuild that crate when the env value changes so a
    // rotated token actually lands in the binary.
    println!("cargo:rerun-if-env-changed=METTLE_UPDATER_PAT");
    tauri_build::build()
}
