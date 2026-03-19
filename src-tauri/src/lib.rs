use std::sync::Mutex;

/// Holds the sidecar child process handle so we can kill it on app close.
pub struct SidecarState {
    pub child: Mutex<Option<std::process::Child>>,
    pub port: Mutex<u16>,
}

impl SidecarState {
    pub fn new() -> Self {
        Self {
            child: Mutex::new(None),
            port: Mutex::new(0),
        }
    }
}
